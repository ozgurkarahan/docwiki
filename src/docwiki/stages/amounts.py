"""Amounts in euros written the French trade way (v1.7, slice D): ``2 390,00 € HT``.

The compile prompts copy amounts exactly as printed (``2390,00 €``), so the citation checks can
compare them with the documents; this deterministic pass then groups the thousands with a narrow
no-break space, keeps the euro sign on the same line and writes ``HT`` / ``TTC`` instead of
"excluding VAT" / "including VAT". Quotes from the documents, tables, footnote definitions and
code are left exactly as they are. The citation checks read these separators as part of the
number (``verify_citations`` drops narrow and ordinary no-break spaces).
"""

from __future__ import annotations

import re
from decimal import Decimal

from docwiki.contracts import Page

__all__ = ["format_amounts", "format_number", "format_page_amounts"]

THIN = " "
"""Narrow no-break space: the thousands separator."""
NBSP = " "

_AMOUNT_RE = re.compile(r"(?<![\d.,\w])(\d{4,})(,\d{1,2})?[   ]?€")
_VAT_RE = re.compile(
    r"€[  ]*(?:\(\s*)?(excluding|excl\.?|including|incl\.?) VAT(?:\s*\))?",
    re.IGNORECASE,
)
_SKIP_PREFIXES = (">", "|", "[^", "    ", "\t")


def _group(digits: str) -> str:
    head = len(digits) % 3 or 3
    parts = [digits[:head], *(digits[i : i + 3] for i in range(head, len(digits), 3))]
    return THIN.join(parts)


def _vat(match: re.Match[str]) -> str:
    word = match.group(1).lower()
    return f"€{NBSP}{'HT' if word.startswith('excl') else 'TTC'}"


def format_number(value: Decimal, *, unit: str | None = None) -> str:
    """A number computed by code, the French way: ``Decimal("12390.50")`` → ``12 390,50``
    (thousands grouped with a narrow no-break space, comma decimals, the value's own decimal
    places); ``unit`` follows after a no-break space (``12 390,50 € HT``)."""
    text = format(value, "f")
    sign = "-" if text.startswith("-") else ""
    digits, _, decimals = text.lstrip("-").partition(".")
    number = sign + _group(digits) + (f",{decimals}" if decimals else "")
    return f"{number}{NBSP}{unit}" if unit else number


def format_amounts(text: str) -> str:
    """``2390,00 € excluding VAT`` → ``2 390,00 € HT`` (one line of prose)."""
    text = _VAT_RE.sub(_vat, text)
    return _AMOUNT_RE.sub(lambda m: f"{_group(m.group(1))}{m.group(2) or ''}{NBSP}€", text)


def format_page_amounts(page: Page) -> Page:
    """The page with its prose amounts formatted; quotes, tables, footnote definitions and code
    blocks unchanged. The summary is formatted too (indexes and search show it)."""
    lines: list[str] = []
    fenced = False
    for line in page.body.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fenced = not fenced
            lines.append(line)
            continue
        if fenced or line.startswith(_SKIP_PREFIXES) or "€" not in line:
            lines.append(line)
            continue
        lines.append(format_amounts(line))
    body = "\n".join(lines)
    summary = page.frontmatter.summary
    new_summary = format_amounts(summary) if summary and "€" in summary else summary
    if body == page.body and new_summary == summary:
        return page
    frontmatter = page.frontmatter.model_copy(update={"summary": new_summary})
    return Page(path=page.path, frontmatter=frontmatter, body=body)
