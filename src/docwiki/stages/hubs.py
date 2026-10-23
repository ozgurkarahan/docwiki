"""Hub pages and the company dashboard (v1.7, ADR 0011), built by code from the release's pages.

Only when the domain pack declares ``scopes.yaml``. Each scope value with at least one source in
the release (the default scope, e.g. ``entreprise``, included) gets a hub page at
``<plural>/<scope>.md`` (``hub:<plural>/<scope>``): the scope's registry entry (its attributes as
a table), its documents grouped by phase with their status, the topics and entities of its
sources, the open contradictions of its own topics and the last document received.
``<plural>/index.md`` (``index:hubs/<plural>``) lists the hubs and the home page shows one
dashboard row per scope (:func:`dashboard_lines`).

No model is involved: scope and phase come from the raw path and the pack; titles and summaries
that originate in documents are escaped with :func:`~docwiki.stages.links.inline_text`.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date

from docwiki.contracts.enums import max_sensitivity
from docwiki.contracts.ids import format_hub_id, hub_page_path, index_page_path
from docwiki.contracts.markdown import relative_link
from docwiki.contracts.pages import (
    DocwikiStamp,
    EntityFrontmatter,
    HubFrontmatter,
    IndexFrontmatter,
    Page,
    SourceFrontmatter,
    TopicFrontmatter,
)
from docwiki.domain.models import DomainPack, RegistryEntry
from docwiki.domain.rules import scope_axes
from docwiki.engine_types import CompiledResult
from docwiki.stages.links import inline_text, md_link, one_line, plural

__all__ = [
    "STAGE_VERSION",
    "HubBundle",
    "ScopeSummary",
    "build_hubs",
    "dashboard_lines",
    "doc_dates",
    "scope_label",
    "source_scope",
]

STAGE_VERSION = "1"
NO_PHASE = "No phase"
_PATH_DATE_RE = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)")


def source_scope(pack: DomainPack, fm: SourceFrontmatter) -> str | None:
    """The scope value of a source page: its frontmatter, else its raw path (never a model)."""
    if pack.scopes is None:
        return None
    return fm.scope or scope_axes(pack, fm.source_path).scope


def _source_phase(pack: DomainPack, fm: SourceFrontmatter) -> str | None:
    """The phase of a source page: its frontmatter, else its raw path (when it has no scope)."""
    if fm.phase is not None or fm.scope is not None:
        return fm.phase
    return scope_axes(pack, fm.source_path).phase


def _registry_entry(pack: DomainPack, scope: str) -> RegistryEntry | None:
    if pack.scopes is None:
        return None
    name = pack.scopes.name
    return next(
        (entry for entry in pack.entities.registry if entry.type == name and entry.key == scope),
        None,
    )


def scope_label(pack: DomainPack, scope: str) -> str:
    """Human name of a scope value: its registry label, the default's title, else the value."""
    entry = _registry_entry(pack, scope)
    if entry is not None:
        return entry.label
    if pack.scopes is not None and scope == pack.scopes.default.key:
        return pack.scopes.default.title
    return scope


def doc_dates(results: Iterable[CompiledResult]) -> dict[str, date]:
    """Source id → the document's own date, when the compile stage found one."""
    found: dict[str, date] = {}
    for result in results:
        value = result.usage.get("doc_date")
        if isinstance(value, str):
            try:
                found[result.source_id] = date.fromisoformat(value)
            except ValueError:
                continue
    return found


def _source_date(fm: SourceFrontmatter, dates: Mapping[str, date]) -> tuple[bool, date]:
    """``(known, date)``: the document's own date, else a ``YYYY-MM-DD`` in its file name
    (known); else the release date of its page (``updated``, when the wiki received it)."""
    if fm.source_id in dates:
        return True, dates[fm.source_id]
    match = _PATH_DATE_RE.search(fm.source_path.rsplit("/", 1)[-1])
    if match:
        try:
            return True, date.fromisoformat(match.group(1))
        except ValueError:
            pass
    return False, fm.updated


def _attribute_name(key: str) -> str:
    text = key.replace("_", " ").replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else key


@dataclass
class ScopeSummary:
    """What the hub and the dashboard row of one scope value show."""

    scope: str
    label: str
    path: str
    sources: list[Page]
    entry: RegistryEntry | None
    phase: str | None
    """The highest phase (pack order) among the scope's sources."""
    last: Page
    last_date: date
    topics: list[Page] = field(default_factory=list)
    entities: list[Page] = field(default_factory=list)
    contradictions: list[Page] = field(default_factory=list)


@dataclass
class HubBundle:
    """The hub pages, the hubs index and the per-scope summaries (empty without scopes)."""

    pages: list[Page]
    summaries: list[ScopeSummary]


def _by_title(pages: Iterable[Page]) -> list[Page]:
    return sorted(pages, key=lambda page: (page.frontmatter.title.casefold(), page.path))


def _summaries(
    pages: Sequence[Page], pack: DomainPack, dates: Mapping[str, date]
) -> list[ScopeSummary]:
    scopes = pack.scopes
    assert scopes is not None
    by_scope: dict[str, list[Page]] = {}
    for page in pages:
        fm = page.frontmatter
        if isinstance(fm, SourceFrontmatter):
            scope = source_scope(pack, fm)
            if scope:
                by_scope.setdefault(scope, []).append(page)
    if "index" in by_scope:
        raise ValueError(
            f"scope value 'index' would overwrite {index_page_path(f'hubs/{scopes.plural}')}; "
            "rename that folder in the raw input or change the scopes.yaml regexes"
        )
    phase_rank = {phase.key: rank for rank, phase in enumerate(scopes.phases)}
    topics = [page for page in pages if isinstance(page.frontmatter, TopicFrontmatter)]
    entities = [page for page in pages if isinstance(page.frontmatter, EntityFrontmatter)]
    summaries: list[ScopeSummary] = []
    for scope, members in by_scope.items():
        ids = {page.frontmatter.id for page in members}
        keys = [_source_phase(pack, page.frontmatter) for page in members]  # type: ignore[arg-type]
        phases = [key for key in keys if key in phase_rank]
        phase = max(phases, key=lambda key: phase_rank[key]) if phases else None

        def received(page: Page) -> tuple[bool, date, str, str]:
            # Documents with a known date come first: the latest of them is the last received.
            fm = page.frontmatter
            assert isinstance(fm, SourceFrontmatter)
            return (*_source_date(fm, dates), fm.title.casefold(), page.path)

        last = max(members, key=received)
        own_topics = [
            page
            for page in topics
            if page.frontmatter.scope == scope  # type: ignore[union-attr]
        ]
        company_topics = [
            page
            for page in topics
            if page.frontmatter.scope is None  # type: ignore[union-attr]
            and ids & set(page.frontmatter.sources)  # type: ignore[union-attr]
        ]
        summaries.append(
            ScopeSummary(
                scope=scope,
                label=scope_label(pack, scope),
                path=hub_page_path(format_hub_id(scopes.plural, scope)),
                sources=members,
                entry=_registry_entry(pack, scope),
                phase=phase,
                last=last,
                last_date=received(last)[1],
                topics=_by_title([*own_topics, *company_topics]),
                entities=_by_title(
                    page
                    for page in entities
                    if ids & set(page.frontmatter.sources)  # type: ignore[union-attr]
                ),
                contradictions=_by_title(
                    page
                    for page in own_topics
                    if page.frontmatter.contradictions  # type: ignore[union-attr]
                ),
            )
        )
    default = scopes.default.key
    return sorted(
        summaries,
        key=lambda item: (item.scope == default, item.label.casefold(), item.scope),
    )


def _phase_text(pack: DomainPack, key: str | None) -> str:
    if key is None or pack.scopes is None:
        return "—"
    title = pack.scopes.phase_title(key)
    return f"{key} {title}" if title and title != key else key


def _status(page: Page, from_path: str, by_id: Mapping[str, Page]) -> str:
    fm = page.frontmatter
    assert isinstance(fm, SourceFrontmatter)
    if fm.status != "superseded":
        return fm.status
    newer = _by_title(by_id[sid] for sid in fm.superseded_by if sid in by_id)
    if not newer:
        return "superseded"
    return "superseded by " + ", ".join(
        md_link(item.frontmatter.title, from_path, item.path) for item in newer
    )


def _documents(summary: ScopeSummary, pack: DomainPack, by_id: Mapping[str, Page]) -> list[str]:
    scopes = pack.scopes
    assert scopes is not None
    grouped: dict[str | None, list[Page]] = {}
    known = {phase.key for phase in scopes.phases}
    for page in summary.sources:
        fm = page.frontmatter
        assert isinstance(fm, SourceFrontmatter)
        phase = _source_phase(pack, fm)
        grouped.setdefault(phase if phase in known else None, []).append(page)
    lines = ["## Documents", ""]
    order: list[tuple[str | None, str]] = [
        (phase.key, f"Phase {_phase_text(pack, phase.key)}") for phase in scopes.phases
    ]
    order.append((None, NO_PHASE))
    shown = [(key, title) for key, title in order if key in grouped]
    for key, title in shown:
        if len(shown) > 1 or key is not None:
            lines += [f"### {inline_text(title)}", ""]
        members = sorted(
            grouped[key],
            key=lambda p: (
                p.frontmatter.status != "current",  # type: ignore[union-attr]
                p.frontmatter.title.casefold(),
                p.path,
            ),
        )
        for page in members:
            link = md_link(page.frontmatter.title, summary.path, page.path)
            lines.append(f"- {link}: {_status(page, summary.path, by_id)}")
        lines.append("")
    return lines


def _counts(summary: ScopeSummary) -> str:
    count = len(summary.sources)
    return f"{count} {plural('document', count)}, last received {summary.last_date.isoformat()}."


def _hub_page(
    summary: ScopeSummary,
    pack: DomainPack,
    by_id: Mapping[str, Page],
    *,
    stamp: DocwikiStamp,
    updated: date,
) -> Page:
    scopes = pack.scopes
    assert scopes is not None
    path = summary.path
    noun = scopes.title.lower()
    last_title = summary.last.frontmatter.title
    summary_text = one_line(f"{summary.label}: {_counts(summary)}")
    lines = [f"# {inline_text(summary.label)}", ""]
    if pack.info.banner:
        lines += [f"> {inline_text(pack.info.banner)}", ""]
    lines += [
        inline_text(_counts(summary)[:1].upper() + _counts(summary)[1:])
        + " Built by code from the documents' folders and the domain pack; the facts themselves "
        "are on the cited source and topic pages.",
        "",
        "## Details",
        "",
    ]
    attributes = summary.entry.attributes if summary.entry is not None else {}
    if attributes:
        lines += [
            "From the domain pack's registry (reviewed, not read from the documents).",
            "",
            "| Attribute | Value |",
            "|---|---|",
        ]
        lines += [
            f"| {inline_text(_attribute_name(key))} | {inline_text(str(value))} |"
            for key, value in attributes.items()
        ]
    else:
        lines.append(f"The domain pack's registry has no entry for {inline_text(summary.label)}.")
    lines.append("")
    lines += _documents(summary, pack, by_id)
    lines += ["## Topics", ""]
    if summary.topics:
        for page in summary.topics:
            link = md_link(page.frontmatter.title, path, page.path)
            text = inline_text(page.frontmatter.summary) if page.frontmatter.summary else ""
            lines.append(f"- {link}: {text}" if text else f"- {link}")
    else:
        lines.append("No topic synthesises these documents yet.")
    lines += ["", "## Entities", ""]
    if summary.entities:
        lines += [
            f"- {md_link(page.frontmatter.title, path, page.path)}" for page in summary.entities
        ]
    else:
        lines.append("No registry entity is mentioned by these documents yet.")
    lines += ["", "## Open contradictions", ""]
    if summary.contradictions:
        for page in summary.contradictions:
            number = page.frontmatter.contradictions  # type: ignore[union-attr]
            lines.append(
                f"- {md_link(page.frontmatter.title, path, page.path)}: "
                f"{number} {plural('contradiction', number)}"
            )
    else:
        lines.append(f"No open contradictions in the topics of this {noun}.")
    lines += [
        "",
        "## Last document received",
        "",
        f"- {md_link(last_title, path, summary.last.path)} ({summary.last_date.isoformat()})",
    ]
    frontmatter = HubFrontmatter(
        id=format_hub_id(scopes.plural, summary.scope),
        title=summary.label,
        summary=summary_text,
        sensitivity=max_sensitivity(  # type: ignore[arg-type]
            *(page.frontmatter.sensitivity for page in summary.sources)
        ),
        updated=updated,
        tags=[scopes.name],
        docwiki=stamp,
        scope_type=scopes.name,
        scope=summary.scope,
        sources=sorted(page.frontmatter.id for page in summary.sources),
    )
    return Page(path=path, frontmatter=frontmatter, body="\n".join(lines) + "\n")


def build_hubs(
    pages: Sequence[Page],
    pack: DomainPack,
    *,
    stamp: DocwikiStamp,
    updated: date,
    dates: Mapping[str, date] | None = None,
) -> HubBundle:
    """Hub pages and the hubs index from the content pages after the ``links`` stage.

    ``dates`` maps source ids to the documents' own dates (see :func:`doc_dates`); without one,
    a ``YYYY-MM-DD`` in the file name, else the source page's ``updated`` date, is used.
    """
    scopes = pack.scopes
    if scopes is None:
        return HubBundle([], [])
    known = dict(dates or {})
    summaries = _summaries(pages, pack, known)
    if not summaries:
        return HubBundle([], [])
    by_id = {page.frontmatter.id: page for page in pages}
    hubs = [_hub_page(summary, pack, by_id, stamp=stamp, updated=updated) for summary in summaries]
    index_path = index_page_path(f"hubs/{scopes.plural}")
    title = plural(scopes.title, 2)
    noun = inline_text(scopes.title.lower())
    body = [f"# {inline_text(title)}", ""]
    body += [
        f"One hub page per {noun}, built by code from the documents' folders and the domain pack.",
        "",
    ]
    body += [
        f"- {md_link(hub.frontmatter.title, index_path, hub.path)}: {inline_text(_counts(item))}"
        for hub, item in zip(hubs, summaries, strict=True)
    ]
    index = Page(
        path=index_path,
        frontmatter=IndexFrontmatter(
            id=f"index:hubs/{scopes.plural}",
            title=title,
            summary=one_line(f"The hub page of every {scopes.title.lower()}."),
            sensitivity=max_sensitivity(  # type: ignore[arg-type]
                *(hub.frontmatter.sensitivity for hub in hubs)
            ),
            updated=updated,
            docwiki=stamp,
        ),
        body="\n".join(body) + "\n",
    )
    return HubBundle([*hubs, index], summaries)


def dashboard_lines(bundle: HubBundle, pack: DomainPack, from_path: str) -> list[str]:
    """The company dashboard section of the home page: one table row per scope value."""
    scopes = pack.scopes
    if scopes is None or not bundle.summaries:
        return []
    title = plural(scopes.title, 2)
    index_path = index_page_path(f"hubs/{scopes.plural}")
    lines = [
        f"## {inline_text(title)}",
        "",
        f"| {inline_text(scopes.title)} | Phase | Client | Documents | Last document received "
        "| Open contradictions |",
        "|---|---|---|---:|---|---:|",
    ]
    for item in bundle.summaries:
        client = item.entry.attributes.get("client") if item.entry is not None else None
        last = md_link(item.last.frontmatter.title, from_path, item.last.path)
        lines.append(
            f"| {md_link(item.label, from_path, item.path)} "
            f"| {inline_text(_phase_text(pack, item.phase))} "
            f"| {inline_text(str(client)) if client is not None else '—'} "
            f"| {len(item.sources)} "
            f"| {last} ({item.last_date.isoformat()}) "
            f"| {sum(page.frontmatter.contradictions for page in item.contradictions)} |"  # type: ignore[union-attr]
        )
    lines += [
        "",
        f"Every {inline_text(scopes.title.lower())} has a hub page; see "
        f"[all {inline_text(title.lower())}]({relative_link(from_path, index_path)}).",
        "",
    ]
    return lines
