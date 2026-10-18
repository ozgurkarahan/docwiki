"""Run report and cost receipt ``work/runs/<run_id>/report.json`` (architecture §7)."""

# Pydantic copies mutable defaults per instance, so `= []` / `= {}` field defaults are safe.
# ruff: noqa: RUF012

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from docwiki.contracts._base import ContractModel, NonEmptyStr, UtcDateTime
from docwiki.contracts.enums import QueueKind, RequestedBy, Sensitivity, StageName
from docwiki.contracts.gates import GateResult
from docwiki.contracts.ids import RELEASE_ID_RE, RUN_ID_RE

__all__ = [
    "ContentUnderstandingUsage",
    "CostReceipt",
    "LlmUsage",
    "ModelVersion",
    "RunCounts",
    "RunReport",
    "StageReport",
    "VersionInfo",
]

NonNegInt = Annotated[int, Field(ge=0)]
NonNegFloat = Annotated[float, Field(ge=0.0)]
RunId = Annotated[str, Field(pattern=RUN_ID_RE.pattern)]
ReleaseId = Annotated[str, Field(pattern=RELEASE_ID_RE.pattern)]


class ModelVersion(ContractModel):
    deployment: NonEmptyStr
    model: NonEmptyStr
    version: str | None = None


class VersionInfo(ContractModel):
    """Everything that identifies how a release/run was produced (shared by manifest and report)."""

    docwiki: NonEmptyStr
    wiki_schema: Literal[1] = 1
    domain_pack: NonEmptyStr
    domain_pack_hash: NonEmptyStr
    prompts: dict[str, str] = {}
    models: dict[str, ModelVersion] = {}
    extractors: dict[str, str] = {}


class LlmUsage(ContractModel):
    """Token usage of one deployment during a run; prices are USD per 1M tokens."""

    role: Literal["fast", "smart"]
    deployment: NonEmptyStr
    model: NonEmptyStr
    model_version: str | None = None
    calls: NonNegInt = 0
    input_tokens: NonNegInt = 0
    cached_input_tokens: NonNegInt = 0
    output_tokens: NonNegInt = 0
    price_input_per_1m: NonNegFloat | None = None
    price_cached_input_per_1m: NonNegFloat | None = None
    price_output_per_1m: NonNegFloat | None = None
    cost: NonNegFloat | None = None


class ContentUnderstandingUsage(ContractModel):
    analyzer: NonEmptyStr
    pages: NonNegInt = 0
    price_per_1k_pages: NonNegFloat | None = None
    cost: NonNegFloat | None = None


class CostReceipt(ContractModel):
    """Tokens × price table, Content Understanding pages and duration (USD)."""

    currency: Literal["USD"] = "USD"
    price_table: NonEmptyStr
    llm: list[LlmUsage] = []
    content_understanding: list[ContentUnderstandingUsage] = []
    duration_s: NonNegFloat = 0.0
    total_cost: NonNegFloat | None = None
    notes: list[str] = []


class StageReport(ContractModel):
    stage: StageName
    status: Literal["done", "failed", "skipped"]
    started_at: UtcDateTime
    finished_at: UtcDateTime | None = None
    duration_s: NonNegFloat = 0.0
    items: NonNegInt = 0
    cache_hits: NonNegInt = 0
    failures: NonNegInt = 0
    errors: list[str] = []


class RunCounts(ContractModel):
    sources_total: NonNegInt = 0
    new: NonNegInt = 0
    changed: NonNegInt = 0
    deleted: NonNegInt = 0
    unchanged: NonNegInt = 0
    quarantined: NonNegInt = 0
    failed: NonNegInt = 0


class RunReport(ContractModel):
    schema_version: Literal[1] = Field(1, alias="schema")
    run_id: RunId
    kind: QueueKind
    requested_by: RequestedBy
    status: Literal["running", "succeeded", "failed", "no-op"]
    started_at: UtcDateTime
    finished_at: UtcDateTime | None = None
    audience: Sensitivity
    release_id: ReleaseId | None = None
    previous_release_id: ReleaseId | None = None
    messages: NonNegInt = 0
    counts: RunCounts = Field(default_factory=RunCounts)
    stages: list[StageReport] = []
    gates: list[GateResult] = []
    versions: VersionInfo
    cost: CostReceipt
    errors: list[str] = []
    warnings: list[str] = []
    """Problems that did not fail the run (skipped overlay entries, retention, queue renewals)."""
