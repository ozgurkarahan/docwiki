"""Amounts in euros written the French trade way (v1.7, slice D): ``2 390,00 € HT``.

The compile prompts copy amounts as printed (``2390,00 €``), so the citation checks can compare
them with the documents; this deterministic pass then groups the thousands with a narrow no-break
space, keeps the euro sign on the same line and writes ``HT`` / ``TTC`` instead of
"excluding VAT" / "including VAT". Amounts are recognised in these shapes:

* a number followed by ``€`` (``12500 €``, ``27786.55 €``);
* a number written straight before ``HT`` or ``TTC``, with or without the euro sign
  (``2390 HT``, ``4386.5 HT``, ``26 590 HT``);
* ``HT`` / ``TTC`` (or "excl./incl. VAT", "excluding/including tax") written before the number
  it qualifies, joined by ``de``, ``à``, ``est de``, ``s'élève à``, ``of``, ``at`` or a colon:
  ``un montant HT de 174910`` becomes ``un montant de 174 910,00 € HT`` and
  ``excl. VAT of 26590`` becomes ``of 26 590,00 € HT`` (v1.7, slice G: amounts copied from
  spreadsheet cells);
* a number with a point and one or two decimals in a sentence about money (``montant``,
  ``retenue``, ``net à payer``, ``amount``…): ``est de 1462.45`` becomes ``est de 1 462,45 €``.

Never an amount: a year without decimals or euro sign (``2026 HT``), a lot, poste, revision or
document number (``lot 5 HT``, ``poste 4.1``, ``BC-2026-009 TTC``), a date, a percentage or a
quantity with a unit. Quotes from the documents (blockquotes, quoted text), tables, footnote
markers and definitions, links and code are left exactly as they are; a footnote marker right
after an amount (``27786.55[^c3]``) is never read as part of the number. The citation checks
read these separators as part of the number (``verify_citations`` drops narrow and ordinary
no-break spaces).
"""

from __future__ import annotations

import re
from decimal import Decimal

from docwiki.contracts import Page

__all__ = ["format_amounts", "format_number", "format_page_amounts"]

THIN = " "
"""Narrow no-break space: the thousands separator."""
NBSP = " "

_SPACE = "[   ]"
_DIGITS = rf"\d{{1,3}}(?:{_SPACE}\d{{3}})+(?!\d)|\d+"
"""Digits, grouped by thousands with spaces or not (``26 590``, ``26590``)."""
_END = r"(?![\d/]|[.,-]\d)"
"""The number ends here: no further digit, decimal, date or document-number part."""
_AMOUNT_RE = re.compile(rf"(?<![\d.,\w-])({_DIGITS})(?:[.,](\d{{1,2}}))?{_END}{_SPACE}?€")
_VAT_RE = re.compile(
    r"€[  ]*(?:\(\s*)?(excluding|excl\.?|including|incl\.?) VAT(?:\s*\))?",
    re.IGNORECASE,
)
_SKIP_PREFIXES = (">", "|", "[^", "    ", "\t")
_VAT_AMOUNT_RE = re.compile(
    rf"(?<![\w.,/#^€  -])({_DIGITS})(?:[.,](\d{{1,2}}))?(?![\d.,])"
    rf"{_SPACE}?(€{_SPACE}?)?(HT|TTC)(?!\w)"
)
"""A number written straight before ``HT`` / ``TTC`` (decimals after a comma or a point)."""
_LEAD_VAT_RE = re.compile(
    r"(?<![\w-])(?P<vat>HT|TTC|(?:excl\.?|excluding|incl\.?|including)[  ]+(?:VAT|tax))"
    r"(?P<link>[  ]+(?:(?:est|sont|s['’]élèvent|s['’]élève)[  ]+)?(?:de|à|of|at)"
    r"[  ]+|[  ]*:[  ]*)"
    rf"(?P<digits>{_DIGITS})(?:[.,](?P<cents>\d{{1,2}}))?{_END}"
    rf"(?P<euro>{_SPACE}?€)?(?!{_SPACE}?(?:%|‰|HT\b|TTC\b))(?![\w])"
)
"""``HT`` / ``TTC`` written before the amount it qualifies (``montant HT de 174910``)."""
_MONEY_WORDS_RE = re.compile(
    r"\b(?:montants?|retenues?|net|reste|totale?s?|prix|co[ûu]ts?|factur\w*|pay\w*|"
    r"TVA|acomptes?|soldes?|cumul\w*|amounts?|price|costs?|retention|invoiced|VAT)\b",
    re.IGNORECASE,
)
_DECIMAL_RE = re.compile(
    rf"(?<![\w.,/#^€  -])(\d+)\.(\d{{1,2}}){_END}"
    rf"(?!{_SPACE}?(?:%|‰|°|€|HT\b|TTC\b|[mM]\b|m[²³23]|[mck]m\b|kg\b|t\b|h\b|j\b|l\b|ml\b|k[WN]))"
)
"""A point decimal (``1462.45``): an amount when its sentence speaks of money."""
_SENTENCE_END_RE = re.compile(r"[.!?;](?:\s|$)")
_NUMBER_PREFIX_RE = re.compile(
    r"(?:\b(?:lot|indice|rev|n°|nº|no|nr|poste|postes|article|art|item|section|version|v|"
    rf"ligne|line|chapitre)\.?|§|\d{_SPACE}){_SPACE}*$",
    re.IGNORECASE,
)
"""Text before a number that makes it a lot, poste, revision or document number, or the tail of
a number already grouped with spaces: never an amount to format."""
_PROTECTED_RE = re.compile(
    r"(`+)(?:(?!\1).)+?\1"
    r"|!?\[(?:[^\[\]\\]|\\.|\[(?:[^\[\]\\]|\\.)*\])*\](?:\([^)\n]*\)|\[[^\]\n]*\])"
    r"|\[\^[^\]\s]+\]"
    r"|<[^>\n]*>"
    r'|"[^"\n]*"|“[^”\n]*”|«[^»\n]*»'
)
"""Code spans, links, footnote markers, autolinks and quoted text: kept exactly as written."""
_HAS_AMOUNT_RE = re.compile(r"€|(?<!\w)(?:HT|TTC|VAT|tax)(?!\w)|\d\.\d")


def _plain(digits: str) -> str:
    return re.sub(_SPACE, "", digits)


def _group(digits: str) -> str:
    digits = _plain(digits)
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


def _not_amount(digits: str, decimals: str | None, euro: str | None, before: str) -> bool:
    """A lot, poste or document number, a year or a code written where an amount could be."""
    if _NUMBER_PREFIX_RE.search(before):
        return True
    if not decimals and not euro and len(digits) == 4 and 1900 <= int(digits) <= 2100:
        return True  # a year (``tarif 2026 HT``), not an amount
    return len(digits) > 1 and digits.startswith("0")  # a code (``0158``), not an amount


def _amount(digits: str, decimals: str | None, vat: str | None = None) -> str:
    cents = (decimals or "").ljust(2, "0")
    return f"{_group(digits)},{cents}{NBSP}€" + (f"{NBSP}{vat}" if vat else "")


def _vat_amount(match: re.Match[str]) -> str:
    digits, decimals, euro, vat = match.groups()
    if _not_amount(_plain(digits), decimals, euro, match.string[: match.start()]):
        return match.group(0)
    return _amount(digits, decimals, vat)


def _lead_vat(match: re.Match[str]) -> str:
    """``HT de 174910`` → ``de 174 910,00 € HT``: the connector stays, the VAT goes after."""
    word, digits = match.group("vat"), match.group("digits")
    decimals, euro = match.group("cents"), match.group("euro")
    if _plain(digits) == digits and _not_amount(digits, decimals, euro, ""):
        return match.group(0)
    english = "HT" if word.lower().startswith("excl") else "TTC"
    vat = word if word in ("HT", "TTC") else english
    link = " ".join(match.group("link").split())
    return f"{link} {_amount(digits, decimals, vat)}"


def _decimal(match: re.Match[str]) -> str:
    """``1462.45`` in a sentence about money → ``1 462,45 €``."""
    before = match.string[: match.start()]
    ends = list(_SENTENCE_END_RE.finditer(before))
    sentence = before[ends[-1].end() :] if ends else before
    if _NUMBER_PREFIX_RE.search(before) or not _MONEY_WORDS_RE.search(sentence):
        return match.group(0)
    return _amount(match.group(1), match.group(2))


def _euro(match: re.Match[str]) -> str:
    cents = f",{match.group(2)}" if match.group(2) else ""
    return f"{_group(match.group(1))}{cents}{NBSP}€"


def _format_prose(text: str) -> str:
    text = _VAT_RE.sub(_vat, text)
    text = _LEAD_VAT_RE.sub(_lead_vat, text)
    text = _VAT_AMOUNT_RE.sub(_vat_amount, text)
    text = _AMOUNT_RE.sub(_euro, text)
    return _DECIMAL_RE.sub(_decimal, text)


def format_amounts(text: str) -> str:
    """``2390,00 € excluding VAT``, ``2390 HT`` and ``HT de 2390`` → ``2 390,00 € HT`` (one line
    of prose); code spans, links, footnote markers and quoted text are left as written."""
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
