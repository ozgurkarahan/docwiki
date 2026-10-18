"""Shared engine types (spec v1 addendum, see docs/spec/engine-interfaces.md).

Main-owned and frozen: the extract, compile and assemble lanes import these types so that they
can be developed in parallel. Change only through the main agent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from docwiki.contracts import CompiledSource, ExtractedDoc, Locator, Proposal, locator_key
from docwiki.contracts.enums import CitationStatus, Provenance

__all__ = [
    "CitedLocator",
    "Classification",
    "CompiledResult",
    "ExtractResult",
    "ExtractSettings",
    "ExtractionError",
    "TopicSkip",
    "VerifiedCitation",
]


class Classification(BaseModel):
    """Result of the classify stage (rules first, LLM fallback)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    doc_type: str
    category: str
    authority: int = Field(ge=1, le=10)
    doc_number: str | None = None
    revision: str | None = None
    lang: str = "en"
    confidence: float = Field(ge=0.0, le=1.0)
    rule_id: str | None = None
    method: Literal["rule", "llm"]


@dataclass(frozen=True)
class CitedLocator:
    """A locator cited by a page; the evidence stage renders one sidecar per distinct key."""

    source_id: str
    locator: Locator
    block_ids: tuple[str, ...]
    quotes: tuple[str, ...] = ()
    provenance: Provenance = "native-text"

    @property
    def key(self) -> str:
        return locator_key(self.locator)


@dataclass(frozen=True)
class VerifiedCitation:
    """One citation after deterministic verification (evidence-contract section 4)."""

    ref: str  # "kf3" for key fact 3, "s2" for section 2 markers, "tp:<slug>:<n>" for topic claims
    source_id: str
    block_ids: tuple[str, ...]
    quote: str | None
    status: CitationStatus
    provenance: Provenance
    locator: Locator | None
    reason: str | None = None


@dataclass
class CompiledResult:
    """Output of compile_source for one source."""

    source_id: str
    compiled: CompiledSource
    citations: list[VerifiedCitation]
    proposals: list[Proposal]
    usage: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TopicSkip:
    topic_slug: str
    reason: Literal["insufficient_evidence", "audience", "no_current_sources"]
    sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtractSettings:
    """How to extract one source. `azure` uses Content Understanding for PDF, images and Office."""

    mode: Literal["local", "azure"] = "local"
    cu_endpoint: str | None = None
    cu_analyzer: str = "prebuilt-layout"
    cu_mode: Literal["live", "record", "replay"] = "live"
    recordings_dir: Path | None = None
    describe_figures: bool = True
    max_pages: int = 300
    page_render_dpi: int = 150


@dataclass
class ExtractResult:
    doc: ExtractedDoc
    figures: dict[str, bytes] = field(default_factory=dict)  # figure id -> PNG bytes
    page_images: dict[int, bytes] = field(default_factory=dict)  # 1-based page -> PNG bytes
    warnings: list[str] = field(default_factory=list)


class ExtractionError(Exception):
    """Unrecoverable extraction failure; the orchestrator quarantines the source."""

    def __init__(self, source_id: str, reason: str) -> None:
        super().__init__(f"{source_id}: {reason}")
        self.source_id = source_id
        self.reason = reason
