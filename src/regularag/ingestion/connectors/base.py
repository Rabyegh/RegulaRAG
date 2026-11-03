"""
Abstract base connector interface for regulatory document acquisition.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from regularag.ingestion.models import AcquisitionResult, RegulatorySourceEntry


class BaseAcquisitionConnector(ABC):
    """Abstract interface defining the lifecycle and contract for document acquisition."""

    @abstractmethod
    async def acquire(
        self,
        source: RegulatorySourceEntry,
        target_format: str | None = None,
    ) -> AcquisitionResult:
        """Acquire an official regulatory document and store its raw artifact.

        Args:
            source: Validated regulatory source entry from the registry.
            target_format: Target format (e.g. 'HTML', 'PDF', 'XML'), or None for preferred.

        Returns:
            An :class:`AcquisitionResult` summarizing the operation.
        """

    @abstractmethod
    async def close(self) -> None:
        """Release underlying HTTP client and connection pool resources."""

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        await self.close()
