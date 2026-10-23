"""Closed vocabularies of the v1 contracts (spec values, as ``Literal`` types).

Fields use ``Literal`` aliases so strict validation accepts plain strings from YAML/JSON and the
JSON Schema stays a simple ``enum``. The ``*_VALUES`` tuples are the runtime lists of the same
values.
"""

from __future__ import annotations

from typing import Literal, get_args

__all__ = [
    "BADGES",
    "BADGE_BY_PROVENANCE",
    "BLOCK_KINDS",
    "EDGE_KINDS",
    "LOG_ACTIONS",
    "PAGE_TYPES",
    "PROVENANCES",
    "SENSITIVITIES",
    "SOURCE_STATUSES",
    "STAGE_NAMES",
    "STAGE_STATUSES",
    "AskedBy",
    "Badge",
    "BlockKind",
    "CitationStatus",
    "Confidence",
    "EdgeKind",
    "ExtractionAdapter",
    "LogAction",
    "PageType",
    "Provenance",
    "QueueKind",
    "RequestedBy",
    "Sensitivity",
    "SourceStatus",
    "StageName",
    "StageStatus",
    "allowed_for_audience",
    "badge_for",
    "max_sensitivity",
    "sensitivity_rank",
]

PageType = Literal[
    "source", "entity", "topic", "hub", "view", "index", "query", "meta", "glossary", "log"
]
Sensitivity = Literal["public", "internal", "restricted"]
SourceStatus = Literal["current", "superseded", "withdrawn"]
Confidence = Literal["high", "medium", "low"]
AskedBy = Literal["researcher", "human"]
Provenance = Literal["native-text", "ocr", "deterministic-table", "model-description"]
BlockKind = Literal[
    "heading",
    "paragraph",
    "list",
    "table-ref",
    "figure-ref",
    "slide",
    "email-header",
    "email-body",
    "cue",
    "ocr-line",
    "note",
]
EdgeKind = Literal["mentions", "supersedes", "cites", "related", "topic-of"]
LogAction = Literal["ingest", "update", "supersede", "withdraw", "topic", "query", "lint"]
StageName = Literal[
    "discover",
    "extract",
    "classify",
    "compile",
    "entities",
    "topics",
    "links",
    "indexes",
    "agentkit",
    "evidence",
    "verify",
    "site",
    "publish",
]
StageStatus = Literal["pending", "done", "failed", "quarantined", "skipped"]
QueueKind = Literal["ingest", "recompile", "rebuild", "reconcile"]
RequestedBy = Literal["librarian", "event", "cli", "schedule", "owner"]
ExtractionAdapter = Literal["local", "content-understanding"]
CitationStatus = Literal["verified", "unverified-paraphrase", "failed"]
Badge = Literal["✓ quote verified", "paraphrase", "table", "OCR", "generated description"]

PAGE_TYPES: tuple[str, ...] = get_args(PageType)
SENSITIVITIES: tuple[str, ...] = get_args(Sensitivity)
SOURCE_STATUSES: tuple[str, ...] = get_args(SourceStatus)
PROVENANCES: tuple[str, ...] = get_args(Provenance)
BLOCK_KINDS: tuple[str, ...] = get_args(BlockKind)
EDGE_KINDS: tuple[str, ...] = get_args(EdgeKind)
LOG_ACTIONS: tuple[str, ...] = get_args(LogAction)
STAGE_NAMES: tuple[str, ...] = get_args(StageName)
STAGE_STATUSES: tuple[str, ...] = get_args(StageStatus)

BADGES: tuple[str, ...] = get_args(Badge)
BADGE_BY_PROVENANCE: dict[str, str] = {
    "native-text": "✓ quote verified",
    "deterministic-table": "table",
    "ocr": "OCR",
    "model-description": "generated description",
}
"""Footnote badge for a *verified* citation of each provenance (wiki-contract §5)."""


def badge_for(provenance: str, status: str = "verified") -> str:
    """Footnote badge for a citation.

    ``native-text`` earns ``✓ quote verified`` only when the quote was verified; an
    ``unverified-paraphrase`` of native text gets ``paraphrase`` (contract decision, see
    CONTRACT.md). ``failed`` citations never reach a page.
    """
    if status == "failed":
        raise ValueError("failed citations must be removed, they have no badge")
    if status not in ("verified", "unverified-paraphrase"):
        raise ValueError(f"unknown citation status: {status!r}")
    if provenance not in BADGE_BY_PROVENANCE:
        raise ValueError(f"unknown provenance: {provenance!r}")
    if provenance == "native-text" and status == "unverified-paraphrase":
        return "paraphrase"
    return BADGE_BY_PROVENANCE[provenance]


_RANK = {tier: index for index, tier in enumerate(SENSITIVITIES)}


def sensitivity_rank(tier: str) -> int:
    """0 for public, 1 for internal, 2 for restricted (ValueError otherwise)."""
    try:
        return _RANK[tier]
    except KeyError:
        raise ValueError(f"unknown sensitivity tier: {tier!r}") from None


def max_sensitivity(*tiers: str) -> str:
    """Highest tier among ``tiers`` (``public`` when empty)."""
    if not tiers:
        return "public"
    return max(tiers, key=sensitivity_rank)


def allowed_for_audience(tier: str, audience: str) -> bool:
    """True when content of ``tier`` may appear in a build for ``audience``."""
    return sensitivity_rank(tier) <= sensitivity_rank(audience)
