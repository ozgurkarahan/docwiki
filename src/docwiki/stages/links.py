"""Stage 7 — ``links``: deterministic cross-links, backlinks and catalog edges (pipeline §1).

For the content pages of a release (source, entity, topic and query pages) this stage:

1. reconciles frontmatter references with the pages that exist (a source lists the entity pages
   that mention it and the topic pages that synthesise it; dangling ids are dropped);
2. makes sure every superseded source links its replacement before its first section (G11): the
   `` `src-…` `` code spans of the render stage's banner become links, and a banner is added
   when none links the replacement;
3. autolinks registry entity names and aliases — first mention per section, never inside
   headings, code, links, footnotes, blockquotes or the generated sections;
4. writes a ``## Related`` section (entities, topics, revisions) before ``## Sources``;
5. writes the backlinks block (``<!-- docwiki:backlinks:start -->`` … ``end``) listing the
   content pages that link to the page, sorted by title;
6. derives the catalog edges of CONTRACT.md §6.

An entity bound to one scope (v1.7, ADR 0011: its registry attribute named after the pack's scope
dimension, ``chantier: moreau``) belongs to that scope only: a source page of another scope does
not list it, and a page of another scope (or a company-wide page without scope) neither autolinks
nor lists it; its own page and the pages of its scope do. This is decided here, on the rendered
pages, so the compiled artifacts stay valid and the cached topic pages are reused.

Running the stage twice gives the same pages: generated sections are stripped before they are
rebuilt and an entity already linked in a section is not linked again.

The Markdown helpers at the top (:func:`inline_text`, :func:`md_link`…) are shared with the
``indexes`` and ``agentkit`` stages: untrusted strings (titles and summaries produced from
documents) are escaped and sanitised before they are placed in generated Markdown.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from docwiki.contracts.catalog import CatalogEdge
from docwiki.contracts.fences import FenceTracker
from docwiki.contracts.i18n import Strings, core_strings, heading_variants
from docwiki.contracts.markdown import (
    BACKLINKS_END,
    BACKLINKS_START,
    extract_footnotes,
    extract_links,
    relative_link,
    resolve_href,
    split_sections,
    strip_backlinks_block,
)
from docwiki.contracts.pages import (
    EntityFrontmatter,
    Page,
    QueryFrontmatter,
    SourceFrontmatter,
    TopicFrontmatter,
    ViewFrontmatter,
)
from docwiki.contracts.safety import sanitize_markdown
from docwiki.domain.models import DomainPack, RegistryEntry
from docwiki.domain.rules import document_scope, entity_in_scope, entity_scope

__all__ = [
    "BACKLINKS_HEADING",
    "BACKLINKS_HEADINGS",
    "CONTENT_TYPES",
    "RELATED_HEADING",
    "RELATED_HEADINGS",
    "SOURCES_HEADING",
    "SOURCES_HEADINGS",
    "STAGE_VERSION",
    "LinkResult",
    "apply_links",
    "autolink_page",
    "build_edges",
    "ensure_superseded_banner",
    "inline_text",
    "link_source_references",
    "md_escape",
    "md_link",
    "one_line",
    "plural",
    "reconcile_references",
    "replace_frontmatter",
    "scope_source_entities",
    "singular",
    "strip_generated_sections",
    "type_label",
]

STAGE_VERSION = "4"
RELATED_HEADING = "Related"
BACKLINKS_HEADING = "Referenced by"
SOURCES_HEADING = "Sources"
RELATED_HEADINGS = heading_variants("related")
"""``## Related`` in every core wiki language (v1.7: the canonical wiki may be French)."""
BACKLINKS_HEADINGS = heading_variants("referenced_by")
SOURCES_HEADINGS = heading_variants("sources")
CONTENT_TYPES = ("source", "entity", "topic", "query")
MIN_ALIAS_LENGTH = 3

# -- Markdown helpers shared by the assemble stages -----------------------------------------

_MD_SPECIAL_RE = re.compile(r"([\\`*_\[\]<>|~#!])")


def one_line(text: str) -> str:
    """Collapse all whitespace (newlines included) to single spaces."""
    return " ".join(str(text).split())


def md_escape(text: str) -> str:
    """Escape Markdown structure characters so ``text`` renders literally on one line."""
    return _MD_SPECIAL_RE.sub(r"\\\1", one_line(text))


def inline_text(text: str) -> str:
    """Safe inline Markdown for an untrusted string: escaped, defanged, single line."""
    clean, _ = sanitize_markdown(md_escape(text), allow_markers=False)
    return one_line(clean)


def md_link(text: str, from_path: str, to_path: str) -> str:
    """``[text](relative path)`` with the text escaped."""
    return f"[{inline_text(text)}]({relative_link(from_path, to_path)})"


def plural(word: str, count: int) -> str:
    """Naive English plural of a singular noun (``page`` → ``pages``, ``Topic`` → ``Topics``)."""
    if count == 1 or not word:
        return word
    lower = word.lower()
    if lower.endswith("sis"):
        return word[:-2] + "es"
    if lower.endswith(("s", "x", "z", "ch", "sh")):
        return word + "es"
    if lower.endswith("y") and len(lower) > 1 and lower[-2] not in "aeiou":
        return word[:-1] + "ies"
    return word + "s"


def singular(word: str) -> str:
    """Naive English singular of a plural title (``Spare parts`` → ``Spare part``)."""
    lower = word.lower()
    if lower.endswith("ies") and len(lower) > 3:
        return word[:-3] + "y"
    if lower.endswith(("sses", "xes", "zes", "ches", "shes")):
        return word[:-2]
    if lower.endswith("s") and not lower.endswith("ss"):
        return word[:-1]
    return word


def type_label(title: str, count: int) -> str:
    """Entity-type group label: pack titles are plural (``Spare parts``), a single member is not."""
    return singular(title) if count == 1 else title


def replace_frontmatter(page: Page, **updates: Any) -> Page:
    """``page`` with validated frontmatter ``updates`` (model validators run again)."""
    fm = page.frontmatter
    data = fm.model_dump(by_alias=True)
    data.update(updates)
    return Page(path=page.path, frontmatter=type(fm).model_validate(data), body=page.body)


# -- body structure -----------------------------------------------------------------------

_ATX_RE = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t#]*$")
_FOOTNOTE_DEF_RE = re.compile(r"^\[\^[^\]\s]+\]:")
_TABLE_RULE_RE = re.compile(r"^\s*\|?\s*:?-{3,}")


def _heading(line: str) -> tuple[int, str] | None:
    match = _ATX_RE.match(line)
    if not match:
        return None
    return len(match.group(1)), (match.group(2) or "").strip()


def _code_mask(lines: Sequence[str]) -> list[bool]:
    fences = FenceTracker()
    return [fences.feed(line) for line in lines]


def strip_generated_sections(body: str) -> str:
    """Remove the backlinks block and the ``## Related`` section (rebuilt by this stage)."""
    text = strip_backlinks_block(body)
    lines = text.split("\n")
    mask = _code_mask(lines)
    out: list[str] = []
    skipping = False
    for line, in_code in zip(lines, mask, strict=True):
        heading = None if in_code else _heading(line)
        if heading is not None:
            level, title = heading
            if level == 2 and title in RELATED_HEADINGS:
                skipping = True
                continue
            if skipping and level <= 2:
                skipping = False
        if not skipping:
            out.append(line)
    return _tidy("\n".join(out))


def _tidy(body: str) -> str:
    """Collapse runs of blank lines (outside code) and trim the ends."""
    lines = body.split("\n")
    mask = _code_mask(lines)
    out: list[str] = []
    for line, in_code in zip(lines, mask, strict=True):
        if not in_code and not line.strip() and out and not out[-1].strip():
            continue
        out.append(line)
    return "\n".join(out).strip("\n") + "\n"


def _insert_before_sources(body: str, block: str) -> str:
    lines = body.rstrip("\n").split("\n")
    mask = _code_mask(lines)
    index = None
    for position, (line, in_code) in enumerate(zip(lines, mask, strict=True)):
        heading = None if in_code else _heading(line)
        if heading is not None and heading[0] == 2 and heading[1] in SOURCES_HEADINGS:
            index = position
    chunk = block.strip("\n").split("\n")
    if index is None:
        return _tidy("\n".join([*lines, "", *chunk, ""]))
    return _tidy("\n".join([*lines[:index], "", *chunk, "", *lines[index:]]))


def _intro_paths(page: Page) -> set[str]:
    intro: list[str] = []
    for section in split_sections(page.body):
        if section.level >= 2:
            break
        intro.append(section.markdown)
    paths: set[str] = set()
    for link in extract_links("\n".join(intro)):
        resolved = resolve_href(page.path, link.href).path
        if resolved:
            paths.add(resolved)
    return paths


# -- reconciliation and banners ---------------------------------------------------------------


def reconcile_references(pages: Sequence[Page]) -> list[Page]:
    """Align source frontmatter with the entity/topic/source pages that exist.

    ``entities`` = entity pages listing the source plus the source's own mentions that have a
    page; ``topics`` = topic pages listing the source; ``supersedes``/``superseded_by`` keep only
    sources with a page (the status follows). Entity, topic and query ``sources`` lists keep only
    sources with a page.
    """
    source_ids = {
        page.frontmatter.source_id
        for page in pages
        if isinstance(page.frontmatter, SourceFrontmatter)
    }
    entity_ids = {
        page.frontmatter.id for page in pages if isinstance(page.frontmatter, EntityFrontmatter)
    }
    mentioned: dict[str, set[str]] = {}
    synthesised: dict[str, set[str]] = {}
    for page in pages:
        fm = page.frontmatter
        if isinstance(fm, EntityFrontmatter):
            for source_id in fm.sources:
                mentioned.setdefault(source_id, set()).add(fm.id)
        elif isinstance(fm, TopicFrontmatter):
            for source_id in fm.sources:
                synthesised.setdefault(source_id, set()).add(fm.id)
    result: list[Page] = []
    for page in pages:
        fm = page.frontmatter
        if isinstance(fm, SourceFrontmatter):
            entities = sorted((set(fm.entities) & entity_ids) | mentioned.get(fm.source_id, set()))
            topics = sorted(synthesised.get(fm.source_id, set()))
            supersedes = sorted(set(fm.supersedes) & source_ids)
            superseded_by = sorted(set(fm.superseded_by) & source_ids)
            status = fm.status
            if status == "superseded" and not superseded_by:
                status = "current"
            elif status == "current" and superseded_by:
                status = "superseded"
            updates = {
                "entities": entities,
                "topics": topics,
                "supersedes": supersedes,
                "superseded_by": superseded_by,
                "status": status,
            }
            if any(getattr(fm, key) != value for key, value in updates.items()):
                page = replace_frontmatter(page, **updates)
        elif isinstance(fm, EntityFrontmatter | TopicFrontmatter | QueryFrontmatter):
            sources = sorted(set(fm.sources) & source_ids)
            if sources != list(fm.sources):
                page = replace_frontmatter(page, sources=sources)
        result.append(page)
    return result


def link_source_references(pages: Sequence[Page]) -> list[Page]:
    """Turn the `` `src-…` `` code spans written by ``render`` (superseded banner) into links.

    Delegates to :func:`docwiki.stages.render.link_source_refs` when the compile lane is
    installed; :func:`ensure_superseded_banner` remains the fallback that guarantees G11.
    """
    try:
        from docwiki.stages.render import link_source_refs
    except ImportError:
        return list(pages)
    sources = {
        page.frontmatter.id: page
        for page in pages
        if isinstance(page.frontmatter, SourceFrontmatter)
    }
    return [link_source_refs(page, sources) for page in pages]


def ensure_superseded_banner(
    page: Page, pages_by_id: Mapping[str, Page], strings: Strings | None = None
) -> Page:
    """Superseded sources must link their replacement before the first ``##`` section."""
    fm = page.frontmatter
    if not isinstance(fm, SourceFrontmatter) or fm.status != "superseded":
        return page
    intro = _intro_paths(page)
    newer = [
        pages_by_id[source_id]
        for source_id in fm.superseded_by
        if source_id in pages_by_id and pages_by_id[source_id].path not in intro
    ]
    if not newer:
        return page
    links = ", ".join(
        md_link(item.frontmatter.title, page.path, item.path)
        for item in sorted(newer, key=lambda item: (item.frontmatter.title, item.path))
    )
    banner = (strings or core_strings())("render.superseded_banner", links=links)
    lines = page.body.split("\n")
    position = 0
    for index, line in enumerate(lines):
        heading = _heading(line)
        if heading is not None and heading[0] == 1:
            position = index + 1
            break
    while position < len(lines) and (
        not lines[position].strip() or lines[position].lstrip().startswith(">")
    ):
        position += 1
    insert = ["", banner, ""]
    new_body = "\n".join([*lines[:position], *insert, *lines[position:]])
    return Page(path=page.path, frontmatter=fm, body=_tidy(new_body))


# -- scopes (v1.7, ADR 0011) ----------------------------------------------------------------


class _Scopes:
    """Which registry entities a page of a given scope may mention (see the module docstring)."""

    def __init__(self, pack: DomainPack) -> None:
        self.pack = pack
        self.registry: dict[str, RegistryEntry] = {
            entry.id: entry for entry in pack.entities.registry
        }

    def page_scope(self, page: Page) -> str | None:
        """Scope of a content page: a source's document scope, a topic's scope, the scope an
        entity is bound to; ``None`` (company-wide) otherwise or without ``scopes.yaml``."""
        fm = page.frontmatter
        if isinstance(fm, SourceFrontmatter):
            return document_scope(self.pack, fm.scope, fm.source_path)
        if isinstance(fm, TopicFrontmatter):
            return fm.scope
        if isinstance(fm, EntityFrontmatter):
            entry = self.registry.get(fm.id)
            return entity_scope(self.pack, entry) if entry is not None else None
        return None

    def allows(self, entity_id: str, scope: str | None) -> bool:
        entry = self.registry.get(entity_id)
        return entry is None or entity_in_scope(self.pack, entry, scope)


def scope_source_entities(pages: Sequence[Page], pack: DomainPack) -> list[Page]:
    """Source pages without the entities bound to another scope than their document's."""
    scopes = _Scopes(pack)
    result: list[Page] = []
    for page in pages:
        fm = page.frontmatter
        if isinstance(fm, SourceFrontmatter) and fm.entities:
            scope = scopes.page_scope(page)
            kept = [entity_id for entity_id in fm.entities if scopes.allows(entity_id, scope)]
            if kept != list(fm.entities):
                page = replace_frontmatter(page, entities=kept)
        result.append(page)
    return result


# -- autolinking --------------------------------------------------------------------------

_PROTECTED_RE = re.compile(
    r"(?P<code>(`+)(?:(?!\2).)+?\2)"
    r"|(?P<link>!?\[(?:[^\[\]\\]|\\.|\[(?:[^\[\]\\]|\\.)*\])*\](?:\([^)\n]*\)|\[[^\]\n]*\]))"
    r"|(?P<footnote>\[\^[^\]\s]+\])"
    r"|(?P<angle><[^>\n]*>)"
    r"|(?P<escaped>\\.)"
)
_SKIPPED_SECTIONS = RELATED_HEADINGS | BACKLINKS_HEADINGS | SOURCES_HEADINGS


@dataclass(frozen=True)
class _Target:
    entity_id: str
    path: str


class _Autolinker:
    def __init__(self, targets: Mapping[str, tuple[str, Sequence[str]]]) -> None:
        """``targets``: entity id → (page path, names)."""
        owners: dict[str, set[str]] = {}
        for entity_id, (_, names) in targets.items():
            for name in names:
                clean = one_line(name)
                if len(clean) >= MIN_ALIAS_LENGTH:
                    owners.setdefault(clean.casefold(), set()).add(entity_id)
        self.alias_owner = {
            alias: next(iter(ids)) for alias, ids in owners.items() if len(ids) == 1
        }
        self.paths = {entity_id: path for entity_id, (path, _) in targets.items()}
        self.by_path = {path: entity_id for entity_id, path in self.paths.items()}
        aliases = sorted(self.alias_owner, key=lambda alias: (-len(alias), alias))
        self.pattern = (
            re.compile(
                r"(?<![\w-])(?:"
                + "|".join(re.escape(alias).replace(r"\ ", r"\s+") for alias in aliases)
                + r")(?![\w-])",
                re.IGNORECASE,
            )
            if aliases
            else None
        )

    def owner(self, matched: str) -> str | None:
        return self.alias_owner.get(one_line(matched).casefold())

    def linked_in(self, page_path: str, lines: Iterable[str]) -> set[str]:
        found: set[str] = set()
        for link in extract_links("\n".join(lines)):
            target = resolve_href(page_path, link.href).path
            if target in self.by_path:
                found.add(self.by_path[target])
        return found

    def link_line(self, line: str, page_path: str, done: set[str], exclude: str | None) -> str:
        if self.pattern is None:
            return line
        out: list[str] = []
        position = 0
        for protected in [*_PROTECTED_RE.finditer(line), None]:
            end = protected.start() if protected is not None else len(line)
            out.append(self._link_segment(line[position:end], page_path, done, exclude))
            if protected is not None:
                out.append(protected.group(0))
                position = protected.end()
        return "".join(out)

    def _link_segment(
        self, segment: str, page_path: str, done: set[str], exclude: str | None
    ) -> str:
        if not segment or self.pattern is None:
            return segment
        out: list[str] = []
        position = 0
        for match in self.pattern.finditer(segment):
            entity_id = self.owner(match.group(0))
            if entity_id is None or entity_id in done or entity_id == exclude:
                continue
            target = relative_link(page_path, self.paths[entity_id])
            out.append(segment[position : match.start()])
            out.append(f"[{match.group(0)}]({target})")
            position = match.end()
            done.add(entity_id)
        out.append(segment[position:])
        return "".join(out)


def autolink_page(page: Page, linker: _Autolinker) -> Page:
    """Link the first mention of each registry entity in every section of ``page``."""
    exclude = page.frontmatter.id if isinstance(page.frontmatter, EntityFrontmatter) else None
    lines = page.body.split("\n")
    mask = _code_mask(lines)
    sections: list[tuple[str | None, list[int]]] = [(None, [])]
    in_backlinks = False
    for index, (line, in_code) in enumerate(zip(lines, mask, strict=True)):
        if line.strip() == BACKLINKS_START:
            in_backlinks = True
        if in_code or in_backlinks:
            if line.strip() == BACKLINKS_END:
                in_backlinks = False
            continue
        heading = _heading(line)
        if heading is not None:
            sections.append((heading[1], []))
            continue
        sections[-1][1].append(index)
    for title, indices in sections:
        if title in _SKIPPED_SECTIONS:
            continue
        done = linker.linked_in(page.path, (lines[index] for index in indices))
        for index in indices:
            line = lines[index]
            stripped = line.lstrip()
            if (
                not stripped
                or stripped.startswith(">")
                or stripped.startswith("<!--")
                or _FOOTNOTE_DEF_RE.match(stripped)
                or _TABLE_RULE_RE.match(line)
            ):
                continue
            lines[index] = linker.link_line(line, page.path, done, exclude)
    body = "\n".join(lines)
    if body == page.body:
        return page
    return Page(path=page.path, frontmatter=page.frontmatter, body=body)


# -- related, backlinks and edges ---------------------------------------------------------------


def _type_order(pack: DomainPack) -> dict[str, tuple[int, str]]:
    return {item.key: (index, item.title) for index, item in enumerate(pack.entities.types)}


def _entity_lines(page: Page, entity_pages: Sequence[Page], pack: DomainPack) -> list[str]:
    order = _type_order(pack)
    groups: dict[str, list[Page]] = {}
    for entity in entity_pages:
        fm = entity.frontmatter
        assert isinstance(fm, EntityFrontmatter)
        groups.setdefault(fm.entity_type, []).append(entity)
    lines: list[str] = []
    for entity_type in sorted(groups, key=lambda key: (order.get(key, (10**6, key))[0], key)):
        members = sorted(
            groups[entity_type], key=lambda p: (p.frontmatter.title.casefold(), p.path)
        )
        definition = order.get(entity_type)
        label = (
            type_label(definition[1], len(members))
            if definition
            else plural(entity_type, len(members))
        )
        links = ", ".join(md_link(item.frontmatter.title, page.path, item.path) for item in members)
        lines.append(f"- {inline_text(label)}: {links}")
    return lines


def _page_links(page: Page, label: str, targets: Sequence[Page], strings: Strings) -> list[str]:
    """``- <label>: <links>``; ``label`` is a string key with ``.one`` / ``.other`` forms."""
    if not targets:
        return []
    ordered = sorted(targets, key=lambda p: (p.frontmatter.title.casefold(), p.path))
    links = ", ".join(md_link(item.frontmatter.title, page.path, item.path) for item in ordered)
    name = strings(f"{label}.{'one' if len(ordered) == 1 else 'other'}")
    return [f"- {name}: {links}"]


def _related_lines(
    page: Page,
    by_id: Mapping[str, Page],
    pack: DomainPack,
    views: Sequence[Page] = (),
    scopes: _Scopes | None = None,
) -> list[str]:
    fm = page.frontmatter
    scopes = scopes or _Scopes(pack)
    t = pack.strings()
    lines: list[str] = []
    if isinstance(fm, SourceFrontmatter):
        entities = [by_id[entity_id] for entity_id in fm.entities if entity_id in by_id]
        lines += _entity_lines(page, entities, pack)
        topics = [by_id[topic] for topic in fm.topics if topic in by_id]
        lines += _page_links(page, "links.topic", topics, t)
        reading = [view for view in views if fm.id in getattr(view.frontmatter, "sources", [])]
        lines += _page_links(page, "links.view", reading, t)
        for label, ids in (
            (t("links.supersedes"), fm.supersedes),
            (t("links.superseded_by"), fm.superseded_by),
        ):
            targets = sorted(
                (by_id[source_id] for source_id in ids if source_id in by_id),
                key=lambda p: (p.frontmatter.title.casefold(), p.path),
            )
            if targets:
                links = ", ".join(md_link(t.frontmatter.title, page.path, t.path) for t in targets)
                lines.append(f"- {label}: {links}")
    elif isinstance(fm, EntityFrontmatter):
        sources = set(fm.sources)
        topics = [
            other
            for other in by_id.values()
            if isinstance(other.frontmatter, TopicFrontmatter)
            and sources & set(other.frontmatter.sources)
            and (other.frontmatter.scope is None or scopes.allows(fm.id, other.frontmatter.scope))
        ]
        lines += _page_links(page, "links.topic", topics, t)
    elif isinstance(fm, TopicFrontmatter):
        entity_ids: set[str] = set()
        for source_id in fm.sources:
            source = by_id.get(source_id)
            if source is not None and isinstance(source.frontmatter, SourceFrontmatter):
                entity_ids.update(source.frontmatter.entities)
        if fm.scope is not None:
            # a topic of one scope never lists an entity bound to another scope
            entity_ids = {item for item in entity_ids if scopes.allows(item, fm.scope)}
        entities = [by_id[entity_id] for entity_id in sorted(entity_ids) if entity_id in by_id]
        lines += _entity_lines(page, entities, pack)
    return lines


def _content_links(page: Page) -> set[str]:
    targets: set[str] = set()
    for link in extract_links(strip_backlinks_block(page.body)):
        resolved = resolve_href(page.path, link.href).path
        if resolved and resolved != page.path:
            targets.add(resolved)
    return targets


def _backlinks_block(page: Page, sources: Sequence[Page], strings: Strings) -> str:
    lines = [BACKLINKS_START, f"## {strings.heading('referenced_by')}", ""]
    if sources:
        ordered = sorted(sources, key=lambda p: (p.frontmatter.title.casefold(), p.path))
        lines += [f"- {md_link(item.frontmatter.title, page.path, item.path)}" for item in ordered]
    else:
        lines.append(strings("links.no_backlinks"))
    lines += ["", BACKLINKS_END]
    return "\n".join(lines)


def build_edges(pages: Sequence[Page]) -> list[CatalogEdge]:
    """Catalog edges (CONTRACT.md §6), unique and sorted by ``(from, to, kind)``."""
    ids = {page.frontmatter.id for page in pages}
    source_ids = {
        page.frontmatter.source_id
        for page in pages
        if isinstance(page.frontmatter, SourceFrontmatter)
    }
    by_path = {page.path: page.frontmatter.id for page in pages}
    edges: set[tuple[str, str, str]] = set()
    for page in pages:
        fm = page.frontmatter
        if isinstance(fm, SourceFrontmatter):
            edges |= {(fm.id, entity, "mentions") for entity in fm.entities if entity in ids}
            edges |= {(fm.id, older, "supersedes") for older in fm.supersedes if older in ids}
        if isinstance(fm, TopicFrontmatter):
            edges |= {(fm.id, source, "topic-of") for source in fm.sources if source in ids}
        _, definitions = extract_footnotes(page.body)
        for definition in definitions:
            for link in extract_links(definition.content):
                target = resolve_href(page.path, link.href).path or ""
                parts = target.split("/")
                if (
                    len(parts) == 3
                    and parts[0] == "evidence"
                    and parts[1] in source_ids
                    and parts[1] != fm.id
                ):
                    edges.add((fm.id, parts[1], "cites"))
    for page in pages:
        for section in split_sections(page.body):
            if section.heading not in RELATED_HEADINGS:
                continue
            for link in extract_links(section.markdown):
                target = by_path.get(resolve_href(page.path, link.href).path or "")
                if not target or target == page.frontmatter.id:
                    continue
                if any(edge[0] == page.frontmatter.id and edge[1] == target for edge in edges):
                    continue
                edges.add((page.frontmatter.id, target, "related"))
    return [
        CatalogEdge.model_validate({"from": a, "to": b, "kind": kind})
        for a, b, kind in sorted(edges)
    ]


@dataclass
class LinkResult:
    pages: list[Page]
    edges: list[CatalogEdge]


def apply_links(pages: Sequence[Page], pack: DomainPack, *, autolink: bool = True) -> LinkResult:
    """Run the whole stage on the content pages of a release (other pages pass through)."""
    content_positions = [
        index for index, page in enumerate(pages) if page.frontmatter.type in CONTENT_TYPES
    ]
    # reconciled first: the entity pages' own source lists cannot bring a foreign entity back
    content = scope_source_entities(
        reconcile_references([pages[index] for index in content_positions]), pack
    )
    content = [
        Page(path=page.path, frontmatter=page.frontmatter, body=strip_generated_sections(page.body))
        for page in content
    ]
    content = link_source_references(content)
    by_id = {page.frontmatter.id: page for page in content}
    strings = pack.strings()
    content = [ensure_superseded_banner(page, by_id, strings) for page in content]
    scopes = _Scopes(pack)
    if autolink:
        registry = scopes.registry
        targets: dict[str, tuple[str, list[str]]] = {}
        for page in content:
            fm = page.frontmatter
            if not isinstance(fm, EntityFrontmatter):
                continue
            entry = registry.get(fm.id)
            names = [fm.title, *(alias.text for alias in fm.aliases)]
            if entry is not None:
                names += [entry.label, *(alias.text for alias in entry.aliases)]
            targets[fm.id] = (page.path, list(dict.fromkeys(names)))
        # one linker per page scope, over the entities that scope may mention (an alias shared
        # by entities of two scopes then links the right one); a single one without scopes
        linkers: dict[str | None, _Autolinker] = {}

        def linker_for(page: Page) -> _Autolinker:
            scope = scopes.page_scope(page)
            if scope not in linkers:
                linkers[scope] = _Autolinker(
                    {
                        entity_id: target
                        for entity_id, target in targets.items()
                        if scopes.allows(entity_id, scope)
                    }
                )
            return linkers[scope]

        content = [
            autolink_page(page, linker_for(page)) if page.frontmatter.type != "query" else page
            for page in content
        ]
    by_id = {page.frontmatter.id: page for page in content}
    # computed views pass through unchanged; the source pages they read link to them
    views = [page for page in pages if isinstance(page.frontmatter, ViewFrontmatter)]
    with_related: list[Page] = []
    for page in content:
        lines = _related_lines(page, by_id, pack, views, scopes)
        if lines and page.frontmatter.type != "query":
            block = "\n".join([f"## {strings.heading('related')}", "", *lines])
            page = Page(
                path=page.path,
                frontmatter=page.frontmatter,
                body=_insert_before_sources(page.body, block),
            )
        with_related.append(page)
    inbound: dict[str, list[Page]] = {}
    paths = {page.path for page in with_related}
    for page in with_related:
        for target in _content_links(page):
            if target in paths:
                inbound.setdefault(target, []).append(page)
    final = [
        Page(
            path=page.path,
            frontmatter=page.frontmatter,
            body=_insert_before_sources(
                page.body, _backlinks_block(page, inbound.get(page.path, []), strings)
            ),
        )
        for page in with_related
    ]
    result = list(pages)
    for position, page in zip(content_positions, final, strict=True):
        result[position] = page
    return LinkResult(pages=result, edges=build_edges(result))
