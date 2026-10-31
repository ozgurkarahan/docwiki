"""Normalised answer records shared by every system under test (docs/spec/evals.md §1)."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["Answer", "Citation", "ToolCallRecord", "ToolHitRecord", "Usage", "tool_hits"]

SEARCH_TOOLS = frozenset({"search", "answer_context"})
"""Tools whose output lists ranked hits."""


class Citation(BaseModel):
    """One cited locator, as the system gave it.

    A source is identified by ``source_path`` (relative to the corpus or to the raw container of a
    deployment), ``source_id`` (``src-<12 hex>`` of a release), ``sha256`` (raw content hash) or,
    as a last resort, ``title``; the locator by ``locator_key`` or a locator ``label``. ``unit``
    groups citations scored together for precision: one source-list entry of the Researcher, one
    passage (chunk) of ``baseline-rag``, one reference of ``baseline-long-context``.
    """

    model_config = ConfigDict(frozen=True)

    source_path: str | None = None
    source_id: str | None = None
    sha256: str | None = None
    locator_key: str | None = None
    label: str | None = None
    title: str | None = None
    unit: str | None = None


class ToolHitRecord(BaseModel):
    """One result a search tool returned, by identifiers only (never its text).

    ``cited`` lists the ``(source_id, locator_key)`` pairs the hit carried as citations (the
    footnotes of a wiki section, the evidence of a source block), so a diagnosis can tell a
    locator that was never retrieved from one that was retrieved but not used.
    """

    model_config = ConfigDict(frozen=True)

    rank: int
    kind: str | None = None
    page_id: str | None = None
    path: str | None = None
    anchor: str | None = None
    scope: str | None = None
    source_id: str | None = None
    locator_key: str | None = None
    cited: list[tuple[str, str]] = Field(default_factory=list)


class ToolCallRecord(BaseModel):
    """A tool call made while answering (MCP calls of the Researcher).

    ``hits`` is set for the search tools (``search``, ``answer_context``) whose output could be
    read; ``None`` otherwise.
    """

    name: str
    status: str
    server_label: str | None = None
    arguments: dict[str, Any] | str = Field(default_factory=dict)
    error: str | None = None
    hits: list[ToolHitRecord] | None = None


class Usage(BaseModel):
    """Model tokens spent on one question."""

    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0
    calls: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class Answer(BaseModel):
    """The normalised answer of a system: text, citations and what it took to produce it.

    ``text`` is the full answer as returned or rendered (with its source list); ``body`` is the
    answer without the source list, the part checked for ``must_include`` items and abstention.
    """

    text: str = ""
    body: str = ""
    citations: list[Citation] = Field(default_factory=list)
    abstained: bool = False
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    cost_usd: float | None = None
    info: dict[str, Any] = Field(default_factory=dict)


def _payload(output: Any) -> dict[str, Any] | None:
    """The JSON object of a tool output: a JSON string, an object, or MCP text content items."""
    if isinstance(output, dict):
        if isinstance(output.get("hits"), list):
            return output
        output = output.get("content")
    if isinstance(output, str):
        try:
            value = json.loads(output)
        except (json.JSONDecodeError, ValueError):
            return None
        return _payload(value) if not isinstance(value, str) else None
    if isinstance(output, list):
        for item in output:
            text = item.get("text") if isinstance(item, dict) else None
            found = _payload(text) if isinstance(text, str) else None
            if found is not None:
                return found
    return None


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def tool_hits(name: str, output: Any) -> list[ToolHitRecord] | None:
    """The identifiers of the hits in the output of a search tool, best first.

    Returns ``None`` for other tools and for outputs that cannot be read (a failure, a missing
    output); text fields (snippet, text, title) are never copied.
    """
    if name not in SEARCH_TOOLS:
        return None
    payload = _payload(output)
    if payload is None:
        return None
    offset = payload.get("offset") if isinstance(payload.get("offset"), int) else 0
    records: list[ToolHitRecord] = []
    for index, hit in enumerate(payload["hits"]):
        if not isinstance(hit, dict):
            continue
        cited: list[tuple[str, str]] = []
        for citation in hit.get("citations") or []:
            if not isinstance(citation, dict):
                continue
            source_id, key = _text(citation.get("source_id")), _text(citation.get("locator_key"))
            if source_id and key and (source_id, key) not in cited:
                cited.append((source_id, key))
        rank = hit.get("rank")
        records.append(
            ToolHitRecord(
                rank=rank if isinstance(rank, int) else offset + index + 1,
                kind=_text(hit.get("kind")),
                page_id=_text(hit.get("page_id")),
                path=_text(hit.get("path")),
                anchor=_text(hit.get("anchor")),
                scope=_text(hit.get("scope")),
                source_id=_text(hit.get("source_id")),
                locator_key=_text(hit.get("locator_key")),
                cited=cited,
            )
        )
    return records