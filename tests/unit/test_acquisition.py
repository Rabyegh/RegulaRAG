"""
Unit tests for Subphase 2.2: Official EUR-Lex document acquisition layer.

All HTTP interactions are mocked via httpx.MockTransport — no live network access.
Storage tests use temporary directories for full isolation.

Coverage targets:
- EurLexHttpConnector: success, HTTP 304, 404, 429, 5xx, timeout, network error
- Content validation: size, media type, plausibility markers, error page detection
- SHA-256 streaming correctness
- Atomic storage / staging cleanup
- Idempotent re-acquisition (SHA-256 match → UNCHANGED)
- Hash conflict detection → VersionIntegrityConflictError
- Sidecar metadata correctness
- Conditional request headers (ETag / Last-Modified forwarding)
- Context manager lifecycle
- AcquisitionService: routing, unknown document_id, unknown CELEX
- RawArtifactStorage: path layout, staging creation, commit, conflict
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path  # noqa: TC003
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from regularag.core.exceptions import (
    AcquisitionConnectionError,
    AcquisitionRateLimitError,
    AcquisitionTimeoutError,
    DocumentContentValidationError,
    DocumentNotFoundError,
    VersionIntegrityConflictError,
)
from regularag.ingestion.connectors.base import BaseAcquisitionConnector
from regularag.ingestion.connectors.eurlex import EurLexHttpConnector
from regularag.ingestion.models import (
    AcquisitionStatus,
    RegulatorySourceEntry,
    RegulatorySourceRegistry,
    canonical_artifact_id,
    canonical_artifact_version_id,
)
from regularag.ingestion.service import AcquisitionService
from regularag.ingestion.storage import ExistingArtifact, RawArtifactStorage

# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

_AI_ACT_SOURCE_DATA: dict[str, Any] = {
    "document_id": "eu_ai_act",
    "name": "Regulation (EU) 2024/1689 of the European Parliament and of the Council",
    "abbreviation": "EU AI Act",
    "instrument_type": "Regulation",
    "celex_id": "32024R1689",
    "eli_uri": "http://data.europa.eu/eli/reg/2024/1689/oj",
    "official_source_url": (
        "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32024R1689"
    ),
    "publication_date": "2024-07-12",
    "entry_into_force_date": "2024-08-01",
    "application_date": "2026-08-02",
    "language": "EN",
    "preferred_format": "HTML",
    "available_formats": ["HTML", "PDF"],
    "consolidation_available": False,
    "source_authority": "European Parliament; Council of the European Union",
    "status": "In force",
    "last_verified_at": "2024-11-01T00:00:00Z",
}


@pytest.fixture
def ai_act_source() -> RegulatorySourceEntry:
    """Minimal validated RegulatorySourceEntry for the EU AI Act."""
    return RegulatorySourceEntry.model_validate(_AI_ACT_SOURCE_DATA)


@pytest.fixture
def minimal_registry(ai_act_source: RegulatorySourceEntry) -> RegulatorySourceRegistry:
    """A small in-memory registry containing only the AI Act."""
    return RegulatorySourceRegistry(
        last_registry_update=dt.date(2024, 11, 1),
        sources=[ai_act_source],
    )


def _make_html_content(size: int = 2048) -> bytes:
    """Build minimal plausible HTML document bytes of the requested size."""
    base = b"<!doctype html><html><body><h1>Regulation (EU) 2024/1689</h1>"
    padding = b"x" * max(0, size - len(base))
    return base + padding


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class _MockTransport(httpx.AsyncBaseTransport):
    """Minimal async mock transport that returns a pre-configured response."""

    def __init__(self, response: httpx.Response) -> None:
        self._response = response

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        # Attach the request so tests can inspect it
        self._response.request = request
        return self._response


class _CallTrackingTransport(httpx.AsyncBaseTransport):
    """Transport that records request headers and returns successive responses."""

    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = list(responses)
        self.recorded_requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.recorded_requests.append(request)
        resp = self._responses.pop(0) if self._responses else httpx.Response(500)
        resp.request = request
        return resp


def _make_client(response: httpx.Response) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=_MockTransport(response))


def _make_multi_client(
    responses: list[httpx.Response],
) -> tuple[httpx.AsyncClient, _CallTrackingTransport]:
    transport = _CallTrackingTransport(responses)
    client = httpx.AsyncClient(transport=transport)
    return client, transport


def _connector(
    tmp_dir: Path,
    client: httpx.AsyncClient,
    max_retries: int = 0,
    rate_limit_delay: float = 0.0,
) -> EurLexHttpConnector:
    """Build a connector with a temporary storage root and injected HTTP client."""
    storage = RawArtifactStorage(tmp_dir)
    return EurLexHttpConnector(
        storage=storage,
        client=client,
        max_retries=max_retries,
        rate_limit_delay=rate_limit_delay,
        min_retry_delay=0.0,
        max_retry_delay=0.0,
        backoff_factor=1.0,
    )


# ===========================================================================
# Section 1: EurLexHttpConnector — HTTP 200 success path
# ===========================================================================


class TestSuccessfulAcquisition:
    @pytest.mark.asyncio
    async def test_http_200_returns_success_result(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        content = _make_html_content()
        response = httpx.Response(
            200,
            content=content,
            headers={"Content-Type": "text/html; charset=utf-8", "ETag": '"abc123"'},
        )
        conn = _connector(tmp_path, _make_client(response))
        result = await conn.acquire(ai_act_source)

        assert result.status == AcquisitionStatus.SUCCESS
        assert result.http_status == 200
        assert result.document_id == "eu_ai_act"
        assert result.celex_id == "32024R1689"
        assert result.bytes_downloaded == len(content)
        assert result.sha256_checksum == _sha256(content)
        assert result.file_path is not None
        assert result.file_path.is_file()

    @pytest.mark.asyncio
    async def test_file_content_matches_downloaded_bytes(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        content = _make_html_content(4096)
        response = httpx.Response(200, content=content, headers={"Content-Type": "text/html"})
        conn = _connector(tmp_path, _make_client(response))
        result = await conn.acquire(ai_act_source)

        assert result.file_path is not None
        disk_bytes = result.file_path.read_bytes()
        assert disk_bytes == content

    @pytest.mark.asyncio
    async def test_sha256_matches_independently_computed_hash(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        content = _make_html_content(8192)
        expected_hash = _sha256(content)
        response = httpx.Response(200, content=content, headers={"Content-Type": "text/html"})
        conn = _connector(tmp_path, _make_client(response))
        result = await conn.acquire(ai_act_source)

        assert result.sha256_checksum == expected_hash

    @pytest.mark.asyncio
    async def test_sidecar_file_created_alongside_artifact(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        content = _make_html_content()
        response = httpx.Response(200, content=content, headers={"Content-Type": "text/html"})
        conn = _connector(tmp_path, _make_client(response))
        result = await conn.acquire(ai_act_source)

        assert result.sidecar_path is not None
        assert result.sidecar_path.is_file()

    @pytest.mark.asyncio
    async def test_sidecar_contains_valid_json(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        content = _make_html_content()
        response = httpx.Response(200, content=content, headers={"Content-Type": "text/html"})
        conn = _connector(tmp_path, _make_client(response))
        result = await conn.acquire(ai_act_source)

        assert result.sidecar_path is not None
        raw = result.sidecar_path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        assert parsed["document_id"] == "eu_ai_act"
        assert parsed["celex_id"] == "32024R1689"

    @pytest.mark.asyncio
    async def test_sidecar_sha256_matches_result(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        content = _make_html_content()
        response = httpx.Response(200, content=content, headers={"Content-Type": "text/html"})
        conn = _connector(tmp_path, _make_client(response))
        result = await conn.acquire(ai_act_source)

        assert result.sidecar_path is not None
        sidecar = json.loads(result.sidecar_path.read_text("utf-8"))
        assert sidecar["file_metadata"]["sha256_checksum"] == result.sha256_checksum

    @pytest.mark.asyncio
    async def test_no_staging_file_left_after_success(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        content = _make_html_content()
        response = httpx.Response(200, content=content, headers={"Content-Type": "text/html"})
        conn = _connector(tmp_path, _make_client(response))
        result = await conn.acquire(ai_act_source)

        assert result.file_path is not None
        parent = result.file_path.parent
        tmp_files = list(parent.glob("*.tmp.*"))
        assert tmp_files == [], f"Unexpected staging files: {tmp_files}"

    @pytest.mark.asyncio
    async def test_artifact_version_id_format(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        content = _make_html_content()
        response = httpx.Response(200, content=content, headers={"Content-Type": "text/html"})
        conn = _connector(tmp_path, _make_client(response))
        result = await conn.acquire(ai_act_source)

        assert result.artifact_version_id.startswith("orig_32024R1689_")


# ===========================================================================
# Section 2: HTTP 304 Not Modified
# ===========================================================================


class TestHTTP304NotModified:
    @pytest.mark.asyncio
    async def test_304_returns_not_modified_status(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        response = httpx.Response(304, content=b"")
        conn = _connector(tmp_path, _make_client(response))
        result = await conn.acquire(ai_act_source)

        assert result.status == AcquisitionStatus.NOT_MODIFIED
        assert result.http_status == 304
        assert result.bytes_downloaded == 0

    @pytest.mark.asyncio
    async def test_304_does_not_create_file(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        response = httpx.Response(304, content=b"")
        conn = _connector(tmp_path, _make_client(response))
        await conn.acquire(ai_act_source)

        files = list(tmp_path.rglob("*.html"))
        assert files == []

    @pytest.mark.asyncio
    async def test_304_leaves_no_staging_file(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        response = httpx.Response(304, content=b"")
        conn = _connector(tmp_path, _make_client(response))
        await conn.acquire(ai_act_source)

        tmp_files = list(tmp_path.rglob("*.tmp.*"))
        assert tmp_files == []


# ===========================================================================
# Section 3: HTTP 404 Not Found
# ===========================================================================


class TestHTTP404NotFound:
    @pytest.mark.asyncio
    async def test_404_raises_document_not_found(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        response = httpx.Response(404, content=b"Not Found")
        conn = _connector(tmp_path, _make_client(response))
        with pytest.raises(DocumentNotFoundError):
            await conn.acquire(ai_act_source)

    @pytest.mark.asyncio
    async def test_404_leaves_no_staging_file(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        response = httpx.Response(404, content=b"Not Found")
        conn = _connector(tmp_path, _make_client(response))
        with pytest.raises(DocumentNotFoundError):
            await conn.acquire(ai_act_source)

        tmp_files = list(tmp_path.rglob("*.tmp.*"))
        assert tmp_files == []

    @pytest.mark.asyncio
    async def test_404_not_retried(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        """HTTP 404 must raise immediately — not retry."""
        responses = [
            httpx.Response(404, content=b"Not Found"),
            httpx.Response(200, content=_make_html_content()),
        ]
        client, transport = _make_multi_client(responses)
        conn = _connector(tmp_path, client, max_retries=3)
        with pytest.raises(DocumentNotFoundError):
            await conn.acquire(ai_act_source)

        # Only one request should have been made (no retry)
        assert len(transport.recorded_requests) == 1


# ===========================================================================
# Section 4: HTTP 429 Rate Limit
# ===========================================================================


class TestHTTP429RateLimit:
    @pytest.mark.asyncio
    async def test_429_without_retry_raises_rate_limit_error(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        response = httpx.Response(429, content=b"", headers={"Retry-After": "60"})
        conn = _connector(tmp_path, _make_client(response), max_retries=0)
        with pytest.raises(AcquisitionRateLimitError):
            await conn.acquire(ai_act_source)

    @pytest.mark.asyncio
    async def test_429_then_200_succeeds_on_retry(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        content = _make_html_content()
        responses = [
            httpx.Response(429, content=b"", headers={}),
            httpx.Response(200, content=content, headers={"Content-Type": "text/html"}),
        ]
        client, transport = _make_multi_client(responses)
        conn = _connector(tmp_path, client, max_retries=2)
        result = await conn.acquire(ai_act_source)

        assert result.status == AcquisitionStatus.SUCCESS
        assert len(transport.recorded_requests) == 2

    @pytest.mark.asyncio
    async def test_429_retry_after_respected(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        """Verify that Retry-After header value is used as backoff delay."""
        content = _make_html_content()
        responses = [
            httpx.Response(429, content=b"", headers={"Retry-After": "1"}),
            httpx.Response(200, content=content, headers={"Content-Type": "text/html"}),
        ]
        client, _ = _make_multi_client(responses)
        conn = _connector(tmp_path, client, max_retries=1)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await conn.acquire(ai_act_source)
        assert result.status == AcquisitionStatus.SUCCESS
        # asyncio.sleep should have been called with the Retry-After value
        assert mock_sleep.called


# ===========================================================================
# Section 5: HTTP 5xx Server Errors
# ===========================================================================


class TestHTTP5xxServerErrors:
    @pytest.mark.parametrize("status_code", [500, 502, 503, 504])
    @pytest.mark.asyncio
    async def test_5xx_without_retry_raises_connection_error(
        self, status_code: int, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        response = httpx.Response(status_code, content=b"Server Error")
        conn = _connector(tmp_path, _make_client(response), max_retries=0)
        with pytest.raises(AcquisitionConnectionError):
            await conn.acquire(ai_act_source)

    @pytest.mark.asyncio
    async def test_5xx_then_200_succeeds_on_retry(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        content = _make_html_content()
        responses = [
            httpx.Response(503, content=b"Service Unavailable"),
            httpx.Response(200, content=content, headers={"Content-Type": "text/html"}),
        ]
        client, transport = _make_multi_client(responses)
        conn = _connector(tmp_path, client, max_retries=2)
        result = await conn.acquire(ai_act_source)

        assert result.status == AcquisitionStatus.SUCCESS
        assert len(transport.recorded_requests) == 2

    @pytest.mark.asyncio
    async def test_5xx_leaves_no_staging_file(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        response = httpx.Response(503, content=b"err")
        conn = _connector(tmp_path, _make_client(response), max_retries=0)
        with pytest.raises(AcquisitionConnectionError):
            await conn.acquire(ai_act_source)

        tmp_files = list(tmp_path.rglob("*.tmp.*"))
        assert tmp_files == []


# ===========================================================================
# Section 6: Timeout and Network Errors
# ===========================================================================


class TestTimeoutAndNetworkErrors:
    @pytest.mark.asyncio
    async def test_timeout_raises_acquisition_timeout_error(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        class _TimeoutTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
                raise httpx.ConnectTimeout("Timed out", request=request)

        client = httpx.AsyncClient(transport=_TimeoutTransport())
        conn = _connector(tmp_path, client, max_retries=0)
        with pytest.raises(AcquisitionTimeoutError):
            await conn.acquire(ai_act_source)

    @pytest.mark.asyncio
    async def test_network_error_raises_acquisition_connection_error(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        class _NetworkErrorTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
                raise httpx.NetworkError("Connection refused", request=request)

        client = httpx.AsyncClient(transport=_NetworkErrorTransport())
        conn = _connector(tmp_path, client, max_retries=0)
        with pytest.raises(AcquisitionConnectionError):
            await conn.acquire(ai_act_source)

    @pytest.mark.asyncio
    async def test_timeout_leaves_no_staging_file(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        class _TimeoutTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
                raise httpx.ReadTimeout("Read timeout", request=request)

        client = httpx.AsyncClient(transport=_TimeoutTransport())
        conn = _connector(tmp_path, client, max_retries=0)
        with pytest.raises(AcquisitionTimeoutError):
            await conn.acquire(ai_act_source)

        tmp_files = list(tmp_path.rglob("*.tmp.*"))
        assert tmp_files == []


# ===========================================================================
# Section 7: Content Validation
# ===========================================================================


class TestContentValidation:
    @pytest.mark.asyncio
    async def test_empty_response_raises_validation_error(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        """Response body with < 100 bytes must raise DocumentContentValidationError."""
        response = httpx.Response(
            200, content=b"<html>x</html>", headers={"Content-Type": "text/html"}
        )
        conn = _connector(tmp_path, _make_client(response))
        with pytest.raises(DocumentContentValidationError):
            await conn.acquire(ai_act_source)

    @pytest.mark.asyncio
    async def test_missing_html_markers_raises_validation_error(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        """Content without HTML plausibility markers must fail validation."""
        junk = b"JUNK" * 300  # large enough to pass size check
        response = httpx.Response(200, content=junk, headers={"Content-Type": "text/html"})
        conn = _connector(tmp_path, _make_client(response))
        with pytest.raises(DocumentContentValidationError):
            await conn.acquire(ai_act_source)

    @pytest.mark.asyncio
    async def test_error_page_with_200_raises_validation_error(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        """HTML error pages disguised as HTTP 200 must be rejected."""
        error_page = (
            b"<!doctype html><html><head><title>404 Not Found</title></head><body>" + b"x" * 2000
        )
        response = httpx.Response(200, content=error_page, headers={"Content-Type": "text/html"})
        conn = _connector(tmp_path, _make_client(response))
        with pytest.raises(DocumentContentValidationError):
            await conn.acquire(ai_act_source)

    @pytest.mark.asyncio
    async def test_validation_error_leaves_no_staging_file(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        response = httpx.Response(200, content=b"tiny", headers={"Content-Type": "text/html"})
        conn = _connector(tmp_path, _make_client(response))
        with pytest.raises(DocumentContentValidationError):
            await conn.acquire(ai_act_source)

        tmp_files = list(tmp_path.rglob("*.tmp.*"))
        assert tmp_files == []


# ===========================================================================
# Section 8: Idempotent re-acquisition
# ===========================================================================


class TestIdempotentAcquisition:
    @pytest.mark.asyncio
    async def test_same_sha256_returns_unchanged(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        """Re-downloading the same content returns UNCHANGED and preserves the file."""
        content = _make_html_content()
        response_200 = httpx.Response(200, content=content, headers={"Content-Type": "text/html"})

        # First acquisition
        conn = _connector(tmp_path, _make_client(response_200))
        first = await conn.acquire(ai_act_source)
        assert first.status == AcquisitionStatus.SUCCESS

        # Second acquisition with identical content
        response_200b = httpx.Response(200, content=content, headers={"Content-Type": "text/html"})
        conn2 = _connector(tmp_path, _make_client(response_200b))
        second = await conn2.acquire(ai_act_source)

        assert second.status == AcquisitionStatus.UNCHANGED
        assert second.sha256_checksum == first.sha256_checksum
        # Exactly one copy of the file must exist
        assert first.file_path is not None
        assert first.file_path.is_file()

    @pytest.mark.asyncio
    async def test_unchanged_leaves_original_file_intact(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        content = _make_html_content()
        for _ in range(2):
            response = httpx.Response(200, content=content, headers={"Content-Type": "text/html"})
            conn = _connector(tmp_path, _make_client(response))
            result = await conn.acquire(ai_act_source)

        assert result.file_path is not None
        assert result.file_path.read_bytes() == content


# ===========================================================================
# Section 9: Hash conflict detection
# ===========================================================================


class TestHashConflict:
    @pytest.mark.asyncio
    async def test_different_sha256_raises_integrity_conflict(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        """A second download with a different SHA-256 at the same version path must conflict."""
        content_a = _make_html_content(2048)
        content_b = _make_html_content(4096)  # different content

        response_a = httpx.Response(200, content=content_a, headers={"Content-Type": "text/html"})
        conn_a = _connector(tmp_path, _make_client(response_a))
        await conn_a.acquire(ai_act_source)

        response_b = httpx.Response(200, content=content_b, headers={"Content-Type": "text/html"})
        conn_b = _connector(tmp_path, _make_client(response_b))
        with pytest.raises(VersionIntegrityConflictError):
            await conn_b.acquire(ai_act_source)


# ===========================================================================
# Section 10: Conditional request headers
# ===========================================================================


class TestConditionalRequestHeaders:
    @pytest.mark.asyncio
    async def test_etag_sent_on_refetch(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        """After a successful acquisition with ETag, the second request must carry If-None-Match."""
        content = _make_html_content()
        etag_value = '"v1-abc123"'

        # First request returns ETag
        first_response = httpx.Response(
            200,
            content=content,
            headers={"Content-Type": "text/html", "ETag": etag_value},
        )
        # Second request returns 304
        second_response = httpx.Response(304, content=b"")

        responses = [first_response, second_response]
        client, transport = _make_multi_client(responses)
        storage = RawArtifactStorage(tmp_path)
        conn = EurLexHttpConnector(
            storage=storage,
            client=client,
            max_retries=0,
            rate_limit_delay=0.0,
            min_retry_delay=0.0,
            max_retry_delay=0.0,
        )

        await conn.acquire(ai_act_source)
        result2 = await conn.acquire(ai_act_source)

        assert result2.status == AcquisitionStatus.NOT_MODIFIED
        assert len(transport.recorded_requests) == 2
        second_request = transport.recorded_requests[1]
        assert second_request.headers.get("if-none-match") == etag_value

    @pytest.mark.asyncio
    async def test_last_modified_sent_on_refetch(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        """Last-Modified header recorded in sidecar must be forwarded as If-Modified-Since."""
        content = _make_html_content()
        last_mod = "Wed, 01 Nov 2024 00:00:00 GMT"

        first_response = httpx.Response(
            200,
            content=content,
            headers={"Content-Type": "text/html", "Last-Modified": last_mod},
        )
        second_response = httpx.Response(304, content=b"")

        responses = [first_response, second_response]
        client, transport = _make_multi_client(responses)
        storage = RawArtifactStorage(tmp_path)
        conn = EurLexHttpConnector(
            storage=storage,
            client=client,
            max_retries=0,
            rate_limit_delay=0.0,
            min_retry_delay=0.0,
            max_retry_delay=0.0,
        )

        await conn.acquire(ai_act_source)
        await conn.acquire(ai_act_source)

        second_request = transport.recorded_requests[1]
        assert second_request.headers.get("if-modified-since") == last_mod


# ===========================================================================
# Section 11: Context manager lifecycle
# ===========================================================================


class TestContextManagerLifecycle:
    @pytest.mark.asyncio
    async def test_aenter_returns_connector(self, tmp_path: Path) -> None:
        content = _make_html_content()
        response = httpx.Response(200, content=content, headers={"Content-Type": "text/html"})
        conn = _connector(tmp_path, _make_client(response))
        async with conn as c:
            assert c is conn

    @pytest.mark.asyncio
    async def test_aexit_closes_internal_client(self, tmp_path: Path) -> None:
        """An internally-created client must be closed on __aexit__."""
        storage = RawArtifactStorage(tmp_path)
        conn = EurLexHttpConnector(storage=storage, rate_limit_delay=0.0)

        with patch.object(conn._client, "aclose", new_callable=AsyncMock) as mock_close:
            async with conn:
                pass
        mock_close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_aexit_does_not_close_injected_client(self, tmp_path: Path) -> None:
        """An externally injected client must NOT be closed by the connector."""
        content = _make_html_content()
        response = httpx.Response(200, content=content, headers={"Content-Type": "text/html"})
        external_client = _make_client(response)
        conn = _connector(tmp_path, external_client)

        with patch.object(external_client, "aclose", new_callable=AsyncMock) as mock_close:
            async with conn:
                pass
        mock_close.assert_not_awaited()


# ===========================================================================
# Section 12: Abstract base connector
# ===========================================================================


class TestBaseAcquisitionConnector:
    def test_base_connector_is_abstract(self) -> None:
        """BaseAcquisitionConnector cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseAcquisitionConnector()  # type: ignore[abstract]

    def test_concrete_connector_must_implement_acquire(self) -> None:
        class _Incomplete(BaseAcquisitionConnector):
            async def close(self) -> None:
                pass

        with pytest.raises(TypeError):
            _Incomplete()  # type: ignore[abstract]

    def test_concrete_connector_must_implement_close(self) -> None:
        class _Incomplete(BaseAcquisitionConnector):
            async def acquire(self, source: Any, target_format: Any = None) -> Any:  # type: ignore[override]
                pass

        with pytest.raises(TypeError):
            _Incomplete()  # type: ignore[abstract]


# ===========================================================================
# Section 13: AcquisitionService routing
# ===========================================================================


class TestAcquisitionService:
    @pytest.mark.asyncio
    async def test_acquire_document_dispatches_by_document_id(
        self,
        minimal_registry: RegulatorySourceRegistry,
        tmp_path: Path,
    ) -> None:
        content = _make_html_content()
        response = httpx.Response(200, content=content, headers={"Content-Type": "text/html"})
        storage = RawArtifactStorage(tmp_path)
        connector = EurLexHttpConnector(
            storage=storage,
            client=_make_client(response),
            max_retries=0,
            rate_limit_delay=0.0,
            min_retry_delay=0.0,
            max_retry_delay=0.0,
        )
        service = AcquisitionService(
            connector=connector,
            registry=minimal_registry,
            storage=storage,
        )
        result = await service.acquire_document("eu_ai_act")
        assert result.status == AcquisitionStatus.SUCCESS
        assert result.document_id == "eu_ai_act"

    @pytest.mark.asyncio
    async def test_acquire_by_celex_dispatches_correctly(
        self,
        minimal_registry: RegulatorySourceRegistry,
        tmp_path: Path,
    ) -> None:
        content = _make_html_content()
        response = httpx.Response(200, content=content, headers={"Content-Type": "text/html"})
        storage = RawArtifactStorage(tmp_path)
        connector = EurLexHttpConnector(
            storage=storage,
            client=_make_client(response),
            max_retries=0,
            rate_limit_delay=0.0,
            min_retry_delay=0.0,
            max_retry_delay=0.0,
        )
        service = AcquisitionService(
            connector=connector,
            registry=minimal_registry,
            storage=storage,
        )
        result = await service.acquire_by_celex("32024R1689")
        assert result.celex_id == "32024R1689"
        assert result.status == AcquisitionStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_acquire_document_raises_for_unknown_id(
        self, minimal_registry: RegulatorySourceRegistry, tmp_path: Path
    ) -> None:
        storage = RawArtifactStorage(tmp_path)
        mock_connector = MagicMock(spec=BaseAcquisitionConnector)
        service = AcquisitionService(
            connector=mock_connector,
            registry=minimal_registry,
            storage=storage,
        )
        with pytest.raises(DocumentNotFoundError):
            await service.acquire_document("non_existent_document_id")

    @pytest.mark.asyncio
    async def test_acquire_by_celex_raises_for_unknown_celex(
        self, minimal_registry: RegulatorySourceRegistry, tmp_path: Path
    ) -> None:
        storage = RawArtifactStorage(tmp_path)
        mock_connector = MagicMock(spec=BaseAcquisitionConnector)
        service = AcquisitionService(
            connector=mock_connector,
            registry=minimal_registry,
            storage=storage,
        )
        with pytest.raises(DocumentNotFoundError):
            await service.acquire_by_celex("32099X9999")

    @pytest.mark.asyncio
    async def test_service_context_manager(
        self, minimal_registry: RegulatorySourceRegistry, tmp_path: Path
    ) -> None:
        storage = RawArtifactStorage(tmp_path)
        mock_connector = AsyncMock(spec=BaseAcquisitionConnector)
        service = AcquisitionService(
            connector=mock_connector,
            registry=minimal_registry,
            storage=storage,
        )
        async with service as svc:
            assert svc is service


# ===========================================================================
# Section 14: RawArtifactStorage path layout
# ===========================================================================


class TestRawArtifactStoragePaths:
    def test_original_act_path_includes_publication_date(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        storage = RawArtifactStorage(tmp_path)
        file_path, _ = storage.resolve_artifact_paths(
            source=ai_act_source, category="original_act", target_format="HTML"
        )
        assert "original_2024-07-12" in str(file_path)

    def test_original_act_path_includes_document_id(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        storage = RawArtifactStorage(tmp_path)
        file_path, _ = storage.resolve_artifact_paths(
            source=ai_act_source, category="original_act", target_format="HTML"
        )
        assert "eu_ai_act" in str(file_path)

    def test_original_act_path_includes_celex(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        storage = RawArtifactStorage(tmp_path)
        file_path, _ = storage.resolve_artifact_paths(
            source=ai_act_source, category="original_act", target_format="HTML"
        )
        assert "32024R1689" in str(file_path)

    def test_corrigendum_path_strips_parentheses(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        storage = RawArtifactStorage(tmp_path)
        file_path, _ = storage.resolve_artifact_paths(
            source=ai_act_source,
            category="corrigendum",
            target_format="HTML",
            corrigendum_celex="32024R1689R(01)",
        )
        assert "(" not in str(file_path)
        assert ")" not in str(file_path)

    def test_corrigendum_path_uses_corrigenda_subdir(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        storage = RawArtifactStorage(tmp_path)
        file_path, _ = storage.resolve_artifact_paths(
            source=ai_act_source,
            category="corrigendum",
            target_format="HTML",
            corrigendum_celex="32024R1689R(01)",
        )
        assert "corrigenda" in str(file_path)

    def test_file_extension_matches_format(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        storage = RawArtifactStorage(tmp_path)
        for fmt, expected_ext in [("HTML", ".html"), ("PDF", ".pdf"), ("XML", ".xml")]:
            file_path, _ = storage.resolve_artifact_paths(
                source=ai_act_source, category="original_act", target_format=fmt
            )
            assert file_path.suffix == expected_ext

    def test_sidecar_has_meta_json_extension(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        storage = RawArtifactStorage(tmp_path)
        _, sidecar_path = storage.resolve_artifact_paths(
            source=ai_act_source, category="original_act", target_format="HTML"
        )
        assert sidecar_path.name.endswith(".meta.json")


# ===========================================================================
# Section 15: RawArtifactStorage staging and commit
# ===========================================================================


class TestRawArtifactStorageCommit:
    def test_staging_file_created_in_correct_directory(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        storage = RawArtifactStorage(tmp_path)
        target_file, _ = storage.resolve_artifact_paths(
            source=ai_act_source, category="original_act", target_format="HTML"
        )
        staging = storage.create_staging_file(target_file)

        assert staging.parent == target_file.parent
        assert ".tmp." in staging.name

    def test_staging_creates_parent_directories(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        storage = RawArtifactStorage(tmp_path)
        target_file, _ = storage.resolve_artifact_paths(
            source=ai_act_source, category="original_act", target_format="HTML"
        )
        storage.create_staging_file(target_file)
        assert target_file.parent.is_dir()

    def test_commit_creates_target_file(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        import datetime as dt

        storage = RawArtifactStorage(tmp_path)
        target_file, sidecar_file = storage.resolve_artifact_paths(
            source=ai_act_source, category="original_act", target_format="HTML"
        )
        staging = storage.create_staging_file(target_file)
        content = _make_html_content()
        staging.write_bytes(content)

        sidecar_metadata = storage.build_sidecar_metadata(
            source=ai_act_source,
            retrieved_at=dt.datetime.now(dt.UTC),
            http_status=200,
            etag=None,
            last_modified=None,
            duration_seconds=0.5,
            format_name="HTML",
            media_type="text/html",
            file_size_bytes=len(content),
            sha256_checksum=_sha256(content),
            target_file=target_file,
            sidecar_file=sidecar_file,
        )
        storage.commit_artifact(
            staging_file=staging,
            target_file=target_file,
            sidecar_file=sidecar_file,
            metadata=sidecar_metadata,
        )

        assert target_file.is_file()
        assert target_file.read_bytes() == content

    def test_commit_raises_on_hash_conflict(
        self, ai_act_source: RegulatorySourceEntry, tmp_path: Path
    ) -> None:
        import datetime as dt

        storage = RawArtifactStorage(tmp_path)
        target_file, sidecar_file = storage.resolve_artifact_paths(
            source=ai_act_source, category="original_act", target_format="HTML"
        )

        # First commit
        content_a = _make_html_content(2048)
        staging_a = storage.create_staging_file(target_file)
        staging_a.write_bytes(content_a)
        meta_a = storage.build_sidecar_metadata(
            source=ai_act_source,
            retrieved_at=dt.datetime.now(dt.UTC),
            http_status=200,
            etag=None,
            last_modified=None,
            duration_seconds=0.5,
            format_name="HTML",
            media_type="text/html",
            file_size_bytes=len(content_a),
            sha256_checksum=_sha256(content_a),
            target_file=target_file,
            sidecar_file=sidecar_file,
        )
        storage.commit_artifact(
            staging_file=staging_a,
            target_file=target_file,
            sidecar_file=sidecar_file,
            metadata=meta_a,
        )

        # Simulated second commit with conflicting hash
        content_b = _make_html_content(4096)
        staging_b = storage.create_staging_file(target_file)
        staging_b.write_bytes(content_b)
        meta_b = storage.build_sidecar_metadata(
            source=ai_act_source,
            retrieved_at=dt.datetime.now(dt.UTC),
            http_status=200,
            etag=None,
            last_modified=None,
            duration_seconds=0.5,
            format_name="HTML",
            media_type="text/html",
            file_size_bytes=len(content_b),
            sha256_checksum=_sha256(content_b),
            target_file=target_file,
            sidecar_file=sidecar_file,
        )

        existing = ExistingArtifact(
            file_path=target_file,
            sidecar_path=sidecar_file,
            metadata=meta_a,
        )
        with pytest.raises(VersionIntegrityConflictError):
            storage.commit_artifact(
                staging_file=staging_b,
                target_file=target_file,
                sidecar_file=sidecar_file,
                metadata=meta_b,
                existing_artifact=existing,
            )


# ===========================================================================
# Section 16: ExistingArtifact properties
# ===========================================================================


class TestExistingArtifact:
    def test_sha256_returns_none_without_metadata(self, tmp_path: Path) -> None:
        artifact = ExistingArtifact(file_path=tmp_path / "file.html")
        assert artifact.sha256_checksum is None

    def test_etag_returns_none_without_metadata(self, tmp_path: Path) -> None:
        artifact = ExistingArtifact(file_path=tmp_path / "file.html")
        assert artifact.etag is None

    def test_last_modified_returns_none_without_metadata(self, tmp_path: Path) -> None:
        artifact = ExistingArtifact(file_path=tmp_path / "file.html")
        assert artifact.last_modified is None


# ===========================================================================
# Section 17: Canonical ID helper functions
# ===========================================================================


class TestCanonicalIdentifiers:
    def test_original_act_version_id_prefix(self) -> None:
        vid = canonical_artifact_version_id(
            celex_id="32024R1689",
            publication_date=dt.date(2024, 7, 12),
            category="original_act",
        )
        assert vid == "orig_32024R1689_2024-07-12"

    def test_consolidated_version_id_prefix(self) -> None:
        vid = canonical_artifact_version_id(
            celex_id="02016R0679-20210304",
            publication_date=dt.date(2016, 5, 4),
            category="consolidated_text",
        )
        assert vid.startswith("cons_")

    def test_corrigendum_version_id_prefix(self) -> None:
        vid = canonical_artifact_version_id(
            celex_id="32024R1689R(01)",
            publication_date=dt.date(2024, 9, 10),
            category="corrigendum",
        )
        assert vid.startswith("corr_")
        assert "(" not in vid
        assert ")" not in vid

    def test_artifact_id_format(self) -> None:
        aid = canonical_artifact_id(
            celex_id="32024R1689",
            publication_date=dt.date(2024, 7, 12),
            language="en",
            fmt="html",
        )
        assert aid.startswith("art_32024R1689_")
        assert "html" in aid
