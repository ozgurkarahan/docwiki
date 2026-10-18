"""Per-source state shard ``work/state/sources/<source_id>.json`` (architecture §5)."""

# Pydantic copies mutable defaults per instance, so `= []` / `= {}` field defaults are safe.
# ruff: noqa: RUF012

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from docwiki.contracts._base import (
    CacheKey,
    ContractModel,
    MediaType,
    RelPath,
    Sha256Ref,
    UtcDateTime,
)
from docwiki.contracts.enums import Sensitivity, StageName, StageStatus
from docwiki.contracts.ids import SOURCE_ID_RE, source_id_for

__all__ = ["RETRY_ATTEMPTS", "SourceState", "StageState"]

RETRY_ATTEMPTS = 3
"""Attempts of a stage whose quarantine is ``retryable`` before the quarantine becomes final."""


class StageState(ContractModel):
    """Status of one stage of a source.

    A quarantine caused by a transient problem (``retryable``) is retried by the next runs until
    ``attempts`` (consecutive failures of this stage for the current content) reaches
    :data:`RETRY_ATTEMPTS`; any other quarantine stays until the content changes or a recompile
    is requested.
    """

    status: StageStatus
    cache_key: CacheKey | None = None
    error: str | None = None
    updated_at: UtcDateTime | None = None
    retryable: bool = False
    attempts: Annotated[int, Field(ge=0)] = 0


class SourceState(ContractModel):
    """State of one raw file. Written with ETag If-Match; conflicts retry with fresh state.

    A deleted raw file keeps its shard as a tombstone (``deleted: true`` + ``deleted_at``).
    """

    schema_version: Literal[1] = Field(1, alias="schema")
    source_id: Annotated[str, Field(pattern=SOURCE_ID_RE.pattern)]
    raw_path: RelPath
    content_hash: Sha256Ref
    size: Annotated[int, Field(ge=0)]
    media_type: MediaType
    sensitivity: Sensitivity
    revision_group: str | None = None
    stages: dict[StageName, StageState] = {}
    last_error: str | None = None
    deleted: bool = False
    first_seen_at: UtcDateTime
    updated_at: UtcDateTime
    deleted_at: UtcDateTime | None = None

    @model_validator(mode="after")
    def _consistency(self) -> Self:
        if source_id_for(self.raw_path) != self.source_id:
            raise ValueError("source_id does not match raw_path")
        if self.deleted != (self.deleted_at is not None):
            raise ValueError("deleted and deleted_at go together")
        return self

    @property
    def quarantined(self) -> bool:
        return any(stage.status == "quarantined" for stage in self.stages.values())

    @property
    def quarantine(self) -> tuple[str, StageState] | None:
        """``(stage, state)`` of the first quarantined stage, else ``None``."""
        for name, stage in self.stages.items():
            if stage.status == "quarantined":
                return name, stage
        return None

    @property
    def retry_pending(self) -> bool:
        """Whether the quarantine is transient and still has attempts left."""
        found = self.quarantine
        return found is not None and found[1].retryable and found[1].attempts < RETRY_ATTEMPTS
