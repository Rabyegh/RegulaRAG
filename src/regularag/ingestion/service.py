"""
Acquisition orchestrator service.

Coordinates the acquisition of official regulatory documents from the source
registry using configured connectors and storage policies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

import structlog

from regularag.core.exceptions import DocumentNotFoundError
from regularag.ingestion.connectors.eurlex import EurLexHttpConnector
from regularag.ingestion.sources import load_regulatory_sources
from regularag.ingestion.storage import RawArtifactStorage

if TYPE_CHECKING:
    from regularag.ingestion.connectors.base import BaseAcquisitionConnector
    from regularag.ingestion.models import RegulatorySourceRegistry

from regularag.ingestion.models import AcquisitionResult  # noqa: TC001

logger = structlog.get_logger(__name__)


class AcquisitionService:
    """High-level service coordinating regulatory document ingestion."""

    def __init__(
        self,
        connector: BaseAcquisitionConnector | None = None,
        registry: RegulatorySourceRegistry | None = None,
        storage: RawArtifactStorage | None = None,
    ) -> None:
        self.registry = registry or load_regulatory_sources()
        self.storage = storage or RawArtifactStorage("data/raw")
        self._connector = connector or EurLexHttpConnector(storage=self.storage)
        self._owns_connector = connector is None

    async def acquire_document(
        self,
        document_id: str,
        target_format: str | None = None,
    ) -> AcquisitionResult:
        """Acquire a single document identified by its system document_id."""
        source = self.registry.get_by_document_id(document_id)
        if source is None:
            raise DocumentNotFoundError(
                f"Document ID '{document_id}' not found in regulatory source registry.",
                document_id=document_id,
            )

        logger.info("Executing document acquisition", document_id=document_id)
        return await self._connector.acquire(source=source, target_format=target_format)

    async def acquire_by_celex(
        self,
        celex_id: str,
        target_format: str | None = None,
    ) -> AcquisitionResult:
        """Acquire a single document identified by its official CELEX identifier."""
        source = self.registry.get_by_celex(celex_id)
        if source is None:
            raise DocumentNotFoundError(
                f"CELEX ID '{celex_id}' not found in regulatory source registry.",
                celex_id=celex_id,
            )

        logger.info("Executing CELEX acquisition", celex_id=celex_id)
        return await self._connector.acquire(source=source, target_format=target_format)

    async def acquire_all(
        self,
        target_format: str | None = None,
    ) -> list[AcquisitionResult]:
        """Acquire all regulatory documents declared in the active registry.

        Executes sequentially to respect polite crawl rate limits.
        """
        results: list[AcquisitionResult] = []
        logger.info(
            "Starting batch acquisition of all registry sources",
            total_documents=len(self.registry.sources),
        )

        for source in self.registry.sources:
            try:
                res = await self._connector.acquire(source=source, target_format=target_format)
                results.append(res)
            except Exception as exc:
                logger.error(
                    "Acquisition failed for document in batch",
                    document_id=source.document_id,
                    error=str(exc),
                )
                raise

        return results

    async def close(self) -> None:
        """Release connector resources if created internally."""
        if self._owns_connector:
            await self._connector.close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        await self.close()
