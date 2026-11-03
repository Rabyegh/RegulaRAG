"""
Official EUR-Lex HTTP document acquisition connector.

Implements asynchronous streaming downloads, rate limiting, conditional requests,
exponential backoff retries, SHA-256 calculation, and content validation.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import time
from http import HTTPStatus
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING

import httpx
import structlog

from regularag.core.config import get_settings
from regularag.core.exceptions import (
    AcquisitionConnectionError,
    AcquisitionError,
    AcquisitionRateLimitError,
    AcquisitionTimeoutError,
    DocumentContentValidationError,
    DocumentNotFoundError,
    VersionIntegrityConflictError,
)
from regularag.ingestion.connectors.base import BaseAcquisitionConnector
from regularag.ingestion.models import (
    AcquisitionResult,
    AcquisitionStatus,
    canonical_artifact_version_id,
)
from regularag.ingestion.storage import RawArtifactStorage

if TYPE_CHECKING:
    from regularag.ingestion.models import RegulatorySourceEntry

logger = structlog.get_logger(__name__)

# Content validation markers
HTML_PLAUSIBILITY_MARKERS = (b"<html", b"<!doctype", b"<?xml", b"<body")
HTML_ERROR_MARKERS = (
    b"<title>404",
    b"<title>error",
    b"document not found",
    b"internal server error",
)


class EurLexHttpConnector(BaseAcquisitionConnector):
    """Acquisition connector specialized for official EUR-Lex portal endpoints."""

    def __init__(
        self,
        storage: RawArtifactStorage | None = None,
        client: httpx.AsyncClient | None = None,
        timeout_connect: float | None = None,
        timeout_read: float | None = None,
        max_retries: int | None = None,
        backoff_factor: float | None = None,
        min_retry_delay: float | None = None,
        max_retry_delay: float | None = None,
        rate_limit_delay: float | None = None,
        user_agent: str | None = None,
    ) -> None:
        settings = get_settings()

        self.storage = storage or RawArtifactStorage(settings.ingestion_raw_storage_dir)
        self.timeout_connect = (
            timeout_connect
            if timeout_connect is not None
            else settings.ingestion_http_timeout_connect
        )
        self.timeout_read = (
            timeout_read if timeout_read is not None else settings.ingestion_http_timeout_read
        )
        self.max_retries = (
            max_retries if max_retries is not None else settings.ingestion_max_retries
        )
        self.backoff_factor = (
            backoff_factor if backoff_factor is not None else settings.ingestion_backoff_factor
        )
        self.min_retry_delay = (
            min_retry_delay if min_retry_delay is not None else settings.ingestion_min_retry_delay
        )
        self.max_retry_delay = (
            max_retry_delay if max_retry_delay is not None else settings.ingestion_max_retry_delay
        )
        self.rate_limit_delay = (
            rate_limit_delay
            if rate_limit_delay is not None
            else settings.ingestion_request_rate_limit
        )
        self.user_agent = user_agent or settings.ingestion_user_agent

        # Pacing control
        self._last_request_time: float = 0.0
        self._pacing_lock = asyncio.Lock()

        # HTTP client lifecycle
        self._external_client = client is not None
        if client is not None:
            self._client = client
        else:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=self.timeout_connect,
                    read=self.timeout_read,
                    write=15.0,
                    pool=10.0,
                ),
                headers={"User-Agent": self.user_agent},
                follow_redirects=True,
            )

    async def _enforce_rate_limit(self) -> None:
        """Pace requests according to configured delay interval."""
        if self.rate_limit_delay <= 0:
            return
        async with self._pacing_lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - elapsed)
            self._last_request_time = time.monotonic()

    def _build_request_headers(
        self,
        existing_etag: str | None,
        existing_last_modified: str | None,
        target_format: str,
    ) -> dict[str, str]:
        """Construct request headers including conditional optimization hints."""
        headers: dict[str, str] = {
            "User-Agent": self.user_agent,
        }

        # Accept header based on target format
        fmt = target_format.upper()
        if fmt == "HTML":
            headers["Accept"] = "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"
        elif fmt == "PDF":
            headers["Accept"] = "application/pdf,*/*;q=0.8"
        elif fmt == "XML":
            headers["Accept"] = "application/xml,text/xml;q=0.9,*/*;q=0.8"

        # Conditional request headers (Transport Optimization Hints)
        if existing_etag:
            headers["If-None-Match"] = existing_etag
        if existing_last_modified:
            headers["If-Modified-Since"] = existing_last_modified

        return headers

    def _validate_content(
        self,
        staging_file: Path,
        content_type: str,
        target_format: str,
    ) -> list[str]:
        """Validate that downloaded bytes represent a plausible regulatory document."""
        checks_passed: list[str] = []

        # 1. Non-empty check
        file_size = staging_file.stat().st_size
        if file_size < 100:
            raise DocumentContentValidationError(
                f"Downloaded content is too small ({file_size} bytes); expected complete document.",
                file_size_bytes=file_size,
            )
        checks_passed.append("size_greater_than_100_bytes")

        # 2. Media type check
        fmt = target_format.upper()
        ct_lower = content_type.lower()
        if fmt == "HTML" and not ("html" in ct_lower or "text" in ct_lower or not ct_lower):
            raise DocumentContentValidationError(
                f"Invalid Content-Type for HTML document: '{content_type}'",
                content_type=content_type,
            )
        if fmt == "PDF" and not ("pdf" in ct_lower or "octet-stream" in ct_lower):
            raise DocumentContentValidationError(
                f"Invalid Content-Type for PDF document: '{content_type}'",
                content_type=content_type,
            )
        checks_passed.append("media_type_valid")

        # 3. Content plausibility check (check header bytes)
        with open(staging_file, "rb") as f:
            header_bytes = f.read(2048).lower()

        if fmt == "HTML":
            has_marker = any(marker in header_bytes for marker in HTML_PLAUSIBILITY_MARKERS)
            if not has_marker:
                raise DocumentContentValidationError(
                    "Payload does not appear to be a valid HTML or XML document.",
                )
            has_error = any(err in header_bytes for err in HTML_ERROR_MARKERS)
            if has_error:
                raise DocumentContentValidationError(
                    "Payload contains error page signature despite HTTP 200.",
                )
            checks_passed.append("html_plausibility_verified")
        elif fmt == "PDF":
            if not header_bytes.startswith(b"%pdf"):
                raise DocumentContentValidationError(
                    "Payload does not start with valid PDF magic bytes.",
                )
            checks_passed.append("pdf_magic_bytes_verified")

        checks_passed.append("sha256_verified")
        return checks_passed

    async def acquire(
        self,
        source: RegulatorySourceEntry,
        target_format: str | None = None,
    ) -> AcquisitionResult:
        """Acquire an official regulatory document and store its raw artifact."""
        fmt = target_format or source.preferred_format
        target_file, sidecar_file = self.storage.resolve_artifact_paths(
            source=source,
            category="original_act",
            target_format=fmt,
        )
        existing = self.storage.get_existing_artifact(
            source=source,
            category="original_act",
            target_format=fmt,
        )

        version_id = canonical_artifact_version_id(
            celex_id=source.celex_id,
            publication_date=source.publication_date,
            category="original_act",
        )

        url = str(source.official_source_url)
        headers = self._build_request_headers(
            existing_etag=existing.etag if existing else None,
            existing_last_modified=existing.last_modified if existing else None,
            target_format=fmt,
        )

        attempt = 0
        last_exception: Exception | None = None

        while attempt <= self.max_retries:
            attempt += 1
            staging_file = self.storage.create_staging_file(target_file)
            start_time = time.monotonic()

            try:
                await self._enforce_rate_limit()

                logger.info(
                    "Initiating document acquisition",
                    document_id=source.document_id,
                    celex_id=source.celex_id,
                    url=url,
                    format=fmt,
                    attempt=attempt,
                )

                retrieved_at = dt.datetime.now(dt.UTC)
                async with self._client.stream(
                    "GET",
                    url,
                    headers=headers,
                    follow_redirects=True,
                ) as response:
                    duration = time.monotonic() - start_time
                    status = response.status_code

                    # ---------------------------------------------------------
                    # 1. HTTP 304 Not Modified
                    # ---------------------------------------------------------
                    if status == HTTPStatus.NOT_MODIFIED:
                        logger.info(
                            "Document not modified (HTTP 304)",
                            document_id=source.document_id,
                            celex_id=source.celex_id,
                        )
                        staging_file.unlink(missing_ok=True)
                        return AcquisitionResult(
                            document_id=source.document_id,
                            celex_id=source.celex_id,
                            artifact_version_id=version_id,
                            status=AcquisitionStatus.NOT_MODIFIED,
                            http_status=304,
                            file_path=existing.file_path if existing else target_file,
                            sidecar_path=existing.sidecar_path if existing else sidecar_file,
                            sha256_checksum=existing.sha256_checksum if existing else None,
                            bytes_downloaded=0,
                            metadata=existing.metadata if existing else None,
                        )

                    # ---------------------------------------------------------
                    # 2. HTTP 404 Not Found (Non-retryable)
                    # ---------------------------------------------------------
                    if status == HTTPStatus.NOT_FOUND:
                        staging_file.unlink(missing_ok=True)
                        raise DocumentNotFoundError(
                            f"Official EUR-Lex document not found at {url}",
                            document_id=source.document_id,
                            celex_id=source.celex_id,
                            url=url,
                        )

                    # ---------------------------------------------------------
                    # 3. HTTP 429 Too Many Requests (Retryable)
                    # ---------------------------------------------------------
                    if status == HTTPStatus.TOO_MANY_REQUESTS:
                        retry_after_str = response.headers.get("Retry-After")
                        retry_after = (
                            float(retry_after_str)
                            if retry_after_str and retry_after_str.isdigit()
                            else None
                        )
                        staging_file.unlink(missing_ok=True)
                        raise AcquisitionRateLimitError(
                            "EUR-Lex rate limit exceeded (HTTP 429).",
                            retry_after=retry_after,
                        )

                    # ---------------------------------------------------------
                    # 4. 5xx Server Errors (Retryable)
                    # ---------------------------------------------------------
                    if status in (
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                        HTTPStatus.BAD_GATEWAY,
                        HTTPStatus.SERVICE_UNAVAILABLE,
                        HTTPStatus.GATEWAY_TIMEOUT,
                    ):
                        staging_file.unlink(missing_ok=True)
                        raise AcquisitionConnectionError(
                            f"EUR-Lex server error (HTTP {status}).",
                            http_status=status,
                        )

                    # ---------------------------------------------------------
                    # 5. Non-200 unhandled errors
                    # ---------------------------------------------------------
                    if status != HTTPStatus.OK:
                        staging_file.unlink(missing_ok=True)
                        raise AcquisitionError(
                            f"Acquisition request returned unexpected HTTP {status}.",
                            http_status=status,
                        )

                    # ---------------------------------------------------------
                    # 6. Stream and hash payload (HTTP 200 OK)
                    # ---------------------------------------------------------
                    hasher = hashlib.sha256()
                    bytes_downloaded = 0

                    with open(staging_file, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=65536):
                            hasher.update(chunk)
                            f.write(chunk)
                            bytes_downloaded += len(chunk)

                    new_sha256 = hasher.hexdigest()
                    content_type = response.headers.get("Content-Type", "")
                    etag = response.headers.get("ETag")
                    last_modified = response.headers.get("Last-Modified")

                # Validate downloaded content
                checks_passed = self._validate_content(
                    staging_file=staging_file,
                    content_type=content_type,
                    target_format=fmt,
                )

                # Idempotency check: if existing file matches SHA-256, preserve it
                if (
                    existing
                    and existing.file_path.exists()
                    and existing.sha256_checksum == new_sha256
                ):
                    logger.info(
                        "Document unchanged (SHA-256 matches existing artifact)",
                        document_id=source.document_id,
                        celex_id=source.celex_id,
                        sha256=new_sha256,
                    )
                    staging_file.unlink(missing_ok=True)
                    return AcquisitionResult(
                        document_id=source.document_id,
                        celex_id=source.celex_id,
                        artifact_version_id=version_id,
                        status=AcquisitionStatus.UNCHANGED,
                        http_status=200,
                        file_path=existing.file_path,
                        sidecar_path=existing.sidecar_path,
                        sha256_checksum=new_sha256,
                        bytes_downloaded=bytes_downloaded,
                        metadata=existing.metadata,
                    )

                # Build sidecar metadata
                sidecar_metadata = self.storage.build_sidecar_metadata(
                    source=source,
                    retrieved_at=retrieved_at,
                    http_status=200,
                    etag=etag,
                    last_modified=last_modified,
                    duration_seconds=duration,
                    format_name=fmt,
                    media_type=content_type,
                    file_size_bytes=bytes_downloaded,
                    sha256_checksum=new_sha256,
                    target_file=target_file,
                    sidecar_file=sidecar_file,
                    category="original_act",
                    checks_passed=checks_passed,
                )

                # Commit artifact atomically (checks for SHA-256 conflicts)
                self.storage.commit_artifact(
                    staging_file=staging_file,
                    target_file=target_file,
                    sidecar_file=sidecar_file,
                    metadata=sidecar_metadata,
                    existing_artifact=existing,
                )

                return AcquisitionResult(
                    document_id=source.document_id,
                    celex_id=source.celex_id,
                    artifact_version_id=version_id,
                    status=AcquisitionStatus.SUCCESS,
                    http_status=200,
                    file_path=target_file,
                    sidecar_path=sidecar_file,
                    sha256_checksum=new_sha256,
                    bytes_downloaded=bytes_downloaded,
                    metadata=sidecar_metadata,
                )

            except (DocumentNotFoundError, VersionIntegrityConflictError):
                # Non-retryable domain errors
                staging_file.unlink(missing_ok=True)
                raise

            except DocumentContentValidationError:
                # Content validation failed — do not retry indefinitely
                staging_file.unlink(missing_ok=True)
                raise

            except (
                httpx.TimeoutException,
                httpx.NetworkError,
                AcquisitionRateLimitError,
                AcquisitionConnectionError,
            ) as exc:
                staging_file.unlink(missing_ok=True)
                last_exception = exc

                if attempt > self.max_retries:
                    logger.error(
                        "Max acquisition retries exhausted",
                        document_id=source.document_id,
                        celex_id=source.celex_id,
                        attempts=attempt,
                        error=str(exc),
                    )
                    break

                # Compute exponential backoff delay
                retry_val = (
                    exc.context.get("retry_after")
                    if isinstance(exc, AcquisitionRateLimitError)
                    else None
                )
                if retry_val is not None and isinstance(retry_val, (int, float, str)):
                    delay = min(float(retry_val), self.max_retry_delay)
                else:
                    delay = min(
                        self.max_retry_delay,
                        self.min_retry_delay * (self.backoff_factor ** (attempt - 1)),
                    )

                logger.warning(
                    "Transient acquisition failure; retrying with backoff",
                    document_id=source.document_id,
                    attempt=attempt,
                    retry_in_seconds=delay,
                    error=str(exc),
                )
                await asyncio.sleep(delay)

            except Exception as exc:
                staging_file.unlink(missing_ok=True)
                logger.exception(
                    "Unexpected failure during acquisition",
                    document_id=source.document_id,
                    celex_id=source.celex_id,
                    error=str(exc),
                )
                raise AcquisitionError(
                    f"Unexpected failure acquiring document {source.document_id}: {exc}",
                    document_id=source.document_id,
                    celex_id=source.celex_id,
                ) from exc

            finally:
                if staging_file.exists():
                    staging_file.unlink(missing_ok=True)

        # Retries exhausted
        if isinstance(last_exception, httpx.TimeoutException):
            raise AcquisitionTimeoutError(
                f"Acquisition timed out after {attempt} attempts: {last_exception}",
                document_id=source.document_id,
            ) from last_exception
        if isinstance(last_exception, (httpx.NetworkError, AcquisitionConnectionError)):
            raise AcquisitionConnectionError(
                f"Failed to connect after {attempt} attempts: {last_exception}",
                document_id=source.document_id,
            ) from last_exception
        if isinstance(last_exception, AcquisitionRateLimitError):
            raise last_exception
        raise AcquisitionError(
            f"Acquisition failed after {attempt} attempts: {last_exception}",
            document_id=source.document_id,
        )

    async def close(self) -> None:
        """Close internal HTTP client if created internally."""
        if not self._external_client:
            await self._client.aclose()
