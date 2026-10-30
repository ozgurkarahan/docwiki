"""Read tools (role ``Wiki.Read``): search, pages, indexes, links, glossary, evidence, tables,
skills and recent changes over the release served by a :class:`ReleaseSource`.

Every method returns the compact JSON text of a bounded payload (see :mod:`docwiki.mcp.bounds`).
Anticipated problems (unknown page, invalid SQL…) raise :class:`ToolInputError` with a message
that tells the agent how to recover. Document text is always returned with its locator and
provenance; compiled wiki text comes with the citations it carries.
"""

from __future__ import annotations

import difflib
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from docwiki.contracts.catalog import CatalogPage
from docwiki.contracts.enums import BADGE_BY_PROVENANCE, allowed_for_audience
from docwiki.contracts.ids import SOURCE_ID_RE
from docwiki.contracts.layout import EVIDENCE_MOUNT, SKILL_PROJECTIONS
from docwiki.contracts.locators import locator_key, locator_label, parse_locator_key
from docwiki.contracts.markdown import (
    FootnoteDef,
    extract_footnotes,
    extract_links,
    markdown_to_text,
    resolve_href,
    split_sections,
    strip_backlinks_block,
)
from docwiki.mcp.bounds import ResultTooLargeError, clip, fit_items, fit_text, result_json
from docwiki.mcp.config import McpConfig
from docwiki.mcp.errors import ToolFailure
from docwiki.mcp.source import ReleaseSource, Snapshot
from docwiki.release import TableQueryError
from docwiki.search.text import tokenize

__all__ = [
    "ANSWER_CONTEXT_HITS",
    "INDEX_SCOPES",
    "MAX_ANSWER_CONTEXT_HITS",
    "ReadTools",
    "ToolInputError",
]


ToolInputError = ToolFailure
"""Anticipated, agent-correctable failure (returned to the agent as ``ok: false``)."""


INDEX_SCOPES: dict[str, str] = {
    "home": "index:home",
    "sources": "index:sources",
    "entities": "index:entities",
    "topics": "index:topics",
    "queries": "index:queries",
    "glossary": "glossary",
    "log": "log",
}
"""Fixed ``get_index`` scopes; ``entities/<type>`` and ``hubs/<folder>`` scopes come from the
catalog."""

SCOPE_VALUE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
"""A ``within`` value: one scope value of the wiki (kebab-case, like the catalog's ``scope``)."""
MAX_SCOPE_CHARS = 64
_SCOPED_TYPES = frozenset({"source", "entity", "topic", "hub", "query"})
"""Index entries pointing at these page types are filtered by ``within``; links to indexes and
other navigation pages (glossary, log, meta) are kept."""
_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+\S")

PROVENANCE_BY_BADGE: dict[str, str] = {
    "✓ quote verified": "native-text",
    "paraphrase": "native-text",
    "table": "deterministic-table",
    "OCR": "ocr",
    "generated description": "model-description",
}
_CITATION_RE = re.compile(r"^\[(?P<text>.+)\]\((?P<href>[^()\s]+)\)\s*(?:·\s*(?P<badge>.+?))?\s*$")
_LOG_HEADING_RE = re.compile(
    r"^\[(?P<date>\d{4}-\d{2}-\d{2})\]\s+(?P<action>[a-z-]+)\s+\|\s+(?P<title>.+)$"
)
_BLANK_RUNS_RE = re.compile(r"\n{3,}")
_FIRST_KEYWORD_RE = re.compile(r"^(?:\s+|--[^\n]*\n|/\*.*?\*/|\()*([A-Za-z]+)", re.DOTALL)
_QUERY_KEYWORDS = frozenset({"select", "with", "from", "values"})
"""Statements DuckDB may rewrite into a SELECT (PRAGMA, SHOW, DESCRIBE...) are refused too."""
_FRONTMATTER_TOP = ("id", "type", "title", "summary", "sensitivity", "docwiki")
MAX_LINKS = 60
MAX_CELL_CHARS = 500
MAX_SQL_CHARS = 4000

ANSWER_CONTEXT_HITS = 5
"""Default number of hits of ``answer_context``."""
MAX_ANSWER_CONTEXT_HITS = 10
CONTEXT_TEXT_BUDGETS = (1600, 1000, 600, 300)
"""Characters of section or evidence text per hit, tried in turn until the result fits."""
CONTEXT_INDEX_CHARS = 1500
CONTEXT_HUB_CHARS = 1500
_CONTEXT_SKIPPED_TYPES = frozenset({"index", "log", "meta"})
"""Navigation pages are not answer hits (the home index and the hub come separately)."""
ANSWER_CONTEXT_HINT = (
    "Answer from these hits when they suffice, citing their citations. For more: read_page "
    "(path, section) of ONE section, query_table for numbers, read_page of a view for money or "
    "compliance, get_evidence only to quote a passage verbatim."
)
ANSWER_CONTEXT_EMPTY_HINT = (
    "No hits: try other words or the glossary; if the wiki has no answer, say 'Not found in the "
    "wiki.'"
)


@dataclass
class _ContextHit:
    """One ``answer_context`` hit before it is cut to the output budget."""

    row: dict[str, Any]
    text: str
    by_label: dict[str, dict[str, Any]] = field(default_factory=dict)
    """Footnote citations of the hit's page by label (wiki hits)."""
    fixed: list[dict[str, Any]] = field(default_factory=list)
    """Citations that always apply (the evidence sidecar of a source hit)."""


def _dominant_scope(rows: Sequence[dict[str, Any]]) -> str | None:
    """The scope carried by most hits when it accounts for at least half of them (two or more)."""
    scopes = [row["scope"] for row in rows if row.get("scope")]
    if not scopes:
        return None
    best = max(sorted(set(scopes)), key=scopes.count)
    count = scopes.count(best)
    return best if count >= 2 and count * 2 >= len(rows) else None


MAX_CONTEXT_HITS_PER_SOURCE = 2
"""Hits of one source or page in a row before the others get their turn (``answer_context``)."""
SCOPE_SLOT_RATIO = 0.5
"""A scope gets a slot in the window when its best hit scores at least this share of the top."""


@dataclass(frozen=True)
class _Candidate:
    hit: Any
    scope: str | None
    group: str


def _spread_hits(items: Sequence[_Candidate], window: int, *, by_scope: bool) -> list[Any]:
    """Hits in answer order: at most :data:`MAX_CONTEXT_HITS_PER_SOURCE` of one source or page
    before the rest, then (``by_scope``) the best hit of every scope that scores at least
    :data:`SCOPE_SLOT_RATIO` of the top one inside the first ``window`` hits, replacing the lowest
    hits of the scopes that have several. Deterministic; nothing is dropped, only reordered."""
    counts: dict[str, int] = {}
    kept: list[_Candidate] = []
    deferred: list[_Candidate] = []
    for item in items:
        if counts.get(item.group, 0) < MAX_CONTEXT_HITS_PER_SOURCE:
            counts[item.group] = counts.get(item.group, 0) + 1
            kept.append(item)
        else:
            deferred.append(item)
    ordered = kept + deferred
    if not by_scope or not ordered or window < 2:
        return [item.hit for item in ordered]
    top = float(ordered[0].hit.score)
    firsts: list[_Candidate] = []
    seen: set[str] = set()
    for item in ordered:
        if item.scope and item.scope not in seen:
            seen.add(item.scope)
            if float(item.hit.score) >= top * SCOPE_SLOT_RATIO:
                firsts.append(item)
    chosen = ordered[:window]
    if len(firsts) < 2:
        return [item.hit for item in ordered]
    for first in firsts:
        if any(item is first for item in chosen):
            continue
        for index in range(len(chosen) - 1, -1, -1):
            scope = chosen[index].scope
            same = sum(1 for item in chosen if item.scope == scope)
            if same > 1 and not any(item is chosen[index] for item in firsts):
                del chosen[index]
                chosen.append(first)
                break
    rank = {id(item): position for position, item in enumerate(ordered)}
    chosen.sort(key=lambda item: rank[id(item)])
    picked = {id(item) for item in chosen}
    return [item.hit for item in chosen] + [item.hit for item in ordered if id(item) not in picked]


def _norm(text: str) -> str:
    return " ".join(tokenize(text))


def _page_ref(entry: CatalogPage) -> dict[str, Any]:
    ref: dict[str, Any] = {"page_id": entry.id, "path": entry.path, "title": entry.title}
    ref["type"] = entry.type
    if entry.status:
        ref["status"] = entry.status
    if entry.scope:
        ref["scope"] = entry.scope
    return ref


def _strip_footnote_definitions(body: str, defs: Sequence[FootnoteDef]) -> str:
    lines = body.split("\n")
    drop = {definition.line for definition in defs}
    kept = [line for number, line in enumerate(lines, 1) if number not in drop]
    text = "\n".join(kept).rstrip()
    text = re.sub(r"\n#{1,6}[ \t]+Sources[ \t]*$", "", text).rstrip()
    return _BLANK_RUNS_RE.sub("\n\n", text) + "\n"


class ReadTools:
    """Implementation of the read tools (no MCP types; easy to test directly)."""

    def __init__(self, source: ReleaseSource, config: McpConfig) -> None:
        self.source = source
        self.config = config

    @property
    def max_chars(self) -> int:
        return self.config.max_chars

    def snapshot(self) -> Snapshot:
        return self.source.current()

    # --- helpers ---------------------------------------------------------------------------

    @staticmethod
    def _by_id(snap: Snapshot, lang: str | None = None) -> dict[str, CatalogPage]:
        """Pages by id: the canonical wiki, or one mirror language completed by the canonical
        pages it does not translate (v1.7)."""
        return snap.cached(f"pages-by-id:{lang or ''}", lambda: snap.catalog.page_by_id(lang))

    @staticmethod
    def _lang(snap: Snapshot, lang: str | None) -> str | None:
        """The validated ``lang`` argument (``None`` for the canonical language)."""
        if lang is None or not lang.strip():
            return None
        value = lang.strip().lower()
        languages = list(snap.catalog.wiki_languages)
        if value not in languages:
            raise ToolInputError(
                f"unknown lang {lang!r}; languages of this wiki: {', '.join(languages)} "
                f"(the first, {languages[0]!r}, is canonical)",
                code="invalid_argument",
                details={"languages": languages},
            )
        return None if value == languages[0] else value

    @staticmethod
    def _by_path(snap: Snapshot) -> dict[str, CatalogPage]:
        return snap.cached("pages-by-path", snap.catalog.page_by_path)

    def _resolve_page(
        self, snap: Snapshot, ref: str, lang: str | None = None
    ) -> tuple[CatalogPage, str | None]:
        """Catalog entry for a page id or wiki path (``./``, ``../``, ``.md`` and ``#anchor``
        tolerated); the anchor, if any, is returned as the section to read. With ``lang`` (a
        mirror language) the mirror page of that language is returned when there is one."""
        entry, anchor = self._find_page(snap, ref, lang)
        if lang is not None and entry.lang != lang and entry.translation_of is None:
            entry = self._by_id(snap, lang).get(entry.id, entry)
        return entry, anchor

    def _find_page(
        self, snap: Snapshot, ref: str, lang: str | None = None
    ) -> tuple[CatalogPage, str | None]:
        text = ref.strip()
        if not text:
            raise ToolInputError("page must not be empty")
        by_id, by_path = self._by_id(snap, lang), self._by_path(snap)
        if text in by_id:
            return by_id[text], None
        path, _, anchor = text.partition("#")
        path = path.strip().replace("\\", "/")
        while path.startswith(("./", "../")):
            path = path.split("/", 1)[1]
        path = path.lstrip("/")
        if path.startswith("wiki/"):
            path = path[len("wiki/") :]
        candidates = [path]
        if path and not path.endswith(".md"):
            candidates += [f"{path}.md", f"{path}/index.md"]
        for candidate in candidates:
            if candidate in by_path:
                return by_path[candidate], (anchor.strip() or None)
        if path.startswith(f"{EVIDENCE_MOUNT}/"):
            raise ToolInputError(
                f"{ref!r} is an evidence sidecar, not a wiki page: call get_evidence with its "
                "source_id and locator_key (evidence/<source_id>/<locator_key>.md)",
                code="invalid_argument",
            )
        if f"topic:{text}" in by_id:
            return by_id[f"topic:{text}"], None
        pool = [*by_id, *by_path]
        close = difflib.get_close_matches(text, pool, n=5, cutoff=0.5)
        hint = f" Did you mean: {', '.join(close)}?" if close else ""
        raise ToolInputError(
            f"unknown page {ref!r}.{hint} Use search, or get_index('home') to browse page ids.",
            code="not_found",
            details={"suggestions": close} if close else None,
        )

    def _citations(self, page_path: str, defs: Sequence[FootnoteDef]) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for definition in defs:
            match = _CITATION_RE.match(definition.content.strip())
            if not match:
                out[definition.label] = {
                    "label": definition.label,
                    "text": clip(definition.content, 300),
                }
                continue
            title, sep, label = match.group("text").rpartition(" — ")
            resolved = resolve_href(page_path, match.group("href"))
            source_id = locator_key = None
            if resolved.path and resolved.path.startswith(f"{EVIDENCE_MOUNT}/"):
                parts = resolved.path.split("/")
                if len(parts) == 3 and parts[2].endswith(".md"):
                    source_id, locator_key = parts[1], parts[2][: -len(".md")]
            badge = (match.group("badge") or "").strip() or None
            out[definition.label] = {
                "label": definition.label,
                "source_title": title if sep else match.group("text"),
                "locator_label": label if sep else None,
                "source_id": source_id,
                "locator_key": locator_key,
                "evidence_path": resolved.path,
                "badge": badge,
                "provenance": PROVENANCE_BY_BADGE.get(badge or ""),
            }
        return out

    def _outgoing(self, snap: Snapshot, entry: CatalogPage, body: str) -> list[dict[str, Any]]:
        by_path = self._by_path(snap)
        links: list[dict[str, Any]] = []
        seen: set[str] = set()
        for link in extract_links(body):
            if link.image:
                continue
            resolved = resolve_href(entry.path, link.href)
            if resolved.external or not resolved.path:
                continue
            target = by_path.get(resolved.path)
            if target is None or target.id in seen or target.id == entry.id:
                continue
            seen.add(target.id)
            links.append({**_page_ref(target), "text": clip(link.text, 120)})
        return links

    def _page_parts(
        self, snap: Snapshot, entry: CatalogPage
    ) -> tuple[Any, str, dict[str, dict[str, Any]], list[dict[str, Any]]]:
        """(frontmatter, processed body, citations by label, outgoing links)."""

        def build() -> tuple[Any, str, dict[str, dict[str, Any]], list[dict[str, Any]]]:
            page = snap.reader.read_page(entry.path)
            body = strip_backlinks_block(page.body)
            _, defs = extract_footnotes(body)
            processed = _strip_footnote_definitions(body, defs)
            return (
                page.frontmatter,
                processed,
                self._citations(entry.path, defs),
                self._outgoing(snap, entry, processed),
            )

        return snap.cached(f"page:{entry.path}", build)

    @staticmethod
    def _section(body: str, wanted: str) -> tuple[str, str]:
        """Markdown of the section matching ``wanted`` (heading text or anchor), subsections
        included; returns ``(heading, markdown)``."""
        target = wanted.strip().lstrip("#").strip()
        sections = split_sections(body)
        for index, section in enumerate(sections):
            if section.heading is None:
                continue
            if section.anchor != target and section.heading.casefold() != target.casefold():
                continue
            parts = [f"{'#' * section.level} {section.heading}\n{section.markdown}".rstrip()]
            for child in sections[index + 1 :]:
                if child.heading is None or child.level <= section.level:
                    break
                parts.append(f"{'#' * child.level} {child.heading}\n{child.markdown}".rstrip())
            return section.heading, "\n\n".join(parts).strip() + "\n"
        headings = [s.heading for s in sections if s.heading and s.level >= 2]
        raise ToolInputError(
            f"section {wanted!r} not found; sections of this page: {', '.join(headings) or '-'}",
            code="not_found",
            details={"sections": headings},
        )

    @staticmethod
    def _headings(body: str) -> list[str]:
        return [s.heading for s in split_sections(body) if s.heading and 2 <= s.level <= 3]

    @staticmethod
    def _scope_values(snap: Snapshot) -> list[str]:
        """Every scope value of the release (pages and sources of the catalog)."""

        def build() -> list[str]:
            values = {page.scope for page in snap.catalog.pages if page.scope}
            values |= {source.scope for source in snap.catalog.sources if source.scope}
            return sorted(values)

        return snap.cached("scope-values", build)

    def _within(self, snap: Snapshot, within: str | None) -> str | None:
        """The validated ``within`` filter (``None`` when absent)."""
        if within is None or not within.strip():
            return None
        value = within.strip()
        if len(value) > MAX_SCOPE_CHARS or not SCOPE_VALUE_RE.match(value):
            raise ToolInputError(
                f"invalid within {within!r}: give one scope value of the wiki in kebab-case "
                "(for example a chantier code); list them with get_index('hubs/<folder>')",
                code="invalid_argument",
            )
        known = self._scope_values(snap)
        if value not in known:
            message = (
                f"unknown scope {value!r}; scopes of this wiki: {', '.join(known)}"
                if known
                else "this wiki has no scopes: call again without within"
            )
            raise ToolInputError(message, code="not_found", details={"scopes": known})
        return value

    def _in_scope(self, snap: Snapshot, entry: CatalogPage, within: str) -> bool:
        """A page with a scope matches its own; a company page (entity, company topic, filed
        answer) matches when one of its sources is of that scope."""
        if entry.scope:
            return entry.scope == within
        scopes: dict[str, str | None] = snap.cached(
            "source-scopes",
            lambda: {source.source_id: source.scope for source in snap.catalog.sources},
        )
        return any(scopes.get(source_id) == within for source_id in entry.sources)

    def _index_target(self, snap: Snapshot, entry: CatalogPage, line: str) -> CatalogPage | None:
        """The page an index line lists: the first link of the line to a wiki page."""
        by_path = self._by_path(snap)
        for link in extract_links(line):
            resolved = resolve_href(entry.path, link.href)
            if resolved.external or not resolved.path:
                continue
            target = by_path.get(resolved.path)
            if target is not None:
                return target
        return None

    def _filter_index(
        self, snap: Snapshot, entry: CatalogPage, body: str, within: str
    ) -> tuple[str, int, int]:
        """The index body without the entries (list items, table rows) that point at a page of
        another scope, and without the sections they leave empty; returns (body, kept, removed).
        """
        lines: list[str] = []
        # one row per heading: [line number in `lines`, level, had entries, kept an entry]
        sections: list[list[int]] = []
        kept = removed = 0
        for line in body.split("\n"):
            heading = _HEADING_RE.match(line)
            if heading:
                sections.append([len(lines), len(heading.group(1)), 0, 0])
                lines.append(line)
                continue
            target = self._index_target(snap, entry, line)
            if target is None or target.type not in _SCOPED_TYPES:
                lines.append(line)
                continue
            keep = self._in_scope(snap, target, within)
            if sections:
                sections[-1][2] = 1
                sections[-1][3] |= int(keep)
            if keep:
                kept += 1
                lines.append(line)
            else:
                removed += 1
        drop: set[int] = set()
        for index, (start, level, had, had_kept) in enumerate(sections):
            if level < 2 or not had or had_kept:
                continue
            end = sections[index + 1][0] if index + 1 < len(sections) else len(lines)
            drop.update(range(start, end))
        text = "\n".join(line for number, line in enumerate(lines) if number not in drop)
        return _BLANK_RUNS_RE.sub("\n\n", text).rstrip() + "\n", kept, removed

    @staticmethod
    def _refs_in(text: str) -> list[str]:
        refs, _ = extract_footnotes(text)
        return list(dict.fromkeys(label for label, _ in refs))

    # --- tools -------------------------------------------------------------------------------

    def search(
        self,
        query: str,
        kinds: Sequence[str] | None = None,
        types: Sequence[str] | None = None,
        entity: str | None = None,
        topic: str | None = None,
        limit: int = 10,
        offset: int = 0,
        within: str | None = None,
        lang: str | None = None,
    ) -> str:
        snap = self.snapshot()
        if not query.strip():
            raise ToolInputError("query must not be empty")
        scope = self._within(snap, within)
        language = self._lang(snap, lang)
        if topic and not topic.startswith("topic:"):
            topic = f"topic:{topic}"
        by_id = self._by_id(snap)
        for value, what in ((entity, "entity"), (topic, "topic")):
            if value and value not in by_id:
                raise ToolInputError(
                    f"unknown {what} {value!r}; use get_index('entities') or get_index('topics')",
                    code="not_found",
                )
        hits = snap.search.search(
            query,
            kinds=list(kinds) if kinds else None,
            types=list(types) if types else None,
            entity=entity or None,
            topic=topic or None,
            limit=offset + limit,
            within=scope,
            lang=language,
        )[offset:]
        expanded = [" ".join(phrase) for phrase in snap.search.expand(query)]
        rows = [self._hit(snap, hit) for hit in hits]

        def build(items: Sequence[dict[str, Any]], truncated: bool) -> dict[str, Any]:
            payload: dict[str, Any] = {
                "release_id": snap.release_id,
                "query": query,
                **({"within": scope} if scope else {}),
                **({"lang": language} if language else {}),
                "expanded_terms": expanded,
                "offset": offset,
                "hits": list(items),
                "truncated": truncated,
                "next_offset": offset + len(items) if truncated or len(rows) == limit else None,
            }
            if not items:
                payload["hint"] = (
                    "No hits. Try other words, synonyms or acronyms (see glossary), or fewer "
                    "filters."
                )
            return payload

        out, _ = fit_items(rows, build, self.max_chars)
        return out

    def _hit(self, snap: Snapshot, hit: Any) -> dict[str, Any]:
        entry = self._by_path(snap).get(hit.path) or self._by_id(snap).get(hit.page_id)
        row: dict[str, Any] = {
            "kind": hit.kind,
            "origin": "source" if hit.kind == "source-block" else "wiki",
            "page_id": hit.page_id,
            "path": hit.path,
            "title": hit.title,
            "section": hit.section,
            "anchor": hit.anchor,
            "snippet": hit.snippet,
            "score": hit.score,
        }
        language = getattr(hit, "lang", None) or (entry.lang if entry is not None else None)
        if language:
            row["lang"] = language
        if entry is not None and entry.status:
            row["status"] = entry.status
        if entry is not None and entry.scope:
            row["scope"] = entry.scope
        if hit.source_id:
            row["source_id"] = hit.source_id
        if hit.kind == "source-block" and hit.source_id and hit.locator_key:
            row["locator_key"] = hit.locator_key
            row["locator_label"] = hit.section
            evidence = self._evidence_meta(snap, hit.source_id, hit.locator_key)
            row["evidence_path"] = evidence["path"] if evidence else None
            row["provenance"] = evidence["provenance"] if evidence else None
        return row

    def _evidence_meta(self, snap: Snapshot, source_id: str, key: str) -> dict[str, Any] | None:
        def build() -> dict[str, Any] | None:
            try:
                record = snap.reader.resolve_evidence(source_id, key)
            except (KeyError, ValueError):
                return None
            return {"path": record.path, "provenance": record.frontmatter.provenance}

        return snap.cached(f"evidence-meta:{source_id}:{key}", build)

    # --- answer_context (index-first research, ADR 0013) -----------------------------------

    @staticmethod
    def _allowed(snap: Snapshot, sensitivity: str | None) -> bool:
        """Defence in depth: content above the release's audience is never returned (the release
        gates already keep it out of a public build)."""
        return allowed_for_audience(sensitivity or "restricted", snap.audience or "public")

    def _context_candidates(
        self,
        snap: Snapshot,
        question: str,
        scope: str | None,
        language: str | None,
        wanted: int,
    ) -> list[Any]:
        """Search hits for the question, one per section or per source locator, without content
        above the release's audience, in answer order (:func:`_spread_hits`: a few hits per
        source, and every strong scope inside the window when no ``within`` is given)."""
        raw = snap.search.search(
            question, limit=min(max(wanted * 3, 20), 100), within=scope, lang=language
        )
        by_path, by_id = self._by_path(snap), self._by_id(snap)
        seen: set[tuple[str, str]] = set()
        out: list[_Candidate] = []
        for hit in raw:
            if hit.kind == "source-block":
                key = (f"src:{hit.source_id}", str(hit.locator_key))
            else:
                key = (hit.path, str(hit.anchor or ""))
            if key in seen:
                continue
            entry = by_path.get(hit.path) or by_id.get(hit.page_id)
            if entry is None or not self._allowed(snap, entry.sensitivity):
                continue
            if entry.type in _CONTEXT_SKIPPED_TYPES:
                continue
            seen.add(key)
            group = f"src:{hit.source_id}" if hit.source_id else hit.path
            out.append(_Candidate(hit, entry.scope, group))
        return _spread_hits(out, wanted, by_scope=scope is None)

    def _context_hit(self, snap: Snapshot, hit: Any) -> _ContextHit | None:
        """The hit row, the full text of its section or evidence and the citations of that text
        (``None`` when the evidence is above the release's audience).

        A wiki hit gives its section (subsections included) and the footnote citations of the
        text actually returned; a source hit gives the verbatim text of its evidence sidecar,
        when one exists, as a ready-made citation."""
        row = self._hit(snap, hit)
        row.pop("snippet", None)
        if hit.kind == "source-block":
            if not (hit.source_id and hit.locator_key and row.get("evidence_path")):
                row["note"] = "no evidence sidecar for this block: cite the source page instead"
                return _ContextHit(row, hit.snippet)
            try:
                record = snap.reader.resolve_evidence(hit.source_id, hit.locator_key)
            except (KeyError, ValueError):
                return _ContextHit(row, hit.snippet)
            if not self._allowed(snap, record.frontmatter.sensitivity):
                return None
            provenance = record.frontmatter.provenance
            citation = {
                "source_title": hit.title,
                "locator_label": locator_label(record.frontmatter.locator),
                "source_id": hit.source_id,
                "locator_key": hit.locator_key,
                "evidence_path": record.path,
                "badge": BADGE_BY_PROVENANCE[provenance],
                "provenance": provenance,
            }
            # the sidecar's content starts at its first section ("## Text", "## Row 6"...): the
            # title, banner and source link before it are already in the hit row
            body = record.body
            start = body.find("\n## ")
            content = body[start + 1 :] if start >= 0 else body
            return _ContextHit(row, content.strip() + "\n", fixed=[citation])
        entry = self._by_path(snap).get(hit.path) or self._by_id(snap).get(hit.page_id)
        if entry is None:
            return _ContextHit(row, hit.snippet)
        _, body, citations, _ = self._page_parts(snap, entry)
        sections = split_sections(body)
        # The section the search row indexed: its own text, without its subsections (they are
        # search rows of their own).
        match = next((s for s in sections if hit.anchor and s.anchor == hit.anchor), None)
        if match is None:
            match = next((s for s in sections if s.heading is None), None)
        if match is None or match.heading is None:
            text = match.markdown if match is not None else hit.snippet
        else:
            text = f"{'#' * match.level} {match.heading}\n{match.markdown}"
        return _ContextHit(row, text.strip() + "\n", by_label=citations)

    @staticmethod
    def _trim(text: str, limit: int) -> tuple[str, bool]:
        """``text`` cut to at most ``limit`` characters at a line break when possible."""
        if len(text) <= limit:
            return text, False
        cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = text.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        return text[:cut].rstrip() + "\n…\n", True

    def _bounded_page(
        self, snap: Snapshot, entry: CatalogPage, limit: int, within: str | None = None
    ) -> dict[str, Any]:
        """A short window of an index or hub page, with the citations of that window."""
        _, body, citations, _ = self._page_parts(snap, entry)
        if within:
            body, _, _ = self._filter_index(snap, entry, body, within)
        window, cut = self._trim(body, limit)
        out: dict[str, Any] = {
            "page_id": entry.id,
            "path": entry.path,
            "title": entry.title,
            "markdown": window,
            "truncated": cut,
        }
        if entry.scope:
            out["scope"] = entry.scope
        labels = self._refs_in(window)
        if labels:
            out["citations"] = [citations[x] for x in labels if x in citations]
        return out

    def _hub_for(self, snap: Snapshot, scope: str, language: str | None) -> CatalogPage | None:
        hubs = sorted(
            (p for p in snap.catalog.pages if p.type == "hub" and p.scope == scope),
            key=lambda p: p.id,
        )
        hubs = [p for p in hubs if p.translation_of is None] or hubs
        if not hubs:
            return None
        entry = self._by_id(snap, language).get(hubs[0].id, hubs[0])
        return entry if self._allowed(snap, entry.sensitivity) else None

    def answer_context(
        self,
        question: str,
        within: str | None = None,
        limit: int = ANSWER_CONTEXT_HITS,
        offset: int = 0,
        lang: str | None = None,
    ) -> str:
        snap = self.snapshot()
        if not question.strip():
            raise ToolInputError("question must not be empty: give the user's question")
        scope = self._within(snap, within)
        language = self._lang(snap, lang)
        limit = max(1, min(limit, MAX_ANSWER_CONTEXT_HITS))
        offset = max(0, offset)
        candidates = self._context_candidates(snap, question, scope, language, offset + limit)
        window = candidates[offset : offset + limit]
        more = len(candidates) > offset + limit
        parts = [part for hit in window if (part := self._context_hit(snap, hit)) is not None]

        def hit_rows(budget: int) -> list[dict[str, Any]]:
            rows: list[dict[str, Any]] = []
            for rank, part in enumerate(parts, offset + 1):
                shown, cut = self._trim(part.text, budget)
                cited = part.fixed + [
                    part.by_label[x] for x in self._refs_in(shown) if x in part.by_label
                ]
                rows.append(
                    {
                        "rank": rank,
                        **part.row,
                        "text": shown,
                        "text_truncated": cut,
                        "citations": cited,
                    }
                )
            return rows

        context: dict[str, Any] = {}
        if offset == 0:
            home = self._by_id(snap, language).get("index:home")
            if home is not None and self._allowed(snap, home.sensitivity):
                context["home_index"] = self._bounded_page(snap, home, CONTEXT_INDEX_CHARS, scope)
            hub_scope = scope or _dominant_scope([part.row for part in parts])
            hub = self._hub_for(snap, hub_scope, language) if hub_scope else None
            if hub is not None:
                context["hub"] = self._bounded_page(snap, hub, CONTEXT_HUB_CHARS)
            hit_scopes = [part.row["scope"] for part in parts if part.row.get("scope")]
            if scope is None and len(set(hit_scopes)) >= 2:
                spread: list[dict[str, Any]] = []
                for value in sorted(set(hit_scopes), key=lambda s: (-hit_scopes.count(s), s)):
                    item: dict[str, Any] = {"scope": value, "hits": hit_scopes.count(value)}
                    scope_hub = self._hub_for(snap, value, language)
                    if scope_hub is not None:
                        item["hub_path"] = scope_hub.path
                    spread.append(item)
                context["scopes"] = spread
            context["views"] = [
                {
                    "page_id": page.id,
                    "path": page.path,
                    "title": page.title,
                    "summary": clip(page.summary, 160),
                }
                for page in sorted(self._by_id(snap, language).values(), key=lambda p: p.id)
                if page.type == "view" and self._allowed(snap, page.sensitivity)
            ]

        def build(items: Sequence[dict[str, Any]], truncated: bool) -> dict[str, Any]:
            return {
                "release_id": snap.release_id,
                "question": question,
                **({"within": scope} if scope else {}),
                **({"lang": language} if language else {}),
                "offset": offset,
                "hits": list(items),
                **context,
                "truncated": truncated,
                "next_offset": offset + len(items) if truncated or more else None,
                "hint": ANSWER_CONTEXT_HINT if items else ANSWER_CONTEXT_EMPTY_HINT,
            }

        # shorten the section texts first; drop hits only when even the shortest do not fit
        for budget in CONTEXT_TEXT_BUDGETS:
            rows = hit_rows(budget)
            out = result_json(build(rows, False))
            if len(out) <= self.max_chars:
                return out
        out, _ = fit_items(rows, build, self.max_chars)
        return out

    def read_page(
        self, page: str, section: str | None = None, offset: int = 0, lang: str | None = None
    ) -> str:
        snap = self.snapshot()
        entry, anchor = self._resolve_page(snap, page, self._lang(snap, lang))
        section = section or anchor
        frontmatter, body, citations, links = self._page_parts(snap, entry)
        heading = None
        text = body
        if section:
            heading, text = self._section(body, section)
        meta = frontmatter.model_dump(mode="json", by_alias=True)
        extra = {key: value for key, value in meta.items() if key not in _FRONTMATTER_TOP}
        headings = self._headings(body)

        def attempt(link_limit: int | None) -> str:
            def build(window: str, next_offset: int | None) -> dict[str, Any]:
                labels = self._refs_in(window)
                payload: dict[str, Any] = {
                    "release_id": snap.release_id,
                    "page_id": entry.id,
                    "path": entry.path,
                    "type": entry.type,
                    "title": entry.title,
                    "lang": entry.lang,
                }
                if entry.translation_of is not None:
                    payload["translation_of"] = entry.translation_of
                if entry.status:
                    payload["status"] = entry.status
                if offset == 0 and link_limit is not None:
                    payload.update(
                        summary=entry.summary,
                        sensitivity=entry.sensitivity,
                        frontmatter=extra,
                        sections=headings,
                        links=links[:link_limit],
                        links_truncated=len(links) > link_limit,
                    )
                elif offset == 0:
                    payload["metadata_omitted"] = True
                payload.update(
                    section=heading,
                    offset=offset,
                    chars_total=len(text),
                    markdown=window,
                    truncated=next_offset is not None,
                    next_offset=next_offset,
                    citations=[citations[label] for label in labels if label in citations],
                )
                if next_offset is not None:
                    payload["hint"] = "Call read_page again with next_offset, or ask for a section."
                return payload

            return fit_text(text, offset, build, self.max_chars)

        limits: tuple[int | None, ...] = (MAX_LINKS, 20, 5, None) if offset == 0 else (None,)
        for limit in limits[:-1]:
            try:
                return attempt(limit)
            except ResultTooLargeError:
                continue
        return attempt(limits[-1])

    def _index_scopes(self, snap: Snapshot) -> list[str]:
        scopes = list(INDEX_SCOPES)
        by_id = self._by_id(snap)
        scopes += sorted(
            page_id.removeprefix("index:")
            for page_id in by_id
            if page_id.startswith(("index:entities/", "index:hubs/"))
        )
        return [scope for scope in scopes if INDEX_SCOPES.get(scope, f"index:{scope}") in by_id]

    def get_index(
        self,
        scope: str = "home",
        offset: int = 0,
        within: str | None = None,
        lang: str | None = None,
    ) -> str:
        snap = self.snapshot()
        wanted = (scope or "home").strip().strip("/").lower().removeprefix("index:")
        language = self._lang(snap, lang)
        by_id = self._by_id(snap, language)
        hubs = sorted(page_id for page_id in by_id if page_id.startswith("index:hubs/"))
        if wanted == "hubs" and len(hubs) == 1:
            wanted = hubs[0].removeprefix("index:")
        page_id = INDEX_SCOPES.get(wanted, f"index:{wanted}")
        entry = by_id.get(page_id)
        if entry is None:
            valid = ", ".join(self._index_scopes(snap))
            raise ToolInputError(
                f"unknown index scope {scope!r}; valid scopes: {valid}",
                code="not_found",
                details={"scopes": self._index_scopes(snap)},
            )
        scope_value = self._within(snap, within)
        _, body, citations, _ = self._page_parts(snap, entry)
        filtered: dict[str, Any] = {}
        if scope_value:
            body, kept, removed = self._filter_index(snap, entry, body, scope_value)
            filtered = {"within": scope_value, "entries_kept": kept, "entries_removed": removed}

        def build(window: str, next_offset: int | None) -> dict[str, Any]:
            payload: dict[str, Any] = {
                "release_id": snap.release_id,
                "scope": wanted,
                "page_id": entry.id,
                "path": entry.path,
                "title": entry.title,
                "lang": entry.lang,
                **filtered,
                "offset": offset,
                "chars_total": len(body),
                "markdown": window,
                "truncated": next_offset is not None,
                "next_offset": next_offset,
            }
            if offset == 0:
                payload["scopes"] = scopes
                if len(snap.catalog.wiki_languages) > 1:
                    payload["languages"] = list(snap.catalog.wiki_languages)
            labels = self._refs_in(window)
            if labels:
                payload["citations"] = [citations[x] for x in labels if x in citations]
            return payload

        scopes = self._index_scopes(snap)
        return fit_text(body, offset, build, self.max_chars)

    def get_links(self, page: str, offset: int = 0) -> str:
        snap = self.snapshot()
        entry, _ = self._resolve_page(snap, page)
        by_id = self._by_id(snap)
        edges = snap.reader.links(entry.id)
        merged: dict[tuple[str, str], set[str]] = {}
        for direction, items in (
            ("outgoing", edges["outgoing"]),
            ("backlinks", edges["backlinks"]),
        ):
            for edge in items:
                other = edge.to if direction == "outgoing" else edge.from_
                merged.setdefault((direction, other), set()).add(edge.kind)
        rows = [
            (direction, {**_page_ref(by_id[other]), "kinds": sorted(kinds)})
            for (direction, other), kinds in sorted(merged.items())
            if other in by_id
        ][offset:]

        def build(items: Sequence[tuple[str, dict[str, Any]]], truncated: bool) -> dict[str, Any]:
            return {
                "release_id": snap.release_id,
                "page_id": entry.id,
                "path": entry.path,
                "title": entry.title,
                "edge_kinds": {
                    "mentions": "source -> entity it mentions",
                    "supersedes": "newer source -> older source it replaces",
                    "topic-of": "topic -> source it synthesises",
                    "cites": "page -> source whose evidence it cites",
                    "related": "page -> page linked in its Related section",
                },
                "outgoing": [item for direction, item in items if direction == "outgoing"],
                "backlinks": [item for direction, item in items if direction == "backlinks"],
                "offset": offset,
                "truncated": truncated,
                "next_offset": offset + len(items) if truncated else None,
            }

        out, _ = fit_items(rows, build, self.max_chars)
        return out

    def _glossary_entries(self, snap: Snapshot) -> list[dict[str, Any]]:
        def build() -> list[dict[str, Any]]:
            by_path = self._by_path(snap)
            sections: dict[str, Any] = {}
            glossary_entry = self._by_id(snap).get("glossary")
            if glossary_entry is not None:
                _, body, _, _ = self._page_parts(snap, glossary_entry)
                for section in split_sections(body):
                    if section.anchor:
                        sections[section.anchor] = section
            entries: list[dict[str, Any]] = []
            for item in snap.catalog.glossary:
                anchor = item.page.partition("#")[2]
                term_section = sections.get(anchor)
                definition_lines: list[str] = []
                see_also: list[dict[str, Any]] = []
                if term_section is not None:
                    for line in term_section.markdown.split("\n"):
                        stripped = line.strip()
                        if stripped.startswith("- Synonyms:"):
                            continue
                        if stripped.startswith("- See also:"):
                            for link in extract_links(stripped):
                                resolved = resolve_href("glossary.md", link.href)
                                target = by_path.get(resolved.path or "")
                                if target is not None:
                                    see_also.append(_page_ref(target))
                            continue
                        definition_lines.append(line)
                definition = markdown_to_text("\n".join(definition_lines)).replace("\n", " ")
                entries.append(
                    {
                        "term": item.term,
                        "definition": clip(definition.strip(), 600) or None,
                        "synonyms": item.synonyms,
                        "see_also": see_also,
                        "anchor": item.page,
                    }
                )
            return entries

        return snap.cached("glossary-entries", build)

    def glossary(self, term: str | None = None, offset: int = 0) -> str:
        snap = self.snapshot()
        entries = self._glossary_entries(snap)
        matched: list[dict[str, Any]]
        if term and term.strip():
            wanted = _norm(term)
            wanted_tokens = set(wanted.split())
            scored: list[tuple[float, str, dict[str, Any]]] = []
            for item in entries:
                names = [item["term"], *(s for values in item["synonyms"].values() for s in values)]
                token_sets = [set(_norm(name).split()) for name in names]
                score = 0.0
                if any(_norm(name) == wanted for name in names):
                    score = 3.0
                elif wanted_tokens and any(
                    tokens and (wanted_tokens <= tokens or tokens <= wanted_tokens)
                    for tokens in token_sets
                ):
                    score = 2.0
                elif any(wanted_tokens & tokens for tokens in token_sets):
                    score = 1.0
                elif wanted_tokens & set(_norm(item["definition"] or "").split()):
                    score = 0.5
                if score:
                    scored.append((score, item["term"].casefold(), item))
            matched = [item for _, _, item in sorted(scored, key=lambda x: (-x[0], x[1]))]
        else:
            matched = sorted(entries, key=lambda item: item["term"].casefold())
        rows = matched[offset:]

        def build(items: Sequence[dict[str, Any]], truncated: bool) -> dict[str, Any]:
            payload: dict[str, Any] = {
                "release_id": snap.release_id,
                "term": term,
                "matches": list(items),
                "total": len(matched),
                "offset": offset,
                "truncated": truncated,
                "next_offset": offset + len(items) if truncated else None,
            }
            if term and not matched:
                payload["hint"] = "No glossary entry matches; try search with the term instead."
            return payload

        out, _ = fit_items(rows, build, self.max_chars)
        return out

    def _source_ref(self, snap: Snapshot, source_id: str) -> dict[str, Any] | None:
        entry = self._by_id(snap).get(source_id)
        raw = next((s for s in snap.catalog.sources if s.source_id == source_id), None)
        if entry is None and raw is None:
            return None
        ref: dict[str, Any] = _page_ref(entry) if entry else {"page_id": None}
        if raw is not None:
            ref.update(
                {
                    "source_path": raw.path,
                    "media_type": raw.media_type,
                    "doc_number": raw.doc_number,
                    "revision": raw.revision,
                    "status": raw.status,
                }
            )
        return ref

    def _check_source_id(self, snap: Snapshot, source_id: str) -> str:
        value = source_id.strip()
        if not SOURCE_ID_RE.match(value):
            raise ToolInputError(
                f"invalid source_id {source_id!r}: expected 'src-' followed by 12 hex digits"
            )
        return value

    def get_evidence(self, source_id: str, locator_key: str, offset: int = 0) -> str:
        snap = self.snapshot()
        sid = self._check_source_id(snap, source_id)
        key = locator_key.strip().removesuffix(".md")
        try:
            parse_locator_key(key)
        except ValueError:
            raise ToolInputError(
                f"invalid locator_key {locator_key!r} (examples: p0003, para-0042, "
                "sheet-plan-r0012-r0020, slide-05)"
            ) from None
        try:
            record = snap.reader.resolve_evidence(sid, key)
        except KeyError:
            available = [
                path.rsplit("/", 1)[-1].removesuffix(".md")
                for path in snap.reader.list_evidence(sid)
            ]
            if not available and self._source_ref(snap, sid) is None:
                raise ToolInputError(
                    f"unknown source {sid} in release {snap.release_id}; use search or "
                    "get_index('sources') to find source ids",
                    code="not_found",
                ) from None
            raise ToolInputError(
                code="not_found",
                details={"available": available[:30]},
                message=f"no evidence sidecar {sid}/{key}; sidecars exist only for cited locators. "
                f"Available for {sid}: {', '.join(available[:30]) or 'none'}. For an uncited "
                "block found by search, cite the source page or use query_table for tables.",
            ) from None
        fm = record.frontmatter
        tables = self._has_tables(snap, sid)
        body = record.body

        def build(window: str, next_offset: int | None) -> dict[str, Any]:
            return {
                "release_id": snap.release_id,
                "source_id": sid,
                "locator_key": key,
                "locator_label": locator_label(fm.locator),
                "locator": fm.locator.model_dump(mode="json"),
                "provenance": fm.provenance,
                "badge": BADGE_BY_PROVENANCE[fm.provenance],
                "title": fm.title,
                "evidence_path": record.path,
                "original": record.original,
                "sensitivity": fm.sensitivity,
                "source": self._source_ref(snap, sid),
                "tables_available": tables,
                "offset": offset,
                "chars_total": len(body),
                "content": window,
                "truncated": next_offset is not None,
                "next_offset": next_offset,
            }

        return fit_text(body, offset, build, self.max_chars)

    @staticmethod
    def _has_tables(snap: Snapshot, source_id: str) -> bool:
        try:
            return bool(snap.reader.tables(source_id).tables)
        except (KeyError, ValueError):
            return False

    def query_table(self, source_id: str, sql: str) -> str:
        snap = self.snapshot()
        sid = self._check_source_id(snap, source_id)
        if not sql.strip():
            raise ToolInputError("sql must not be empty")
        if len(sql) > MAX_SQL_CHARS:
            raise ToolInputError(f"sql is longer than {MAX_SQL_CHARS} characters", code="too_large")
        first = _FIRST_KEYWORD_RE.match(sql)
        if first is None or first.group(1).lower() not in _QUERY_KEYWORDS:
            raise ToolInputError(
                "query rejected: only a single read-only SELECT (or WITH ... SELECT) is allowed"
            )
        try:
            index = snap.reader.tables(sid)
        except (KeyError, ValueError):
            with_tables = snap.reader.sources_with_tables()
            raise ToolInputError(
                f"source {sid} has no tables in this release; sources with tables: "
                f"{', '.join(with_tables) or 'none'}",
                code="not_found",
                details={"sources_with_tables": with_tables[:30]},
            ) from None
        schema: list[dict[str, Any]] = [
            {
                "table": table.id,
                "locator_key": _locator_key_or_none(table.locator),
                "locator_label": locator_label(table.locator),
                "provenance": table.provenance,
                "row_count": table.row_count,
                "columns": [[c.name, c.header, c.type] for c in table.columns],
            }
            for table in index.tables
        ]
        try:
            result = snap.reader.query_table(sid, sql, max_rows=self.config.query_max_rows)
        except TableQueryError as exc:
            raise ToolInputError(
                f"query rejected: {exc}. Write one read-only SELECT over tables "
                f"{', '.join(t['table'] for t in schema)} (see the schema below).\n"
                + "\n".join(
                    f"{t['table']}({', '.join(c[0] for c in t['columns'])}, row_id)" for t in schema
                )
            ) from None
        rows = [
            [clip(v, MAX_CELL_CHARS) if isinstance(v, str) else v for v in row]
            for row in result.rows
        ]
        source = self._source_ref(snap, sid)

        def build(items: Sequence[list[Any]], truncated: bool) -> dict[str, Any]:
            payload: dict[str, Any] = {
                "release_id": snap.release_id,
                "source_id": sid,
                "source": source,
                "sql": sql,
                "columns": result.columns,
                "rows": list(items),
                "row_count": len(items),
                "row_limit": self.config.query_max_rows,
                "truncated": truncated or result.truncated,
                "tables": schema,
            }
            if truncated or result.truncated:
                payload["hint"] = (
                    "More rows match: narrow the WHERE clause, select fewer columns, or page with "
                    "LIMIT/OFFSET."
                )
            if "row_id" not in result.columns:
                payload["note"] = "Select row_id to cite individual rows (row_id = original row)."
            return payload

        out, _ = fit_items(rows, build, self.max_chars)
        return out

    def get_skill(self, name: str, offset: int = 0) -> str:
        snap = self.snapshot()
        skills = {skill.name: skill for skill in snap.reader.list_skills()}
        wanted = name.strip()
        if wanted not in skills:
            raise ToolInputError(
                f"unknown skill {name!r}; available skills: {', '.join(sorted(skills)) or 'none'}",
                code="not_found",
            )
        info = skills[wanted]
        text = snap.reader.read_skill(wanted)

        def build(window: str, next_offset: int | None) -> dict[str, Any]:
            return {
                "release_id": snap.release_id,
                "name": info.name,
                "description": info.description,
                "path": info.path,
                "offset": offset,
                "chars_total": len(text),
                "content": window,
                "truncated": next_offset is not None,
                "next_offset": next_offset,
            }

        return fit_text(text, offset, build, self.max_chars)

    def list_skills(self) -> str:
        snap = self.snapshot()
        skills = [
            {"name": skill.name, "description": skill.description, "path": skill.path}
            for skill in snap.reader.list_skills()
        ]

        def build(items: Sequence[dict[str, Any]], truncated: bool) -> dict[str, Any]:
            return {
                "release_id": snap.release_id,
                "skills": list(items),
                "projections": list(SKILL_PROJECTIONS),
                "truncated": truncated,
            }

        out, _ = fit_items(skills, build, self.max_chars)
        return out

    def _log_entries(self, snap: Snapshot) -> list[dict[str, Any]]:
        def build() -> list[dict[str, Any]]:
            entry = self._by_id(snap).get("log")
            if entry is None:
                return []
            by_path = self._by_path(snap)
            page = snap.reader.read_page(entry.id)
            entries: list[dict[str, Any]] = []
            for section in split_sections(page.body):
                match = _LOG_HEADING_RE.match(section.heading or "")
                if not match:
                    continue
                pages: list[dict[str, Any]] = []
                for link in extract_links(section.markdown):
                    resolved = resolve_href(entry.path, link.href)
                    target = by_path.get(resolved.path or "")
                    if target is not None and all(p["page_id"] != target.id for p in pages):
                        pages.append(_page_ref(target))
                details = markdown_to_text(section.markdown).replace("\n", " ").strip()
                title = match.group("title").strip()
                entries.append(
                    {
                        "date": match.group("date"),
                        "action": match.group("action"),
                        "title": title,
                        "details": clip(details, 300) if details and details != title else None,
                        "pages": pages,
                    }
                )
            entries.reverse()
            return entries

        return snap.cached("log-entries", build)

    def recent_changes(self, since: date | None = None, limit: int = 20, offset: int = 0) -> str:
        snap = self.snapshot()
        entries = self._log_entries(snap)
        if since is not None:
            floor = since.isoformat()
            entries = [item for item in entries if item["date"] >= floor]
        window = entries[offset : offset + limit]
        more = offset + limit < len(entries)

        def build(items: Sequence[dict[str, Any]], truncated: bool) -> dict[str, Any]:
            return {
                "release_id": snap.release_id,
                "since": since.isoformat() if since else None,
                "order": "newest first",
                "entries": list(items),
                "total": len(entries),
                "offset": offset,
                "truncated": truncated or more,
                "next_offset": offset + len(items) if truncated or more else None,
            }

        out, _ = fit_items(window, build, self.max_chars)
        return out


def _locator_key_or_none(locator: Any) -> str | None:
    """Locator key of a table locator (``None`` when it cannot be derived)."""
    try:
        return locator_key(locator)
    except (ValueError, TypeError):
        return None
