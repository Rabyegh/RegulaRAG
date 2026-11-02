"""
Unit tests for the Regulatory Source Registry and Ingestion Data Contract.

Validates the YAML source registry, Pydantic data models, CELEX/ELI identifiers,
URL schemas, and legal instrument constraints.
"""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from regularag.core.exceptions import ConfigurationError
from regularag.ingestion.models import (
    RegulatorySourceEntry,
    RegulatorySourceRegistry,
)
from regularag.ingestion.sources import load_regulatory_sources

EXPECTED_DOC_IDS = {
    "eu_ai_act",
    "eu_gdpr",
    "eu_dsa",
    "eu_dma",
    "eu_data_act",
    "eu_nis2",
}

EXPECTED_CELEX_IDS = {
    "32024R1689",  # EU AI Act
    "32016R0679",  # GDPR
    "32022R2065",  # DSA
    "32022R1925",  # DMA
    "32023R2854",  # Data Act
    "32022L2555",  # NIS2 Directive
}


@pytest.fixture(scope="module")
def registry() -> RegulatorySourceRegistry:
    """Load the official regulatory sources registry once for the test module."""
    return load_regulatory_sources()


@pytest.mark.unit
class TestRegulatorySourceRegistryLoading:
    """Tests for loading and schema validation of configs/regulatory_sources.yaml."""

    def test_load_default_registry_succeeds(self, registry: RegulatorySourceRegistry) -> None:
        assert isinstance(registry, RegulatorySourceRegistry)
        assert registry.schema_version == "1.0.0"
        assert registry.source_repository == "EUR-Lex"
        assert "eur-lex.europa.eu" in str(registry.base_authority_url)

    def test_registry_contains_six_initial_documents(
        self, registry: RegulatorySourceRegistry
    ) -> None:
        assert len(registry.sources) == 6

    def test_expected_document_ids_present(self, registry: RegulatorySourceRegistry) -> None:
        found_ids = {s.document_id for s in registry.sources}
        assert found_ids == EXPECTED_DOC_IDS

    def test_unique_document_ids(self, registry: RegulatorySourceRegistry) -> None:
        doc_ids = [s.document_id for s in registry.sources]
        assert len(doc_ids) == len(set(doc_ids)), "Duplicate document_id found in registry"

    def test_unique_celex_ids(self, registry: RegulatorySourceRegistry) -> None:
        celex_ids = [s.celex_id for s in registry.sources]
        assert len(celex_ids) == len(set(celex_ids)), "Duplicate celex_id found in registry"
        assert set(celex_ids) == EXPECTED_CELEX_IDS


@pytest.mark.unit
class TestRegulatorySourceFieldsAndIntegrity:
    """Tests for individual document field validity and legal instrument rules."""

    @pytest.mark.parametrize("doc_id", sorted(EXPECTED_DOC_IDS))
    def test_official_url_structure(self, registry: RegulatorySourceRegistry, doc_id: str) -> None:
        source = registry.get_by_document_id(doc_id)
        assert source is not None
        url_str = str(source.official_source_url)
        assert url_str.startswith("https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:")
        assert source.celex_id in url_str

    @pytest.mark.parametrize("doc_id", sorted(EXPECTED_DOC_IDS))
    def test_eli_uri_structure(self, registry: RegulatorySourceRegistry, doc_id: str) -> None:
        source = registry.get_by_document_id(doc_id)
        assert source is not None
        eli_str = str(source.eli_uri)
        assert eli_str.startswith("http://data.europa.eu/eli/")
        if source.instrument_type == "Directive":
            assert "/dir/" in eli_str
        else:
            assert "/reg/" in eli_str

    @pytest.mark.parametrize("doc_id", sorted(EXPECTED_DOC_IDS))
    def test_publication_and_entry_into_force_dates(
        self, registry: RegulatorySourceRegistry, doc_id: str
    ) -> None:
        source = registry.get_by_document_id(doc_id)
        assert source is not None
        assert isinstance(source.publication_date, date)
        if source.entry_into_force_date:
            assert source.publication_date <= source.entry_into_force_date

    def test_directive_transposition_deadline_required(
        self, registry: RegulatorySourceRegistry
    ) -> None:
        nis2 = registry.get_by_document_id("eu_nis2")
        assert nis2 is not None
        assert nis2.instrument_type == "Directive"
        assert nis2.transposition_deadline == date(2024, 10, 17)

    @pytest.mark.parametrize("reg_id", ["eu_ai_act", "eu_gdpr", "eu_dsa", "eu_dma", "eu_data_act"])
    def test_regulations_have_no_transposition_deadline(
        self, registry: RegulatorySourceRegistry, reg_id: str
    ) -> None:
        source = registry.get_by_document_id(reg_id)
        assert source is not None
        assert source.instrument_type == "Regulation"
        assert source.transposition_deadline is None

    def test_gdpr_consolidated_version_metadata(self, registry: RegulatorySourceRegistry) -> None:
        gdpr = registry.get_by_document_id("eu_gdpr")
        assert gdpr is not None
        assert gdpr.consolidation_available is True
        assert gdpr.consolidated_celex_id == "02016R0679-20210304"
        assert len(gdpr.corrigenda) == 2

    def test_ai_act_corrigendum_metadata(self, registry: RegulatorySourceRegistry) -> None:
        ai_act = registry.get_by_document_id("eu_ai_act")
        assert ai_act is not None
        assert len(ai_act.corrigenda) >= 1
        assert ai_act.corrigenda[0].celex_id == "32024R1689R(01)"


@pytest.mark.unit
class TestRegulatoryRegistryModelValidation:
    """Tests for Pydantic model validation rules and error conditions."""

    def test_get_by_celex(self, registry: RegulatorySourceRegistry) -> None:
        entry = registry.get_by_celex("32024R1689")
        assert entry is not None
        assert entry.document_id == "eu_ai_act"

    def test_get_by_nonexistent_celex(self, registry: RegulatorySourceRegistry) -> None:
        assert registry.get_by_celex("99999X0000") is None

    def test_get_by_nonexistent_document_id(self, registry: RegulatorySourceRegistry) -> None:
        assert registry.get_by_document_id("nonexistent_act") is None

    def test_missing_file_raises_configuration_error(self) -> None:
        with pytest.raises(ConfigurationError) as exc_info:
            load_regulatory_sources("nonexistent_sources_file.yaml")
        assert "not found" in str(exc_info.value)

    def test_malformed_yaml_raises_configuration_error(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as tmp:
            tmp.write("sources: [unclosed_list")
            tmp_path = tmp.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_regulatory_sources(tmp_path)
            assert "Failed to parse" in str(exc_info.value)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_missing_required_fields_raises_configuration_error(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as tmp:
            tmp.write(
                """
schema_version: "1.0.0"
source_repository: "EUR-Lex"
last_registry_update: "2026-11-02"
sources:
  - document_id: "incomplete_entry"
    name: "Short"
"""
            )
            tmp_path = tmp.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_regulatory_sources(tmp_path)
            assert "Validation failed" in str(exc_info.value)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_directive_without_transposition_fails_validation(self) -> None:
        with pytest.raises(ValidationError):
            RegulatorySourceEntry(
                document_id="invalid_directive",
                name="Directive (EU) 2024/9999 of the European Parliament and Council",
                abbreviation="TestDir",
                instrument_type="Directive",
                celex_id="32024L9999",
                eli_uri="http://data.europa.eu/eli/dir/2024/9999/oj",  # type: ignore[arg-type]
                official_source_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024L9999",  # type: ignore[arg-type]
                jurisdiction="EU",
                publication_date=date(2024, 1, 1),
                entry_into_force_date=date(2024, 1, 20),
                transposition_deadline=None,  # Invalid for Directives!
                language="EN",
                preferred_format="HTML",
                available_formats=["HTML"],
                consolidation_available=False,
                source_authority="EU",
                status="in_force",
                last_verified_at="2026-11-02T00:00:00Z",  # type: ignore[arg-type]
            )

    def test_regulation_with_transposition_fails_validation(self) -> None:
        with pytest.raises(ValidationError):
            RegulatorySourceEntry(
                document_id="invalid_regulation",
                name="Regulation (EU) 2024/9999 of the European Parliament and Council",
                abbreviation="TestReg",
                instrument_type="Regulation",
                celex_id="32024R9999",
                eli_uri="http://data.europa.eu/eli/reg/2024/9999/oj",  # type: ignore[arg-type]
                official_source_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R9999",  # type: ignore[arg-type]
                jurisdiction="EU",
                publication_date=date(2024, 1, 1),
                entry_into_force_date=date(2024, 1, 20),
                transposition_deadline=date(2024, 10, 1),  # Invalid for Regulations!
                language="EN",
                preferred_format="HTML",
                available_formats=["HTML"],
                consolidation_available=False,
                source_authority="EU",
                status="in_force",
                last_verified_at="2026-11-02T00:00:00Z",  # type: ignore[arg-type]
            )
