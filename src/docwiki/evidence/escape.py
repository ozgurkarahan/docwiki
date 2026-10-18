"""Rendering untrusted document text as inert Markdown.

Document text is data: it must never become a link, raw HTML, a heading, a list, a table, a
footnote, a tag, a comment or math when a sidecar is rendered by GitHub, Quartz or Obsidian.
Markdown-significant characters are backslash-escaped (``<`` and ``>`` become ``&lt;`` and
``&gt;``), URLs and e-mail addresses become code spans (not clickable), line-start constructs
are neutralised, and the result goes through :func:`docwiki.contracts.sanitize_markdown` as a
last line of defence (escaped text is a fixed point of it).
"""

from __future__ import annotations

import re

from docwiki.contracts import sanitize_markdown
from docwiki.extract._text import clean_text, one_line

__all__ = ["escape_text", "plain_text", "quote_block", "table_cell"]

_LINK_LIKE_RE = re.compile(
    r"(?:[A-Za-z][A-Za-z0-9+.\-]*://|www\.)[^\s<>`|()\[\]]*"
    r"|[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+"
)
# CommonMark punctuation with a meaning here, plus Obsidian/Quartz extensions: # tags, ^ block
# ids, $ math. "%", "=" and "&" only matter as "%%" comments, "==" highlights / setext
# underlines and entity references, so they are escaped only in those positions.
_ALWAYS = frozenset("\\`*_[]|~$#^")
_ENTITIES = {"<": "&lt;", ">": "&gt;"}
_ENTITY_RE = re.compile(r"&(?:#[0-9]{1,7}|#[xX][0-9A-Fa-f]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});")
_ORDERED_RE = re.compile(r"^(\d{1,9})([.)])")


def _code(value: str) -> str:
    fence = "``" if "`" in value else "`"
    pad = " " if value.startswith("`") or value.endswith("`") else ""
    return f"{fence}{pad}{value}{pad}{fence}"


def _escape_chars(text: str, *, line_start: bool) -> str:
    out: list[str] = []
    for index, char in enumerate(text):
        before, after = text[index - 1 : index], text[index + 1 : index + 2]
        if char in _ENTITIES:
            out.append(_ENTITIES[char])
        elif (
            char in _ALWAYS
            or (char == "%" and "%" in (before, after))
            or (char == "=" and ("=" in (before, after) or (line_start and index == 0)))
            or (char == "&" and _ENTITY_RE.match(text, index))
        ):
            out.append("\\" + char)
        else:
            out.append(char)
    return "".join(out)


def _escape_line(line: str) -> str:
    line = line.lstrip()
    out: list[str] = []
    position = 0
    for match in _LINK_LIKE_RE.finditer(line):
        out.append(_escape_chars(line[position : match.start()], line_start=position == 0))
        out.append(_code(match.group(0)))
        position = match.end()
    out.append(_escape_chars(line[position:], line_start=position == 0))
    escaped = "".join(out)
    if escaped[:1] in ("-", "+"):
        escaped = "\\" + escaped
    return _ORDERED_RE.sub(r"\1\\\2", escaped)


def escape_text(text: str) -> str:
    """Escape document text for inline use (line breaks kept as separate lines)."""
    lines = [_escape_line(line) for line in clean_text(text).split("\n")]
    return "\n".join(lines)


def table_cell(text: str) -> str:
    """One GFM table cell: a single escaped line."""
    return _escape_line(one_line(text))


def quote_block(text: str) -> list[str]:
    """Blockquote lines for a block's text, keeping its line breaks (hard breaks)."""
    lines = [line for line in escape_text(text).split("\n") if line.strip()]
    if not lines:
        return []
    return [f"> {line}\\" for line in lines[:-1]] + [f"> {lines[-1]}"]


def plain_text(text: str, *, max_len: int = 300) -> str:
    """A single inert line for frontmatter values and titles (tags and brackets dropped)."""
    value = one_line(text)
    value = re.sub(r"<[^<>]*>", "", value)
    value = re.sub(r"[<>\[\]`\\|]", "", value)
    value = _LINK_LIKE_RE.sub(lambda match: _code(match.group(0)), value)
    value = sanitize_markdown(value, allow_markers=False)[0].replace("\n", " ").strip()
    if len(value) > max_len:
        value = value[:max_len].rstrip() + "…"
    return value
