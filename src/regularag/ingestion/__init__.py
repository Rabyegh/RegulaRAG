"""
Ingestion module — regulatory document ingestion pipeline.

Provides the authoritative source registry, data contracts, and acquisition
components for EUR-Lex regulatory frameworks.
"""

from regularag.ingestion.connectors.base import BaseAcquisitionConnector
from regularag.ingestion.connectors.eurlex import EurLexHttpConnector
from regularag.ingestion.models import (
    CELEX_CONSOLIDATED_REGEX,
    CELEX_CORRIGENDUM_REGEX,
    CELEX_ORIGINAL_ACT_REGEX,
    AcquisitionResult,
    AcquisitionStatus,
    ArtifactSidecarMetadata,
    CelexType,
    CorrigendumEntry,
    PhasedApplicationItem,
    RegulatorySourceEntry,
    RegulatorySourceRegistry,
    canonical_artifact_id,
    canonical_artifact_version_id,
    classify_celex,
)
from regularag.ingestion.service import AcquisitionService
from regularag.ingestion.sources import load_regulatory_sources
from regularag.ingestion.storage import ExistingArtifact, RawArtifactStorage

__all__ = [
    "CELEX_CONSOLIDATED_REGEX",
    "CELEX_CORRIGENDUM_REGEX",
    "CELEX_ORIGINAL_ACT_REGEX",
    "AcquisitionResult",
    "AcquisitionService",
    "AcquisitionStatus",
    "ArtifactSidecarMetadata",
    "BaseAcquisitionConnector",
    "CelexType",
    "CorrigendumEntry",
    "EurLexHttpConnector",
    "ExistingArtifact",
    "PhasedApplicationItem",
    "RawArtifactStorage",
    "RegulatorySourceEntry",
    "RegulatorySourceRegistry",
    "canonical_artifact_id",
    "canonical_artifact_version_id",
    "classify_celex",
    "load_regulatory_sources",
]
