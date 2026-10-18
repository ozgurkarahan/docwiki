"""BM25 scorer shared by both search paths (FTS5 candidates or full in-memory matching).

FTS5's built-in ``bm25()`` clamps the IDF of terms present in more than half of the rows to
~0, which makes rankings meaningless on domain-focused wikis where key terms are frequent.
DocWiki therefore ranks candidates with Okapi BM25 using the ``log(1 + (N - df + 0.5) /
(df + 0.5))`` IDF (always positive) over weighted columns, identically in both paths.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

__all__ = ["K1", "B", "Bm25Corpus", "Bm25Doc", "count_phrase"]

K1 = 1.2
B = 0.75


def count_phrase(tokens: Sequence[str], phrase: Sequence[str]) -> int:
    """Occurrences of the token sequence ``phrase`` in ``tokens``."""
    size = len(phrase)
    if size == 0 or size > len(tokens):
        return 0
    if size == 1:
        return sum(1 for token in tokens if token == phrase[0])
    first = phrase[0]
    target = tuple(phrase)
    return sum(
        1
        for index in range(len(tokens) - size + 1)
        if tokens[index] == first and tuple(tokens[index : index + size]) == target
    )


@dataclass(frozen=True)
class Bm25Doc:
    rowid: int
    fields: tuple[tuple[str, ...], ...]
    """Token tuples per column (title, section, text)."""


class Bm25Corpus:
    """In-memory corpus with postings for fast phrase matching and BM25 scoring."""

    def __init__(self, docs: Iterable[Bm25Doc], weights: Sequence[float]) -> None:
        self.docs: dict[int, Bm25Doc] = {doc.rowid: doc for doc in docs}
        self.weights = tuple(weights)
        self.postings: dict[str, set[int]] = {}
        totals = [0] * len(self.weights)
        for doc in self.docs.values():
            for column, field in enumerate(doc.fields):
                totals[column] += len(field)
                for token in field:
                    self.postings.setdefault(token, set()).add(doc.rowid)
        count = len(self.docs)
        self.avg_len = [(total / count) if count else 0.0 for total in totals]
        self._matching: dict[tuple[str, ...], frozenset[int]] = {}

    def matching(self, phrase: tuple[str, ...]) -> frozenset[int]:
        """Rowids whose title, section or text contains ``phrase``."""
        cached = self._matching.get(phrase)
        if cached is not None:
            return cached
        if not phrase:
            return frozenset()
        candidates = set(self.postings.get(phrase[0], set()))
        for token in phrase[1:]:
            candidates &= self.postings.get(token, set())
            if not candidates:
                break
        if len(phrase) > 1:
            candidates = {
                rowid
                for rowid in candidates
                if any(count_phrase(field, phrase) for field in self.docs[rowid].fields)
            }
        result = frozenset(candidates)
        self._matching[phrase] = result
        return result

    def idf(self, phrase: tuple[str, ...]) -> float:
        total = len(self.docs)
        df = len(self.matching(phrase))
        return math.log(1.0 + (total - df + 0.5) / (df + 0.5))

    def score(
        self, phrases: Sequence[tuple[str, ...]], candidates: Iterable[int] | None = None
    ) -> dict[int, float]:
        """BM25 score per rowid (only rows matching at least one phrase get a score)."""
        allowed = None if candidates is None else set(candidates)
        scores: dict[int, float] = {}
        for phrase in dict.fromkeys(phrases):
            hits: frozenset[int] | set[int] = self.matching(phrase)
            if allowed is not None:
                hits = hits & allowed
            if not hits:
                continue
            idf = self.idf(phrase)
            for rowid in hits:
                contribution = 0.0
                for column, field in enumerate(self.docs[rowid].fields):
                    tf = count_phrase(field, phrase)
                    if not tf:
                        continue
                    avg = self.avg_len[column] or 1.0
                    norm = tf * (K1 + 1) / (tf + K1 * (1 - B + B * len(field) / avg))
                    contribution += self.weights[column] * norm
                if contribution:
                    scores[rowid] = scores.get(rowid, 0.0) + idf * contribution
        return scores
