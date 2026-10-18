"""Text normalisation and value extraction for the deterministic metrics (docs/spec/evals.md §2).

Answers, expected strings (``must_include``, ``forbidden``) and evidence text are compared after
the same normalisation, which extends the quote rules of evidence-contract §4 to answers written
by models:

1. Unicode NFKC, soft hyphens and zero-width characters removed, case-folded, accents stripped,
   typographic quotes and dashes unified, a hyphen between two letters read as a space
   (``high-speed`` = ``high speed``), whitespace collapsed.
2. Dates: ``31 July 2026``, ``July 31, 2026``, ``31/07/2026``, ``31.07.2026``, ``31 juillet
   2026`` and ``2026/07/31`` become ``2026-07-31``; a day and a month name without a year become
   ``31 july`` (English, French and German month names).
3. Numbers: thousands separators removed (``1,450`` and ``1 450`` become ``1450``), decimal
   commas read as points (``90,4`` becomes ``90.4``).
4. Units right after a number become one symbol after one space: ``450 N·m``, ``450Nm`` and
   ``450 newton metres`` become ``450 nm``; ``10°C`` and ``10 degrees C`` become ``10 °c``;
   ``300 metres`` becomes ``300 m``; ``90.4 percent`` becomes ``90.4 %``.

Matching (:func:`contains_item`) is boundary-aware: ``12`` does not match ``WTG-12`` or ``412``,
``40`` does not match ``40.5``, a word may take a plural ``s``/``es``. Codes such as
``FGT-P-22328`` also match with other separators (``FGT P 22328``), and numbers with units also
match by value (``6.0 m/s`` matches ``6 m/s``).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

__all__ = [
    "UNITS",
    "Quantity",
    "Values",
    "contains_item",
    "extract_values",
    "find_term",
    "fold",
    "normalize_text",
    "value_tokens",
]

# --------------------------------------------------------------------------- step 1: folding

_INVISIBLE = dict.fromkeys(map(ord, "\u00ad\u200b\u200c\u200d\u2060\ufeff"), None)
_PUNCTUATION = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201b": "'",
        "\u2032": "'",
        "`": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u201f": '"',
        "\u2033": '"',
        "\u00ab": '"',
        "\u00bb": '"',
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2015": "-",
        "\u2212": "-",
        "\ufe58": "-",
        "\ufe63": "-",
        "\u22c5": "\u00b7",
        "\u2219": "\u00b7",
    }
)
_LETTER_HYPHEN = re.compile(r"(?<=[^\W\d_])-(?=[^\W\d_])")
_SPACES = re.compile(r"\s+")


def fold(text: str) -> str:
    """Unicode, case, accent, punctuation and whitespace folding (step 1 only)."""
    text = unicodedata.normalize("NFKC", text).translate(_INVISIBLE).translate(_PUNCTUATION)
    text = text.casefold()
    text = "".join(
        char for char in unicodedata.normalize("NFD", text) if not unicodedata.combining(char)
    )
    text = unicodedata.normalize("NFC", text)
    text = _LETTER_HYPHEN.sub(" ", text)
    return _SPACES.sub(" ", text).strip()


# ----------------------------------------------------------------------------- step 2: dates

_FULL_MONTHS: dict[str, int] = {
    "january": 1,
    "janvier": 1,
    "januar": 1,
    "february": 2,
    "fevrier": 2,
    "februar": 2,
    "march": 3,
    "mars": 3,
    "marz": 3,
    "maerz": 3,
    "april": 4,
    "avril": 4,
    "may": 5,
    "mai": 5,
    "june": 6,
    "juin": 6,
    "juni": 6,
    "july": 7,
    "juillet": 7,
    "juli": 7,
    "august": 8,
    "aout": 8,
    "september": 9,
    "septembre": 9,
    "october": 10,
    "octobre": 10,
    "oktober": 10,
    "november": 11,
    "novembre": 11,
    "december": 12,
    "decembre": 12,
    "dezember": 12,
}
_SHORT_MONTHS: dict[str, int] = {
    "jan": 1,
    "janv": 1,
    "feb": 2,
    "fev": 2,
    "fevr": 2,
    "mar": 3,
    "apr": 4,
    "avr": 4,
    "jun": 6,
    "jul": 7,
    "juil": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "okt": 10,
    "nov": 11,
    "dec": 12,
    "dez": 12,
}
_MONTHS = {**_SHORT_MONTHS, **_FULL_MONTHS}
_ENGLISH_MONTHS = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)


def _alternation(names: Iterable[str]) -> str:
    return "|".join(sorted(names, key=len, reverse=True))


_ANY_MONTH = _alternation(_MONTHS)
_FULL_MONTH = _alternation(_FULL_MONTHS)
_DAY = r"(?P<day>[0-3]?\d)(?:st|nd|rd|th|er)?\.?"
_YEAR = r"(?P<year>(?:19|20)\d{2})"
_DAY_MONTH_YEAR = re.compile(rf"(?<![\w.-]){_DAY} (?P<month>{_ANY_MONTH})\.?,? {_YEAR}(?!\d)")
_MONTH_DAY_YEAR = re.compile(
    rf"(?<![\w.-])(?P<month>{_ANY_MONTH})\.? (?P<day>[0-3]?\d)(?:st|nd|rd|th)?,? {_YEAR}(?!\d)"
)
_NUMERIC_DATE = re.compile(
    r"(?<![\w./-])(?P<a>\d{1,2})(?P<sep>[./])(?P<b>\d{1,2})(?P=sep)(?P<year>(?:19|20)\d{2})"
    r"(?![\w/-]|\.\d)"
)
_SLASHED_ISO = re.compile(
    r"(?<![\w./-])(?P<year>(?:19|20)\d{2})/(?P<month>\d{1,2})/(?P<day>\d{1,2})(?![\w/.-])"
)
_DAY_MONTH = re.compile(rf"(?<![\w.-]){_DAY} (?P<month>{_FULL_MONTH})(?![\w])")


def _iso(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _named_date(match: re.Match[str]) -> str:
    iso = _iso(int(match["year"]), _MONTHS[match["month"]], int(match["day"]))
    return iso or match[0]


def _numeric_date(match: re.Match[str]) -> str:
    first, second, year = int(match["a"]), int(match["b"]), int(match["year"])
    iso = _iso(year, second, first) if second <= 12 else _iso(year, first, second)
    return iso or match[0]


def _slashed_iso(match: re.Match[str]) -> str:
    iso = _iso(int(match["year"]), int(match["month"]), int(match["day"]))
    return iso or match[0]


def _day_month(match: re.Match[str]) -> str:
    day = int(match["day"])
    if not 1 <= day <= 31:
        return match[0]
    return f"{day} {_ENGLISH_MONTHS[_FULL_MONTHS[match['month']] - 1]}"


def _dates(text: str) -> str:
    text = _DAY_MONTH_YEAR.sub(_named_date, text)
    text = _MONTH_DAY_YEAR.sub(_named_date, text)
    text = _NUMERIC_DATE.sub(_numeric_date, text)
    text = _SLASHED_ISO.sub(_slashed_iso, text)
    return _DAY_MONTH.sub(_day_month, text)


# --------------------------------------------------------------------------- step 3: numbers

_THOUSANDS_COMMA = re.compile(r"(?<![\d.,])([1-9]\d{0,2})((?:,\d{3})+)(?!\d|,\d)")
_THOUSANDS_SPACE = re.compile(r"(?<![\d.,])([1-9]\d{0,2})((?: \d{3})+)(?!\d|[.,]\d)")
_DECIMAL_COMMA = re.compile(r"(?<=\d),(?=\d)")


def _numbers(text: str) -> str:
    text = _THOUSANDS_COMMA.sub(lambda m: m[1] + m[2].replace(",", ""), text)
    text = _THOUSANDS_SPACE.sub(lambda m: m[1] + m[2].replace(" ", ""), text)
    return _DECIMAL_COMMA.sub(".", text)


# ----------------------------------------------------------------------------- step 4: units

_UNIT_SPECS: tuple[tuple[str, str], ...] = (
    ("nm", r"n ?[·.]? ?m|newton ?met(?:re|er)s?"),
    (
        "°c",
        r"° ?c(?:elsius)?|o ?c|deg(?:rees?|s)?\.? ?c(?:elsius)?|degres? celsius|grad celsius"
        r"|celsius",
    ),
    ("mm/s", r"mm ?/ ?s"),
    ("m/s", r"m ?/ ?s|met(?:re|er)s? per second"),
    ("km/h", r"km ?/ ?h"),
    ("mm", r"millimet(?:re|er)s?|mm"),
    ("cm", r"centimet(?:re|er)s?|cm"),
    ("km", r"kilomet(?:re|er)s?|km"),
    ("m", r"met(?:re|er)s?|m"),
    ("ml", r"millilit(?:re|er)s?|ml"),
    ("l", r"lit(?:re|er)s?|ltrs?|l"),
    ("kg", r"kilogram(?:me)?s?|kg"),
    ("t", r"tonnes?|t"),
    ("bar", r"bars?"),
    ("ppm", r"ppm"),
    ("%", r"%|percent|per cent|pour cent|prozent"),
    ("kwh", r"kwh"),
    ("mwh", r"mwh"),
    ("gwh", r"gwh"),
    ("mva", r"mva"),
    ("kva", r"kva"),
    ("kv", r"kv"),
    ("kw", r"kw"),
    ("mw", r"mw"),
    ("rpm", r"rpm|tr ?/ ?min|u ?/ ?min"),
    ("hz", r"hz"),
    ("h", r"hours?|hrs?|h|heures?|stunden?"),
    ("min", r"minutes?|mins?"),
    ("s", r"seconds?|secs?|s"),
    ("eur", r"eur|euros?|€"),
)
UNITS: frozenset[str] = frozenset(unit for unit, _ in _UNIT_SPECS)
"""Canonical unit symbols produced by :func:`normalize_text`."""

_UNIT_RES: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (
        re.compile(rf"(?<![\w.])(?P<num>[-+]?\d+(?:\.\d+)?)[ -]?(?:{pattern})(?![\w/])"),
        unit,
    )
    for unit, pattern in _UNIT_SPECS
)


def _units(text: str) -> str:
    for pattern, unit in _UNIT_RES:
        text = pattern.sub(lambda match, unit=unit: f"{match['num']} {unit}", text)
    return text


def normalize_text(text: str) -> str:
    """Canonical form used by every comparison (see the module docstring)."""
    return _units(_numbers(_dates(fold(text))))


# ----------------------------------------------------------------------------------- values


@dataclass(frozen=True)
class Quantity:
    """A number and the unit written right after it (``None`` when there is none)."""

    value: Decimal
    unit: str | None = None

    def __str__(self) -> str:
        number = format(self.value.normalize(), "f") if self.value else "0"
        return f"{number} {self.unit}" if self.unit else number


@dataclass(frozen=True)
class Values:
    """Quantities and ISO dates found in a normalised text."""

    quantities: tuple[Quantity, ...] = ()
    dates: frozenset[str] = field(default_factory=frozenset)

    def has_quantity(self, wanted: Quantity) -> bool:
        """Same value, and the same unit when ``wanted`` has one (6.0 m/s == 6 m/s)."""
        return any(
            found.value == wanted.value and (wanted.unit is None or found.unit == wanted.unit)
            for found in self.quantities
        )

    def __bool__(self) -> bool:
        return bool(self.quantities or self.dates)


_TOKEN_RE = re.compile(r"[^\s;:!?()\[\]{}\"'<>|,=]+")
_NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
_RANGE_RE = re.compile(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)")
_ISO_DATE_RE = re.compile(r"(?:19|20)\d{2}-[01]\d-[0-3]\d")
_EDGE_MARKS = "*_~#"
_LEADING_MARKS = "~≈<>≤≥±€$£"


def _clean_token(token: str) -> str:
    token = token.strip(_EDGE_MARKS)
    while token.endswith((".", "…")):
        token = token[:-1]
    return token.lstrip(_LEADING_MARKS).strip(_EDGE_MARKS)


def _tokens(text: str) -> list[str]:
    tokens = (_clean_token(token) for token in _TOKEN_RE.findall(text))
    return [token for token in tokens if token]


def _decimal(text: str) -> Decimal | None:
    try:
        return Decimal(text)
    except InvalidOperation:  # pragma: no cover - the regexes only pass valid numbers
        return None


def extract_values(text_norm: str) -> Values:
    """Quantities (standalone numbers with an optional unit) and ISO dates of a normalised text.

    Numbers inside codes (``WO-26-0412``, ``A2101``, ``FGT-3200-18-07752``) are not
    quantities; a range ``40-60 °c`` gives two quantities with the unit.
    """
    tokens = _tokens(text_norm)
    quantities: list[Quantity] = []
    dates: set[str] = set()
    for index, token in enumerate(tokens):
        following = tokens[index + 1] if index + 1 < len(tokens) else None
        unit = following if following in UNITS else None
        if _ISO_DATE_RE.fullmatch(token):
            dates.add(token)
        elif _NUMBER_RE.fullmatch(token):
            value = _decimal(token)
            if value is not None:
                quantities.append(Quantity(value, unit))
        elif match := _RANGE_RE.fullmatch(token):
            for part in (match[1], match[2]):
                value = _decimal(part)
                if value is not None:
                    quantities.append(Quantity(value, unit))
    return Values(tuple(quantities), frozenset(dates))


def value_tokens(text_norm: str, *, min_digits: int = 4) -> set[str]:
    """Distinctive values of a normalised text: numbers with ``min_digits`` digits or more
    (years 1900-2100 excluded) and codes mixing letters and digits (five characters or more).

    Used for the restricted-content fingerprint; dates are not distinctive and are skipped.
    """
    found: set[str] = set()
    for token in _tokens(text_norm):
        if _ISO_DATE_RE.fullmatch(token):
            continue
        if _NUMBER_RE.fullmatch(token):
            digits = sum(char.isdigit() for char in token)
            value = _decimal(token.lstrip("+-"))
            if value is None or digits < min_digits:
                continue
            if value == value.to_integral_value() and 1900 <= value <= 2100:
                continue
            found.add(str(Quantity(value)))
        elif len(token) >= 5 and _has_letter_and_digit(token):
            found.add(token)
    return found


# --------------------------------------------------------------------------------- matching


def _has_letter_and_digit(text: str) -> bool:
    return any(char.isdigit() for char in text) and any(char.isalpha() for char in text)


def _left_ok(term: str, text: str, start: int) -> bool:
    if start == 0:
        return True
    previous, first = text[start - 1], term[0]
    if not first.isalnum():
        return True
    if previous.isalnum():
        return False
    # "12" must not match "WTG-12", "0.12", "1,12" or "1/12"; a minus sign changes the value.
    return not (first.isdigit() and previous in "-.,/")


def _right_ok(term: str, text: str, end: int) -> bool:
    if end == len(text):
        return True
    following, last = text[end], term[-1]
    if last.isdigit():
        if following.isalnum():
            return False
        return not (following in ".," and end + 1 < len(text) and text[end + 1].isdigit())
    if last.isalpha() and following.isalnum():
        for suffix in ("s", "es"):
            stop = end + len(suffix)
            if text.startswith(suffix, end) and (stop == len(text) or not text[stop].isalnum()):
                return True
        return False
    return True


def find_term(term: str, text: str) -> bool:
    """``term`` occurs in ``text`` at token boundaries (both already normalised)."""
    if not term:
        return True
    start = text.find(term)
    while start >= 0:
        if _left_ok(term, text, start) and _right_ok(term, text, start + len(term)):
            return True
        start = text.find(term, start + 1)
    return False


_CODE_PARTS = re.compile(r"\d+|[^\W\d_]+")
_CODE_SEPARATOR = r"[\s\-_./]?"


def _is_code(term: str) -> bool:
    """Identifiers (``fgt p-22328``, ``wtg-07``, ``pwg 220``), not quantities (``6.0 m/s``)."""
    tokens = _tokens(term)
    if any(_has_letter_and_digit(token) for token in tokens):
        return True
    has_word = any(token.isalpha() and token not in UNITS for token in tokens)
    return has_word and any(token.isdigit() for token in tokens)


def _find_code(term: str, text: str) -> bool:
    """Codes match with any single separator between their parts (``FGT P 22328``)."""
    parts = _CODE_PARTS.findall(term)
    if len(parts) < 2:
        return False
    pattern = re.compile(_CODE_SEPARATOR.join(re.escape(part) for part in parts))
    return any(
        _left_ok(term, text, match.start()) and _right_ok(term, text, match.end())
        for match in pattern.finditer(text)
    )


def contains_item(item: str, text_norm: str, values: Values | None = None) -> bool:
    """Whether the normalised ``text_norm`` contains the expected string ``item``.

    Tried in order: boundary-aware substring of the normalised item; codes with other
    separators; for items made only of numbers, dates and units, the same values (a number with a
    unit must keep its unit). ``values`` may pass precomputed :func:`extract_values` of the text.
    """
    term = normalize_text(item)
    if not term:
        return True
    if find_term(term, text_norm):
        return True
    if _is_code(term) and _find_code(term, text_norm):
        return True
    wanted = extract_values(term)
    words = [token for token in _tokens(term) if any(char.isalpha() for char in token)]
    if not wanted or any(word not in UNITS for word in words):
        return False
    found = values if values is not None else extract_values(text_norm)
    return wanted.dates <= found.dates and all(
        found.has_quantity(quantity) for quantity in wanted.quantities
    )
