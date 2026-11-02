"""
Ingestion module — regulatory document ingestion pipeline.

Provides the authoritative source registry, data contracts, and acquisition
components for EUR-Lex regulatory frameworks.
"""

from regularag.ingestion.models import (
    CorrigendumEntry,
    PhasedApplicationItem,
    RegulatorySourceEntry,
    RegulatorySourceRegistry,
)
from regularag.ingestion.sources import load_regulatory_sources

__all__ = [
    "CorrigendumEntry",
    "PhasedApplicationItem",
    "RegulatorySourceEntry",
    "RegulatorySourceRegistry",
    "load_regulatory_sources",
]
