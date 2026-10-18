"""Injection containment of compiled sources (infra-ops-security, pipeline gate G08).

A source is *contained* when its compilation flagged blocks as text addressed to AI systems
(injection flags or ``injection`` proposals) or when it contains a known canary
(``DOCWIKI_CANARIES`` / ``<pack>/canaries.txt``). For a contained source the build:

* never publishes the original file (``build_evidence(..., publish_original=False)``);
* renders pages, evidence sidecars and tables from a redacted copy of the ExtractedDoc where the
  flagged blocks and every text holding a canary are replaced by :data:`WITHHELD`;
* leaves the withheld blocks out of ``search.db``;
* lists the flags in ``_meta/quality.md`` by source id, block id and reason only.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from docwiki.contracts.extracted import ExtractedDoc
from docwiki.contracts.proposals import InjectionProposal
from docwiki.engine_types import CompiledResult
from docwiki.stages.verify import InjectionItem, contains_canary

__all__ = [
    "CANARY_REASON",
    "ORIGINAL_REASON",
    "WITHHELD",
    "Containment",
    "assess",
    "redact",
    "searchable",
]

WITHHELD = "[Withheld: suspected prompt injection.]"
CANARY_REASON = "contains a known canary string"
ORIGINAL_REASON = "the original file contains a known canary string"
_ENCODINGS = ("utf-8", "utf-16-le", "utf-16-be")


@dataclass(frozen=True)
class Containment:
    source_id: str
    blocks: frozenset[str] = frozenset()
    canary_text: bool = False
    raw_canary: bool = False
    items: tuple[InjectionItem, ...] = ()

    @property
    def contained(self) -> bool:
        return bool(self.blocks or self.canary_text or self.raw_canary)

    @property
    def publish_original(self) -> bool:
        return not self.contained


def _raw_has_canary(raw: bytes | None, canaries: Sequence[str]) -> bool:
    if not raw:
        return False
    return any(
        canary.encode(encoding) in raw for canary in canaries if canary for encoding in _ENCODINGS
    )


def _other_texts(doc: ExtractedDoc) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if doc.title_hint:
        found.append(("title", doc.title_hint))
    for table in doc.tables:
        found.extend((table.id, column) for column in table.columns)
        found.extend((table.id, cell) for row in table.rows for cell in row.cells)
    for figure in doc.figures:
        found.extend((figure.id, text) for text in (figure.caption, figure.description) if text)
    return found


def assess(
    doc: ExtractedDoc,
    result: CompiledResult | None,
    canaries: Sequence[str] = (),
    *,
    raw: bytes | None = None,
) -> Containment:
    """What of ``doc`` must be withheld from the release, and why."""
    known = {block.id for block in doc.blocks}
    reasons: dict[str, list[str]] = {}

    def flag(element_id: str, reason: str) -> None:
        bucket = reasons.setdefault(element_id, [])
        if reason and reason not in bucket:
            bucket.append(reason)

    if result is not None:
        for injection in result.compiled.injection_flags:
            if injection.block_id in known:
                flag(injection.block_id, injection.reason)
        for proposal in result.proposals:
            if isinstance(proposal, InjectionProposal):
                payload = proposal.payload
                if payload.source_id == doc.source_id and payload.block_id in known:
                    flag(payload.block_id, payload.reason)
    for block in doc.blocks:
        if contains_canary(block.text, canaries):
            flag(block.id, CANARY_REASON)
    blocks = frozenset(reasons)
    canary_text = False
    for element_id, text in _other_texts(doc):
        if contains_canary(text, canaries):
            canary_text = True
            flag(element_id, CANARY_REASON)
    raw_canary = _raw_has_canary(raw, canaries)
    if raw_canary and not reasons:
        flag("original", ORIGINAL_REASON)
    items = tuple(
        InjectionItem(doc.source_id, element_id, "; ".join(reasons[element_id]))
        for element_id in sorted(reasons)
    )
    return Containment(doc.source_id, blocks, canary_text, raw_canary, items)


def redact(
    doc: ExtractedDoc, containment: Containment, canaries: Sequence[str] = ()
) -> ExtractedDoc:
    """Copy of ``doc`` with withheld blocks and canary-bearing texts replaced by WITHHELD."""
    if not containment.blocks and not containment.canary_text:
        return doc

    def clean(text: str) -> str:
        return WITHHELD if contains_canary(text, canaries) else text

    def clean_optional(text: str | None) -> str | None:
        return clean(text) if text else text

    blocks = [
        block.model_copy(update={"text": WITHHELD}) if block.id in containment.blocks else block
        for block in doc.blocks
    ]
    tables = [
        table.model_copy(
            update={
                "columns": [clean(column) for column in table.columns],
                "rows": [
                    row.model_copy(update={"cells": [clean(cell) for cell in row.cells]})
                    for row in table.rows
                ],
            }
        )
        for table in doc.tables
    ]
    figures = [
        figure.model_copy(
            update={
                "caption": clean_optional(figure.caption),
                "description": clean_optional(figure.description),
            }
        )
        for figure in doc.figures
    ]
    title_hint = doc.title_hint
    if title_hint and contains_canary(title_hint, canaries):
        title_hint = None
    return doc.model_copy(
        update={"blocks": blocks, "tables": tables, "figures": figures, "title_hint": title_hint}
    )


def searchable(doc: ExtractedDoc, containment: Containment) -> ExtractedDoc:
    """``doc`` without the withheld blocks (input of the ``search.db`` source blocks)."""
    if not containment.blocks:
        return doc
    return doc.model_copy(
        update={"blocks": [block for block in doc.blocks if block.id not in containment.blocks]}
    )
