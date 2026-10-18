"""Release manifest ``releases/<id>/manifest.json`` and pointer ``releases/current.json``.

The release id is ``YYYYMMDDTHHMMSSZ-<8 hex>`` where the 8 hex are the start of the SHA-256 of the
manifest *identity* (canonical JSON of schema, created_at, audience, run_id, inputs and versions).
The identity is known before any file is rendered, so pages can embed the release id; file hashes
are recorded separately in ``files`` and the pointer pins the full manifest by its SHA-256.
"""

# Pydantic copies mutable defaults per instance, so `= []` / `= {}` field defaults are safe.
# ruff: noqa: RUF012

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, Self

from pydantic import Field, model_validator

from docwiki.contracts._base import ContractModel, Hex64, RelPath, Sha256Ref, UtcDateTime
from docwiki.contracts.enums import Sensitivity
from docwiki.contracts.gates import GateResult
from docwiki.contracts.ids import RELEASE_ID_RE, RUN_ID_RE, SOURCE_ID_RE, release_id_for
from docwiki.contracts.runs import VersionInfo

__all__ = ["CurrentPointer", "FileEntry", "ReleaseInputs", "ReleaseManifest"]

ReleaseId = Annotated[str, Field(pattern=RELEASE_ID_RE.pattern)]
SourceId = Annotated[str, Field(pattern=SOURCE_ID_RE.pattern)]


class FileEntry(ContractModel):
    sha256: Hex64
    size: Annotated[int, Field(ge=0)]


class ReleaseInputs(ContractModel):
    """Sources (``source_id`` → ``sha256:…`` of the raw bytes) included in this audience build."""

    sources: dict[SourceId, Sha256Ref] = {}


class ReleaseManifest(ContractModel):
    schema_version: Literal[1] = Field(1, alias="schema")
    release_id: ReleaseId
    created_at: UtcDateTime
    audience: Sensitivity
    run_id: Annotated[str, Field(pattern=RUN_ID_RE.pattern)] | None = None
    inputs: ReleaseInputs = Field(default_factory=ReleaseInputs)
    versions: VersionInfo
    counts: dict[str, Annotated[int, Field(ge=0)]] = {}
    gates: list[GateResult] = []
    files: dict[RelPath, FileEntry] = {}

    @staticmethod
    def identity_payload(
        *,
        created_at: datetime,
        audience: str,
        run_id: str | None,
        inputs: ReleaseInputs,
        versions: VersionInfo,
    ) -> dict[str, Any]:
        """Canonical identity hashed into the release id."""
        return {
            "schema": 1,
            "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "audience": audience,
            "run_id": run_id,
            "inputs": inputs.to_json_dict(),
            "versions": versions.to_json_dict(),
        }

    @classmethod
    def compute_release_id(
        cls,
        *,
        created_at: datetime,
        audience: str,
        run_id: str | None,
        inputs: ReleaseInputs,
        versions: VersionInfo,
    ) -> str:
        if created_at.microsecond:
            raise ValueError("created_at must have second precision")
        identity = cls.identity_payload(
            created_at=created_at,
            audience=audience,
            run_id=run_id,
            inputs=inputs,
            versions=versions,
        )
        return release_id_for(created_at, identity)

    @model_validator(mode="after")
    def _identity(self) -> Self:
        expected = self.compute_release_id(
            created_at=self.created_at,
            audience=self.audience,
            run_id=self.run_id,
            inputs=self.inputs,
            versions=self.versions,
        )
        if self.release_id != expected:
            raise ValueError(
                f"release_id does not match the manifest identity (expected {expected})"
            )
        if "manifest.json" in self.files:
            raise ValueError("manifest.json cannot list itself")
        return self

    @property
    def blocking_failures(self) -> list[GateResult]:
        return [gate for gate in self.gates if gate.blocks_publish]


class CurrentPointer(ContractModel):
    """``releases/current.json``; ``created_at`` is when this pointer was written."""

    release_id: ReleaseId
    created_at: UtcDateTime
    audience: Sensitivity
    manifest_sha256: Hex64
