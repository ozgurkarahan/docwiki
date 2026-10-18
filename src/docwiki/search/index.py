"""``search.db`` (pipeline §6): build with SQLite FTS5, query with FTS5 or a BM25 fallback.

Schema = the frozen DDL of pipeline §6 plus two additive tables used for filtering:
``pages(page_id, type, path, title)`` and ``page_refs(page_id, ref_kind, ref_id)`` where
``ref_kind`` is ``entity`` or ``topic``.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from docwiki.contracts._base import ContractModel
from docwiki.contracts.enums import Sensitivity
from docwiki.contracts.extracted import ExtractedDoc
from docwiki.contracts.locators import locator_label
from docwiki.contracts.markdown import markdown_to_text, split_sections, strip_backlinks_block
from docwiki.contracts.pages import (
    EntityFrontmatter,
    Page,
    SourceFrontmatter,
    TopicFrontmatter,
)
from docwiki.search.bm25 import Bm25Corpus, Bm25Doc
from docwiki.search.text import token_spans, tokenize

__all__ = [
    "COLUMN_WEIGHTS",
    "SCHEMA_VERSION",
    "TOKENIZER",
    "SearchBlock",
    "SearchDbInfo",
    "SearchHit",
    "SearchIndex",
    "blocks_from_extracted",
    "build_search_db",
    "fts5_available",
    "make_snippet",
]

SCHEMA_VERSION = "1"
TOKENIZER = "unicode61 remove_diacritics 2"
COLUMN_WEIGHTS = (3.0, 2.0, 1.0)
"""bm25 weights for (title, section, text)."""

_DDL = """
CREATE TABLE docs(rowid INTEGER PRIMARY KEY, kind TEXT, page_id TEXT, path TEXT, title TEXT,
                  section TEXT, anchor TEXT, source_id TEXT, locator_key TEXT, sensitivity TEXT,
                  status TEXT, lang TEXT, text TEXT);
CREATE TABLE synonyms(term TEXT, synonym TEXT, lang TEXT);
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE pages(page_id TEXT PRIMARY KEY, type TEXT NOT NULL, path TEXT NOT NULL,
                   title TEXT NOT NULL);
CREATE TABLE page_refs(page_id TEXT NOT NULL, ref_kind TEXT NOT NULL, ref_id TEXT NOT NULL,
                       PRIMARY KEY(page_id, ref_kind, ref_id));
"""
_FTS_DDL = (
    "CREATE VIRTUAL TABLE docs_fts USING fts5(title, section, text, content='docs', "
    f"content_rowid='rowid', tokenize='{TOKENIZER}');"
)

Kind = Literal["page-section", "source-block"]


class SearchBlock(ContractModel):
    """One extracted block to index as a ``source-block`` row."""

    source_id: str
    page_id: str
    path: str
    title: str
    locator_key: str
    section: str | None = None
    text: str
    sensitivity: Sensitivity
    status: str | None = None
    lang: str | None = None


class SearchHit(ContractModel):
    kind: Kind
    page_id: str
    path: str
    title: str
    section: str | None = None
    anchor: str | None = None
    snippet: str
    source_id: str | None = None
    locator_key: str | None = None
    score: float


@dataclass(frozen=True)
class SearchDbInfo:
    path: Path
    rows: int
    fts5: bool


def fts5_available(conn: sqlite3.Connection | None = None) -> bool:
    """True when this SQLite build provides FTS5."""
    own = conn is None
    connection = conn or sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE VIRTUAL TABLE temp._docwiki_probe USING fts5(x)")
        connection.execute("DROP TABLE temp._docwiki_probe")
        return True
    except sqlite3.OperationalError:
        return False
    finally:
        if own:
            connection.close()


def blocks_from_extracted(
    doc: ExtractedDoc,
    *,
    page_path: str,
    title: str,
    sensitivity: str,
    status: str | None = "current",
) -> list[SearchBlock]:
    """``source-block`` rows for every non-empty block of an ExtractedDoc."""
    rows: list[SearchBlock] = []
    for block in doc.blocks:
        if not block.text.strip():
            continue
        rows.append(
            SearchBlock(
                source_id=doc.source_id,
                page_id=doc.source_id,
                path=page_path,
                title=title,
                locator_key=block.locator_key,
                section=locator_label(block.locator),
                text=block.text,
                sensitivity=sensitivity,  # type: ignore[arg-type]
                status=status,
                lang=block.lang or doc.lang,
            )
        )
    return rows


def _page_rows(page: Page) -> list[tuple[object, ...]]:
    fm = page.frontmatter
    source_id = fm.source_id if isinstance(fm, SourceFrontmatter) else None
    status = fm.status if isinstance(fm, SourceFrontmatter) else None
    rows: list[tuple[object, ...]] = []
    for section in split_sections(strip_backlinks_block(page.body)):
        text = markdown_to_text(section.markdown).strip()
        if not text:
            continue
        heading = section.heading if section.heading is not None else fm.title
        rows.append(
            (
                "page-section",
                fm.id,
                page.path,
                fm.title,
                heading,
                section.anchor,
                source_id,
                None,
                fm.sensitivity,
                status,
                fm.lang,
                text,
            )
        )
    return rows


def _page_refs(page: Page) -> list[tuple[str, str, str]]:
    fm = page.frontmatter
    refs: list[tuple[str, str, str]] = []
    if isinstance(fm, SourceFrontmatter):
        refs += [(fm.id, "entity", entity_id) for entity_id in fm.entities]
        refs += [(fm.id, "topic", topic_id) for topic_id in fm.topics]
    elif isinstance(fm, EntityFrontmatter):
        refs.append((fm.id, "entity", fm.id))
    elif isinstance(fm, TopicFrontmatter):
        refs.append((fm.id, "topic", fm.id))
    return refs


def build_search_db(
    pages: Iterable[Page],
    blocks: Iterable[SearchBlock],
    synonyms: Iterable[tuple[str, str, str]],
    path: str | Path,
    *,
    release_id: str | None = None,
    audience: str | None = None,
    use_fts5: bool | None = None,
) -> SearchDbInfo:
    """Create ``search.db`` at ``path`` (replaced if present). Deterministic for equal inputs.

    ``use_fts5=None`` auto-detects; ``False`` builds the plain tables only (BM25 fallback).
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    page_list = sorted(pages, key=lambda page: page.path)
    block_list = sorted(blocks, key=lambda block: block.source_id)
    conn = sqlite3.connect(target)
    try:
        fts = fts5_available(conn) if use_fts5 is None else use_fts5
        conn.executescript(_DDL)
        if fts:
            conn.execute(_FTS_DDL)
        rows: list[tuple[object, ...]] = []
        for page in page_list:
            rows.extend(_page_rows(page))
            conn.execute(
                "INSERT INTO pages(page_id, type, path, title) VALUES (?, ?, ?, ?)",
                (page.frontmatter.id, page.frontmatter.type, page.path, page.frontmatter.title),
            )
            conn.executemany(
                "INSERT OR IGNORE INTO page_refs(page_id, ref_kind, ref_id) VALUES (?, ?, ?)",
                _page_refs(page),
            )
        for block in block_list:
            rows.append(
                (
                    "source-block",
                    block.page_id,
                    block.path,
                    block.title,
                    block.section,
                    None,
                    block.source_id,
                    block.locator_key,
                    block.sensitivity,
                    block.status,
                    block.lang,
                    block.text,
                )
            )
        conn.executemany(
            "INSERT INTO docs(kind, page_id, path, title, section, anchor, source_id, locator_key, "
            "sensitivity, status, lang, text) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.executemany(
            "INSERT INTO synonyms(term, synonym, lang) VALUES (?, ?, ?)",
            list(dict.fromkeys(tuple(row) for row in synonyms)),
        )
        meta = {
            "schema": SCHEMA_VERSION,
            "tokenizer": TOKENIZER,
            "fts5": "1" if fts else "0",
            "rows": str(len(rows)),
            "release_id": release_id or "",
            "audience": audience or "",
        }
        conn.executemany("INSERT INTO meta(key, value) VALUES (?, ?)", sorted(meta.items()))
        if fts:
            conn.execute("INSERT INTO docs_fts(docs_fts) VALUES('rebuild')")
        conn.commit()
        conn.execute("VACUUM")
    finally:
        conn.close()
    return SearchDbInfo(target, len(rows), fts)


@dataclass(frozen=True)
class _Row:
    rowid: int
    kind: str
    page_id: str
    path: str
    title: str
    section: str | None
    anchor: str | None
    source_id: str | None
    locator_key: str | None
    text: str


class SearchIndex:
    """Read-only access to a ``search.db`` (thread-safe)."""

    def __init__(self, conn: sqlite3.Connection, *, backend: Literal["fts5", "bm25"]) -> None:
        self._conn = conn
        self._lock = threading.Lock()
        self.backend = backend
        self.meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
        self._synonym_groups = self._load_synonyms()
        self._corpus: Bm25Corpus | None = None
        self._rows: dict[int, _Row] | None = None

    @classmethod
    def open(cls, path: str | Path, *, force_fallback: bool = False) -> SearchIndex:
        """Open read-only; uses FTS5 when the table exists and this SQLite supports it."""
        file = Path(path)
        if not file.is_file():
            raise FileNotFoundError(f"search database not found: {file}")
        uri = file.resolve().as_uri() + "?mode=ro&immutable=1"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        has_table = conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name = 'docs_fts'"
        ).fetchone()[0]
        backend: Literal["fts5", "bm25"] = "bm25"
        if has_table and not force_fallback and fts5_available():
            try:
                conn.execute("SELECT rowid FROM docs_fts LIMIT 1").fetchall()
                backend = "fts5"
            except sqlite3.OperationalError:
                backend = "bm25"
        return cls(conn, backend=backend)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> SearchIndex:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _load_synonyms(self) -> list[set[tuple[str, ...]]]:
        groups: dict[tuple[str, ...], set[tuple[str, ...]]] = {}
        for term, synonym, _lang in self._conn.execute("SELECT term, synonym, lang FROM synonyms"):
            key = tuple(tokenize(term))
            alt = tuple(tokenize(synonym))
            if not key or not alt:
                continue
            groups.setdefault(key, {key}).add(alt)
        merged: list[set[tuple[str, ...]]] = []
        for group in groups.values():
            overlapping = [existing for existing in merged if existing & group]
            for existing in overlapping:
                group |= existing
                merged.remove(existing)
            merged.append(group)
        return merged

    def expand(self, query: str) -> list[tuple[str, ...]]:
        """Query phrases after synonym expansion (each phrase is a token tuple)."""
        tokens = tokenize(query)
        phrases: list[tuple[str, ...]] = []
        consumed = [False] * len(tokens)
        for group in self._synonym_groups:
            for variant in sorted(group, key=len, reverse=True):
                size = len(variant)
                for start in range(len(tokens) - size + 1):
                    if tuple(tokens[start : start + size]) == variant:
                        phrases.extend(sorted(group))
                        for index in range(start, start + size):
                            consumed[index] = True
        phrases.extend((token,) for token, used in zip(tokens, consumed, strict=True) if not used)
        if not phrases:
            return []
        return list(dict.fromkeys(phrases))

    def _filters(
        self,
        kinds: Sequence[str] | None,
        types: Sequence[str] | None,
        entity: str | None,
        topic: str | None,
    ) -> tuple[str, list[object]]:
        clauses: list[str] = []
        params: list[object] = []
        if kinds:
            clauses.append(f"d.kind IN ({','.join('?' * len(kinds))})")
            params.extend(kinds)
        if types:
            clauses.append(
                "d.page_id IN (SELECT page_id FROM pages WHERE type IN "
                f"({','.join('?' * len(types))}))"
            )
            params.extend(types)
        for ref_kind, ref_id in (("entity", entity), ("topic", topic)):
            if ref_id:
                clauses.append(
                    "(d.page_id = ? OR d.page_id IN (SELECT page_id FROM page_refs "
                    "WHERE ref_kind = ? AND ref_id = ?))"
                )
                params.extend([ref_id, ref_kind, ref_id])
        return (" AND " + " AND ".join(clauses)) if clauses else "", params

    def search(
        self,
        query: str,
        kinds: Sequence[str] | None = None,
        types: Sequence[str] | None = None,
        entity: str | None = None,
        topic: str | None = None,
        limit: int = 10,
    ) -> list[SearchHit]:
        """Ranked hits: synonym-expanded phrases, OR semantics, BM25 (title 3, section 2, text 1).

        The FTS5 backend selects candidate rows with ``MATCH``; the BM25 backend matches in
        memory. Both rank with the same scorer, so results are identical.
        """
        if limit < 1:
            return []
        phrases = self.expand(query)
        if not phrases:
            return []
        where, params = self._filters(kinds, types, entity, topic)
        with self._lock:
            corpus, rows = self._load_corpus()
            if self.backend == "fts5":
                candidates = self._fts_candidates(phrases, where, params)
            else:
                candidates = set().union(*(corpus.matching(phrase) for phrase in phrases))
                if where:
                    sql = f"SELECT d.rowid FROM docs d WHERE 1 = 1{where}"
                    candidates &= {rowid for (rowid,) in self._conn.execute(sql, params)}
            scores = corpus.score(phrases, candidates)
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:limit]
        return [self._hit(rows[rowid], score, phrases) for rowid, score in ranked]

    def _fts_candidates(
        self, phrases: list[tuple[str, ...]], where: str, params: list[object]
    ) -> set[int]:
        expression = " OR ".join(
            '"' + " ".join(phrase).replace('"', '""') + '"' for phrase in phrases
        )
        sql = (
            "SELECT d.rowid FROM docs_fts JOIN docs d ON d.rowid = docs_fts.rowid "
            f"WHERE docs_fts MATCH ?{where}"
        )
        return {rowid for (rowid,) in self._conn.execute(sql, [expression, *params])}

    def _load_corpus(self) -> tuple[Bm25Corpus, dict[int, _Row]]:
        if self._corpus is None or self._rows is None:
            rows: dict[int, _Row] = {}
            docs: list[Bm25Doc] = []
            for record in self._conn.execute(
                "SELECT rowid, kind, page_id, path, title, section, anchor, source_id, "
                "locator_key, text FROM docs ORDER BY rowid"
            ):
                row = _Row(*record)
                rows[row.rowid] = row
                docs.append(
                    Bm25Doc(
                        row.rowid,
                        (
                            tuple(tokenize(row.title or "")),
                            tuple(tokenize(row.section or "")),
                            tuple(tokenize(row.text or "")),
                        ),
                    )
                )
            self._corpus = Bm25Corpus(docs, COLUMN_WEIGHTS)
            self._rows = rows
        return self._corpus, self._rows

    @staticmethod
    def _hit(row: _Row, score: float, phrases: list[tuple[str, ...]]) -> SearchHit:
        return SearchHit(
            kind=row.kind,  # type: ignore[arg-type]
            page_id=row.page_id,
            path=row.path,
            title=row.title,
            section=row.section,
            anchor=row.anchor,
            snippet=make_snippet(row.text or "", phrases),
            source_id=row.source_id,
            locator_key=row.locator_key,
            score=round(score, 6),
        )


def make_snippet(
    text: str,
    phrases: Sequence[tuple[str, ...]],
    *,
    before: int = 10,
    after: int = 20,
    max_chars: int = 240,
) -> str:
    """Plain-text window around the first phrase occurrence (or the start of the text)."""
    spans = list(token_spans(text))
    if not spans:
        return " ".join(text.split())[:max_chars]
    tokens = [token for token, _, _ in spans]
    first = None
    for index in range(len(tokens)):
        for phrase in phrases:
            if tuple(tokens[index : index + len(phrase)]) == tuple(phrase):
                first = index
                break
        if first is not None:
            break
    if first is None:
        first = 0
        start_index = 0
    else:
        start_index = max(0, first - before)
    end_index = min(len(spans) - 1, first + after)
    start_char = spans[start_index][1]
    end_char = spans[end_index][2]
    snippet = " ".join(text[start_char:end_char].split())
    if len(snippet) > max_chars:
        snippet = snippet[: max_chars - 1].rstrip() + "…"
    prefix = "…" if start_char > 0 and text[:start_char].strip() else ""
    suffix = "…" if text[end_char:].strip() and not snippet.endswith("…") else ""
    return f"{prefix}{snippet}{suffix}"
