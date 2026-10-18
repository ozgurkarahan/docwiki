"""Deterministic citation verification (evidence-contract §4) and document look-ups.

Normalisation (applied to quotes and cited text alike): soft hyphens and zero-width characters
removed, Unicode NFKC, typographic quotes made straight, dashes and minus signs made ``-``,
case-folded, whitespace collapsed. The spec rules are NFKC, case-fold, straight quotes, collapsed
whitespace and soft hyphens; dash unification and zero-width removal are additions.

Citation ids (the ``block_id`` field of a compiled citation and the ``[[cite:…]]`` markers):

* ``b0042`` — one block; ``b0042,b0043`` — several blocks (quotes are checked against their
  concatenation, then the reference is narrowed to the block(s) holding the quote, keeping the
  cited blocks that hold quantities of the fact the quote lacks); ``b0042-b0045`` — a block range;
* ``t03:r0012`` — one table row (``t03:r0012,t03:r0013`` — several rows of one table);
  ``t03`` — a whole table (narrowed to the first row matching the quote);
* ``f02`` — a figure (caption and generated description).

A reference to several blocks carries the locator of its first block (the union of their boxes
when all lie on one PDF page): the footnote names that locator and the evidence stage shows every
cited block in its sidecar, with one more sidecar per other locator key the blocks span.

Ids are matched by number, so ``b42`` resolves to ``b0042``. Rules per citation:

1. the id must resolve (else ``failed``);
2. a quote must be a substring of the normalised cited text; for table rows every ``|``-separated
   part must match a cell on word boundaries (else ``failed``);
3. without a quote the citation is an ``unverified-paraphrase`` when the fact states no quantity
   or at least one stated quantity appears in the cited text (else ``failed``);
4. per fact, every quantity listed in ``numbers`` (value and unit words) and every quantity found
   in the fact text (value only) must appear in the text of one surviving citation; otherwise
   the fact is dropped and its citations fail.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from functools import cached_property
from typing import Literal

from docwiki.contracts.compiled import Citation, KeyFact
from docwiki.contracts.enums import CitationStatus
from docwiki.contracts.extracted import Block, ExtractedDoc, Figure, Table
from docwiki.contracts.fences import FenceTracker, escape_fence
from docwiki.contracts.locators import (
    CsvRowsLocator,
    DocxTableLocator,
    Locator,
    PdfPageLocator,
    XlsxRowsLocator,
    locator_key,
)

__all__ = [
    "CitationCheck",
    "CitationRefError",
    "CitedRef",
    "DocIndex",
    "FactCheck",
    "MarkerCheck",
    "NumberSpec",
    "SectionCheck",
    "available_numbers",
    "figure_locator",
    "find_quantities",
    "normalize_text",
    "number_values",
    "parse_number_spec",
    "split_sentences",
    "strip_markers",
    "unsigned_values",
    "unsupported_quantities",
    "verify_citation",
    "verify_fact",
    "verify_section_body",
]

_INVISIBLE_RE = re.compile("[\u00ad\u180e\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")
_QUOTES = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201b": "'",
        "\u2032": "'",
        "\u2039": "'",
        "\u203a": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u201f": '"',
        "\u2033": '"',
        "\u00ab": '"',
        "\u00bb": '"',
    }
)
_DASHES = str.maketrans(
    dict.fromkeys("\u2010\u2011\u2012\u2013\u2014\u2015\u2212\ufe58\ufe63", "-")
)
_THOUSANDS_RE = re.compile(r"(?<=\d)[\u00a0\u202f\u2009'\u2019](?=\d{3}(?!\d))")
_NUMBER_PATTERN = r"(?:(?<![\w.,\-])(?P<sign>-))?(?<![\d.,])(?P<body>\d+(?:[.,]\d+)*)"
_NUMBER_RE = re.compile(_NUMBER_PATTERN)
_UNIT_TOKEN_RE = re.compile(r"[%‰°]+[^\W\d_]*|[^\W\d_]+")
_UNIT_STRIP_RE = re.compile(r"[\s·.*]+")
_UNITS = (
    "%",
    "‰",
    "°c",
    "°f",
    "°",
    "ppm",
    "dba",
    "db",
    "rpm",
    "knm",
    "n·m",
    "nm",
    "kn",
    "n",
    "µm",
    "μm",
    "mm",
    "cm",
    "km",
    "m/s",
    "km/h",
    "m²",
    "m³",
    "m2",
    "m3",
    "m",
    "mpa",
    "kpa",
    "pa",
    "mbar",
    "bar",
    "psi",
    "kv",
    "mv",
    "v",
    "ka",
    "ma",
    "a",
    "gwh",
    "mwh",
    "kwh",
    "wh",
    "gw",
    "mw",
    "kw",
    "w",
    "mva",
    "kva",
    "va",
    "khz",
    "hz",
    "ms",
    "seconds",
    "second",
    "secs",
    "sec",
    "s",
    "minutes",
    "minute",
    "mins",
    "min",
    "hours",
    "hour",
    "hrs",
    "hr",
    "h",
    "days",
    "day",
    "weeks",
    "week",
    "months",
    "month",
    "years",
    "year",
    "litres",
    "litre",
    "liters",
    "liter",
    "ml",
    "l",
    "kg",
    "g",
    "tonnes",
    "tonne",
    "tons",
    "ton",
    "t",
    "cst",
)
_QUANTITY_RE = re.compile(
    _NUMBER_PATTERN
    + r"\s?(?:"
    + "|".join(re.escape(unit) for unit in sorted(_UNITS, key=len, reverse=True))
    + r")(?![^\W\d_])",
    re.IGNORECASE,
)
_MARKER_RE = re.compile(r"\[\[\s*cite\s*:\s*([^\]\n]*?)\s*\]\]", re.IGNORECASE)
_SINGLE_MARKER_RE = re.compile(r"(?<!\[)\[\s*cite\s*:\s*([^\]\n]+?)\s*\](?!\])", re.IGNORECASE)
_SENTENCE_END_RE = re.compile(r"[.!?](?:[\"')\]]*)(?:\s*\[\[\s*cite\s*:[^\]\n]*\]\])*(?=\s|$)")
_LIST_PREFIX_RE = re.compile(r"^(\s*(?:[-*+]|\d+[.)])\s+)")
_PROVENANCE_RANK = {"native-text": 0, "deterministic-table": 1, "ocr": 2, "model-description": 3}
_MAX_BLOCKS_PER_CITATION = 20
_MIN_QUOTE_CHARS = 3


# --------------------------------------------------------------------------- normalisation


def normalize_text(text: str) -> str:
    """Normalised form used for quote matching (evidence-contract §4 rule 1)."""
    text = _INVISIBLE_RE.sub("", text)
    text = unicodedata.normalize("NFKC", text).translate(_QUOTES).translate(_DASHES)
    return " ".join(text.casefold().split())


def _number_text(text: str) -> str:
    text = _THOUSANDS_RE.sub("", _INVISIBLE_RE.sub("", text))
    return unicodedata.normalize("NFKC", text).translate(_DASHES)


def _unit_key(text: str) -> str:
    text = unicodedata.normalize("NFKC", _INVISIBLE_RE.sub("", text)).casefold()
    return _UNIT_STRIP_RE.sub("", text.translate(_DASHES))


def _canonical(sign: str, digits: str) -> str | None:
    try:
        value = Decimal(sign + digits)
    except InvalidOperation:
        return None
    text = format(value.normalize(), "f")
    return "0" if text == "-0" else text


def _token_values(sign: str, body: str) -> frozenset[str]:
    """Candidate values of one number token (``1,500`` is 1500 or 1.5)."""
    separators = [char for char in body if char in ".,"]
    values: set[str | None] = set()
    if not separators:
        values.add(_canonical(sign, body))
    elif len(set(separators)) == 1:
        groups = re.split(r"[.,]", body)
        if len(groups) == 2:
            values.add(_canonical(sign, f"{groups[0]}.{groups[1]}"))
            if len(groups[1]) == 3:
                values.add(_canonical(sign, groups[0] + groups[1]))
        elif 1 <= len(groups[0]) <= 3 and all(len(group) == 3 for group in groups[1:]):
            values.add(_canonical(sign, "".join(groups)))
        else:
            values.add(sign + body)
    else:
        last = max(body.rfind("."), body.rfind(","))
        integer = re.sub(r"[.,]", "", body[:last])
        values.add(_canonical(sign, f"{integer}.{body[last + 1 :]}"))
    return frozenset(value for value in values if value)


def number_values(text: str) -> set[str]:
    """Every candidate value of every number in ``text`` (signed, canonical decimal strings)."""
    values: set[str] = set()
    for match in _NUMBER_RE.finditer(_number_text(text)):
        values |= _token_values(match.group("sign") or "", match.group("body"))
    return values


def _unsigned(values: Iterable[str]) -> set[str]:
    return {value.removeprefix("-") for value in values}


@dataclass(frozen=True)
class NumberSpec:
    """A quantity to find in cited text: one candidate set per number token, plus unit words."""

    raw: str
    values: tuple[frozenset[str], ...]
    units: tuple[str, ...] = ()
    signed: bool = True


def parse_number_spec(raw: str) -> NumberSpec | None:
    """Parse one entry of ``KeyFact.numbers`` (``"12 Nm"``, ``"-20 °C"``…); None without digits."""
    prepared = _number_text(raw)
    matches = list(_NUMBER_RE.finditer(prepared))
    if not matches:
        return None
    values = tuple(
        _token_values(match.group("sign") or "", match.group("body")) for match in matches
    )
    rest = _NUMBER_RE.sub(" ", prepared).casefold()
    units = tuple(dict.fromkeys(_UNIT_TOKEN_RE.findall(rest)))
    return NumberSpec(raw=raw, values=values, units=units, signed=True)


def find_quantities(text: str) -> list[NumberSpec]:
    """Quantities (number + unit) found in free English text; checked by value only."""
    specs: list[NumberSpec] = []
    for match in _QUANTITY_RE.finditer(_number_text(text)):
        values = _token_values(match.group("sign") or "", match.group("body"))
        if values:
            specs.append(NumberSpec(raw=match.group(0), values=(values,), signed=False))
    return specs


# --------------------------------------------------------------------------- document index


class CitationRefError(ValueError):
    """A citation id that does not resolve in the document."""


@dataclass(frozen=True)
class CitedRef:
    """What a citation id resolves to."""

    ref: str
    kind: Literal["blocks", "table-rows", "table", "figure"]
    block_ids: tuple[str, ...]
    text: str
    context: str
    provenance: str
    locator: Locator
    rows: tuple[tuple[str, ...], ...] = ()
    table_id: str | None = None
    row_ids: tuple[str, ...] = ()


def _union_bbox(locators: Sequence[Locator]) -> Locator:
    first = locators[0]
    if not all(isinstance(loc, PdfPageLocator) for loc in locators):
        return first
    pages = {loc.page for loc in locators if isinstance(loc, PdfPageLocator)}
    boxes = [loc.bbox for loc in locators if isinstance(loc, PdfPageLocator) and loc.bbox]
    if len(pages) != 1 or len(boxes) != len(locators):
        return first
    union = [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    ]
    return PdfPageLocator(page=next(iter(pages)), bbox=union)


def _row_number(row_id: str) -> int:
    return int(row_id[1:])


def _narrow_rows(table: Table, row_ids: Sequence[str]) -> Locator:
    """The table locator narrowed to the cited rows when the locator has a row range."""
    locator = table.locator
    numbers = [_row_number(row_id) for row_id in row_ids]
    if not numbers or not isinstance(locator, XlsxRowsLocator | CsvRowsLocator | DocxTableLocator):
        return locator
    return locator.model_copy(update={"row_start": min(numbers), "row_end": max(numbers)})


class DocIndex:
    """Look-ups over one :class:`ExtractedDoc` (blocks, table rows, figures) with caches."""

    def __init__(self, doc: ExtractedDoc) -> None:
        self.doc = doc
        self.blocks: dict[str, Block] = {block.id: block for block in doc.blocks}
        self.order: dict[str, int] = {block.id: index for index, block in enumerate(doc.blocks)}
        self.tables: dict[str, Table] = {table.id: table for table in doc.tables}
        self.figures: dict[str, Figure] = {figure.id: figure for figure in doc.figures}
        self._block_numbers = {int(block.id[1:]): block.id for block in doc.blocks}
        self._table_numbers = {int(table.id[1:]): table.id for table in doc.tables}
        self._figure_numbers = {int(figure.id[1:]): figure.id for figure in doc.figures}
        self._rows = {
            table.id: {_row_number(row.row_id): row for row in table.rows} for table in doc.tables
        }
        self._norm: dict[str, str] = {}
        self._numbers: dict[str, set[str]] = {}

    # -- caches ---------------------------------------------------------------------------

    def norm(self, text: str) -> str:
        value = self._norm.get(text)
        if value is None:
            value = self._norm[text] = normalize_text(text)
        return value

    def numbers(self, text: str) -> set[str]:
        value = self._numbers.get(text)
        if value is None:
            value = self._numbers[text] = number_values(text)
        return value

    @cached_property
    def all_numbers(self) -> set[str]:
        """Unsigned candidate values of every number in the document (blocks, tables, figures)."""
        values: set[str] = set()
        for block in self.doc.blocks:
            values |= self.numbers(block.text)
        for table in self.doc.tables:
            values |= self.numbers(" | ".join(table.columns))
            for row in table.rows:
                values |= self.numbers(" | ".join(row.cells))
        for figure in self.doc.figures:
            values |= self.numbers(f"{figure.caption or ''} {figure.description or ''}")
        return _unsigned(values)

    def block_id(self, token: str) -> str | None:
        match = re.fullmatch(r"b(\d+)", token)
        return self._block_numbers.get(int(match.group(1))) if match else None

    def table_id(self, token: str) -> str | None:
        match = re.fullmatch(r"t(\d+)", token)
        return self._table_numbers.get(int(match.group(1))) if match else None

    def figure_id(self, token: str) -> str | None:
        match = re.fullmatch(r"f(\d+)", token)
        return self._figure_numbers.get(int(match.group(1))) if match else None

    def page_provenance(self, locator: Locator) -> str:
        """Provenance of the first block sharing ``locator``'s key (``native-text`` if none)."""
        key = locator_key(locator)
        for block in self.doc.blocks:
            if block.locator_key == key:
                return block.provenance
        return "native-text"

    # -- resolution -----------------------------------------------------------------------

    def resolve(self, raw: str) -> CitedRef:
        """Resolve a citation id; raises :class:`CitationRefError` with the reason."""
        text = raw.strip().lower()
        text = re.sub(r"^\[*\s*(?:cite\s*:)?\s*", "", text)
        text = re.sub(r"\s*\]*$", "", text)
        tokens = [token for token in re.split(r"[\s,;+&]+", text) if token]
        if not tokens:
            raise CitationRefError("empty citation id")
        rows = [re.fullmatch(r"t(\d+)\s*[:/.#_]?\s*r(\d+)", token) for token in tokens]
        if all(rows):
            return self._resolve_rows(tokens)
        if len(tokens) == 1 and re.fullmatch(r"t\d+", tokens[0]):
            return self._resolve_table(tokens[0])
        if len(tokens) == 1 and re.fullmatch(r"f\d+", tokens[0]):
            return self._resolve_figure(tokens[0])
        return self._resolve_blocks(tokens)

    def _resolve_blocks(self, tokens: Sequence[str]) -> CitedRef:
        ids: list[str] = []
        for token in tokens:
            span = re.fullmatch(r"b(\d+)-b?(\d+)", token)
            if span:
                low, high = int(span.group(1)), int(span.group(2))
                if high < low or high - low >= _MAX_BLOCKS_PER_CITATION:
                    raise CitationRefError(f"invalid block range {token}")
                numbers = range(low, high + 1)
                found = [self._block_numbers[n] for n in numbers if n in self._block_numbers]
                if not found:
                    raise CitationRefError(f"unknown block range {token}")
                ids.extend(found)
                continue
            if not re.fullmatch(r"b\d+", token):
                raise CitationRefError(f"unrecognised citation id {token!r}")
            block_id = self.block_id(token)
            if block_id is None:
                raise CitationRefError(f"unknown block id {token}")
            ids.append(block_id)
        ordered = sorted(dict.fromkeys(ids), key=self.order.__getitem__)
        if len(ordered) > _MAX_BLOCKS_PER_CITATION:
            raise CitationRefError("too many blocks in one citation")
        return self._blocks_ref(ordered)

    def _blocks_ref(self, block_ids: Sequence[str]) -> CitedRef:
        """The reference to ``block_ids`` (existing ids, in reading order)."""
        blocks = [self.blocks[block_id] for block_id in block_ids]
        text = "\n".join(block.text for block in blocks)
        provenance = max(
            (block.provenance for block in blocks), key=lambda p: _PROVENANCE_RANK.get(p, 0)
        )
        return CitedRef(
            ref=",".join(block_ids),
            kind="blocks",
            block_ids=tuple(block_ids),
            text=text,
            context=text,
            provenance=provenance,
            locator=_union_bbox([block.locator for block in blocks]),
        )

    def _resolve_rows(self, tokens: Sequence[str]) -> CitedRef:
        table_ids: set[str] = set()
        row_ids: list[str] = []
        for token in tokens:
            match = re.fullmatch(r"t(\d+)\s*[:/.#_]?\s*r(\d+)", token)
            assert match is not None
            table_id = self._table_numbers.get(int(match.group(1)))
            if table_id is None:
                raise CitationRefError(f"unknown table t{match.group(1)}")
            row = self._rows[table_id].get(int(match.group(2)))
            if row is None:
                raise CitationRefError(f"unknown row r{match.group(2)} in table {table_id}")
            table_ids.add(table_id)
            row_ids.append(row.row_id)
        if len(table_ids) != 1:
            raise CitationRefError("one citation may cite rows of one table only")
        table = self.tables[table_ids.pop()]
        ordered = sorted(dict.fromkeys(row_ids), key=_row_number)
        return self._rows_ref(table, ordered)

    def _rows_ref(self, table: Table, row_ids: Sequence[str]) -> CitedRef:
        by_id = {row.row_id: row for row in table.rows}
        cells = tuple(tuple(by_id[row_id].cells) for row_id in row_ids)
        text = "\n".join(" | ".join(row) for row in cells)
        return CitedRef(
            ref=",".join(f"{table.id}:{row_id}" for row_id in row_ids),
            kind="table-rows",
            block_ids=(),
            text=text,
            context=" | ".join(table.columns) + "\n" + text,
            provenance=table.provenance,
            locator=_narrow_rows(table, row_ids),
            rows=cells,
            table_id=table.id,
            row_ids=tuple(row_ids),
        )

    def _resolve_table(self, token: str) -> CitedRef:
        table_id = self.table_id(token)
        if table_id is None:
            raise CitationRefError(f"unknown table {token}")
        table = self.tables[table_id]
        cells = tuple(tuple(row.cells) for row in table.rows)
        text = "\n".join(" | ".join(row) for row in cells)
        return CitedRef(
            ref=table.id,
            kind="table",
            block_ids=(),
            text=text,
            context=" | ".join(table.columns) + "\n" + text,
            provenance=table.provenance,
            locator=table.locator,
            rows=cells,
            table_id=table.id,
            row_ids=tuple(row.row_id for row in table.rows),
        )

    def _resolve_figure(self, token: str) -> CitedRef:
        figure_id = self.figure_id(token)
        if figure_id is None:
            raise CitationRefError(f"unknown figure {token}")
        figure = self.figures[figure_id]
        parts = [part for part in (figure.caption, figure.description) if part]
        text = "\n".join(parts)
        return CitedRef(
            ref=figure.id,
            kind="figure",
            block_ids=(),
            text=text,
            context=text,
            provenance="model-description" if figure.description else "native-text",
            locator=figure_locator(figure),
        )


def figure_locator(figure: Figure) -> Locator:
    """The figure locator, carrying the figure bbox when the page locator has none."""
    locator = figure.locator
    if isinstance(locator, PdfPageLocator) and locator.bbox is None and figure.bbox is not None:
        return PdfPageLocator(page=locator.page, bbox=list(figure.bbox))
    return locator


# --------------------------------------------------------------------------- verification


@dataclass
class CitationCheck:
    """Verification result of one citation (``cited`` is None when the id did not resolve)."""

    raw_id: str
    quote: str | None
    status: CitationStatus
    cited: CitedRef | None = None
    reason: str | None = None

    @property
    def citation(self) -> Citation:
        """The canonical citation as kept in the compiled output."""
        return Citation(block_id=self.cited.ref if self.cited else self.raw_id, quote=self.quote)


@dataclass
class FactCheck:
    fact: KeyFact
    checks: list[CitationCheck]
    kept: bool
    reason: str | None = None

    @property
    def kept_checks(self) -> list[CitationCheck]:
        return [check for check in self.checks if check.status != "failed"]


def _clean_quote(quote: str | None, kind: str) -> str | None:
    if quote is None:
        return None
    value = " ".join(quote.split())
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1].strip()
    pairs = {"“": "”", "„": "“", "«": "»", "‘": "’"}
    if len(value) >= 2 and pairs.get(value[0]) == value[-1]:
        value = value[1:-1].strip()
    normalized = normalize_text(value)
    if not normalized or not any(char.isalnum() for char in normalized):
        return None
    if kind in ("blocks", "figure") and len(normalized) < _MIN_QUOTE_CHARS:
        return None
    return value


def _in_cell(part: str, cell: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(part)}(?!\w)", cell) is not None


def _row_matches(index: DocIndex, cells: Sequence[str], parts: Sequence[str]) -> bool:
    normalized = [index.norm(cell) for cell in cells]
    return all(any(_in_cell(part, cell) for cell in normalized) for part in parts)


def _match_quote(index: DocIndex, cited: CitedRef, quote: str) -> CitedRef | None:
    """``cited`` when the quote verifies, narrowed to the matching row for whole tables and to
    the block(s) holding the quote for several blocks."""
    normalized = normalize_text(quote)
    if cited.kind in ("table-rows", "table"):
        parts = [part.strip() for part in normalized.split("|") if part.strip()]
        if not parts:
            return None
        if cited.kind == "table-rows":
            joined = [cell for row in cited.rows for cell in row]
            return cited if _row_matches(index, joined, parts) else None
        assert cited.table_id is not None
        table = index.tables[cited.table_id]
        for row in table.rows:
            if _row_matches(index, row.cells, parts):
                return index._rows_ref(table, [row.row_id])
        return None
    if cited.kind == "figure":
        figure = index.figures[cited.ref]
        if figure.caption and normalized in index.norm(figure.caption):
            locator = cited.locator
            return CitedRef(
                ref=cited.ref,
                kind="figure",
                block_ids=(),
                text=figure.caption,
                context=cited.context,
                provenance=index.page_provenance(locator),
                locator=locator,
            )
        return cited if normalized in index.norm(cited.text) else None
    if normalized not in index.norm(cited.text):
        return None
    return _quote_blocks(index, cited, normalized)


def _quote_blocks(index: DocIndex, cited: CitedRef, quote: str) -> CitedRef:
    """``cited`` narrowed to the blocks holding the normalised ``quote``.

    The first cited block that contains the whole quote wins; a quote running across blocks
    keeps the cited blocks spanned by its first occurrence in their concatenation.
    """
    if len(cited.block_ids) < 2:
        return cited
    texts = [(block_id, index.norm(index.blocks[block_id].text)) for block_id in cited.block_ids]
    for block_id, text in texts:
        if quote in text:
            return index._blocks_ref([block_id])
    spans: list[tuple[str, int, int]] = []
    offset = 0
    for block_id, text in texts:
        if text:
            spans.append((block_id, offset, offset + len(text)))
            offset += len(text) + 1
    start = " ".join(text for _, text in texts if text).find(quote)
    if start < 0:
        return cited
    end = start + len(quote)
    spanned = [block_id for block_id, low, high in spans if low < end and start < high]
    return cited if len(spanned) == len(cited.block_ids) else index._blocks_ref(spanned)


def _with_quantity_blocks(
    index: DocIndex, cited: CitedRef, narrowed: CitedRef, specs: Sequence[NumberSpec]
) -> CitedRef:
    """``narrowed`` plus the cited blocks holding quantities of the fact that it lacks.

    Narrowing must not make rule 4 stricter than the citation the model wrote; the blocks kept
    for a quantity are shown in the evidence too. A quantity that no single cited block holds
    keeps the whole citation.
    """
    kept = set(narrowed.block_ids)
    for spec in specs:
        if _spec_supported(index, spec, narrowed) or not _spec_supported(index, spec, cited):
            continue
        holders = [
            block_id
            for block_id in cited.block_ids
            if _spec_supported(index, spec, index._blocks_ref([block_id]))
        ]
        if not holders:
            return cited
        kept.add(holders[0])
    if len(kept) == len(narrowed.block_ids):
        return narrowed
    return index._blocks_ref([block_id for block_id in cited.block_ids if block_id in kept])


def _spec_supported(index: DocIndex, spec: NumberSpec, cited: CitedRef) -> bool:
    available = index.numbers(cited.context)
    if not spec.signed:
        available = _unsigned(available)
    for candidates in spec.values:
        wanted = candidates if spec.signed else _unsigned(candidates)
        if not wanted & available:
            return False
    if spec.units:
        key = _unit_key(cited.context)
        if not all(unit in key for unit in spec.units):
            return False
    return True


def verify_citation(
    index: DocIndex, citation: Citation, specs: Sequence[NumberSpec] = ()
) -> CitationCheck:
    """Verify one citation of a fact whose quantities are ``specs`` (rules 1–3)."""
    try:
        cited = index.resolve(citation.block_id)
    except CitationRefError as exc:
        return CitationCheck(citation.block_id, citation.quote, "failed", None, str(exc))
    quote = _clean_quote(citation.quote, cited.kind)
    if quote is not None:
        matched = _match_quote(index, cited, quote)
        if matched is None:
            return CitationCheck(
                citation.block_id, quote, "failed", cited, "quote not found in the cited text"
            )
        if matched.kind == "blocks" and matched.block_ids != cited.block_ids:
            matched = _with_quantity_blocks(index, cited, matched, specs)
        return CitationCheck(citation.block_id, quote, "verified", matched)
    if specs and not any(_spec_supported(index, spec, cited) for spec in specs):
        return CitationCheck(
            citation.block_id,
            None,
            "failed",
            cited,
            "paraphrase: none of the stated quantities appears in the cited text",
        )
    return CitationCheck(citation.block_id, None, "unverified-paraphrase", cited)


def verify_fact(index: DocIndex, fact: KeyFact) -> FactCheck:
    """Verify every citation of ``fact`` and the fact-level quantity rule (rule 4)."""
    specs = [spec for spec in (parse_number_spec(raw) for raw in fact.numbers) if spec]
    text_specs = find_quantities(fact.text)
    all_specs = [*specs, *text_specs]
    checks: list[CitationCheck] = []
    seen: set[tuple[str, str | None]] = set()
    for citation in fact.citations:
        check = verify_citation(index, citation, all_specs)
        key = (check.cited.ref if check.cited else check.raw_id, check.quote)
        if check.status != "failed" and key in seen:
            continue
        seen.add(key)
        checks.append(check)
    if not fact.text.strip():
        for check in checks:
            _fail(check, "empty fact")
        return FactCheck(fact, checks, kept=False, reason="empty fact")
    alive = [check for check in checks if check.status != "failed"]
    if not alive:
        return FactCheck(fact, checks, kept=False, reason="no verifiable citation")
    missing = [
        spec.raw
        for spec in all_specs
        if not any(check.cited and _spec_supported(index, spec, check.cited) for check in alive)
    ]
    if missing:
        reason = "quantities not found in the cited evidence: " + ", ".join(missing)
        for check in alive:
            _fail(check, reason)
        return FactCheck(fact, checks, kept=False, reason=reason)
    kept_fact = KeyFact(
        text=fact.text,
        citations=[check.citation for check in alive],
        numbers=list(fact.numbers),
    )
    return FactCheck(kept_fact, checks, kept=True)


def _fail(check: CitationCheck, reason: str) -> None:
    check.status = "failed"
    check.reason = reason


# --------------------------------------------------------------------------- section bodies


def strip_markers(text: str) -> str:
    """Text without ``[[cite:…]]`` markers (for scoring, summaries and plain text)."""
    return re.sub(r"[ \t]+([.,;:!?])", r"\1", _MARKER_RE.sub("", text)).strip()


def split_sentences(line: str) -> list[str]:
    """Split one line into sentences, keeping trailing ``[[cite:…]]`` markers with each."""
    parts: list[str] = []
    start = 0
    for match in _SENTENCE_END_RE.finditer(line):
        parts.append(line[start : match.end()])
        start = match.end()
    if start < len(line):
        parts.append(line[start:])
    return [part for part in parts if part]


@dataclass
class MarkerCheck:
    """One ``[[cite:…]]`` marker of a section body."""

    raw_id: str
    status: CitationStatus
    cited: CitedRef | None = None
    reason: str | None = None


@dataclass
class SectionCheck:
    body: str
    markers: list[MarkerCheck] = field(default_factory=list)
    failed: list[MarkerCheck] = field(default_factory=list)
    dropped_sentences: int = 0


def unsupported_quantities(text: str, available: set[str]) -> list[str]:
    """Quantities stated in ``text`` whose value is not among the unsigned ``available`` ones."""
    return [
        spec.raw
        for spec in find_quantities(text)
        if not all(_unsigned(candidates) & available for candidates in spec.values)
    ]


def unsigned_values(texts: Iterable[str]) -> set[str]:
    """Unsigned candidate values of every number in ``texts`` (no caching)."""
    values: set[str] = set()
    for text in texts:
        values |= _unsigned(number_values(text))
    return values


def available_numbers(index: DocIndex, texts: Iterable[str]) -> set[str]:
    """Unsigned candidate values of every number in ``texts``."""
    available: set[str] = set()
    for value in texts:
        available |= _unsigned(index.numbers(value))
    return available


def verify_section_body(index: DocIndex, body: str) -> SectionCheck:
    """Verify the markers of a section body sentence by sentence.

    A sentence is dropped when one of its markers fails or when a quantity it states is missing
    from its cited text (or, for sentences without markers, from the whole document). Kept
    markers are rewritten with canonical ids and duplicates inside a sentence are removed.
    Fenced code is kept verbatim and never verified; it is recognised by the tracker that the
    renderer uses too (:mod:`docwiki.contracts.fences`), so both count the same markers.
    """
    body = _SINGLE_MARKER_RE.sub(lambda m: f"[[cite:{m.group(1)}]]", body)
    result = SectionCheck(body="")
    out_lines: list[str] = []
    fences = FenceTracker()
    for line in body.split("\n"):
        if fences.feed(line):
            out_lines.append(line)
            continue
        prefix_match = _LIST_PREFIX_RE.match(line)
        prefix = prefix_match.group(1) if prefix_match else ""
        content = line[len(prefix) :]
        lead = content[: len(content) - len(content.lstrip())]
        kept: list[str] = []
        for sentence in split_sentences(content):
            rendered = _check_sentence(index, sentence, result)
            if rendered is not None:
                kept.append(rendered)
        text = "".join(kept).strip()
        if content.strip() and not text:
            continue
        out_lines.append(escape_fence(prefix + lead + text) if text else line.rstrip())
    result.body = "\n".join(out_lines).strip("\n")
    return result


def _check_sentence(index: DocIndex, sentence: str, result: SectionCheck) -> str | None:
    markers = list(_MARKER_RE.finditer(sentence))
    plain = _MARKER_RE.sub("", sentence)
    if not markers:
        if unsupported_quantities(plain, index.all_numbers):
            result.dropped_sentences += 1
            return None
        return sentence
    checks: list[MarkerCheck] = []
    for marker in markers:
        try:
            cited = index.resolve(marker.group(1))
        except CitationRefError as exc:
            checks.append(MarkerCheck(marker.group(1), "failed", None, str(exc)))
            continue
        checks.append(MarkerCheck(marker.group(1), "unverified-paraphrase", cited))
    failed = [check for check in checks if check.status == "failed"]
    if not failed:
        available = available_numbers(
            index, [check.cited.context for check in checks if check.cited]
        )
        missing = unsupported_quantities(plain, available)
        if missing:
            for check in checks:
                check.status = "failed"
                check.reason = "quantities not found in the cited evidence: " + ", ".join(missing)
            failed = checks
    if failed:
        for check in checks:
            if check.status != "failed":
                check.status = "failed"
                check.reason = "sentence dropped: another marker failed"
        result.failed.extend(checks)
        result.dropped_sentences += 1
        return None
    seen: set[str] = set()
    pieces: list[str] = []
    cursor = 0
    for marker, check in zip(markers, checks, strict=True):
        pieces.append(sentence[cursor : marker.start()])
        cursor = marker.end()
        assert check.cited is not None
        if check.cited.ref in seen:
            continue
        seen.add(check.cited.ref)
        pieces.append(f"[[cite:{check.cited.ref}]]")
        result.markers.append(check)
    pieces.append(sentence[cursor:])
    return "".join(pieces)
