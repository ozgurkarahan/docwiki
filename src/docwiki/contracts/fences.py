"""Fenced code blocks (CommonMark §4.5), tracked line by line.

Citation verification, section rendering, link insertion, the release validator's footnote scan,
Markdown sanitisation and injection neutralisation all share this one tracker so that they always
agree on which lines are code (a ``[[cite:…]]`` marker is verified and rendered only outside code,
and only text outside code is sanitised as prose):

* an opening fence is a run of at least three backticks or tildes indented by at most three
  spaces; its info string may follow, but after backticks it may not contain a backtick;
* the block is closed only by a fence of the same character that is at least as long as the
  opening one, indented by at most three spaces and followed by nothing but spaces or tabs (a
  shorter run, the other character or a fence with an info string is code);
* a block that is never closed runs to the end of the text.

Container blocks are not modelled: a fence written after a list or block-quote marker (on the
same line as ``-`` or ``>``) is read as text by every stage alike.

Simpler Markdown parsers in other tools open a block on any line starting with a fence run and
close it on any long-enough run of the same character. :func:`escape_fence` and
:func:`widen_fences` rewrite generated Markdown so that both readings give the same blocks
without changing how it displays.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

__all__ = ["FenceTracker", "closes_fence", "escape_fence", "opening_fence", "widen_fences"]

_OPENING_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
_CLOSING_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})[ \t]*$")
_FENCE_LIKE_RE = re.compile(r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})")


def opening_fence(line: str) -> str | None:
    """The fence run (``"```"``, ``"~~~~"``…) when ``line`` opens a fenced code block."""
    match = _OPENING_RE.match(line)
    if match is None:
        return None
    fence = match.group("fence")
    if fence[0] == "`" and "`" in match.group("info"):
        return None
    return fence


def closes_fence(line: str, opener: str) -> bool:
    """True when ``line`` closes the block opened by the fence run ``opener``."""
    match = _CLOSING_RE.match(line)
    if match is None:
        return False
    fence = match.group("fence")
    return fence[0] == opener[0] and len(fence) >= len(opener)


class FenceTracker:
    """Feed every line in order; :meth:`feed` says whether the line is part of a fenced block.

    ``opener`` is the fence run of the open block (``None`` outside code).
    """

    def __init__(self) -> None:
        self.opener: str | None = None

    @property
    def inside(self) -> bool:
        """True while a fenced block is open."""
        return self.opener is not None

    def feed(self, line: str) -> bool:
        """Advance over ``line``: True for the lines of a fenced block, fence lines included."""
        if self.opener is None:
            self.opener = opening_fence(line)
            return self.opener is not None
        if closes_fence(line, self.opener):
            self.opener = None
        return True


def escape_fence(line: str) -> str:
    """A text line that starts like a fence, made text for every parser (same display).

    A backslash goes before the fence run: three backticks followed by an info string holding a
    backtick are text in CommonMark but an opening fence for simpler parsers, and editing a text
    line (dropping a sentence or a footnote reference) can leave it starting with a fence run.
    Lines that do not start like a fence are returned unchanged; never pass code-block lines.
    """
    match = _FENCE_LIKE_RE.match(line)
    if match is None:
        return line
    return f"{match.group('indent')}\\{line[match.end('indent') :]}"


def widen_fences(lines: Sequence[str]) -> list[str]:
    """``lines`` with each code block's fences made longer than the fence-like lines it holds.

    Inside a block opened by three backticks, a line of three backticks followed by an info
    string is code in CommonMark (a closing fence has no info string) but closes the block for
    simpler parsers; lengthening the opening and closing fences of that block removes the
    ambiguity. The code itself is not changed.
    """
    result = list(lines)
    tracker = FenceTracker()
    start = 0
    longest = 0
    for number, line in enumerate(lines):
        opener = tracker.opener
        tracker.feed(line)
        if opener is None:
            if tracker.opener is not None:
                start, longest = number, 0
            continue
        if tracker.opener is not None:
            match = _FENCE_LIKE_RE.match(line)
            run = match.group("fence") if match else ""
            if run[:1] == opener[0] and len(run) >= len(opener):
                longest = max(longest, len(run))
            continue
        if longest:
            result[start] = _resize(lines[start], longest + 1)
            result[number] = _resize(lines[number], longest + 1)
    if tracker.opener is not None and longest:
        result[start] = _resize(lines[start], longest + 1)
    return result


def _resize(line: str, width: int) -> str:
    match = _FENCE_LIKE_RE.match(line)
    assert match is not None
    fence = match.group("fence")
    return f"{match.group('indent')}{fence[0] * width}{line[match.end('fence') :]}"
