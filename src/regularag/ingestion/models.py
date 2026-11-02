"""
Pydantic data models for the Regulatory Source Registry and Ingestion Data Contract.

Defines schemas for authoritative legal sources, document metadata contracts,
and verification rules ensuring adherence to EUR-Lex standards.
"""

from __future__ import annotations

import datetime as dt  # noqa: TC003 (needed at runtime by Pydantic)
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class CorrigendumEntry(BaseModel):
    """Metadata regarding an official corrigendum (correction) published in the OJ."""

    celex_id: str = Field(description="CELEX identifier of the corrigendum")
    publication_date: dt.date = Field(description="Date the corrigendum was published in the OJ")
    description: str = Field(description="Summary of the scope and nature of the correction")


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
        pattern=r"^[0-9]{1}[0-9]{4}[A-Z][0-9]{4}.*$",
        description="Official CELEX identifier assigned by the Publications Office",
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
        default=None, description="CELEX ID of the latest consolidated text, if applicable"
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
