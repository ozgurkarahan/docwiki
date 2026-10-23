"""Source page rendering (wiki-contract §3–5) and helpers shared by the page builders.

``render_source_page`` writes every part of a source page except ``## Related`` and the
backlinks block: the assemble lane inserts them right before ``## Sources``. Footnotes follow
the contracts format ``[^cN]: [<source title> — <locator label>](<sidecar>) · <badge>`` with labels
in order of first use; one footnote per (source, locator key, badge). Every footnote's locator is
returned as a :class:`~docwiki.engine_types.CitedLocator` so the evidence stage writes its sidecar.

The superseded banner names the replacement sources as code spans (`` `src-…` ``) because page
paths of other sources are not inputs of this function; :func:`link_source_refs` turns them into
relative links once all source pages exist (assemble lane, ``links`` stage).
"""

from __future__ import annotations

import logging
import posixpath
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import cast

from docwiki.contracts.compiled import CompiledSource
from docwiki.contracts.enums import PROVENANCES, Provenance, badge_for
from docwiki.contracts.extracted import ExtractedDoc, Figure, Table
from docwiki.contracts.fences import FenceTracker, escape_fence, opening_fence, widen_fences
from docwiki.contracts.i18n import CORE_STRINGS, Strings, core_strings
from docwiki.contracts.ids import normalize_tags, parse_release_id, source_page_path
from docwiki.contracts.locators import Locator, locator_key, locator_label
from docwiki.contracts.markdown import FOOTNOTE_DEF_RE, relative_link
from docwiki.contracts.pages import DocwikiStamp, ExtractionSummary, Page, SourceFrontmatter
from docwiki.contracts.safety import detect_injection, neutralize_injections, sanitize_markdown
from docwiki.contracts.state import SourceState
from docwiki.domain import DomainPack
from docwiki.engine_types import CitedLocator, Classification, CompiledResult, VerifiedCitation
from docwiki.stages.models import FactRecord, SourceInfo
from docwiki.stages.verify_citations import (
    CitationRefError,
    DocIndex,
    figure_locator,
    normalize_text,
    split_sentences,
)

__all__ = [
    "MAX_RENDERED_TABLE_ROWS",
    "RESERVED_SECTION_HEADINGS",
    "Footnotes",
    "attach_refs",
    "banner_line",
    "clean_block_markdown",
    "clean_inline",
    "clean_title",
    "escape_document_text",
    "fact_key",
    "fact_records",
    "link_source_refs",
    "release_date",
    "render_source_page",
    "render_table",
    "section_heading",
    "source_infos",
]

MAX_RENDERED_TABLE_ROWS = 200
"""Rows rendered per table on a source page; the full table stays queryable (``query_table``)."""

logger = logging.getLogger("docwiki.stages.render")

FICTIONAL_NOTICE = "FICTIONAL - NOT FOR OPERATIONAL USE."
_RESERVED_KEYS = (
    "key_facts",
    "contents",
    "figures",
    "related",
    "referenced_by",
    "sources",
    "facts",
    "timeline",
    "documents",
    "overview",
    "contradictions",
    "superseded",
    "sources_consulted",
)
RESERVED_SECTION_HEADINGS = frozenset(
    table[f"heading.{key}"].casefold() for table in CORE_STRINGS.values() for key in _RESERVED_KEYS
)
"""Generated headings of content pages, in every core language (case-folded)."""

_MARKER_RE = re.compile(r"\[\[\s*cite\s*:\s*([^\]\n]*?)\s*\]\]", re.IGNORECASE)
_WIKILINK_RE = re.compile(r"\[\[([^\[\]\n]*)\]\]")
_IMAGE_RE = re.compile(r"!\[([^\]\n]*)\]\([^)\n]*\)")
_LINK_RE = re.compile(r"(?<!\\)\[([^\[\]\n]*)\]\([^)\n]*\)")
_REF_LINK_RE = re.compile(r"(?<!\\)\[([^\[\]\n]+)\]\[[^\]\n]*\]")
_REF_DEF_LINE_RE = re.compile(r"^ {0,3}\[[^\]\n]+\]:\s*\S.*$")
_FOOTNOTE_REF_RE = re.compile(r"\[\^[^\]\s]*\]")
_ATX_RE = re.compile(r"^( {0,3})(#{1,6})(?=\s|$)")
_SETEXT_RE = re.compile(r"^ {0,3}(?:=+|-+)\s*$")
_TABLE_LINE_RE = re.compile(r"^\s*\|.*\|\s*$")
_CODE_SPAN_RE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")
_SOURCE_REF_RE = re.compile(r"`(src-[0-9a-f]{12})`")


# --------------------------------------------------------------------------- text cleaning


def _strip_links(text: str) -> str:
    for _ in range(5):
        before = text
        text = _IMAGE_RE.sub(lambda m: m.group(1), text)
        text = _LINK_RE.sub(lambda m: m.group(1), text)
        text = _REF_LINK_RE.sub(lambda m: m.group(1), text)
        if text == before:
            break
    return text


def _neutralize(text: str) -> str:
    """Drop sentences addressed to AI systems (marker-aware sentence split; code untouched)."""
    out: list[str] = []
    fences = FenceTracker()
    for line in text.split("\n"):
        if fences.feed(line):
            out.append(line)
            continue
        if not detect_injection(line):
            out.append(line)
            continue
        prefix = re.match(r"^(\s*(?:(?:[-*+]|\d+[.)]|>)\s+)?)", line)
        head = prefix.group(1) if prefix else ""
        kept = [
            sentence
            for sentence in split_sentences(line[len(head) :])
            if not detect_injection(sentence)
        ]
        remaining = "".join(kept).strip()
        if remaining:
            out.append(escape_fence(head + remaining))
    return "\n".join(out)


def _sanitize(text: str) -> str:
    text, _ = neutralize_injections(_neutralize(text))
    text, _ = sanitize_markdown(text, allow_markers=False)
    return _strip_links(text)


def clean_inline(text: str, *, keep_markers: bool = False) -> str:
    """Model text as one safe Markdown line (no links, footnotes, HTML or injected sentences)."""
    text = _FOOTNOTE_REF_RE.sub("", text.replace("\r", "\n"))
    if not keep_markers:
        text = _MARKER_RE.sub("", text)
    text = _sanitize(text)
    lines = [line.strip() for line in text.split("\n") if not FOOTNOTE_DEF_RE.match(line.strip())]
    text = " ".join(line for line in lines if line)
    text = re.sub(r"^(?:#+\s+|[>*+-]\s+|\d+[.)]\s+)+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"[ \t]+([.,;:!?])", r"\1", text)


def clean_title(text: str, *, max_len: int = 160) -> str:
    """A page title: one line, no brackets, angle brackets, backticks or emphasis markers."""
    text = clean_inline(text)
    text = text.replace("\\<", "").replace("\\>", "")
    text = re.sub(r"[\[\]<>`*_|]", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" .-—–:")
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0].rstrip(" .-—–:") or text[:max_len]
    return text


def _close_fences(lines: list[str]) -> list[str]:
    fences = FenceTracker()
    for line in lines:
        fences.feed(line)
    return [*lines, fences.opener] if fences.opener is not None else lines


def _strip_code_markers(line: str) -> str:
    """Remove ``[[cite:…]]`` markers inside inline code spans (they would never render)."""
    return _CODE_SPAN_RE.sub(lambda m: _MARKER_RE.sub("", m.group(0)), line)


def clean_block_markdown(text: str, *, keep_markers: bool = True) -> str:
    """Model Markdown for a section body: safe, no headings above level 4, no tables, footnotes,
    links or images, balanced code fences; ``[[cite:…]]`` markers kept when ``keep_markers``
    (outside code only).

    Code follows :mod:`docwiki.contracts.fences`, the tracker citation verification uses too. Lines
    are classified as they are written out (removing a marker can turn a code line into the
    closing fence), text lines that start like a fence are escaped, and fences are widened where
    simpler parsers (the release validator) would otherwise read other blocks."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not keep_markers:
        text = _MARKER_RE.sub("", text)
    text = _sanitize(text)
    out: list[str] = []
    fences = FenceTracker()
    for line in text.split("\n"):
        if fences.inside or opening_fence(line) is not None:
            line = _MARKER_RE.sub("", line)
            fences.feed(line)
            out.append(line)
            continue
        if FOOTNOTE_DEF_RE.match(line.strip()) or _REF_DEF_LINE_RE.match(line):
            continue
        if _TABLE_LINE_RE.match(line) or _SETEXT_RE.match(line):
            continue
        line = _strip_code_markers(_FOOTNOTE_REF_RE.sub("", line))
        heading = _ATX_RE.match(line)
        if heading:
            line = "####" + line[heading.end() :]
            if not line[4:].strip():
                continue
        out.append(escape_fence(line.rstrip()))
    out = widen_fences(_close_fences(out))
    body = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", body).strip("\n")


def escape_document_text(text: str) -> str:
    """Document text (captions, table cells) as one safe Markdown line."""
    text, _ = sanitize_markdown(text.replace("\r", "\n"), allow_markers=False)
    text = _strip_links(text)
    text = " ".join(text.split())
    text = text.replace("[^", "\\[^").replace("[[", "\\[\\[")
    return text


def release_date(stamp: DocwikiStamp) -> date:
    """Calendar date (UTC) of the release a page belongs to (frontmatter ``updated``)."""
    return parse_release_id(stamp.release)[0].date()


def banner_line(pack: DomainPack) -> str | None:
    """The pack banner as a quote line (a fictional notice when the pack is fictional)."""
    banner = pack.info.banner
    if banner:
        text = clean_inline(banner)
        return f"> {text}" if text else None
    if pack.info.fictional:
        return f"> {FICTIONAL_NOTICE}"
    return None


def section_heading(text: str, used: set[str], *, suffix: str = "document section") -> str | None:
    """A compiled section heading that cannot collide with the page structure."""
    heading = clean_title(text, max_len=100)
    if not heading:
        return None
    if heading.casefold() in RESERVED_SECTION_HEADINGS:
        heading = f"{heading} ({suffix})"
    base, number = heading, 2
    while heading.casefold() in used:
        heading = f"{base} ({number})"
        number += 1
    used.add(heading.casefold())
    return heading


# --------------------------------------------------------------------------- footnotes


@dataclass
class _CitedEntry:
    source_id: str
    locator: Locator
    provenance: str
    block_ids: list[str] = field(default_factory=list)
    quotes: list[str] = field(default_factory=list)


class Footnotes:
    """Footnote labels ``c1…cN`` in order of first use and the cited locators behind them."""

    def __init__(
        self, page_path: str, titles: Mapping[str, str], strings: Strings | None = None
    ) -> None:
        self.page_path = page_path
        self.titles = titles
        self.strings = strings or core_strings()
        self._labels: dict[tuple[str, str, str], str] = {}
        self._definitions: list[str] = []
        self._cited: dict[tuple[str, str, str], _CitedEntry] = {}

    def __len__(self) -> int:
        return len(self._definitions)

    def ref(
        self,
        source_id: str,
        locator: Locator,
        provenance: str,
        status: str,
        *,
        block_ids: Iterable[str] = (),
        quote: str | None = None,
    ) -> str:
        """``[^cN]`` for a citation (a new label on first use of its locator and badge)."""
        badge = badge_for(provenance, status)
        key = (source_id, locator_key(locator), badge)
        label = self._labels.get(key)
        if label is None:
            label = f"c{len(self._definitions) + 1}"
            self._labels[key] = label
            title = self.titles[source_id]
            target = relative_link(self.page_path, f"evidence/{source_id}/{key[1]}.md")
            self._definitions.append(
                f"[^{label}]: [{title} — {locator_label(locator)}]({target}) · {badge}"
            )
        cited_key = (source_id, locator.model_dump_json(), provenance)
        entry = self._cited.get(cited_key)
        if entry is None:
            entry = self._cited[cited_key] = _CitedEntry(source_id, locator, provenance)
        for block_id in block_ids:
            if block_id not in entry.block_ids:
                entry.block_ids.append(block_id)
        if quote and quote not in entry.quotes:
            entry.quotes.append(quote)
        return f"[^{label}]"

    def cite(self, citation: VerifiedCitation) -> str:
        """``[^cN]`` for a verified citation (``failed`` ones are rejected)."""
        if citation.status == "failed" or citation.locator is None:
            raise ValueError("failed citations never reach a page")
        return self.ref(
            citation.source_id,
            citation.locator,
            citation.provenance,
            citation.status,
            block_ids=citation.block_ids,
            quote=citation.quote,
        )

    def cite_all(self, citations: Iterable[VerifiedCitation]) -> str:
        """Concatenated references of several citations, without repeating a label."""
        refs: list[str] = []
        for citation in citations:
            ref = self.cite(citation)
            if ref not in refs:
                refs.append(ref)
        return "".join(refs)

    def definitions(self) -> list[str]:
        return list(self._definitions)

    def cited_locators(self) -> list[CitedLocator]:
        return [
            CitedLocator(
                source_id=entry.source_id,
                locator=entry.locator,
                block_ids=tuple(entry.block_ids),
                quotes=tuple(entry.quotes),
                provenance=entry.provenance,  # type: ignore[arg-type]
            )
            for entry in self._cited.values()
        ]

    def sources_section(self) -> list[str]:
        """The ``## Sources`` section lines (always present: the assemble lane anchors on it)."""
        lines = [f"## {self.strings.heading('sources')}", ""]
        lines += self._definitions or [self.strings("render.no_evidence")]
        return lines


def attach_refs(text: str, refs: str) -> str:
    """Append footnote references to a sentence, after its final punctuation."""
    return f"{text.rstrip()}{refs}" if refs else text


# --------------------------------------------------------------------------- tables


def _cell(text: str) -> str:
    return escape_document_text(text).replace("|", "\\|")


def render_table(
    table: Table, *, max_rows: int = MAX_RENDERED_TABLE_ROWS, strings: Strings | None = None
) -> list[str]:
    """A table rendered from the extracted data (never re-typed by a model)."""
    t = strings or core_strings()
    label = locator_label(table.locator)
    lines = [
        t("render.table_caption", table_id=table.id, label=escape_document_text(label)),
        "",
    ]
    columns = [
        _cell(name) or t("render.column", number=number)
        for number, name in enumerate(table.columns, 1)
    ]
    header = [t("render.row"), *columns]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join("---" for _ in header) + " |")
    for row in table.rows[:max_rows]:
        cells = [str(int(row.row_id[1:])), *(_cell(cell) for cell in row.cells)]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    shown = min(len(table.rows), max_rows)
    if len(table.rows) > shown:
        lines.append(t("render.table_more", shown=shown, total=len(table.rows), table_id=table.id))
    else:
        lines.append(t("render.table_query", table_id=table.id))
    return lines


# --------------------------------------------------------------------------- source page


def _citations_by_ref(citations: Sequence[VerifiedCitation]) -> dict[str, list[VerifiedCitation]]:
    grouped: dict[str, list[VerifiedCitation]] = {}
    for citation in citations:
        if citation.status != "failed":
            grouped.setdefault(citation.ref, []).append(citation)
    return grouped


def _provenance_mix(doc: ExtractedDoc) -> dict[Provenance, int]:
    counts: dict[str, int] = {provenance: 0 for provenance in PROVENANCES}
    for block in doc.blocks:
        counts[block.provenance] += 1
    return {cast(Provenance, provenance): count for provenance, count in counts.items() if count}


def _pair_markers(
    markers: Sequence[re.Match[str]], citations: Sequence[VerifiedCitation], index: DocIndex
) -> list[VerifiedCitation | None]:
    """Each marker's verified citation, matched in body order by what its id resolves to."""
    paired: list[VerifiedCitation | None] = []
    position = 0
    for marker in markers:
        try:
            cited = index.resolve(marker.group(1))
        except CitationRefError:
            paired.append(None)
            continue
        found = next(
            (
                number
                for number in range(position, len(citations))
                if citations[number].block_ids == cited.block_ids
                and citations[number].locator == cited.locator
            ),
            None,
        )
        if found is None:
            paired.append(None)
            continue
        paired.append(citations[found])
        position = found + 1
    return paired


def _render_section_body(
    body: str,
    citations: list[VerifiedCitation],
    footnotes: Footnotes,
    where: str,
    index: DocIndex,
) -> str:
    """Section body with footnotes for its markers (in body order, outside fenced code).

    Compilation verified exactly these markers, so their count matches the citations. If it
    ever does not (for example a result compiled by an older engine), markers are matched to
    the citations they resolve to and unmatched ones are dropped with a warning instead of
    failing the build.
    """
    markers = list(_MARKER_RE.finditer(body))
    paired: list[VerifiedCitation | None] = list(citations)
    if len(markers) != len(citations):
        paired = _pair_markers(markers, citations, index)
        logger.warning(
            "%s: %d citation marker(s) but %d verified citation(s); %d unmatched marker(s) dropped",
            where,
            len(markers),
            len(citations),
            sum(1 for citation in paired if citation is None),
        )
    pieces: list[str] = []
    cursor = 0
    for marker, citation in zip(markers, paired, strict=True):
        pieces.append(body[cursor : marker.start()].rstrip(" \t"))
        if citation is not None:
            pieces.append(footnotes.cite(citation))
        cursor = marker.end()
    pieces.append(body[cursor:])
    text = "".join(pieces)
    text = re.sub(r"(\[\^c\d+\])(?:\1)+", r"\1", text)
    return _WIKILINK_RE.sub(lambda m: m.group(1), text)


def _figure_line(figure: Figure, index: DocIndex, source_id: str, footnotes: Footnotes) -> str:
    t = footnotes.strings
    locator = figure_locator(figure)
    parts: list[str] = []
    if figure.caption:
        caption = escape_document_text(figure.caption)
        if caption:
            parts.append(caption.rstrip(".") + ".")
    if figure.description:
        description = clean_inline(figure.description)
        if description:
            parts.append(t("render.generated_description", text=description.rstrip(".")))
    if not parts:
        parts.append(t("render.no_caption"))
    if figure.description:
        ref = footnotes.ref(source_id, locator, "model-description", "verified")
    else:
        provenance = index.page_provenance(locator)
        ref = footnotes.ref(source_id, locator, provenance, "unverified-paraphrase")
    label = escape_document_text(locator_label(locator))
    return t("render.figure", figure_id=figure.id, label=label) + attach_refs(" ".join(parts), ref)


def render_source_page(
    result: CompiledResult,
    doc: ExtractedDoc,
    classification: Classification,
    state: SourceState,
    *,
    slug: str,
    stamp: DocwikiStamp,
    pack: DomainPack,
    supersedes: Sequence[str] = (),
    superseded_by: Sequence[str] = (),
) -> tuple[Page, list[CitedLocator]]:
    """The source page of one compiled source and the locators its footnotes cite."""
    source_id = doc.source_id
    if result.source_id != source_id or state.source_id != source_id:
        raise ValueError("result, doc and state must describe the same source")
    if state.raw_path != doc.source_path:
        raise ValueError(f"{source_id}: state raw_path does not match the extracted source path")
    compiled: CompiledSource = result.compiled
    path = source_page_path(slug)
    title = (
        clean_title(compiled.title)
        or clean_title(posixpath.splitext(posixpath.basename(doc.source_path))[0])
        or source_id
    )
    t = pack.strings()
    footnotes = Footnotes(path, {source_id: title}, t)
    index = DocIndex(doc)
    grouped = _citations_by_ref(result.citations)

    lines = [f"# {title}", ""]
    banner = banner_line(pack)
    if banner:
        lines += [banner, ""]
    newer = sorted({sid for sid in superseded_by if sid != source_id})
    older = sorted({sid for sid in supersedes if sid != source_id})
    if newer:
        refs = ", ".join(f"`{sid}`" for sid in newer)
        lines += [t("render.superseded_banner", links=refs), ""]
    summary = clean_inline(compiled.summary) or f"{title}."
    lines += [summary, "", f"## {t.heading('key_facts')}", ""]

    fact_lines: list[str] = []
    for number, fact in enumerate(compiled.key_facts, start=1):
        citations = grouped.get(f"kf{number}", [])
        if len(citations) != len(fact.citations) or not citations:
            raise ValueError(f"{source_id}: key fact {number} and its verified citations differ")
        text = clean_inline(fact.text)
        if text:
            fact_lines.append(f"- {attach_refs(text, footnotes.cite_all(citations))}")
    lines += fact_lines or [t("render.no_key_facts")]

    lines += ["", f"## {t.heading('contents')}", ""]
    used_headings: set[str] = set()
    rendered_tables: set[str] = set()
    section_count = 0
    for number, section in enumerate(compiled.sections, start=1):
        heading = section_heading(section.heading, used_headings)
        body = _render_section_body(
            clean_block_markdown(section.body),
            grouped.get(f"s{number}", []),
            footnotes,
            f"{source_id} section {number}",
            index,
        )
        tables = [
            index.tables[table_id]
            for table_id in dict.fromkeys(section.table_refs)
            if table_id in index.tables
        ]
        if heading is None or (not body.strip() and not tables):
            continue
        section_count += 1
        lines += [f"### {heading}", ""]
        if body.strip():
            lines += [body, ""]
        for table in tables:
            if table.id in rendered_tables:
                lines += [t("render.see_table", table_id=table.id), ""]
                continue
            rendered_tables.add(table.id)
            lines += [*render_table(table, strings=t), ""]
    remaining = [table for table in doc.tables if table.id not in rendered_tables]
    if remaining:
        tables_title = t.heading("tables")
        heading = section_heading(tables_title, used_headings) or tables_title
        lines += [f"### {heading}", ""]
        for table in remaining:
            lines += [*render_table(table, strings=t), ""]
    elif not section_count:
        lines += [t("render.no_sections"), ""]
    while lines and not lines[-1]:
        lines.pop()

    lines += ["", f"## {t.heading('figures')}", ""]
    if doc.figures:
        lines += [_figure_line(figure, index, source_id, footnotes) for figure in doc.figures]
    else:
        lines.append(t("render.no_figures"))
    lines += ["", *footnotes.sources_section()]

    entity_ids = sorted({mention.entity_id for mention in compiled.entity_mentions})
    known = set(pack.entity_ids)
    unknown = [entity_id for entity_id in entity_ids if entity_id not in known]
    if unknown:
        raise ValueError(f"{source_id}: entity ids not in the registry: {unknown}")
    pages = doc.metadata.page_count
    frontmatter = SourceFrontmatter(
        id=source_id,
        title=title,
        summary=summary,
        lang=pack.canonical_lang,
        sensitivity=state.sensitivity,
        updated=release_date(stamp),
        tags=normalize_tags([classification.doc_type, classification.category]),
        docwiki=stamp,
        source_id=source_id,
        source_path=doc.source_path,
        source_hash=doc.source_hash,
        media_type=doc.media_type,
        doc_type=classification.doc_type,
        doc_type_label=_doc_type_label(pack, classification.doc_type),
        category=classification.category,
        doc_number=classification.doc_number,
        revision=classification.revision,
        scope=classification.scope,
        phase=classification.phase,
        lot=classification.lot,
        status="superseded" if newer else "current",
        supersedes=older,
        superseded_by=newer,
        original_lang=classification.lang,
        pages=pages if pages else None,
        entities=entity_ids,
        topics=[],
        authority=classification.authority,
        extraction=ExtractionSummary(
            adapter=doc.extraction.adapter,
            version=doc.extraction.adapter_version,
            provenance_mix=_provenance_mix(doc),
        ),
    )
    page = Page(path=path, frontmatter=frontmatter, body="\n".join(lines) + "\n")
    return page, footnotes.cited_locators()


def link_source_refs(page: Page, pages: Mapping[str, Page]) -> Page:
    """Replace `` `src-…` `` code spans of ``page`` (e.g. the superseded banner) with links.

    ``pages`` maps source ids to their source pages; unknown ids are left as code spans.
    """
    targets = {
        candidate.frontmatter.id: candidate
        for candidate in pages.values()
        if isinstance(candidate.frontmatter, SourceFrontmatter)
    }

    def replace(match: re.Match[str]) -> str:
        target = targets.get(match.group(1))
        if target is None:
            return match.group(0)
        return f"[{target.frontmatter.title}]({relative_link(page.path, target.path)})"

    body = _SOURCE_REF_RE.sub(replace, page.body)
    return page if body == page.body else page.model_copy(update={"body": body})


# --------------------------------------------------------------------------- shared by pages


def fact_key(text: str) -> str:
    """De-duplication key of a fact text (normalised, without final punctuation)."""
    return normalize_text(text).rstrip(" .;:!")


def _parse_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def source_infos(
    source_pages: Mapping[str, Page], results: Iterable[CompiledResult] = ()
) -> dict[str, SourceInfo]:
    """Source id → what entity and topic pages need (title, path, status, tier, date…)."""
    dates = {result.source_id: _parse_date(result.usage.get("doc_date")) for result in results}
    infos: dict[str, SourceInfo] = {}
    for page in source_pages.values():
        fm = page.frontmatter
        if not isinstance(fm, SourceFrontmatter):
            continue
        infos[fm.source_id] = SourceInfo(
            source_id=fm.source_id,
            title=fm.title,
            path=page.path,
            status=fm.status,
            sensitivity=fm.sensitivity,
            authority=fm.authority,
            doc_type=fm.doc_type,
            doc_number=fm.doc_number,
            revision=fm.revision,
            date=dates.get(fm.source_id),
            supersedes=tuple(fm.supersedes),
            superseded_by=tuple(fm.superseded_by),
        )
    return infos


def _doc_type_label(pack: DomainPack, doc_type: str) -> str | None:
    """The pack's display label of a doc type (``PV de réception``), never its key."""
    try:
        return pack.doc_type(doc_type).display_label
    except KeyError:
        return None


def fact_records(result: CompiledResult) -> list[FactRecord]:
    """The verified key facts of a compiled source with their (non-failed) citations."""
    grouped = _citations_by_ref(result.citations)
    records: list[FactRecord] = []
    for number, fact in enumerate(result.compiled.key_facts, start=1):
        ref = f"kf{number}"
        citations = tuple(grouped.get(ref, ()))
        text = clean_inline(fact.text)
        if citations and text:
            records.append(
                FactRecord(
                    source_id=result.source_id,
                    ref=ref,
                    text=text,
                    numbers=tuple(fact.numbers),
                    citations=citations,
                )
            )
    return records
