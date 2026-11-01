"""Versioned rule turning one indexed row into the text sent to the embedding model.

``embed-input-v1``: the title, then the section heading, then a blank line and the body text.
Whitespace inside the title and heading collapses to single spaces; in the body, spaces and tabs
collapse and runs of blank lines shrink to one. The result is cut deterministically at
:data:`EMBED_INPUT_MAX_CHARS` characters, backing off to the last whitespace in the final 10 %
so words stay whole. 8 000 characters stay under the 8 191-token input limit of the
``text-embedding-3`` models even at one token per character, so no call can be rejected for
length. Changing any of this is a new version (``embed-input-v2``): vectors built with another
version must be recomputed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from docwiki.llm.hashing import normalize_newlines

EMBED_INPUT_VERSION: Final = "embed-input-v1"
EMBED_INPUT_MAX_CHARS: Final = 8_000
_BACKOFF_FRACTION: Final = 0.9
_SPACES = re.compile(r"[ \t\f\v\u00a0\u202f\u2009]+")
_ANY_WHITESPACE = re.compile(r"\s+")
_BLANK_LINES = re.compile(r"\n\s*\n+")


@dataclass(frozen=True, slots=True)
class EmbedInput:
    """The text to embed and whether the length rule cut it."""

    text: str
    truncated: bool
    original_chars: int
    version: str = EMBED_INPUT_VERSION


def build_embed_input(
    title: str | None,
    section: str | None,
    text: str | None,
    *,
    max_chars: int = EMBED_INPUT_MAX_CHARS,
) -> EmbedInput:
    """Apply ``embed-input-v1`` to one row; raises ``ValueError`` when every part is empty."""
    if max_chars < 1:
        raise ValueError("max_chars must be >= 1")
    header = [part for part in (_one_line(title), _one_line(section)) if part]
    body = _body(text)
    combined = "\n".join(header)
    if body:
        combined = f"{combined}\n\n{body}" if combined else body
    if not combined:
        raise ValueError("embed-input-v1 needs a non-empty title, section or text")
    if len(combined) <= max_chars:
        return EmbedInput(text=combined, truncated=False, original_chars=len(combined))
    return EmbedInput(
        text=_cut(combined, max_chars), truncated=True, original_chars=len(combined)
    )


def _one_line(value: str | None) -> str:
    if not value:
        return ""
    return _ANY_WHITESPACE.sub(" ", value).strip()


def _body(value: str | None) -> str:
    if not value:
        return ""
    lines = [_SPACES.sub(" ", line).strip() for line in normalize_newlines(value).split("\n")]
    return _BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()


def _cut(text: str, max_chars: int) -> str:
    head = text[:max_chars]
    floor = int(max_chars * _BACKOFF_FRACTION)
    space = max(head.rfind(" "), head.rfind("\n"))
    if space >= floor:
        head = head[:space]
    return head.rstrip()
