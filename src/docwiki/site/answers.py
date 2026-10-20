"""``answers.json``: the filed research answers of a release, for the "Ask this wiki" drawer.

ADR 0007: visitors of the static site get research answers that were reviewed and filed as
``queries/<yyyy-mm-dd>-<slug>.md`` pages, never a live model. This module turns those pages into
the data that the drawer (``site/quartz/components/docwiki/AskPanel.tsx``) renders with DOM nodes
and ``textContent`` only. Everything is derived from the structure of the pages, without a model:

* ``banners``: the superseded and warning notices that open the page, as plain text (the
  fictional-sample stamp is left out: the site banner shows it on every page);
* ``paragraphs``: the answer before the first ``##`` section, its inline Markdown reduced to text
  segments and citation numbers (``{"text": …}``, ``{"cite": n}``);
* ``citations``: the contract footnotes ``[^cN]: [<title> — <label>](<sidecar>) · <badge>``, the
  sidecar as a content slug (``evidence/<source_id>/<locator_key>``);
* ``steps``: the bullet items of the "How this answer was produced" section, and ``provenance``:
  the paragraphs directly under its heading (agent and version, dates, release, review);
* ``pages``: the content slugs the answer is about (its own page, its evidence, its source pages
  and their topic and entity pages), so that the drawer lists it first on those pages.

Page text was sanitised by the pipeline; it stays data here and in the drawer. The build writes the
payload into the Quartz checkout (:data:`ANSWERS_QUARTZ_PATH`) and Quartz publishes it as
:data:`ANSWERS_SITE_PATH`.
"""

from __future__ import annotations

import json
import re
from collections.abc import Collection, Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypedDict

from markdown_it.token import Token

from docwiki.contracts.catalog import Catalog
from docwiki.contracts.layout import EVIDENCE_MOUNT, WikiFiles
from docwiki.contracts.markdown import (
    FOOTNOTE_DEF_RE,
    FOOTNOTE_REF_RE,
    extract_footnotes,
    markdown_parser,
    resolve_href,
    split_sections,
    strip_backlinks_block,
)
from docwiki.contracts.pages import Page, QueryFrontmatter
from docwiki.release.validate import CITATION_RE
from docwiki.site.errors import SiteBuildError

if TYPE_CHECKING:
    from docwiki.site.build import ReleaseView

__all__ = [
    "ANSWERS_QUARTZ_PATH",
    "ANSWERS_SCHEMA",
    "ANSWERS_SITE_PATH",
    "HOW_HEADING",
    "QUERIES_DIR",
    "Answer",
    "AnswerCitation",
    "AnswersPayload",
    "NoticeKind",
    "Segment",
    "answer_for_page",
    "build_answers",
    "notice_kind",
    "query_pages",
    "write_answers",
]

ANSWERS_SCHEMA = 1
ANSWERS_SITE_PATH = "static/docwiki/answers.json"
"""Path of the answers in the built site (fetched by the drawer from the same origin)."""
ANSWERS_QUARTZ_PATH = f"quartz/{ANSWERS_SITE_PATH}"
"""Path written in the Quartz checkout; Quartz's ``Static`` emitter publishes it."""
HOW_HEADING = "How this answer was produced"
"""Section of a filed answer that records the agent and its tool steps (ADR 0007)."""
QUERIES_DIR = "queries"

NoticeKind = Literal["fictional", "superseded", "warning"]

_FICTIONAL_RE = re.compile(r"FICTIONAL\b", re.ASCII)
_SUPERSEDED_RE = re.compile(r"superseded\b", re.ASCII | re.IGNORECASE)
_WARNING_RE = re.compile(r"(?:warning|withdrawn)\b", re.ASCII | re.IGNORECASE)
_CITE_LABEL_RE = re.compile(r"^c(\d+)$")
_COMMENT_RE = re.compile(r"^\s*<!--.*?-->\s*$", re.DOTALL)
_SPACE_RE = re.compile(r"\s")


class Segment(TypedDict, total=False):
    """``{"text": …}`` or ``{"cite": n}`` (the number of a citation of the answer)."""

    text: str
    cite: int


class AnswerCitation(TypedDict):
    n: int
    title: str
    label: str
    href: str
    """Content slug of the evidence sidecar, without ``.md`` (``evidence/<source_id>/<key>``)."""
    badge: str


class Answer(TypedDict):
    id: str
    slug: str
    question: str
    date: str
    banners: list[str]
    paragraphs: list[list[Segment]]
    citations: list[AnswerCitation]
    steps: list[str]
    provenance: str
    """The paragraphs directly under "How this answer was produced" (agent, version, dates,
    release, review), as plain text; ``""`` without them."""
    pages: list[str]


class AnswersPayload(TypedDict):
    schema: int
    release: str
    answers: list[Answer]


def notice_kind(text: str) -> NoticeKind | None:
    """Kind of a notice blockquote (``> FICTIONAL …``, ``> **Superseded:** …``,
    ``> **Warning:** …``), as ``noticeKind`` of the site overlay (``docwiki-text.ts``)."""
    head = text.lstrip()
    if _FICTIONAL_RE.match(head):
        return "fictional"
    if _SUPERSEDED_RE.match(head):
        return "superseded"
    if _WARNING_RE.match(head):
        return "warning"
    return None


def _text_of(segment: Segment) -> str | None:
    return segment.get("text")


def _merge(segments: Iterable[Segment]) -> list[Segment]:
    """Adjacent text segments joined, empty ones dropped."""
    merged: list[Segment] = []
    for segment in segments:
        text = _text_of(segment)
        if text is None:
            merged.append(segment)
            continue
        if not text:
            continue
        previous = _text_of(merged[-1]) if merged else None
        if previous is None:
            merged.append({"text": text})
        else:
            merged[-1] = {"text": previous + text}
    return merged


def _trim(segments: Sequence[Segment]) -> list[Segment]:
    """Segments without leading and trailing whitespace; empty when only whitespace is left."""
    items = list(segments)
    first = _text_of(items[0]) if items else None
    if first is not None:
        items[0] = {"text": first.lstrip()}
    last = _text_of(items[-1]) if items else None
    if last is not None:
        items[-1] = {"text": last.rstrip()}
    return _merge(items)


def _plain(segments: Iterable[Segment]) -> str:
    """Text of the segments (citations dropped), whitespace collapsed."""
    return " ".join("".join(_text_of(segment) or "" for segment in segments).split())


def _with_citations(text: str, cites: Collection[int]) -> list[Segment]:
    """Footnote references ``[^cN]`` of known citations become ``{"cite": N}``; others go."""
    segments: list[Segment] = []
    last = 0
    for match in FOOTNOTE_REF_RE.finditer(text):
        segments.append({"text": text[last : match.start()]})
        label = _CITE_LABEL_RE.match(match.group("label"))
        if label is not None and int(label.group(1)) in cites:
            segments.append({"cite": int(label.group(1))})
        last = match.end()
    segments.append({"text": text[last:]})
    return segments


def _inline_segments(token: Token, cites: Collection[int]) -> list[Segment]:
    """Segments of an inline token: link and image text kept, emphasis, strong and code markers
    dropped, raw HTML kept as text (as the site renders it), HTML comments dropped."""
    segments: list[Segment] = []
    for child in token.children or []:
        if child.type == "text":
            segments.extend(_with_citations(child.content, cites))
        elif child.type in ("code_inline", "image"):
            segments.append({"text": child.content})
        elif child.type in ("softbreak", "hardbreak"):
            segments.append({"text": " "})
        elif child.type == "html_inline" and not _COMMENT_RE.match(child.content):
            segments.append({"text": child.content})
    return _merge(segments)


def _inline_plain(markdown: str) -> str:
    """Plain text of a line of inline Markdown (a citation title or locator label)."""
    tokens = markdown_parser().parseInline(markdown)
    return " ".join(_plain(_inline_segments(token, ())) for token in tokens).strip()


def _step_text(token: Token) -> str:
    """A tool step as plain text; a code span with spaces is quoted (``search "window date"``)."""
    parts: list[str] = []
    for child in token.children or []:
        if child.type == "text":
            parts.append(FOOTNOTE_REF_RE.sub("", child.content))
        elif child.type == "code_inline":
            code = child.content.strip()
            parts.append(f'"{code}"' if _SPACE_RE.search(code) else code)
        elif child.type == "image":
            parts.append(child.content)
        elif child.type in ("softbreak", "hardbreak"):
            parts.append(" ")
        elif child.type == "html_inline" and not _COMMENT_RE.match(child.content):
            parts.append(child.content)
    return " ".join("".join(parts).split())


def _block_end(tokens: Sequence[Token], start: int) -> int:
    """Index of the token that closes the block opened at ``start``."""
    if tokens[start].nesting != 1:
        return start
    depth = 0
    for index in range(start, len(tokens)):
        depth += tokens[index].nesting
        if depth == 0:
            return index
    return len(tokens) - 1


def _blocks(tokens: Sequence[Token]) -> Iterator[Sequence[Token]]:
    """Top-level blocks, each with all its tokens."""
    index = 0
    while index < len(tokens):
        end = _block_end(tokens, index)
        yield tokens[index : end + 1]
        index = end + 1


@dataclass
class _List:
    ordered: bool
    number: int


def _joined(cells: Sequence[Sequence[Segment]], separator: str) -> list[Segment]:
    segments: list[Segment] = []
    for index, cell in enumerate(cells):
        if index:
            segments.append({"text": separator})
        segments.extend(cell)
    return _merge(segments)


def _paragraphs(block: Sequence[Token], cites: Collection[int]) -> list[list[Segment]]:
    """One paragraph per paragraph, heading, list item (``• `` or ``1. `` first) or table row
    (cells separated by `` | ``) of a block; code keeps its text."""
    paragraphs: list[list[Segment]] = []
    lists: list[_List] = []
    prefix: str | None = None
    row: list[list[Segment]] | None = None
    for token in block:
        kind = token.type
        if kind in ("bullet_list_open", "ordered_list_open"):
            start = token.attrGet("start") if kind == "ordered_list_open" else None
            lists.append(_List(kind == "ordered_list_open", int(start or 1) - 1))
        elif kind in ("bullet_list_close", "ordered_list_close"):
            if lists:
                lists.pop()
        elif kind == "list_item_open" and lists:
            current = lists[-1]
            current.number += 1
            prefix = f"{current.number}. " if current.ordered else "• "
        elif kind == "list_item_close":
            prefix = None
        elif kind == "tr_open":
            row = []
        elif kind == "tr_close" and row is not None:
            paragraphs.append(_joined(row, " | "))
            row = None
        elif kind == "inline":
            segments = _inline_segments(token, cites)
            if row is not None:
                row.append(segments)
                continue
            if prefix is not None:
                segments = _merge([{"text": prefix}, *segments])
                prefix = None
            paragraphs.append(segments)
        elif kind in ("fence", "code_block") or (
            kind == "html_block" and not _COMMENT_RE.match(token.content)
        ):
            paragraphs.append([{"text": token.content}])
    return [trimmed for trimmed in (_trim(paragraph) for paragraph in paragraphs) if trimmed]


def _lead(body: str, cites: Collection[int]) -> tuple[list[str], list[list[Segment]]]:
    """Banners and paragraphs: the body before its first ``##`` section, without the ``# Title``
    line and the fictional-sample notice."""
    lines = strip_backlinks_block(body).split("\n")
    text = "\n".join("" if FOOTNOTE_DEF_RE.match(line) else line for line in lines)
    banners: list[str] = []
    paragraphs: list[list[Segment]] = []
    for block in _blocks(markdown_parser().parse(text)):
        first = block[0]
        if first.type == "heading_open" and first.tag == "h2":
            break
        if first.type == "heading_open" and first.tag == "h1":
            continue
        inner = _paragraphs(block, cites)
        if first.type == "blockquote_open":
            notice = " ".join(_plain(paragraph) for paragraph in inner)
            kind = notice_kind(notice)
            if kind == "fictional":
                continue
            if kind is not None:
                banners.append(notice)
                continue
        paragraphs.extend(inner)
    return banners, paragraphs


def _production(body: str) -> tuple[list[str], str]:
    """``(steps, provenance)`` of the "How this answer was produced" section: its bullet items,
    and the paragraphs directly under its heading as plain text; ``([], "")`` without one."""
    wanted = HOW_HEADING.casefold()
    for section in split_sections(strip_backlinks_block(body)):
        if section.level != 2 or (section.heading or "").strip().casefold() != wanted:
            continue
        tokens = markdown_parser().parse(section.markdown)
        notes: list[str] = []
        for block in _blocks(tokens):
            if block[0].type != "paragraph_open":
                break
            notes += [
                _plain(_inline_segments(token, ())) for token in block if token.type == "inline"
            ]
        steps: list[str] = []
        taken: list[bool] = []
        for token in tokens:
            if token.type == "list_item_open":
                taken.append(False)
            elif token.type == "list_item_close" and taken:
                taken.pop()
            elif token.type == "inline" and taken and not taken[-1]:
                taken[-1] = True
                step = _step_text(token)
                if step:
                    steps.append(step)
        return steps, " ".join(note for note in notes if note)
    return [], ""


def _citations(page: Page) -> list[AnswerCitation]:
    """Contract footnotes ``[^cN]`` of a page, by number (the first definition of a label)."""
    _, definitions = extract_footnotes(page.body)
    found: dict[int, AnswerCitation] = {}
    for definition in definitions:
        label = _CITE_LABEL_RE.match(definition.label)
        if label is None:
            continue
        match = CITATION_RE.match(definition.content)
        if match is None:
            raise SiteBuildError(
                f"{page.path}: footnote [^{definition.label}] is not a citation "
                "'[<title> — <label>](<sidecar>) · <badge>'"
            )
        resolved = resolve_href(page.path, match.group("href"))
        target = resolved.path or ""
        if (
            resolved.error
            or not target.startswith(f"{EVIDENCE_MOUNT}/")
            or not target.endswith(".md")
        ):
            raise SiteBuildError(
                f"{page.path}: citation [^{definition.label}] does not open an evidence "
                f"sidecar: {match.group('href')!r}"
            )
        number = int(label.group(1))
        anchor = f"#{resolved.anchor}" if resolved.anchor else ""
        found.setdefault(
            number,
            {
                "n": number,
                "title": _inline_plain(match.group("title")),
                "label": _inline_plain(match.group("label")),
                "href": target.removesuffix(".md") + anchor,
                "badge": match.group("badge").strip(),
            },
        )
    return [found[number] for number in sorted(found)]


def _slug(path: str) -> str:
    return path.removesuffix(".md")


def _context_pages(
    slug: str,
    sources: Sequence[str],
    citations: Sequence[AnswerCitation],
    catalog: Catalog,
) -> list[str]:
    """The answer's page, its evidence, its source pages, then their topic and entity pages."""
    by_id = catalog.page_by_id()
    source_pages = [
        by_id[source_id]
        for source_id in sources
        if source_id in by_id and by_id[source_id].type == "source"
    ]
    pages = [slug, *(citation["href"].partition("#")[0] for citation in citations)]
    pages += [_slug(page.path) for page in source_pages]
    topics = [topic for page in source_pages for topic in page.topics]
    entities = [entity for page in source_pages for entity in page.entities]
    pages += [_slug(by_id[ref].path) for ref in (*topics, *entities) if ref in by_id]
    return list(dict.fromkeys(pages))


def query_pages(wiki_dir: Path) -> list[Page]:
    """Pages of ``queries/`` (``queries/index.md`` excluded), by path."""
    folder = wiki_dir / QUERIES_DIR
    if not folder.is_dir():
        return []
    pages: list[Page] = []
    for file in sorted(folder.glob("*.md")):
        rel = f"{QUERIES_DIR}/{file.name}"
        if rel == WikiFiles.QUERIES_INDEX or file.name.startswith(".") or not file.is_file():
            continue
        try:
            pages.append(Page.parse(file.read_text(encoding="utf-8"), rel))
        except ValueError as exc:
            raise SiteBuildError(f"{rel} is not a valid query page: {exc}") from exc
    return pages


def answer_for_page(page: Page, catalog: Catalog) -> Answer:
    """The drawer's record of one query page; ``catalog`` maps its sources to their pages."""
    frontmatter = page.frontmatter
    if not isinstance(frontmatter, QueryFrontmatter):
        raise SiteBuildError(f"{page.path}: a {frontmatter.type} page in {QUERIES_DIR}/")
    citations = _citations(page)
    banners, paragraphs = _lead(page.body, {citation["n"] for citation in citations})
    steps, provenance = _production(page.body)
    slug = _slug(page.path)
    return {
        "id": frontmatter.id,
        "slug": slug,
        "question": " ".join(frontmatter.question.split()),
        "date": frontmatter.updated.isoformat(),
        "banners": banners,
        "paragraphs": paragraphs,
        "citations": citations,
        "steps": steps,
        "provenance": provenance,
        "pages": _context_pages(slug, frontmatter.sources, citations, catalog),
    }


def build_answers(release: ReleaseView) -> AnswersPayload:
    """``answers.json`` of a release: its query pages, newest first, then by question."""
    answers = [answer_for_page(page, release.catalog) for page in query_pages(release.wiki_dir)]
    answers.sort(key=lambda answer: (answer["question"].casefold(), answer["id"]))
    answers.sort(key=lambda answer: answer["date"], reverse=True)
    return {"schema": ANSWERS_SCHEMA, "release": release.release_id, "answers": answers}


def write_answers(payload: AnswersPayload, quartz_dir: Path) -> Path:
    """Write ``answers.json`` into a Quartz checkout (UTF-8, LF); returns the file."""
    target = quartz_dir / ANSWERS_QUARTZ_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    target.write_bytes(text.encode("utf-8"))
    return target
