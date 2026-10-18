"""Text normalisation and tokenisation shared by the FTS5 and the pure-Python search paths.

Mirrors SQLite's ``unicode61 remove_diacritics 2`` tokenizer closely enough for ranking parity:
NFKD, combining marks removed, lower-cased, tokens are maximal runs of letters and digits.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator

__all__ = ["normalize_token_text", "token_spans", "tokenize"]

_TOKEN_RE = re.compile(r"[^\W_]+")


def normalize_token_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()


def tokenize(text: str) -> list[str]:
    """Search tokens of ``text``."""
    return _TOKEN_RE.findall(normalize_token_text(text))


def token_spans(text: str) -> Iterator[tuple[str, int, int]]:
    """``(token, start, end)`` with offsets into the original ``text`` (for snippets)."""
    for match in _TOKEN_RE.finditer(text):
        for token in _TOKEN_RE.findall(normalize_token_text(match.group(0))):
            yield token, match.start(), match.end()
