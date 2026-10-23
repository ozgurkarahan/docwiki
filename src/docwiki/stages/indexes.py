"""Stage 8 — ``indexes``: home page, indexes, glossary, log, ``llms.txt`` and the catalog.

Everything here is computed from validated page frontmatter and the domain pack; strings that
originate in documents (titles, summaries) are escaped with :func:`inline_text`. The log is
append-only: the previous release's ``log.md`` is kept verbatim and dated entries are appended
for this release's ingest / update / supersede / withdraw / topic changes; links in old entries
whose target no longer exists are turned into plain text so that the release stays link-clean.
"""

from __future__ import annotations

import contextlib
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime

from docwiki.contracts.catalog import (
    Catalog,
    CatalogEdge,
    CatalogGlossaryEntry,
    catalog_page_for,
    catalog_source_for,
)
from docwiki.contracts.enums import LogAction
from docwiki.contracts.frontmatter import FrontmatterError, read_frontmatter
from docwiki.contracts.i18n import Strings, core_strings
from docwiki.contracts.layout import WikiFiles
from docwiki.contracts.markdown import extract_headings, relative_link, resolve_href
from docwiki.contracts.pages import (
    DocwikiStamp,
    EntityFrontmatter,
    GlossaryFrontmatter,
    IndexFrontmatter,
    LogFrontmatter,
    MetaFrontmatter,
    Page,
    QueryFrontmatter,
    SourceFrontmatter,
    TopicFrontmatter,
)
from docwiki.domain.models import DomainPack
from docwiki.engine_types import TopicSkip
from docwiki.stages.hubs import HubBundle, dashboard_lines, scope_label
from docwiki.stages.links import inline_text, md_link, one_line, plural

__all__ = [
    "META_RUNS_DIR",
    "STAGE_VERSION",
    "IndexBundle",
    "LogEntry",
    "ParsedLogEntry",
    "build_catalog",
    "build_indexes",
    "changes_since",
    "meta_page",
    "parse_log_entries",
    "run_page_path",
]

STAGE_VERSION = "2"
META_RUNS_DIR = WikiFiles.RUNS_DIR
RECENT_CHANGES = 10
_LOG_HEADING_RE = re.compile(
    r"^## \[(?P<day>\d{4}-\d{2}-\d{2})\] (?P<action>[a-z]+) \| (?P<title>.+)$"
)
_INLINE_LINK_RE = re.compile(r"(?<!!)\[(?P<text>(?:[^\[\]\\]|\\.)*)\]\((?P<href>[^)\s]+)\)")
_SKIP_REASONS = ("insufficient_evidence", "audience", "no_current_sources")


def run_page_path(run_id: str) -> str:
    return f"{META_RUNS_DIR}/{run_id}.md"


def meta_page(
    page_id: str,
    path: str,
    title: str,
    summary: str,
    body: str,
    *,
    stamp: DocwikiStamp,
    updated: date,
    sensitivity: str,
) -> Page:
    """A ``meta`` page (``AGENTS.md``, ``_meta/quality.md``, ``_meta/runs/<run_id>.md``)."""
    frontmatter = MetaFrontmatter(
        id=page_id,
        title=title,
        summary=summary,
        sensitivity=sensitivity,  # type: ignore[arg-type]
        updated=updated,
        docwiki=stamp,
    )
    return Page(path=path, frontmatter=frontmatter, body=body)


def _index_page(
    scope: str,
    path: str,
    title: str,
    summary: str,
    body: str,
    *,
    stamp: DocwikiStamp,
    updated: date,
    sensitivity: str,
    lang: str = "en",
) -> Page:
    frontmatter = IndexFrontmatter(
        id=f"index:{scope}",
        title=title,
        summary=summary,
        lang=lang,
        sensitivity=sensitivity,  # type: ignore[arg-type]
        updated=updated,
        docwiki=stamp,
    )
    return Page(path=path, frontmatter=frontmatter, body=body)


def _by_title(pages: Iterable[Page]) -> list[Page]:
    return sorted(pages, key=lambda page: (page.frontmatter.title.casefold(), page.path))


def _summary(page: Page) -> str:
    return inline_text(page.frontmatter.summary) if page.frontmatter.summary.strip() else ""


def _item(page: Page, from_path: str, detail: str | None = None) -> str:
    text = detail if detail is not None else _summary(page)
    link = md_link(page.frontmatter.title, from_path, page.path)
    return f"- {link}: {text}" if text else f"- {link}"


# -- log -------------------------------------------------------------------------------


@dataclass(frozen=True)
class LogEntry:
    """A new log entry; ``bullets`` are Markdown with links relative to the wiki root."""

    day: date
    action: LogAction
    title: str
    bullets: tuple[str, ...]

    def render(self) -> str:
        lines = [f"## [{self.day.isoformat()}] {self.action} | {inline_text(self.title)}", ""]
        lines += [f"- {bullet}" for bullet in self.bullets]
        return "\n".join(lines)


@dataclass(frozen=True)
class ParsedLogEntry:
    day: str
    action: str
    title: str
    link: str | None
    """Path (relative to the wiki root) of the first live link of the entry."""


def changes_since(
    previous: Catalog | None,
    pages: Sequence[Page],
    *,
    day: date,
    removed: Mapping[str, str] | None = None,
    removed_queries: Mapping[str, str] | None = None,
    strings: Strings | None = None,
) -> list[LogEntry]:
    """Log entries for this release compared with the previous release's catalog.

    ``removed`` explains why a source that had a page is gone (``source_id`` → reason text);
    the default reason is a deleted raw file. ``removed_queries`` explains why research answers
    are left out of this release (page id → reason text): those the previous release published
    get a ``withdraw`` entry. Answers left out for the audience are not passed (no mention).
    ``strings`` is the language of the entries (default English); the previous release's pages
    of that language are compared (its canonical pages when it had no such mirror).
    """
    t = strings or core_strings()
    prev_sources = {source.source_id: source for source in (previous.sources if previous else [])}
    prev_pages = previous.page_by_id(t.lang) if previous else {}
    by_id = {page.frontmatter.id: page for page in pages}
    sources = _by_title(p for p in pages if isinstance(p.frontmatter, SourceFrontmatter))
    entries: list[LogEntry] = []

    def link(page: Page) -> str:
        return md_link(page.frontmatter.title, WikiFiles.LOG, page.path)

    for page in sources:
        fm = page.frontmatter
        assert isinstance(fm, SourceFrontmatter)
        before = prev_sources.get(fm.source_id)
        if before is None:
            entries.append(LogEntry(day, "ingest", fm.title, (link(page),)))
        elif before.hash != fm.source_hash:
            entries.append(LogEntry(day, "update", fm.title, (link(page),)))
    for page in sources:
        fm = page.frontmatter
        assert isinstance(fm, SourceFrontmatter)
        before = prev_sources.get(fm.source_id)
        if fm.status == "superseded" and (before is None or before.status != "superseded"):
            newer = [by_id[s] for s in fm.superseded_by if s in by_id]
            replacement = ", ".join(link(item) for item in _by_title(newer))
            bullet = (
                t("index.log.superseded", page=link(page), replacement=replacement)
                if replacement
                else link(page)
            )
            entries.append(LogEntry(day, "supersede", fm.title, (bullet,)))
    current_ids = {page.frontmatter.id for page in sources}
    for source_id in sorted(set(prev_sources) - current_ids):
        title = prev_pages[source_id].title if source_id in prev_pages else source_id
        reason = (removed or {}).get(source_id, t("index.log.raw_deleted"))
        entries.append(
            LogEntry(
                day,
                "withdraw",
                title,
                (t("index.log.source_removed", reason=inline_text(reason)),),
            )
        )
    for page in _by_title(p for p in pages if isinstance(p.frontmatter, TopicFrontmatter)):
        fm = page.frontmatter
        assert isinstance(fm, TopicFrontmatter)
        before_page = prev_pages.get(fm.id)
        if (
            before_page is None
            or sorted(before_page.sources) != list(fm.sources)
            or before_page.summary != fm.summary
        ):
            entries.append(LogEntry(day, "topic", fm.title, (link(page),)))
    for page in _by_title(p for p in pages if isinstance(p.frontmatter, QueryFrontmatter)):
        fm = page.frontmatter
        assert isinstance(fm, QueryFrontmatter)
        before_page = prev_pages.get(fm.id)
        if before_page is None or before_page.summary != fm.summary:
            entries.append(LogEntry(day, "query", fm.title, (link(page),)))
    queries_removed = removed_queries or {}
    gone = [
        prev_pages[page_id]
        for page_id in queries_removed
        if page_id in prev_pages and page_id not in by_id
    ]
    for before_page in sorted(gone, key=lambda item: (item.title.casefold(), item.path)):
        reason = inline_text(queries_removed[before_page.id])
        entries.append(
            LogEntry(
                day,
                "withdraw",
                before_page.title,
                (t("index.log.query_removed", reason=reason),),
            )
        )
    return entries


def _previous_entries(previous_log: str | None) -> str:
    """Entries of the previous ``log.md`` (everything from the first ``## [`` heading)."""
    if not previous_log:
        return ""
    body = previous_log
    with contextlib.suppress(FrontmatterError):
        _, body = read_frontmatter(previous_log, where=WikiFiles.LOG)
    lines = body.split("\n")
    for index, line in enumerate(lines):
        if _LOG_HEADING_RE.match(line):
            return "\n".join(lines[index:]).strip("\n")
    return ""


def _unlink_dead(markdown: str, existing: set[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        target = resolve_href(WikiFiles.LOG, match.group("href"))
        if target.external or target.path is None or target.path not in existing:
            return match.group("text")
        return match.group(0)

    return _INLINE_LINK_RE.sub(replace, markdown)


def parse_log_entries(body: str) -> list[ParsedLogEntry]:
    """Entries of a log body in file order (oldest first)."""
    entries: list[ParsedLogEntry] = []
    current: dict[str, str | None] | None = None
    for line in body.split("\n"):
        match = _LOG_HEADING_RE.match(line)
        if match:
            if current is not None:
                entries.append(ParsedLogEntry(**current))  # type: ignore[arg-type]
            current = {
                "day": match.group("day"),
                "action": match.group("action"),
                "title": match.group("title"),
                "link": None,
            }
            continue
        if current is not None and current["link"] is None:
            link = _INLINE_LINK_RE.search(line)
            if link:
                resolved = resolve_href(WikiFiles.LOG, link.group("href"))
                current["link"] = resolved.path
    if current is not None:
        entries.append(ParsedLogEntry(**current))  # type: ignore[arg-type]
    return entries


def _log_body(
    previous_log: str | None,
    entries: Sequence[LogEntry],
    existing: set[str],
    t: Strings | None = None,
) -> str:
    t = t or core_strings()
    old = _unlink_dead(_previous_entries(previous_log), existing)
    blocks = [block for block in [old, *(entry.render() for entry in entries)] if block]
    text = "\n\n".join(blocks) if blocks else t("index.log.empty")
    return f"# {t('index.log.title')}\n\n{text}\n"


# -- glossary ----------------------------------------------------------------------------


def _glossary(
    pack: DomainPack, by_id: Mapping[str, Page], t: Strings
) -> tuple[str, list[tuple[str, dict[str, list[str]]]]]:
    terms = sorted(pack.glossary.terms, key=lambda term: (term.term.casefold(), term.term))
    lines = [f"# {t('index.glossary.title')}", ""]
    if not terms:
        lines.append(t("index.glossary.empty"))
        return "\n".join(lines) + "\n", []
    lines += [t("index.glossary.intro"), ""]
    catalog_terms: list[tuple[str, dict[str, list[str]]]] = []
    for term in terms:
        lines += [f"## {inline_text(term.term)}", "", inline_text(term.definition), ""]
        synonyms = {lang: list(values) for lang, values in term.synonyms.items() if values}
        if synonyms:
            rendered = " · ".join(
                f"{lang}: {', '.join(inline_text(value) for value in values)}"
                for lang, values in synonyms.items()
            )
            lines.append(t("index.glossary.synonyms", synonyms=rendered))
        related = [by_id[ref] for ref in term.see_also if ref in by_id]
        if related:
            links = ", ".join(
                md_link(page.frontmatter.title, WikiFiles.GLOSSARY, page.path) for page in related
            )
            lines.append(t("index.glossary.see_also", links=links))
        if lines[-1]:
            lines.append("")
        catalog_terms.append((term.term, synonyms))
    return "\n".join(lines).rstrip("\n") + "\n", catalog_terms


# -- bundle ------------------------------------------------------------------------------


@dataclass
class IndexBundle:
    """Generated pages and machine data of the ``indexes`` stage."""

    pages: list[Page]
    llms_txt: str
    glossary: list[CatalogGlossaryEntry]
    log_entries: list[ParsedLogEntry] = field(default_factory=list)


def build_indexes(
    pages: Sequence[Page],
    pack: DomainPack,
    *,
    stamp: DocwikiStamp,
    updated: date,
    sensitivity: str,
    run_id: str,
    previous_log: str | None,
    new_entries: Sequence[LogEntry],
    topic_skips: Sequence[TopicSkip] = (),
    extra_paths: Iterable[str] = (),
    hubs: HubBundle | None = None,
    lang: str | None = None,
) -> IndexBundle:
    """Home page, source/entity/topic/query indexes, glossary, log and ``llms.txt``.

    ``pages`` are the content pages after the ``links`` stage; ``extra_paths`` lists other wiki
    pages of the release (``AGENTS.md``, ``_meta/…``) so that log links to them stay live.
    ``hubs`` (v1.7, ADR 0011, only when the pack declares scopes) adds the company dashboard to
    the home page; its pages are written by the caller. ``lang`` is the language of the generated
    text (default: the pack's canonical language; a mirror language for the translate stage).
    """
    t = pack.strings(lang)
    common = {"stamp": stamp, "updated": updated, "sensitivity": sensitivity, "lang": t.lang}
    sources = [p for p in pages if isinstance(p.frontmatter, SourceFrontmatter)]
    entities = [p for p in pages if isinstance(p.frontmatter, EntityFrontmatter)]
    topics = [p for p in pages if isinstance(p.frontmatter, TopicFrontmatter)]
    queries = [p for p in pages if isinstance(p.frontmatter, QueryFrontmatter)]
    by_id = {page.frontmatter.id: page for page in pages}
    generated: list[Page] = []

    # sources/index.md
    path = WikiFiles.SOURCES_INDEX
    categories = {category.key: category.title for category in pack.taxonomy.categories}
    order = {key: index for index, key in enumerate(categories)}
    grouped: dict[str, list[Page]] = {}
    for page in sources:
        fm = page.frontmatter
        assert isinstance(fm, SourceFrontmatter)
        grouped.setdefault(fm.category, []).append(page)
    body = [f"# {t('index.sources.title')}", ""]
    category_lines: list[tuple[str, str, int, int]] = []
    if not sources:
        body.append(t("index.sources.empty"))
    else:
        body += [t.count("index.sources.intro", len(sources)), ""]
    for key in sorted(grouped, key=lambda item: (order.get(item, 10**6), item)):
        title = categories.get(key, key)
        members = sorted(
            grouped[key],
            key=lambda p: (
                p.frontmatter.status != "current",  # type: ignore[union-attr]
                p.frontmatter.title.casefold(),
                p.path,
            ),
        )
        body += [f"## {inline_text(title)}", ""]
        superseded = 0
        for page in members:
            fm = page.frontmatter
            assert isinstance(fm, SourceFrontmatter)
            if fm.status == "superseded":
                superseded += 1
                newer = [by_id[s] for s in fm.superseded_by if s in by_id]
                status = t(
                    "index.sources.superseded_by",
                    links=", ".join(
                        md_link(item.frontmatter.title, path, item.path) for item in newer
                    ),
                )
            else:
                status = t.status(fm.status)
            body.append(f"- {md_link(fm.title, path, page.path)}: {status} · {fm.sensitivity}")
        body.append("")
        category_lines.append((key, title, len(members), superseded))
    sources_body = "\n".join(body).rstrip("\n") + "\n"
    generated.append(
        _index_page(
            "sources",
            path,
            t("index.sources.title"),
            t("index.sources.summary"),
            sources_body,
            **common,
        )
    )
    anchors = [heading.anchor for heading in extract_headings(sources_body) if heading.level == 2]

    # entities/index.md and entities/<type>/index.md
    type_titles = {item.key: item for item in pack.entities.types}
    type_order = {item.key: index for index, item in enumerate(pack.entities.types)}
    by_type: dict[str, list[Page]] = {}
    for page in entities:
        fm = page.frontmatter
        assert isinstance(fm, EntityFrontmatter)
        by_type.setdefault(fm.entity_type, []).append(page)
    body = [f"# {t('index.entities.title')}", ""]
    if not entities:
        body.append(t("index.entities.empty"))
    for entity_type in sorted(by_type, key=lambda key: (type_order.get(key, 10**6), key)):
        members = _by_title(by_type[entity_type])
        definition = type_titles.get(entity_type)
        title = definition.title if definition else plural(entity_type, 2)
        type_path = f"entities/{entity_type}/index.md"
        count = t.count("index.entities.pages", len(members))
        body.append(f"- {md_link(title, WikiFiles.ENTITIES_INDEX, type_path)}: {count}")
        type_body = [f"# {inline_text(title)}", ""]
        if definition and definition.description:
            type_body += [inline_text(definition.description), ""]
        type_body += [_item(page, type_path) for page in members]
        generated.append(
            _index_page(
                f"entities/{entity_type}",
                type_path,
                title,
                one_line(definition.description)
                if definition and definition.description
                else t("index.entities.type_summary", entity_type=entity_type),
                "\n".join(type_body) + "\n",
                **common,
            )
        )
    generated.append(
        _index_page(
            "entities",
            WikiFiles.ENTITIES_INDEX,
            t("index.entities.title"),
            t("index.entities.summary"),
            "\n".join(body) + "\n",
            **common,
        )
    )

    # topics/index.md (v1.7: per-scope topics under their scope)
    body = [f"# {t('index.topics.title')}", ""]
    company = [page for page in topics if getattr(page.frontmatter, "scope", None) is None]
    scoped: dict[str, list[Page]] = {}
    for page in topics:
        scope = getattr(page.frontmatter, "scope", None)
        if scope is not None:
            scoped.setdefault(scope, []).append(page)
    if company:
        body += [_item(page, WikiFiles.TOPICS_INDEX) for page in _by_title(company)]
    elif not topics:
        body.append(t("index.topics.empty"))
    labels = {scope: scope_label(pack, scope) for scope in scoped}
    for scope in sorted(scoped, key=lambda key: (labels[key].casefold(), key)):
        if body[-1]:
            body.append("")
        body += [f"## {inline_text(labels[scope])}", ""]
        body += [_item(page, WikiFiles.TOPICS_INDEX) for page in _by_title(scoped[scope])]
    pack_topics = {topic.slug: topic for topic in pack.topics.topics}
    skipped = [skip for skip in topic_skips if skip.topic_slug in pack_topics]
    if skipped:
        body += ["", f"## {t.heading('not_synthesised')}", ""]
        for skip in sorted(skipped, key=lambda item: item.topic_slug):
            reason = (
                t(f"index.skip.{skip.reason}")
                if skip.reason in _SKIP_REASONS
                else skip.reason.replace("_", " ")
            )
            body.append(f"- {inline_text(pack_topics[skip.topic_slug].title)}: {reason}")
    generated.append(
        _index_page(
            "topics",
            WikiFiles.TOPICS_INDEX,
            t("index.topics.title"),
            t("index.topics.summary"),
            "\n".join(body) + "\n",
            **common,
        )
    )

    # queries/index.md (only when research answers were filed)
    if queries:
        body = [f"# {t('index.queries.title')}", ""]
        body += [_item(page, WikiFiles.QUERIES_INDEX) for page in _by_title(queries)]
        generated.append(
            _index_page(
                "queries",
                WikiFiles.QUERIES_INDEX,
                t("index.queries.title"),
                t("index.queries.summary"),
                "\n".join(body) + "\n",
                **common,
            )
        )

    # glossary.md
    glossary_body, glossary_terms = _glossary(pack, by_id, t)
    generated.append(
        Page(
            path=WikiFiles.GLOSSARY,
            frontmatter=GlossaryFrontmatter(
                title=t("index.glossary.title"),
                summary=t("index.glossary.summary"),
                lang=t.lang,
                sensitivity=sensitivity,  # type: ignore[arg-type]
                updated=updated,
                docwiki=stamp,
            ),
            body=glossary_body,
        )
    )
    glossary_anchors = [h.anchor for h in extract_headings(glossary_body) if h.level == 2]
    glossary_entries = [
        CatalogGlossaryEntry(term=term, synonyms=synonyms, page=f"{WikiFiles.GLOSSARY}#{anchor}")
        for (term, synonyms), anchor in zip(glossary_terms, glossary_anchors, strict=True)
        if anchor
    ]

    # log.md
    existing = {page.path for page in pages} | {page.path for page in generated}
    existing |= {page.path for page in (hubs.pages if hubs else [])}
    existing |= {WikiFiles.INDEX, WikiFiles.LOG, WikiFiles.AGENTS, WikiFiles.QUALITY}
    existing |= {run_page_path(run_id), *extra_paths}
    log_body = _log_body(previous_log, new_entries, existing, t)
    generated.append(
        Page(
            path=WikiFiles.LOG,
            frontmatter=LogFrontmatter(
                title=t("index.log.title"),
                summary=t("index.log.summary"),
                lang=t.lang,
                sensitivity=sensitivity,  # type: ignore[arg-type]
                updated=updated,
                docwiki=stamp,
            ),
            body=log_body,
        )
    )
    log_entries = parse_log_entries(log_body)

    # index.md
    info = pack.info
    path = WikiFiles.INDEX
    body = [f"# {inline_text(info.wiki_title)}", ""]
    if info.banner:
        body += [f"> {inline_text(info.banner)}", ""]
    description = info.description.strip() or info.title
    body += [
        inline_text(description),
        "",
        t("index.home.cited"),
        "",
        f"## {t.heading('how_to_navigate')}",
        "",
        t("index.home.nav1", href=relative_link(path, WikiFiles.TOPICS_INDEX)),
        t("index.home.nav2", href=relative_link(path, WikiFiles.ENTITIES_INDEX)),
        t("index.home.nav3", href=relative_link(path, WikiFiles.SOURCES_INDEX)),
        t("index.home.nav4", href=relative_link(path, WikiFiles.GLOSSARY)),
        t(
            "index.home.nav5",
            log=relative_link(path, WikiFiles.LOG),
            quality=relative_link(path, WikiFiles.QUALITY),
        ),
        "",
        t("index.home.agents", href=relative_link(path, WikiFiles.AGENTS)),
        "",
    ]
    dashboard = dashboard_lines(hubs, pack, path, t.lang) if hubs else []
    if dashboard:
        # The company dashboard (v1.7, ADR 0011) comes first, before "How to navigate".
        position = body.index(f"## {t.heading('how_to_navigate')}")
        body[position:position] = dashboard
    if category_lines:
        body += [f"## {t.heading('categories')}", ""]
        for (_, title, count, superseded), anchor in zip(category_lines, anchors, strict=True):
            target = f"{WikiFiles.SOURCES_INDEX}#{anchor}"
            text = t.count("index.home.category", count)
            if superseded:
                text += t("index.home.category_superseded", count=superseded)
            body.append(f"- [{inline_text(title)}]({relative_link(path, target)}): {text}")
        body.append("")
    body += [f"## {t.heading('topics')}", ""]
    body += (
        [_item(page, path) for page in _by_title(topics)] if topics else [t("index.home.no_topics")]
    )
    current = sum(
        1
        for page in sources
        if isinstance(page.frontmatter, SourceFrontmatter) and page.frontmatter.status == "current"
    )
    body += [
        "",
        f"## {t.heading('stats')}",
        "",
        t(
            "index.home.stat_sources",
            total=len(sources),
            current=current,
            superseded=len(sources) - current,
        ),
        t("index.home.stat_entities", count=len(entities)),
        t("index.home.stat_topics", count=len(topics)),
        t("index.home.stat_glossary", count=len(glossary_entries)),
    ]
    if queries:
        body.append(
            t(
                "index.home.stat_queries",
                count=len(queries),
                href=relative_link(path, WikiFiles.QUERIES_INDEX),
            )
        )
    body += ["", f"## {t.heading('recent_changes')}", ""]
    recent = list(reversed(log_entries))[:RECENT_CHANGES]
    if not recent:
        body.append(t("index.log.empty"))
    for entry in recent:
        title = entry.title
        if entry.link and entry.link in existing:
            body.append(
                f"- {entry.day} {entry.action}: [{title}]({relative_link(path, entry.link)})"
            )
        else:
            body.append(f"- {entry.day} {entry.action}: {title}")
    body += [
        "",
        f"## {t.heading('quality')}",
        "",
        t("index.home.quality_report", href=relative_link(path, WikiFiles.QUALITY)),
        t("index.home.run_receipt", href=relative_link(path, run_page_path(run_id))),
    ]
    generated.append(
        _index_page(
            "home",
            path,
            info.wiki_title,
            t("index.home.summary"),
            "\n".join(body) + "\n",
            **common,
        )
    )

    # llms.txt
    llms = [f"# {one_line(info.wiki_title)}", ""]
    llms += [f"> {inline_text(description)}", ""]
    llms += [
        "## Start here",
        "",
        "- [Home](index.md): how to navigate this wiki",
        "- [Agent guide](AGENTS.md): page types, citation rules, skills and tools",
        "- [Glossary](glossary.md): acronyms and multilingual synonyms",
        "- [Log](log.md): recent changes",
    ]
    hubs_index = next(
        (page for page in (hubs.pages if hubs else []) if page.frontmatter.type == "index"), None
    )
    if hubs_index is not None:
        llms.append(_item(hubs_index, WikiFiles.LLMS))
    llms += [
        "",
        "## Topics",
        "",
    ]
    llms += [_item(page, WikiFiles.LLMS) for page in _by_title(topics)] or ["- No topics yet."]
    llms += ["", "## Entities", ""]
    llms += [_item(page, WikiFiles.LLMS) for page in _by_title(entities)] or ["- No entities yet."]
    llms += ["", "## Sources", ""]
    ordered_sources = sorted(
        sources,
        key=lambda p: (
            p.frontmatter.status != "current",  # type: ignore[union-attr]
            p.frontmatter.title.casefold(),
            p.path,
        ),
    )
    for page in ordered_sources:
        fm = page.frontmatter
        assert isinstance(fm, SourceFrontmatter)
        detail = _summary(page)
        if fm.status != "current":
            detail = f"({fm.status}) {detail}".strip()
        llms.append(_item(page, WikiFiles.LLMS, detail))
    if not ordered_sources:
        llms.append("- No sources yet.")
    return IndexBundle(
        pages=generated,
        llms_txt="\n".join(llms).rstrip("\n") + "\n",
        glossary=glossary_entries,
        log_entries=log_entries,
    )


def build_catalog(
    pages: Sequence[Page],
    edges: Sequence[CatalogEdge],
    *,
    release_id: str,
    audience: str,
    generated_at: datetime,
    glossary: Sequence[CatalogGlossaryEntry],
    wiki_languages: Sequence[str] = ("en",),
) -> Catalog:
    """``catalog.json`` from the final pages (single source of truth: their frontmatter); mirror
    pages are listed with their language, the sources once (from the canonical pages)."""
    sources = [p for p in pages if isinstance(p.frontmatter, SourceFrontmatter) and not p.is_mirror]
    return Catalog(
        release_id=release_id,
        audience=audience,  # type: ignore[arg-type]
        generated_at=generated_at,
        pages=sorted(
            (catalog_page_for(page.frontmatter, page.path) for page in pages),
            key=lambda entry: entry.path,
        ),
        edges=list(edges),
        wiki_languages=list(wiki_languages),
        sources=sorted(
            (catalog_source_for(page.frontmatter) for page in sources),  # type: ignore[arg-type]
            key=lambda entry: entry.source_id,
        ),
        glossary=list(glossary),
    )
