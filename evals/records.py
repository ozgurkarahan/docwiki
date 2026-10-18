"""Normalised answer records shared by every system under test (docs/spec/evals.md §1)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["Answer", "Citation", "ToolCallRecord", "Usage"]


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


class ToolCallRecord(BaseModel):
    """A tool call made while answering (MCP calls of the Researcher)."""

    name: str
    status: str
    server_label: str | None = None
    arguments: dict[str, Any] | str = Field(default_factory=dict)
    error: str | None = None


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
