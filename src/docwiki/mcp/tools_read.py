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
from datetime import date
from typing import Any

from docwiki.contracts.catalog import CatalogPage
from docwiki.contracts.enums import BADGE_BY_PROVENANCE
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
from docwiki.mcp.bounds import ResultTooLargeError, clip, fit_items, fit_text
from docwiki.mcp.config import McpConfig
from docwiki.mcp.errors import ToolFailure
from docwiki.mcp.source import ReleaseSource, Snapshot
from docwiki.release import TableQueryError
from docwiki.search.text import tokenize

__all__ = ["INDEX_SCOPES", "ReadTools", "ToolInputError"]


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
"""Fixed ``get_index`` scopes; ``entities/<type>`` scopes come from the catalog."""

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


def _norm(text: str) -> str:
    return " ".join(tokenize(text))


def _page_ref(entry: CatalogPage) -> dict[str, Any]:
    ref: dict[str, Any] = {"page_id": entry.id, "path": entry.path, "title": entry.title}
    ref["type"] = entry.type
    if entry.status:
        ref["status"] = entry.status
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
    def _by_id(snap: Snapshot) -> dict[str, CatalogPage]:
        return snap.cached("pages-by-id", snap.catalog.page_by_id)

    @staticmethod
    def _by_path(snap: Snapshot) -> dict[str, CatalogPage]:
        return snap.cached("pages-by-path", snap.catalog.page_by_path)

    def _resolve_page(self, snap: Snapshot, ref: str) -> tuple[CatalogPage, str | None]:
        """Catalog entry for a page id or wiki path (``./``, ``../``, ``.md`` and ``#anchor``
        tolerated); the anchor, if any, is returned as the section to read."""
        text = ref.strip()
        if not text:
            raise ToolInputError("page must not be empty")
        by_id, by_path = self._by_id(snap), self._by_path(snap)
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
            page = snap.reader.read_page(entry.id)
            body = strip_backlinks_block(page.body)
            _, defs = extract_footnotes(body)
            processed = _strip_footnote_definitions(body, defs)
            return (
                page.frontmatter,
                processed,
                self._citations(entry.path, defs),
                self._outgoing(snap, entry, processed),
            )

        return snap.cached(f"page:{entry.id}", build)

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
    ) -> str:
        snap = self.snapshot()
        if not query.strip():
            raise ToolInputError("query must not be empty")
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
        )[offset:]
        expanded = [" ".join(phrase) for phrase in snap.search.expand(query)]
        rows = [self._hit(snap, hit) for hit in hits]

        def build(items: Sequence[dict[str, Any]], truncated: bool) -> dict[str, Any]:
            payload: dict[str, Any] = {
                "release_id": snap.release_id,
                "query": query,
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
        entry = self._by_id(snap).get(hit.page_id)
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
        if entry is not None and entry.status:
            row["status"] = entry.status
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

    def read_page(self, page: str, section: str | None = None, offset: int = 0) -> str:
        snap = self.snapshot()
        entry, anchor = self._resolve_page(snap, page)
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
                }
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
            if page_id.startswith("index:entities/")
        )
        return [scope for scope in scopes if INDEX_SCOPES.get(scope, f"index:{scope}") in by_id]

    def get_index(self, scope: str = "home", offset: int = 0) -> str:
        snap = self.snapshot()
        wanted = (scope or "home").strip().strip("/").lower().removeprefix("index:")
        page_id = INDEX_SCOPES.get(wanted, f"index:{wanted}")
        entry = self._by_id(snap).get(page_id)
        if entry is None:
            valid = ", ".join(self._index_scopes(snap))
            raise ToolInputError(
                f"unknown index scope {scope!r}; valid scopes: {valid}",
                code="not_found",
                details={"scopes": self._index_scopes(snap)},
            )
        _, body, citations, _ = self._page_parts(snap, entry)

        def build(window: str, next_offset: int | None) -> dict[str, Any]:
            payload: dict[str, Any] = {
                "release_id": snap.release_id,
                "scope": wanted,
                "page_id": entry.id,
                "path": entry.path,
                "title": entry.title,
                "offset": offset,
                "chars_total": len(body),
                "markdown": window,
                "truncated": next_offset is not None,
                "next_offset": next_offset,
            }
            if offset == 0:
                payload["scopes"] = scopes
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
