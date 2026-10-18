"""Markdown structure helpers: heading anchors, links, footnotes, sections and plain text.

Parsing uses markdown-it-py (CommonMark + GFM tables/strikethrough) so link detection matches what
renderers produce. Footnotes are handled by small regexes because the canonical wiki only uses
single-line footnote definitions ``[^cN]: …``.
"""

from __future__ import annotations

import posixpath
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import unquote

from markdown_it import MarkdownIt
from markdown_it.token import Token

from docwiki.contracts.fences import FenceTracker

__all__ = [
    "BACKLINKS_END",
    "BACKLINKS_START",
    "FootnoteDef",
    "Heading",
    "MdLink",
    "ResolvedHref",
    "Section",
    "Slugger",
    "extract_footnotes",
    "extract_headings",
    "extract_links",
    "heading_anchor",
    "markdown_parser",
    "markdown_to_text",
    "relative_link",
    "resolve_href",
    "split_sections",
    "strip_backlinks_block",
]

BACKLINKS_START = "<!-- docwiki:backlinks:start -->"
BACKLINKS_END = "<!-- docwiki:backlinks:end -->"

FOOTNOTE_DEF_RE = re.compile(r"^\[\^(?P<label>[^\]\s]+)\]:[ \t]?(?P<content>.*)$")
FOOTNOTE_REF_RE = re.compile(r"\[\^(?P<label>[^\]\s]+)\](?!:)")
_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:")


@lru_cache(maxsize=1)
def markdown_parser() -> MarkdownIt:
    """Shared parser: CommonMark with raw HTML tokenised (never rendered by us) + GFM tables.

    ``validateLink`` accepts every URL so that unsafe schemes (``javascript:``…) still produce
    link tokens and can be reported instead of silently degrading to text.
    """
    parser = MarkdownIt("commonmark", {"html": True}).enable(["table", "strikethrough"])
    parser.validateLink = lambda url: True  # type: ignore[method-assign]
    return parser


def heading_anchor(text: str) -> str:
    """GitHub/Quartz (github-slugger) anchor of a heading text, without de-duplication.

    Lower-cases, removes every character that is not a letter, mark, number, connector
    punctuation, ``-`` or space, then turns each space into ``-``. Identical to GitHub for ASCII
    headings (``Page 12`` → ``page-12``).
    """
    out: list[str] = []
    for char in text.strip().lower():
        if char == " ":
            out.append("-")
        elif char in "-_":
            out.append(char)
        elif char.isascii():
            if char.isalnum():
                out.append(char)
        elif unicodedata.category(char)[0] in "LMN" or unicodedata.category(char) == "Pc":
            out.append(char)
    return "".join(out)


class Slugger:
    """Per-document anchor generator with github-slugger de-duplication (``x``, ``x-1``…)."""

    def __init__(self) -> None:
        self._occurrences: dict[str, int] = {}

    def slug(self, text: str) -> str:
        result = heading_anchor(text)
        original = result
        while result in self._occurrences:
            self._occurrences[original] += 1
            result = f"{original}-{self._occurrences[original]}"
        self._occurrences[result] = 0
        return result


@dataclass(frozen=True)
class Heading:
    level: int
    text: str
    anchor: str
    line: int
    """1-based line number in the parsed text."""


@dataclass(frozen=True)
class MdLink:
    href: str
    text: str
    line: int
    image: bool = False
    autolink: bool = False


@dataclass(frozen=True)
class FootnoteDef:
    label: str
    content: str
    line: int


@dataclass(frozen=True)
class Section:
    level: int
    heading: str | None
    anchor: str | None
    markdown: str
    line_start: int
    line_end: int


def _inline_text(token: Token) -> str:
    parts: list[str] = []
    for child in token.children or []:
        if child.type in ("text", "code_inline"):
            parts.append(child.content)
        elif child.type in ("softbreak", "hardbreak"):
            parts.append(" ")
    return "".join(parts)


def _mask_code_lines(lines: list[str]) -> list[bool]:
    """True for lines inside fenced code blocks (fence lines included), CommonMark rules."""
    tracker = FenceTracker()
    return [tracker.feed(line) for line in lines]


def extract_footnotes(markdown: str) -> tuple[list[tuple[str, int]], list[FootnoteDef]]:
    """Return ``(references, definitions)``; references are ``(label, line)`` in order of use."""
    refs: list[tuple[str, int]] = []
    defs: list[FootnoteDef] = []
    lines = markdown.split("\n")
    for number, (line, in_code) in enumerate(zip(lines, _mask_code_lines(lines), strict=True), 1):
        if in_code:
            continue
        match = FOOTNOTE_DEF_RE.match(line)
        if match:
            defs.append(FootnoteDef(match.group("label"), match.group("content"), number))
            continue
        for ref in FOOTNOTE_REF_RE.finditer(_strip_code_spans(line)):
            refs.append((ref.group("label"), number))
    return refs, defs


def _strip_code_spans(line: str) -> str:
    return re.sub(r"(`+)(?:(?!\1).)+?\1", lambda m: " " * len(m.group(0)), line)


def _prepare(markdown: str) -> str:
    """Unwrap footnote definitions so their content is parsed as ordinary inline Markdown."""
    lines = markdown.split("\n")
    masked = _mask_code_lines(lines)
    out: list[str] = []
    for line, in_code in zip(lines, masked, strict=True):
        if not in_code:
            match = FOOTNOTE_DEF_RE.match(line)
            if match:
                line = match.group("content")
        out.append(line)
    return "\n".join(out)


def extract_headings(markdown: str) -> list[Heading]:
    """Headings (ATX and setext) with de-duplicated anchors, in document order."""
    tokens = markdown_parser().parse(_prepare(markdown))
    slugger = Slugger()
    headings: list[Heading] = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            text = _inline_text(tokens[index + 1])
            line = (token.map[0] + 1) if token.map else 0
            headings.append(Heading(int(token.tag[1]), text.strip(), slugger.slug(text), line))
    return headings


def extract_links(markdown: str) -> list[MdLink]:
    """Every link and image the renderer would produce (inline, reference, autolink)."""
    tokens = markdown_parser().parse(_prepare(markdown))
    links: list[MdLink] = []
    for block in tokens:
        if block.type != "inline" or not block.children:
            continue
        line = (block.map[0] + 1) if block.map else 1
        children = block.children
        for index, child in enumerate(children):
            if child.type in ("softbreak", "hardbreak"):
                line += 1
            elif child.type == "link_open":
                text_parts: list[str] = []
                for follower in children[index + 1 :]:
                    if follower.type == "link_close":
                        break
                    if follower.type in ("text", "code_inline"):
                        text_parts.append(follower.content)
                links.append(
                    MdLink(
                        href=str(child.attrGet("href") or ""),
                        text="".join(text_parts),
                        line=line,
                        autolink=child.markup in ("autolink", "linkify"),
                    )
                )
            elif child.type == "image":
                links.append(
                    MdLink(
                        href=str(child.attrGet("src") or ""),
                        text=child.content,
                        line=line,
                        image=True,
                    )
                )
    return links


def strip_backlinks_block(markdown: str) -> str:
    """Remove the generated backlinks block (markers included)."""
    pattern = re.compile(re.escape(BACKLINKS_START) + r".*?" + re.escape(BACKLINKS_END), re.DOTALL)
    return pattern.sub("", markdown)


def split_sections(markdown: str) -> list[Section]:
    """Split a body into sections at every heading; text before the first heading is level 0."""
    lines = markdown.split("\n")
    headings = extract_headings(markdown)
    sections: list[Section] = []
    starts = [heading.line for heading in headings]
    if not headings or starts[0] > 1:
        first_end = (starts[0] - 1) if headings else len(lines)
        sections.append(Section(0, None, None, "\n".join(lines[:first_end]), 1, first_end))
    for position, heading in enumerate(headings):
        end = starts[position + 1] - 1 if position + 1 < len(headings) else len(lines)
        content_start = heading.line  # the heading line itself is excluded from markdown
        if content_start < len(lines) and re.match(r"^ {0,3}(=+|-+)\s*$", lines[content_start]):
            content_start += 1  # setext underline
        sections.append(
            Section(
                heading.level,
                heading.text,
                heading.anchor,
                "\n".join(lines[content_start:end]),
                heading.line,
                end,
            )
        )
    return sections


def markdown_to_text(markdown: str) -> str:
    """Plain text for search/snippets: no markup, footnotes, HTML or backlinks block."""
    lines = strip_backlinks_block(markdown).split("\n")
    masked = _mask_code_lines(lines)
    kept = [
        line if in_code else FOOTNOTE_REF_RE.sub("", line)
        for line, in_code in zip(lines, masked, strict=True)
        if in_code or not FOOTNOTE_DEF_RE.match(line)
    ]
    tokens = markdown_parser().parse("\n".join(kept))
    chunks: list[str] = []
    for token in tokens:
        if token.type == "inline":
            parts: list[str] = []
            for child in token.children or []:
                if child.type in ("text", "code_inline"):
                    parts.append(child.content)
                elif child.type in ("softbreak", "hardbreak"):
                    parts.append(" ")
                elif child.type == "image":
                    parts.append(child.content)
            text = "".join(parts).strip()
            if text:
                chunks.append(text)
        elif token.type in ("fence", "code_block"):
            chunks.append(token.content.strip())
    return "\n".join(chunk for chunk in chunks if chunk)


@dataclass(frozen=True)
class ResolvedHref:
    """Result of resolving a link found on a page of the content namespace."""

    path: str | None
    anchor: str | None
    external: bool = False
    scheme: str | None = None
    error: str | None = None


def _check_ns_path(path: str, what: str) -> str:
    if not path or path.startswith("/") or "\\" in path:
        raise ValueError(f"{what} must be a relative POSIX path: {path!r}")
    if any(part in ("", ".", "..") for part in path.split("/")):
        raise ValueError(f"{what} must be normalised (no '.', '..' or empty segments): {path!r}")
    return path


def relative_link(from_path: str, to_path: str) -> str:
    """Relative link from page ``from_path`` to ``to_path`` (both in the content namespace).

    ``to_path`` may carry an ``#anchor``. Example: ``sources/a.md`` → ``evidence/src-x/p0003.md``
    gives ``../evidence/src-x/p0003.md``.
    """
    target, sep, anchor = to_path.partition("#")
    _check_ns_path(from_path, "from_path")
    _check_ns_path(target, "to_path")
    start = posixpath.dirname(from_path) or "."
    rel = posixpath.relpath(target, start)
    return f"{rel}#{anchor}" if sep else rel


def resolve_href(from_path: str, href: str) -> ResolvedHref:
    """Resolve ``href`` found on ``from_path`` into a content-namespace path and anchor."""
    _check_ns_path(from_path, "from_path")
    if not href:
        return ResolvedHref(None, None, error="empty link")
    if href.startswith("//"):
        return ResolvedHref(None, None, external=True, scheme="", error="protocol-relative URL")
    scheme_match = _SCHEME_RE.match(href)
    if scheme_match:
        scheme = scheme_match.group(0)[:-1].lower()
        return ResolvedHref(None, None, external=True, scheme=scheme, error=f"{scheme}: link")
    target, sep, anchor = href.partition("#")
    anchor_value = unquote(anchor) if sep else None
    if not target:
        return ResolvedHref(from_path, anchor_value)
    if target.startswith("/"):
        return ResolvedHref(None, anchor_value, error="absolute path link")
    if "?" in target:
        return ResolvedHref(None, anchor_value, error="query strings are not allowed in links")
    decoded = unquote(target)
    joined = posixpath.normpath(posixpath.join(posixpath.dirname(from_path), decoded))
    if joined == ".." or joined.startswith("../") or joined.startswith("/"):
        return ResolvedHref(None, anchor_value, error="link escapes the content root")
    return ResolvedHref(joined, anchor_value)
