"""Markdown and plain text: blocks are runs of consecutive non-empty lines (``text-lines``).

Markdown ATX headings (``# Title``) become their own ``heading`` blocks. Line numbers are the
1-based physical lines of the decoded file.
"""

from __future__ import annotations

import re

from docwiki.contracts.enums import BlockKind
from docwiki.contracts.locators import TextLinesLocator
from docwiki.extract._draft import Draft
from docwiki.extract._text import BULLET_RE, decode_text, normalize_lines, one_line

__all__ = ["extract_text"]

_ATX_RE = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def extract_text(data: bytes, draft: Draft, *, markdown: bool) -> None:
    text, encoding = decode_text(data)
    if encoding == "cp1252":
        draft.warn("encoding", "the file is not valid UTF-8; decoded as Windows-1252")
    lines = normalize_lines(text)
    in_fence = False
    run: list[int] = []

    def flush() -> None:
        if not run:
            return
        start, end = run[0], run[-1]
        body = "\n".join(lines[start - 1 : end]).strip()
        kind: BlockKind = "list" if BULLET_RE.match(body) else "paragraph"
        draft.block(kind, body, TextLinesLocator(line_start=start, line_end=end), "native-text")
        run.clear()

    for number, line in enumerate(lines, 1):
        if markdown and _FENCE_RE.match(line):
            in_fence = not in_fence
        heading = None if (in_fence or not markdown) else _ATX_RE.match(line)
        if heading:
            flush()
            title = one_line(heading[2] or "")
            if title:
                level = len(heading[1])
                locator = TextLinesLocator(line_start=number, line_end=number)
                draft.block("heading", title, locator, "native-text", level=level)
                if level == 1 and draft.title_hint is None:
                    draft.title_hint = title
            continue
        if line.strip():
            run.append(number)
        else:
            flush()
    flush()
    if not draft.items:
        draft.warn("empty", "the file has no text")
