"""Closed-world name scan: capitalised multi-word sequences must use known words only.

A capitalised token starts with an upper-case letter and contains a lower-case letter, so IDs
and acronyms (WTG-07, PWG, FICTIONAL) are ignored. Two or more capitalised tokens separated by
single spaces form a candidate name. Every token of a candidate must belong to an allowlisted
name (samples/fiction/allowlist.txt), a technology name or the bible's generic vocabulary.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

_TOKEN = re.compile(r"[^\W\d_][\w'\u2019-]*", re.UNICODE)
_SEQUENCE = re.compile(r"(?:[^\W\d_][\w'\u2019-]*)(?: (?:[^\W\d_][\w'\u2019-]*))+", re.UNICODE)


def is_capitalised(token: str) -> bool:
    return token[:1].isupper() and any(ch.islower() for ch in token)


def candidate_names(text: str) -> list[str]:
    """Runs of two or more consecutive capitalised tokens."""
    names: list[str] = []
    for line in text.splitlines():
        run: list[str] = []
        position = 0
        for match in _TOKEN.finditer(line):
            token = match.group(0).rstrip("'\u2019-")
            gap = line[position : match.start()]
            position = match.end()
            if run and gap != " ":
                if len(run) > 1:
                    names.append(" ".join(run))
                run = []
            if is_capitalised(token):
                run.append(token)
            else:
                if len(run) > 1:
                    names.append(" ".join(run))
                run = []
        if len(run) > 1:
            names.append(" ".join(run))
    return names


def known_tokens(allowlist_lines: Iterable[str], extra: Iterable[str] = ()) -> set[str]:
    tokens: set[str] = set()
    for line in [*allowlist_lines, *extra]:
        if not line or line.startswith("re:"):
            continue
        tokens.update(t.rstrip("'\u2019-") for t in _TOKEN.findall(line))
    return tokens


def unknown_names(text: str, known: set[str]) -> list[str]:
    return [name for name in candidate_names(text) if any(t not in known for t in name.split())]
