"""
Regulatory source registry loader and validation helpers.

Provides functions to locate, parse, and validate the authoritative
regulatory source configuration against the Pydantic schema.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from regularag.core.exceptions import ConfigurationError
from regularag.ingestion.models import RegulatorySourceRegistry

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[3] / "configs" / "regulatory_sources.yaml"


def load_regulatory_sources(
    registry_path: Path | str | None = None,
) -> RegulatorySourceRegistry:
    """Load and validate the regulatory sources registry from YAML.

    Args:
        registry_path: Path to the YAML file. If omitted, defaults to
            `configs/regulatory_sources.yaml` at the project root.

    Returns:
        A validated :class:`RegulatorySourceRegistry` instance.

    Raises:
        ConfigurationError: If the file does not exist, cannot be parsed,
            or fails Pydantic schema validation.
    """
    path = Path(registry_path) if registry_path else DEFAULT_REGISTRY_PATH

    if not path.is_file():
        raise ConfigurationError(
            f"Regulatory sources registry file not found: {path}",
            path=str(path),
        )

    try:
        with open(path, encoding="utf-8") as file:
            raw_data: Any = yaml.safe_load(file)
    except Exception as exc:
        raise ConfigurationError(
            f"Failed to parse regulatory sources YAML at {path}: {exc}",
            path=str(path),
        ) from exc

    try:
        return RegulatorySourceRegistry.model_validate(raw_data)
    except Exception as exc:
        raise ConfigurationError(
            f"Validation failed for regulatory sources registry at {path}: {exc}",
            path=str(path),
        ) from exc
