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
    CelexType,
    CorrigendumEntry,
    RegulatorySourceEntry,
    RegulatorySourceRegistry,
    classify_celex,
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

    def test_publication_after_entry_into_force_fails_validation(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            RegulatorySourceEntry(
                document_id="invalid_dates",
                name="Regulation (EU) 2024/9999 of the European Parliament and Council",
                abbreviation="TestDates",
                instrument_type="Regulation",
                celex_id="32024R9999",
                eli_uri="http://data.europa.eu/eli/reg/2024/9999/oj",  # type: ignore[arg-type]
                official_source_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R9999",  # type: ignore[arg-type]
                jurisdiction="EU",
                publication_date=date(2024, 6, 1),
                entry_into_force_date=date(2024, 1, 1),  # Earlier than publication date!
                transposition_deadline=None,
                language="EN",
                preferred_format="HTML",
                available_formats=["HTML"],
                consolidation_available=False,
                source_authority="EU",
                status="in_force",
                last_verified_at="2026-11-02T00:00:00Z",  # type: ignore[arg-type]
            )
        assert "cannot precede publication_date" in str(exc_info.value)


@pytest.mark.unit
class TestCelexClassificationAndValidation:
    """Comprehensive tests for CELEX identifier parsing, classification, and validation."""

    @pytest.mark.parametrize(
        ("celex_id", "expected_type"),
        [
            # Original Acts (Regulations, Directives, Decisions across Sectors 1-4)
            ("32024R1689", CelexType.ORIGINAL_ACT),  # EU AI Act
            ("32016R0679", CelexType.ORIGINAL_ACT),  # GDPR
            ("32022R2065", CelexType.ORIGINAL_ACT),  # DSA
            ("32022R1925", CelexType.ORIGINAL_ACT),  # DMA
            ("32023R2854", CelexType.ORIGINAL_ACT),  # Data Act
            ("32022L2555", CelexType.ORIGINAL_ACT),  # NIS2 Directive
            ("32019R0881", CelexType.ORIGINAL_ACT),  # Cybersecurity Act
            ("32023D0001", CelexType.ORIGINAL_ACT),  # Decision
            # Consolidated texts (Sector 0)
            ("02016R0679-20210304", CelexType.CONSOLIDATED),  # GDPR consolidated
            ("02022R2065-20240217", CelexType.CONSOLIDATED),  # DSA synthetic consolidation
            ("02024R1689-20250202", CelexType.CONSOLIDATED),  # AI Act synthetic consolidation
            ("02022L2555-20230116", CelexType.CONSOLIDATED),  # NIS2 synthetic consolidation
            # Corrigenda (Sector 3 with R(XX))
            ("32024R1689R(01)", CelexType.CORRIGENDUM),  # AI Act corrigendum 1
            ("32016R0679R(02)", CelexType.CORRIGENDUM),  # GDPR corrigendum 2
            ("32016R0679R(03)", CelexType.CORRIGENDUM),  # GDPR corrigendum 3
            ("32022L2555R(01)", CelexType.CORRIGENDUM),  # NIS2 corrigendum 1
        ],
    )
    def test_classify_celex_valid_identifiers(
        self, celex_id: str, expected_type: CelexType
    ) -> None:
        assert classify_celex(celex_id) == expected_type

    @pytest.mark.parametrize(
        "invalid_celex",
        [
            "",  # Empty string
            "   ",  # Whitespace
            "not_a_celex",  # Arbitrary string
            "99999X0000",  # Invalid sector and format
            "32024R",  # Truncated
            "32024R168900",  # Too many digits
            "32024r1689",  # Lowercase type letter
            "02016R0679",  # Consolidated prefix without date suffix
            "02016R0679-202103",  # Incomplete date suffix
            "02016R0679_20210304",  # Underscore instead of hyphen
            "32024R1689R1",  # Corrigendum missing parens
            "32024R1689(01)",  # Corrigendum missing 'R'
            "32024R1689R(1)",  # Corrigendum single digit without zero pad
            "32024R1689R(100)",  # Corrigendum 3 digits
        ],
    )
    def test_classify_celex_invalid_identifiers_raises(self, invalid_celex: str) -> None:
        with pytest.raises(ValueError, match="Invalid or unsupported CELEX identifier format"):
            classify_celex(invalid_celex)

    def test_consolidated_celex_rejected_as_primary_act(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            RegulatorySourceEntry(
                document_id="invalid_celex_type",
                name="Consolidated Regulation (EU) 2016/679",
                abbreviation="ConsGDPR",
                instrument_type="Regulation",
                celex_id="02016R0679-20210304",  # Consolidated CELEX instead of original!
                eli_uri="http://data.europa.eu/eli/reg/2016/679/oj",  # type: ignore[arg-type]
                official_source_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679",  # type: ignore[arg-type]
                jurisdiction="EU",
                publication_date=date(2016, 5, 4),
                entry_into_force_date=date(2016, 5, 24),
                transposition_deadline=None,
                language="EN",
                preferred_format="HTML",
                available_formats=["HTML"],
                consolidation_available=False,
                source_authority="EU",
                status="in_force",
                last_verified_at="2026-11-02T00:00:00Z",  # type: ignore[arg-type]
            )
        assert "Primary celex_id must be an original legal act" in str(exc_info.value)

    def test_corrigendum_celex_rejected_as_primary_act(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            RegulatorySourceEntry(
                document_id="invalid_corr_primary",
                name="Corrigendum to Regulation (EU) 2024/1689",
                abbreviation="CorrAIAct",
                instrument_type="Regulation",
                celex_id="32024R1689R(01)",  # Corrigendum CELEX instead of original!
                eli_uri="http://data.europa.eu/eli/reg/2024/1689/oj",  # type: ignore[arg-type]
                official_source_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689",  # type: ignore[arg-type]
                jurisdiction="EU",
                publication_date=date(2024, 7, 12),
                entry_into_force_date=date(2024, 8, 1),
                transposition_deadline=None,
                language="EN",
                preferred_format="HTML",
                available_formats=["HTML"],
                consolidation_available=False,
                source_authority="EU",
                status="in_force",
                last_verified_at="2026-11-02T00:00:00Z",  # type: ignore[arg-type]
            )
        assert "Primary celex_id must be an original legal act" in str(exc_info.value)

    def test_original_celex_rejected_as_consolidated_id(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            RegulatorySourceEntry(
                document_id="invalid_cons_field",
                name="Regulation (EU) 2016/679 of the European Parliament and Council",
                abbreviation="GDPR",
                instrument_type="Regulation",
                celex_id="32016R0679",
                eli_uri="http://data.europa.eu/eli/reg/2016/679/oj",  # type: ignore[arg-type]
                official_source_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679",  # type: ignore[arg-type]
                jurisdiction="EU",
                publication_date=date(2016, 5, 4),
                entry_into_force_date=date(2016, 5, 24),
                transposition_deadline=None,
                language="EN",
                preferred_format="HTML",
                available_formats=["HTML"],
                consolidation_available=True,
                consolidated_celex_id="32016R0679",  # Invalid! Not consolidated CELEX
                source_authority="EU",
                status="in_force",
                last_verified_at="2026-11-02T00:00:00Z",  # type: ignore[arg-type]
            )
        assert "consolidated_celex_id must be a consolidated text" in str(exc_info.value)

    def test_consolidated_celex_base_mismatch_raises(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            RegulatorySourceEntry(
                document_id="mismatched_cons",
                name="Regulation (EU) 2024/1689 AI Act",
                abbreviation="AI Act",
                instrument_type="Regulation",
                celex_id="32024R1689",
                eli_uri="http://data.europa.eu/eli/reg/2024/1689/oj",  # type: ignore[arg-type]
                official_source_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689",  # type: ignore[arg-type]
                jurisdiction="EU",
                publication_date=date(2024, 7, 12),
                entry_into_force_date=date(2024, 8, 1),
                transposition_deadline=None,
                language="EN",
                preferred_format="HTML",
                available_formats=["HTML"],
                consolidation_available=True,
                consolidated_celex_id="02016R0679-20210304",  # GDPR ID assigned to AI Act!
                source_authority="EU",
                status="in_force",
                last_verified_at="2026-11-02T00:00:00Z",  # type: ignore[arg-type]
            )
        assert "does not match document celex_id" in str(exc_info.value)

    def test_corrigendum_parent_mismatch_raises(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            RegulatorySourceEntry(
                document_id="mismatched_corr",
                name="Regulation (EU) 2024/1689 AI Act",
                abbreviation="AI Act",
                instrument_type="Regulation",
                celex_id="32024R1689",
                eli_uri="http://data.europa.eu/eli/reg/2024/1689/oj",  # type: ignore[arg-type]
                official_source_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689",  # type: ignore[arg-type]
                jurisdiction="EU",
                publication_date=date(2024, 7, 12),
                entry_into_force_date=date(2024, 8, 1),
                transposition_deadline=None,
                language="EN",
                preferred_format="HTML",
                available_formats=["HTML"],
                consolidation_available=False,
                corrigenda=[
                    CorrigendumEntry(
                        celex_id="32016R0679R(02)",  # GDPR corrigendum attached to AI Act!
                        publication_date=date(2018, 5, 23),
                        description="Mismatched corrigendum",
                    )
                ],
                source_authority="EU",
                status="in_force",
                last_verified_at="2026-11-02T00:00:00Z",  # type: ignore[arg-type]
            )
        assert "does not match parent celex_id" in str(exc_info.value)

    def test_corrigendum_model_rejects_original_celex(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            CorrigendumEntry(
                celex_id="32024R1689",  # Original act passed as corrigendum
                publication_date=date(2024, 11, 20),
                description="Invalid corrigendum",
            )
        assert "Corrigendum celex_id must be of type CORRIGENDUM" in str(exc_info.value)

    def test_consolidation_available_true_without_id_fails(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            RegulatorySourceEntry(
                document_id="missing_cons_id",
                name="Regulation (EU) 2016/679 GDPR",
                abbreviation="GDPR",
                instrument_type="Regulation",
                celex_id="32016R0679",
                eli_uri="http://data.europa.eu/eli/reg/2016/679/oj",  # type: ignore[arg-type]
                official_source_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679",  # type: ignore[arg-type]
                jurisdiction="EU",
                publication_date=date(2016, 5, 4),
                entry_into_force_date=date(2016, 5, 24),
                transposition_deadline=None,
                language="EN",
                preferred_format="HTML",
                available_formats=["HTML"],
                consolidation_available=True,
                consolidated_celex_id=None,  # Missing!
                source_authority="EU",
                status="in_force",
                last_verified_at="2026-11-02T00:00:00Z",  # type: ignore[arg-type]
            )
        assert "specifies consolidation_available=True but consolidated_celex_id is None" in str(
            exc_info.value
        )

    def test_consolidation_available_false_with_id_fails(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            RegulatorySourceEntry(
                document_id="spurious_cons_id",
                name="Regulation (EU) 2024/1689 AI Act",
                abbreviation="AI Act",
                instrument_type="Regulation",
                celex_id="32024R1689",
                eli_uri="http://data.europa.eu/eli/reg/2024/1689/oj",  # type: ignore[arg-type]
                official_source_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689",  # type: ignore[arg-type]
                jurisdiction="EU",
                publication_date=date(2024, 7, 12),
                entry_into_force_date=date(2024, 8, 1),
                transposition_deadline=None,
                language="EN",
                preferred_format="HTML",
                available_formats=["HTML"],
                consolidation_available=False,
                consolidated_celex_id="02024R1689-20250202",  # Should be None!
                source_authority="EU",
                status="in_force",
                last_verified_at="2026-11-02T00:00:00Z",  # type: ignore[arg-type]
            )
        assert "specifies consolidation_available=False but has consolidated_celex_id" in str(
            exc_info.value
        )
