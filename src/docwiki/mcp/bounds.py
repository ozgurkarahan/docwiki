"""Size-bounded JSON tool results (spec: default 12k characters, ``truncated`` flag, paging).

Every tool builds a JSON-serialisable payload and hands it to one of the fitting helpers:

* :func:`fit_text` returns the largest window ``text[offset:end]`` whose payload fits, cutting at
  a line break when possible and reporting ``next_offset`` for the following call;
* :func:`fit_items` returns the longest prefix of a list whose payload fits.

The measure is the length of the compact JSON text actually sent to the client. Successful
results start with ``"ok": true`` (:func:`result_json`); failures are built by
:mod:`docwiki.mcp.errors`.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any

__all__ = ["ResultTooLargeError", "clip", "dumps", "fit_items", "fit_text", "result_json"]


class ResultTooLargeError(RuntimeError):
    """Even the smallest possible payload exceeds the output budget."""


def _default(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    if isinstance(value, set | frozenset):
        return sorted(value)
    return str(value)


def dumps(payload: Any) -> str:
    """Compact JSON (UTF-8 characters kept) used for every tool result."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=_default)


def result_json(payload: dict[str, Any]) -> str:
    """JSON of a successful result: ``{"ok": true, ...payload}`` (``ok`` first)."""
    return dumps({"ok": True, **payload} if "ok" not in payload else payload)


def clip(text: str | None, limit: int) -> str | None:
    """``text`` shortened to ``limit`` characters with an ellipsis (``None`` stays ``None``)."""
    if text is None or len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def fit_text(
    text: str,
    offset: int,
    build: Callable[[str, int | None], dict[str, Any]],
    max_chars: int,
) -> str:
    """JSON of ``build(window, next_offset)`` for the largest window starting at ``offset``.

    ``next_offset`` is ``None`` when the window reaches the end of ``text``. The window is cut at
    a line break when one exists in its second half, so paged Markdown stays readable. A window
    always makes progress: when not even one character fits, :class:`ResultTooLargeError`.
    """
    total = len(text)
    start = min(max(offset, 0), total)
    end = total
    while True:
        window = text[start:end]
        out = result_json(build(window, end if end < total else None))
        if len(out) <= max_chars:
            return out
        if end - start <= 1:
            raise ResultTooLargeError("the result does not fit in the output budget")
        overflow = len(out) - max_chars
        target = max(start + 1, end - max(overflow, (end - start) // 20, 1))
        cut = text.rfind("\n", start, target)
        end = cut + 1 if cut >= start + (target - start) // 2 else target


def fit_items[T](
    items: Sequence[T],
    build: Callable[[Sequence[T], bool], dict[str, Any]],
    max_chars: int,
) -> tuple[str, int]:
    """``(json, count)`` for the longest prefix of ``items`` whose payload fits.

    ``build(prefix, truncated)`` must produce the payload; ``truncated`` tells it whether items
    were dropped (so it can set ``truncated`` and ``next_offset``).
    """
    out = result_json(build(items, False))
    if len(out) <= max_chars:
        return out, len(items)
    low, high = 0, len(items) - 1
    best: str | None = None
    best_count = 0
    while low <= high:
        middle = (low + high) // 2
        candidate = result_json(build(items[:middle], True))
        if len(candidate) <= max_chars:
            best, best_count = candidate, middle
            low = middle + 1
        else:
            high = middle - 1
    if best is None:
        raise ResultTooLargeError("the result does not fit in the output budget")
    return best, best_count
