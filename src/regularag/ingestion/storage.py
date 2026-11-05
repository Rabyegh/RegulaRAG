"""
Raw artifact storage manager for acquired regulatory documents.

Manages deterministic filesystem layouts, atomic writes, metadata sidecars,
and version integrity validation according to docs/data-ingestion-design.md.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import structlog

from regularag.core.exceptions import VersionIntegrityConflictError
from regularag.ingestion.models import (
    AcquisitionAuditMetadata,
    ArtifactSidecarMetadata,
    FileAuditMetadata,
    ValidationAuditMetadata,
    canonical_artifact_id,
    canonical_artifact_version_id,
)

if TYPE_CHECKING:
    from regularag.ingestion.models import RegulatorySourceEntry

logger = structlog.get_logger(__name__)


class ExistingArtifact:
    """Represents a previously acquired local document artifact."""

    def __init__(
        self,
        file_path: Path,
        sidecar_path: Path | None = None,
        metadata: ArtifactSidecarMetadata | None = None,
    ) -> None:
        self.file_path = file_path
        self.sidecar_path = sidecar_path
        self.metadata = metadata

    @property
    def is_complete(self) -> bool:
        """True if both the document payload and valid sidecar metadata exist."""
        return (
            self.file_path.is_file()
            and self.sidecar_path is not None
            and self.sidecar_path.is_file()
            and self.metadata is not None
        )

    @property
    def sha256_checksum(self) -> str | None:
        """Return the SHA-256 hash recorded in the sidecar, or compute directly from disk."""
        if self.metadata and self.metadata.file_metadata:
            return self.metadata.file_metadata.sha256_checksum
        if self.file_path.is_file():
            hasher = hashlib.sha256()
            with open(self.file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        return None

    @property
    def etag(self) -> str | None:
        """Return the HTTP ETag recorded in the sidecar, if available."""
        if self.metadata and self.metadata.acquisition:
            return self.metadata.acquisition.etag
        return None

    @property
    def last_modified(self) -> str | None:
        """Return the HTTP Last-Modified string from the sidecar, if available."""
        if self.metadata and self.metadata.acquisition:
            return self.metadata.acquisition.last_modified_header
        return None


class RawArtifactStorage:
    """Manages raw document storage and metadata sidecars in data/raw."""

    def __init__(self, root_dir: Path | str) -> None:
        self.root_dir = Path(root_dir).resolve()

    def resolve_version_dir(
        self,
        source: RegulatorySourceEntry,
        category: str = "original_act",
        corrigendum_celex: str | None = None,
    ) -> Path:
        """Compute the deterministic version directory for a regulatory document.

        Layout:
        - Original:     {root}/{jurisdiction}/{document_id}/original_{pub_date}/
        - Consolidated: {root}/{jurisdiction}/{document_id}/consolidated_{cons_date}/
        - Corrigenda:   {root}/{jurisdiction}/{document_id}/corrigenda/{normalized_celex}/
        """
        base = self.root_dir / source.jurisdiction.lower() / source.document_id

        if category == "corrigendum" and corrigendum_celex:
            clean_corr = corrigendum_celex.replace("(", "").replace(")", "")
            return base / "corrigenda" / clean_corr
        if category == "consolidated_text" and source.consolidated_celex_id:
            # Suffix of consolidated CELEX is YYYYMMDD
            date_part = source.consolidated_celex_id.split("-")[-1]
            formatted_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
            return base / f"consolidated_{formatted_date}"
        return base / f"original_{source.publication_date.isoformat()}"

    def resolve_artifact_paths(
        self,
        source: RegulatorySourceEntry,
        category: str = "original_act",
        target_format: str = "HTML",
        corrigendum_celex: str | None = None,
    ) -> tuple[Path, Path]:
        """Return (target_file_path, sidecar_file_path) for an artifact."""
        version_dir = self.resolve_version_dir(
            source=source,
            category=category,
            corrigendum_celex=corrigendum_celex,
        )
        ext = target_format.lower()
        active_celex = corrigendum_celex or source.celex_id
        clean_celex = active_celex.replace("(", "").replace(")", "")
        cat_suffix = "original" if category == "original_act" else category

        file_name = f"{source.document_id}_{clean_celex}_{cat_suffix}.{ext}"
        sidecar_name = f"{source.document_id}_{clean_celex}_{cat_suffix}.meta.json"

        return version_dir / file_name, version_dir / sidecar_name

    def get_existing_artifact(
        self,
        source: RegulatorySourceEntry,
        category: str = "original_act",
        target_format: str = "HTML",
        corrigendum_celex: str | None = None,
    ) -> ExistingArtifact | None:
        """Inspect storage for an already acquired artifact and its sidecar."""
        file_path, sidecar_path = self.resolve_artifact_paths(
            source=source,
            category=category,
            target_format=target_format,
            corrigendum_celex=corrigendum_celex,
        )

        has_file = file_path.is_file()
        has_sidecar = sidecar_path.is_file()

        if not has_file and not has_sidecar:
            return None

        metadata: ArtifactSidecarMetadata | None = None
        if has_sidecar:
            try:
                raw_json = sidecar_path.read_text(encoding="utf-8")
                metadata = ArtifactSidecarMetadata.model_validate_json(raw_json)
            except Exception as exc:
                logger.warning(
                    "Failed to parse existing sidecar metadata",
                    sidecar_path=str(sidecar_path),
                    error=str(exc),
                )

        return ExistingArtifact(
            file_path=file_path,
            sidecar_path=sidecar_path if has_sidecar else None,
            metadata=metadata,
        )

    def write_sidecar(
        self,
        sidecar_file: Path,
        metadata: ArtifactSidecarMetadata,
    ) -> None:
        """Write metadata sidecar atomically via temporary file."""
        sidecar_file.parent.mkdir(parents=True, exist_ok=True)
        sidecar_tmp = sidecar_file.with_name(f"{sidecar_file.name}.tmp.{uuid4().hex[:8]}")
        try:
            sidecar_dict = metadata.model_dump(by_alias=True, mode="json")
            sidecar_tmp.write_text(
                json.dumps(sidecar_dict, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            sidecar_tmp.replace(sidecar_file)
        finally:
            if sidecar_tmp.exists():
                sidecar_tmp.unlink(missing_ok=True)

    def verify_artifact_integrity(
        self,
        source: RegulatorySourceEntry,
        category: str = "original_act",
        target_format: str = "HTML",
        corrigendum_celex: str | None = None,
    ) -> tuple[str, ExistingArtifact | None]:
        """Verify presence and internal consistency of an artifact pair.

        Returns:
            A tuple of (status, existing_artifact), where status is one of:
            - 'COMPLETE': Both payload and sidecar exist, sidecar is valid and checksum matches.
            - 'MISSING_SIDECAR': Payload exists on disk but sidecar is missing or invalid.
            - 'ORPHAN_SIDECAR': Sidecar exists on disk but raw document file is missing.
            - 'CHECKSUM_MISMATCH': Both exist but sidecar checksum disagrees with disk file.
            - 'NOT_FOUND': Neither payload nor sidecar exists.
        """
        existing = self.get_existing_artifact(
            source=source,
            category=category,
            target_format=target_format,
            corrigendum_celex=corrigendum_celex,
        )
        if existing is None:
            return "NOT_FOUND", None

        has_file = existing.file_path.is_file()
        has_sidecar = (
            existing.sidecar_path is not None
            and existing.sidecar_path.is_file()
            and existing.metadata is not None
        )

        if has_file and not has_sidecar:
            return "MISSING_SIDECAR", existing
        if not has_file and has_sidecar:
            return "ORPHAN_SIDECAR", existing

        # Both present — verify checksum
        if existing.metadata and existing.metadata.file_metadata:
            sidecar_hash = existing.metadata.file_metadata.sha256_checksum
            # Compute actual disk file hash
            hasher = hashlib.sha256()
            with open(existing.file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
            actual_hash = hasher.hexdigest()
            if sidecar_hash != actual_hash:
                return "CHECKSUM_MISMATCH", existing

        return "COMPLETE", existing

    def create_staging_file(self, target_file: Path) -> Path:
        """Create and return a temporary staging path in the target directory."""
        target_file.parent.mkdir(parents=True, exist_ok=True)
        staging_name = f"{target_file.name}.tmp.{uuid4().hex[:8]}"
        return target_file.parent / staging_name

    def commit_artifact(
        self,
        staging_file: Path,
        target_file: Path,
        sidecar_file: Path,
        metadata: ArtifactSidecarMetadata,
        existing_artifact: ExistingArtifact | None = None,
    ) -> None:
        """Atomically commit a downloaded staging file and write its sidecar metadata.

        Raises:
            VersionIntegrityConflictError: If an existing artifact is found whose
                SHA-256 differs from the newly acquired artifact.
        """
        new_sha256 = metadata.file_metadata.sha256_checksum

        # Integrity conflict check
        if existing_artifact and existing_artifact.file_path.exists():
            existing_hash = existing_artifact.sha256_checksum
            if existing_hash and existing_hash != new_sha256:
                # Remove staging file to avoid leaving artifacts
                staging_file.unlink(missing_ok=True)
                raise VersionIntegrityConflictError(
                    f"Version integrity conflict for artifact '{metadata.artifact_version_id}': "
                    f"Existing SHA-256 ({existing_hash}) differs from new payload ({new_sha256}). "
                    "Cannot overwrite without explicit administrative resolution.",
                    document_id=metadata.document_id,
                    celex_id=metadata.celex_id,
                    existing_hash=existing_hash,
                    new_hash=new_sha256,
                )

        # Prepare sidecar in staging file before touching target_file
        sidecar_tmp = sidecar_file.with_name(f"{sidecar_file.name}.tmp.{uuid4().hex[:8]}")
        try:
            sidecar_dict = metadata.model_dump(by_alias=True, mode="json")
            sidecar_tmp.write_text(
                json.dumps(sidecar_dict, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            # Both payload and sidecar staging are ready: commit both atomically
            staging_file.replace(target_file)
            sidecar_tmp.replace(sidecar_file)
        finally:
            if sidecar_tmp.exists():
                sidecar_tmp.unlink(missing_ok=True)

        logger.info(
            "Raw artifact committed successfully",
            artifact_id=metadata.artifact_id,
            version_id=metadata.artifact_version_id,
            target_path=str(target_file),
            size_bytes=metadata.file_metadata.file_size_bytes,
            sha256=metadata.file_metadata.sha256_checksum,
        )

    def build_sidecar_metadata(
        self,
        source: RegulatorySourceEntry,
        retrieved_at: dt.datetime,
        http_status: int,
        etag: str | None,
        last_modified: str | None,
        duration_seconds: float,
        format_name: str,
        media_type: str,
        file_size_bytes: int,
        sha256_checksum: str,
        target_file: Path,
        sidecar_file: Path,
        category: str = "original_act",
        corrigendum_celex: str | None = None,
        checks_passed: list[str] | None = None,
    ) -> ArtifactSidecarMetadata:
        """Construct a validated ArtifactSidecarMetadata model instance."""
        active_celex = corrigendum_celex or source.celex_id
        version_id = canonical_artifact_version_id(
            celex_id=active_celex,
            publication_date=source.publication_date,
            category=category,
        )
        art_id = canonical_artifact_id(
            celex_id=active_celex,
            publication_date=source.publication_date,
            language=source.language,
            fmt=format_name,
        )

        try:
            rel_target = str(target_file.relative_to(self.root_dir.parent))
            rel_sidecar = str(sidecar_file.relative_to(self.root_dir.parent))
        except ValueError:
            rel_target = str(target_file)
            rel_sidecar = str(sidecar_file)

        return ArtifactSidecarMetadata(
            artifact_id=art_id,
            artifact_version_id=version_id,
            document_id=source.document_id,
            name=source.name,
            abbreviation=source.abbreviation,
            instrument_type=source.instrument_type,
            celex_id=active_celex,
            eli_uri=str(source.eli_uri),
            jurisdiction=source.jurisdiction,
            source_authority=source.source_authority,
            source_url=str(source.official_source_url),
            language=source.language,
            document_category=category,
            is_consolidated=(category == "consolidated_text"),
            consolidation_date=None,
            is_corrigendum=(category == "corrigendum"),
            corrigendum_parent_celex=source.celex_id if category == "corrigendum" else None,
            publication_date=source.publication_date,
            entry_into_force_date=source.entry_into_force_date,
            application_date=source.application_date,
            transposition_deadline=source.transposition_deadline,
            acquisition=AcquisitionAuditMetadata(
                retrieved_at=retrieved_at,
                http_status=http_status,
                etag=etag,
                last_modified_header=last_modified,
                retrieval_duration_seconds=round(duration_seconds, 3),
            ),
            file_metadata=FileAuditMetadata(
                format=format_name.upper(),
                media_type=media_type,
                file_size_bytes=file_size_bytes,
                sha256_checksum=sha256_checksum,
                storage_relpath=rel_target.replace("\\", "/"),
                sidecar_relpath=rel_sidecar.replace("\\", "/"),
            ),
            validation=ValidationAuditMetadata(
                is_valid=True,
                validated_at=dt.datetime.now(dt.UTC),
                validation_checks_passed=checks_passed
                or ["size_greater_than_zero", "media_type_valid", "sha256_verified"],
            ),
        )
