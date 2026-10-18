"""Guards applied to every document-derived string before it is rendered in a sidecar.

* Canary strings (known markers planted in injection tests, gate G08) are replaced by
  ``[redacted]`` — case-insensitively, before escaping, so they never reach a release file.
* Sentences that :func:`docwiki.contracts.detect_injection` flags (text addressed to AI
  systems) are replaced by a visible placeholder; the ExtractedDoc itself is unchanged, so quote
  verification still sees the original text.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence

from docwiki.contracts import detect_injection

__all__ = ["CANARY_PLACEHOLDER", "INJECTION_PLACEHOLDER", "TextGuard", "neutralize_sentences"]

INJECTION_PLACEHOLDER = "[instruction addressed to AI assistants removed — see quality report]"
CANARY_PLACEHOLDER = "[redacted]"

logger = logging.getLogger("docwiki.evidence")

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _flatten(text: str) -> str:
    return " ".join(line.strip() for line in text.split("\n") if line.strip())


def neutralize_sentences(text: str) -> tuple[str, int]:
    """Replace flagged sentences by :data:`INJECTION_PLACEHOLDER`; returns ``(text, count)``.

    Detection runs on the text and on its line-joined form (a sentence wrapped over two PDF
    lines is still caught). Unflagged text keeps its line breaks; a flagged text is returned as
    one line. When the flagged part cannot be isolated, the whole text is replaced.
    """
    flat = _flatten(text)
    if not detect_injection(text) and not detect_injection(flat):
        return text, 0
    kept: list[str] = []
    removed = 0
    for sentence in _SENTENCE_SPLIT_RE.split(flat):
        if detect_injection(sentence):
            removed += 1
            if not kept or kept[-1] != INJECTION_PLACEHOLDER:
                kept.append(INJECTION_PLACEHOLDER)
        else:
            kept.append(sentence)
    result = " ".join(kept)
    if removed == 0 or detect_injection(result):
        return INJECTION_PLACEHOLDER, max(removed, 1)
    return result, removed


class TextGuard:
    """Canary redaction + injection neutralisation for one evidence build."""

    def __init__(self, canaries: Sequence[str] = ()) -> None:
        unique = sorted({canary for canary in canaries if canary and canary.strip()}, key=len)
        self.canaries: tuple[str, ...] = tuple(reversed(unique))
        self._canary_re = (
            re.compile("|".join(re.escape(canary) for canary in self.canaries), re.IGNORECASE)
            if self.canaries
            else None
        )
        self.neutralized = 0
        self.redacted = 0

    def redact(self, text: str) -> str:
        """Replace every canary occurrence (case-insensitive) by :data:`CANARY_PLACEHOLDER`."""
        if self._canary_re is None:
            return text
        result, count = self._canary_re.subn(CANARY_PLACEHOLDER, text)
        self.redacted += count
        return result

    def contains_canary(self, data: bytes) -> bool:
        """True when raw bytes contain a canary (UTF-8 or UTF-16 text, any case)."""
        if not self.canaries:
            return False
        lowered = data.lower()
        for canary in self.canaries:
            needle = canary.lower()
            if needle.encode("utf-8") in lowered or needle.encode("utf-16-le") in lowered:
                return True
        return False

    def __call__(self, text: str) -> str:
        """Document text safe to render: canaries redacted, AI-addressed sentences replaced."""
        result, count = neutralize_sentences(self.redact(text))
        self.neutralized += count
        return result
