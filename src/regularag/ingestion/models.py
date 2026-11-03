"""
Pydantic data models for the Regulatory Source Registry and Ingestion Data Contract.

Defines schemas for authoritative legal sources, document metadata contracts,
and verification rules ensuring adherence to EUR-Lex standards.
"""

from __future__ import annotations

import datetime as dt  # noqa: TC003 (needed at runtime by Pydantic)
import re
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

# -----------------------------------------------------------------------------
# CELEX Validation & Classification Standards
# -----------------------------------------------------------------------------
# EUR-Lex CELEX identifiers follow a structured schema: [Sector][Year][Type][Number][Suffix]
#
# 1. Original Legal Acts (Sector 1-4, predominantly Sector 3 for secondary legislation):
#    Format: 3YYYY[Type]NNNN (e.g. 32024R1689, 32016R0679, 32022L2555)
# 2. Consolidated Texts (Sector 0):
#    Format: 0YYYY[Type]NNNN-YYYYMMDD (e.g. 02016R0679-20210304)
# 3. Corrigenda (Official Corrections published in the OJ):
#    Format: 3YYYY[Type]NNNNR(XX) (e.g. 32024R1689R(01), 32016R0679R(02))
# -----------------------------------------------------------------------------

CELEX_ORIGINAL_ACT_REGEX = r"^[1-4]\d{4}[A-Z]{1,2}\d{4}$"
CELEX_CONSOLIDATED_REGEX = r"^0\d{4}[A-Z]{1,2}\d{4}-\d{8}$"
CELEX_CORRIGENDUM_REGEX = r"^[1-4]\d{4}[A-Z]{1,2}\d{4}R\(\d{2}\)$"


class CelexType(StrEnum):
    """Classification of EUR-Lex CELEX identifiers by legal nature."""

    ORIGINAL_ACT = "original_act"
    CONSOLIDATED = "consolidated"
    CORRIGENDUM = "corrigendum"


def classify_celex(celex_id: str) -> CelexType:
    """Classify a CELEX identifier into its legal category.

    Args:
        celex_id: Official CELEX string to inspect.

    Returns:
        The corresponding :class:`CelexType` member.

    Raises:
        ValueError: If the identifier does not match any known CELEX pattern.
    """
    if re.match(CELEX_ORIGINAL_ACT_REGEX, celex_id):
        return CelexType.ORIGINAL_ACT
    if re.match(CELEX_CONSOLIDATED_REGEX, celex_id):
        return CelexType.CONSOLIDATED
    if re.match(CELEX_CORRIGENDUM_REGEX, celex_id):
        return CelexType.CORRIGENDUM
    raise ValueError(
        f"Invalid or unsupported CELEX identifier format: '{celex_id}'. "
        "Expected original legal act (e.g. '32024R1689'), consolidated text "
        "(e.g. '02016R0679-20210304'), or corrigendum (e.g. '32024R1689R(01)')."
    )


class CorrigendumEntry(BaseModel):
    """Metadata regarding an official corrigendum (correction) published in the OJ."""

    celex_id: str = Field(
        description="Official CELEX identifier of the corrigendum (e.g., 32024R1689R(01))",
    )
    publication_date: dt.date = Field(description="Date the corrigendum was published in the OJ")
    description: str = Field(description="Summary of the scope and nature of the correction")

    @field_validator("celex_id")
    @classmethod
    def validate_celex_type(cls, value: str) -> str:
        """Ensure corrigendum celex_id matches the Corrigendum CELEX format."""
        celex_type = classify_celex(value)
        if celex_type != CelexType.CORRIGENDUM:
            raise ValueError(
                f"Corrigendum celex_id must be of type CORRIGENDUM, got '{value}' ({celex_type})."
            )
        return value


class PhasedApplicationItem(BaseModel):
    """Timeline entry for regulations with staggered application dates."""

    phase: str = Field(description="Name or description of the phased milestone")
    date: dt.date = Field(description="Effective milestone date")
    reference: str = Field(description="Legal article reference establishing this date")


class RegulatorySourceEntry(BaseModel):
    """Schema representing an authoritative regulatory document entry in the registry."""

    document_id: str = Field(
        pattern=r"^[a-z0-9_]+$",
        description="Unique system slug for the regulatory document",
    )
    name: str = Field(min_length=10, description="Full official legal title")
    abbreviation: str = Field(min_length=2, description="Recognized acronym or common title")
    instrument_type: Literal["Regulation", "Directive", "Decision"] = Field(
        description="EU legal instrument classification"
    )
    celex_id: str = Field(
        description="Official CELEX identifier of the primary authentic legal act",
    )
    eli_uri: HttpUrl = Field(description="Official European Legislation Identifier URI")
    official_source_url: HttpUrl = Field(description="Authoritative EUR-Lex document URL")
    jurisdiction: Literal["EU"] = Field(default="EU", description="Legal jurisdiction")
    publication_date: dt.date = Field(description="Publication date in the Official Journal")
    entry_into_force_date: dt.date | None = Field(
        default=None, description="Date the act entered into legal force"
    )
    application_date: dt.date | None = Field(
        default=None, description="Date from which the act becomes enforceable"
    )
    transposition_deadline: dt.date | None = Field(
        default=None,
        description="Member State transposition deadline (applicable to Directives)",
    )
    language: str = Field(default="EN", max_length=5, description="ISO language code")
    preferred_format: Literal["HTML", "XML", "PDF"] = Field(
        default="HTML", description="Preferred structural representation for RAG"
    )
    available_formats: list[Literal["HTML", "XML", "PDF"]] = Field(
        min_length=1, description="Official formats distributed on EUR-Lex"
    )
    consolidation_available: bool = Field(
        description="Whether an official consolidated version exists on EUR-Lex"
    )
    consolidated_celex_id: str | None = Field(
        default=None,
        description="CELEX ID of the latest consolidated text, if applicable",
    )
    source_authority: str = Field(description="Institutional author(s) of the legal instrument")
    status: str = Field(description="Current legal status")
    official_journal_reference: str | None = Field(
        default=None, description="Official Journal citation (e.g., OJ L 119, 4.5.2016)"
    )
    corrigenda: list[CorrigendumEntry] = Field(
        default_factory=list, description="List of published corrigenda"
    )
    phased_application_timeline: list[PhasedApplicationItem] = Field(
        default_factory=list, description="Staggered effective application milestones"
    )
    notes: str | None = Field(default=None, description="Legal context and operational remarks")
    last_verified_at: dt.datetime = Field(
        description="Timestamp of the most recent verification against EUR-Lex"
    )

    @field_validator("celex_id")
    @classmethod
    def validate_primary_celex(cls, value: str) -> str:
        """Ensure primary celex_id represents an authentic original legal act."""
        celex_type = classify_celex(value)
        if celex_type != CelexType.ORIGINAL_ACT:
            raise ValueError(
                f"Primary celex_id must be an original legal act (e.g. '32024R1689'), "
                f"got '{value}' ({celex_type})."
            )
        return value

    @field_validator("consolidated_celex_id")
    @classmethod
    def validate_consolidated_celex(cls, value: str | None) -> str | None:
        """Ensure consolidated_celex_id matches the consolidated CELEX format."""
        if value is not None:
            celex_type = classify_celex(value)
            if celex_type != CelexType.CONSOLIDATED:
                raise ValueError(
                    "consolidated_celex_id must be a consolidated text "
                    f"(e.g. '02016R0679-20210304'), got '{value}' ({celex_type})."
                )
        return value

    @field_validator("transposition_deadline")
    @classmethod
    def validate_transposition(cls, value: dt.date | None, info: object) -> dt.date | None:
        """Verify that Directives specify a transposition deadline."""
        data = getattr(info, "data", {})
        if data.get("instrument_type") == "Directive" and value is None:
            raise ValueError("Directives must specify a transposition_deadline.")
        if data.get("instrument_type") == "Regulation" and value is not None:
            raise ValueError(
                "Regulations do not have a transposition_deadline (directly applicable)."
            )
        return value

    @model_validator(mode="after")
    def validate_cross_field_relationships(self) -> Self:
        """Validate legal consistency across related fields."""
        # 1. Consolidation consistency
        if self.consolidation_available and self.consolidated_celex_id is None:
            raise ValueError(
                f"Document '{self.document_id}' specifies consolidation_available=True "
                "but consolidated_celex_id is None."
            )
        if not self.consolidation_available and self.consolidated_celex_id is not None:
            raise ValueError(
                f"Document '{self.document_id}' specifies consolidation_available=False "
                f"but has consolidated_celex_id='{self.consolidated_celex_id}'."
            )

        # 2. Referential integrity: Consolidated base act must match primary CELEX
        if self.consolidated_celex_id is not None:
            base_in_cons = self.consolidated_celex_id[1:10]
            base_in_orig = self.celex_id[1:10]
            if base_in_cons != base_in_orig:
                raise ValueError(
                    f"Consolidated CELEX '{self.consolidated_celex_id}' base act '{base_in_cons}' "
                    f"does not match document celex_id '{self.celex_id}' ('{base_in_orig}')."
                )

        # 3. Referential integrity: Corrigenda must belong to parent act
        for corr in self.corrigenda:
            if not corr.celex_id.startswith(self.celex_id + "R("):
                raise ValueError(
                    f"Corrigendum '{corr.celex_id}' does not match "
                    f"parent celex_id '{self.celex_id}'."
                )

        # 4. Publication vs Entry-into-force date ordering
        if self.entry_into_force_date and self.entry_into_force_date < self.publication_date:
            raise ValueError(
                f"entry_into_force_date ({self.entry_into_force_date}) cannot precede "
                f"publication_date ({self.publication_date})."
            )

        return self


class RegulatorySourceRegistry(BaseModel):
    """Root model for the regulatory source registry configuration."""

    schema_version: str = Field(default="1.0.0")
    source_repository: str = Field(default="EUR-Lex")
    base_authority_url: HttpUrl = Field(default="https://eur-lex.europa.eu")  # type: ignore[assignment]
    last_registry_update: dt.date
    sources: list[RegulatorySourceEntry] = Field(min_length=1)

    def get_by_document_id(self, document_id: str) -> RegulatorySourceEntry | None:
        """Find a source entry by its unique document ID."""
        for source in self.sources:
            if source.document_id == document_id:
                return source
        return None

    def get_by_celex(self, celex_id: str) -> RegulatorySourceEntry | None:
        """Find a source entry by its CELEX ID."""
        for source in self.sources:
            if source.celex_id == celex_id:
                return source
        return None
