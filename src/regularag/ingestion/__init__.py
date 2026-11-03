"""
Ingestion module — regulatory document ingestion pipeline.

Provides the authoritative source registry, data contracts, and acquisition
components for EUR-Lex regulatory frameworks.
"""

from regularag.ingestion.models import (
    CELEX_CONSOLIDATED_REGEX,
    CELEX_CORRIGENDUM_REGEX,
    CELEX_ORIGINAL_ACT_REGEX,
    CelexType,
    CorrigendumEntry,
    PhasedApplicationItem,
    RegulatorySourceEntry,
    RegulatorySourceRegistry,
    classify_celex,
)
from regularag.ingestion.sources import load_regulatory_sources

__all__ = [
    "CELEX_CONSOLIDATED_REGEX",
    "CELEX_CORRIGENDUM_REGEX",
    "CELEX_ORIGINAL_ACT_REGEX",
    "CelexType",
    "CorrigendumEntry",
    "PhasedApplicationItem",
    "RegulatorySourceEntry",
    "RegulatorySourceRegistry",
    "classify_celex",
    "load_regulatory_sources",
]
