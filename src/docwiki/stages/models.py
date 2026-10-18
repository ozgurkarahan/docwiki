"""Lane-local intermediate types of the compile stages (not part of the frozen contracts).

* Structured-output models of the LLM calls made by the entity, topic and repair steps (the
  classification model is built per domain pack in :mod:`docwiki.stages.classify`; compilation
  itself returns the frozen :class:`docwiki.contracts.CompiledSource`).
* Plain dataclasses shared by the page builders.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from docwiki.contracts.compiled import Citation
from docwiki.engine_types import VerifiedCitation

__all__ = [
    "EntitySummaryOutput",
    "FactRecord",
    "FactRepairOutput",
    "RepairedFact",
    "SourceInfo",
    "SummarySentence",
    "TopicClaimOut",
    "TopicContradictionOut",
    "TopicSectionOut",
    "TopicSupersededOut",
    "TopicSynthesisOutput",
]


class _Output(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RepairedFact(_Output):
    fact_number: int = Field(description="Number of the rejected fact that this item repairs.")
    text: str = Field(description="The fact in English.")
    citations: list[Citation] = Field(description="At least one citation.")
    numbers: list[str] = Field(
        description="Quantities stated in the fact, exactly as written in the cited text."
    )


class FactRepairOutput(_Output):
    """Answer of the ``compile-repair`` prompt."""

    facts: list[RepairedFact]


class SummarySentence(_Output):
    text: str = Field(description="One English sentence.")
    fact_ids: list[str] = Field(description="Ids of the facts supporting the sentence, e.g. F3.")


class EntitySummaryOutput(_Output):
    """Answer of the ``entity-summary`` prompt."""

    sentences: list[SummarySentence]


class TopicClaimOut(_Output):
    text: str = Field(description="One English claim.")
    fact_ids: list[str] = Field(description="Ids of the facts supporting the claim, e.g. F3.")


class TopicSectionOut(_Output):
    heading: str = Field(description="Short English heading.")
    claims: list[TopicClaimOut]


class TopicContradictionOut(_Output):
    subject: str = Field(description="What the two sources disagree about.")
    fact_ids_a: list[str] = Field(description="Facts of the first current source.")
    fact_ids_b: list[str] = Field(description="Facts of the second current source.")


class TopicSupersededOut(_Output):
    subject: str = Field(description="What changed.")
    old_fact_ids: list[str] = Field(description="Facts from superseded sources.")
    replacement_fact_ids: list[str] = Field(
        description="Facts of current sources replacing them ([] when withdrawn)."
    )
    superseding_source: str | None = Field(description="Id of the superseding source, e.g. S2.")


class TopicSynthesisOutput(_Output):
    """Answer of the ``topic-synthesis`` prompt."""

    summary: str = Field(description="One sentence describing what the page covers.")
    overview: list[TopicClaimOut]
    sections: list[TopicSectionOut]
    contradictions: list[TopicContradictionOut]
    superseded: list[TopicSupersededOut]


@dataclass(frozen=True)
class SourceInfo:
    """What entity and topic pages need to know about one source page."""

    source_id: str
    title: str
    path: str
    status: str
    sensitivity: str
    authority: int
    doc_type: str
    doc_number: str | None
    revision: str | None
    date: date | None
    supersedes: tuple[str, ...]
    superseded_by: tuple[str, ...]


@dataclass(frozen=True)
class FactRecord:
    """A verified key fact of one compiled source (``ref`` is ``kf<N>`` in that source)."""

    source_id: str
    ref: str
    text: str
    numbers: tuple[str, ...]
    citations: tuple[VerifiedCitation, ...]
