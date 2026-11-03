"""Acquisition connector package for official regulatory document sources."""

from regularag.ingestion.connectors.base import BaseAcquisitionConnector
from regularag.ingestion.connectors.eurlex import EurLexHttpConnector

__all__ = ["BaseAcquisitionConnector", "EurLexHttpConnector"]
