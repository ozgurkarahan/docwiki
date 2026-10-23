"""Amounts in euros written the French trade way (v1.7, slice D): ``2 390,00 € HT``.

The compile prompts copy amounts exactly as printed (``2390,00 €``), so the citation checks can
compare them with the documents; this deterministic pass then groups the thousands with a narrow
no-break space, keeps the euro sign on the same line and writes ``HT`` / ``TTC`` instead of
"excluding VAT" / "including VAT". A number written straight before ``HT`` or ``TTC`` is an
amount too, with or without the euro sign (``2390 HT`` and ``4386.5 HT`` become ``2 390,00 € HT``
and ``4 386,50 € HT``), except a year (``2026 HT``, without decimals or euro sign), a lot,
revision or document number (``lot 5 HT``, ``BC-2026-009 TTC``) or a percentage. Quotes from the
documents (blockquotes, quoted text), tables, footnote markers and definitions, links and code
are left exactly as they are. The citation checks read these separators as part of the
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
_SPACE = "[   ]"
_VAT_AMOUNT_RE = re.compile(
    r"(?<![\w.,/#^€  -])(\d+)(?:[.,](\d{1,2}))?(?![\d.,])"
    rf"{_SPACE}?(€{_SPACE}?)?(HT|TTC)(?!\w)"
)
"""A number written straight before ``HT`` / ``TTC`` (decimals after a comma or a point)."""
_NUMBER_PREFIX_RE = re.compile(
    rf"(?:\b(?:lot|indice|rev|n°|nº|no|nr)\.?|\d{_SPACE}){_SPACE}*$", re.IGNORECASE
)
"""Text before a number that makes it a lot, revision or document number, or the tail of a number
already grouped with spaces: never an amount to format."""
_PROTECTED_RE = re.compile(
    r"(`+)(?:(?!\1).)+?\1"
    r"|!?\[(?:[^\[\]\\]|\\.|\[(?:[^\[\]\\]|\\.)*\])*\](?:\([^)\n]*\)|\[[^\]\n]*\])"
    r"|\[\^[^\]\s]+\]"
    r"|<[^>\n]*>"
    r'|"[^"\n]*"|“[^”\n]*”|«[^»\n]*»'
)
"""Code spans, links, footnote markers, autolinks and quoted text: kept exactly as written."""
_HAS_AMOUNT_RE = re.compile(rf"€|\d{_SPACE}?(?:HT|TTC)(?!\w)")


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


def _vat_amount(match: re.Match[str]) -> str:
    digits, decimals, euro, vat = match.groups()
    if _NUMBER_PREFIX_RE.search(match.string[: match.start()]):
        return match.group(0)
    if not decimals and not euro and len(digits) == 4 and 1900 <= int(digits) <= 2100:
        return match.group(0)  # a year (``tarif 2026 HT``), not an amount
    if len(digits) > 1 and digits.startswith("0"):
        return match.group(0)  # a code (``0158``), not an amount
    cents = (decimals or "").ljust(2, "0")
    return f"{_group(digits)},{cents}{NBSP}€{NBSP}{vat}"


def _format_prose(text: str) -> str:
    text = _VAT_RE.sub(_vat, text)
    text = _VAT_AMOUNT_RE.sub(_vat_amount, text)
    return _AMOUNT_RE.sub(lambda m: f"{_group(m.group(1))}{m.group(2) or ''}{NBSP}€", text)


def format_amounts(text: str) -> str:
    """``2390,00 € excluding VAT`` and ``2390 HT`` → ``2 390,00 € HT`` (one line of prose);
    code spans, links, footnote markers and quoted text are left as written."""
    out: list[str] = []
    position = 0
    for protected in _PROTECTED_RE.finditer(text):
        out.append(_format_prose(text[position : protected.start()]))
        out.append(protected.group(0))
        position = protected.end()
    out.append(_format_prose(text[position:]))
    return "".join(out)


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
        if fenced or line.startswith(_SKIP_PREFIXES) or not _HAS_AMOUNT_RE.search(line):
            lines.append(line)
            continue
        lines.append(format_amounts(line))
    body = "\n".join(lines)
    summary = page.frontmatter.summary
    new_summary = format_amounts(summary) if summary and _HAS_AMOUNT_RE.search(summary) else summary
    if body == page.body and new_summary == summary:
        return page
    frontmatter = page.frontmatter.model_copy(update={"summary": new_summary})
    return Page(path=page.path, frontmatter=frontmatter, body=body)
