"""Locator semantics used by the metrics: granularity matching, range compaction, labels.

Citation recall and precision compare locator keys (evidence-contract §2) at the granularity of
docs/spec/evals.md: the same page, paragraph, slide, cue or image region; overlapping row ranges
of the same sheet, DOCX table or CSV file; overlapping line ranges of a text file or of the same
e-mail part. ``*`` (used by the golden set for images, whose region numbering depends on the OCR
engine) matches any locator of the file.
"""

from __future__ import annotations

import functools
import re
import unicodedata
from collections.abc import Iterable

from docwiki.contracts import ExtractedDoc
from docwiki.contracts.locators import (
    CsvRowsLocator,
    DocxTableLocator,
    EmlPartLocator,
    LocatorKeyParts,
    XlsxRowsLocator,
    locator_key,
    parse_locator_key,
)

__all__ = [
    "ANY_LOCATOR",
    "compact_keys",
    "is_key",
    "keys_match",
    "locator_key_from_label",
]

ANY_LOCATOR = "*"


@functools.lru_cache(maxsize=65536)
def _parts(key: str) -> LocatorKeyParts | None:
    try:
        return parse_locator_key(key)
    except ValueError:
        return None


def is_key(key: str | None) -> bool:
    """A canonical locator key, or ``*``."""
    return key is not None and (key == ANY_LOCATOR or _parts(key) is not None)


def _overlap(
    a_start: int | None, a_end: int | None, b_start: int | None, b_end: int | None
) -> bool:
    if a_start is None or a_end is None or b_start is None or b_end is None:
        return False
    return a_start <= b_end and b_start <= a_end


def keys_match(first: str, second: str) -> bool:
    """Whether two locator keys of the same source designate overlapping evidence."""
    if ANY_LOCATOR in (first, second) or first == second:
        return True
    a, b = _parts(first), _parts(second)
    if a is None or b is None or a.kind != b.kind:
        return False
    match a.kind:
        case "pdf-page":
            return a.page == b.page
        case "docx-paragraph":
            return a.paragraph == b.paragraph
        case "docx-table":
            return a.table == b.table and _overlap(a.row_start, a.row_end, b.row_start, b.row_end)
        case "xlsx-rows":
            return a.sheet_slug == b.sheet_slug and _overlap(
                a.row_start, a.row_end, b.row_start, b.row_end
            )
        case "csv-rows":
            return _overlap(a.row_start, a.row_end, b.row_start, b.row_end)
        case "pptx-slide":
            return a.slide == b.slide
        case "eml-part":
            if a.part != b.part:
                return False
            if a.line_start is None or b.line_start is None:
                return True  # the whole part covers every line range of it
            return _overlap(a.line_start, a.line_end, b.line_start, b.line_end)
        case "vtt-cue":
            return a.cue_start == b.cue_start
        case "image-region":
            return a.region == b.region
        case "text-lines":
            return _overlap(a.line_start, a.line_end, b.line_start, b.line_end)
    return False  # pragma: no cover - every kind is handled above


def _merge(first: str, second: str) -> str | None:
    a, b = _parts(first), _parts(second)
    if a is None or b is None or a.kind != b.kind:
        return None
    if a.kind in ("csv-rows", "xlsx-rows", "docx-table"):
        if a.sheet_slug != b.sheet_slug or a.table != b.table:
            return None
        names, gap = ("row_start", "row_end"), 1
    elif a.kind == "text-lines" or (a.kind == "eml-part" and a.part == b.part):
        names, gap = ("line_start", "line_end"), 2  # blank lines separate text blocks
    else:
        return None
    start, end = getattr(a, names[0]), getattr(a, names[1])
    other_start, other_end = getattr(b, names[0]), getattr(b, names[1])
    if start is None or end is None or other_start is None or other_end is None:
        return None
    if other_start > end + gap or start > other_end + gap:
        return None
    merged = a.model_copy(update={names[0]: min(start, other_start), names[1]: max(end, other_end)})
    return merged.key


def compact_keys(keys: Iterable[str]) -> list[str]:
    """Distinct keys in first-use order, adjacent row and line ranges merged
    (``r0002-r0002``, ``r0003-r0003`` -> ``r0002-r0003``)."""
    result: list[str] = []
    for key in keys:
        if key in result:
            continue
        merged = _merge(result[-1], key) if result else None
        if merged is None:
            result.append(key)
        else:
            result[-1] = merged
    return result


# ------------------------------------------------------------------------------ labels

_DASHES = re.compile(r"\s*[\u2010-\u2015\u2212-]\s*")
_RANGE = r"(?P<start>\d+)(?:-(?P<end>\d+))?"
_LABELS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "query-table",
        re.compile(r"^table (?P<table>t\d+), rows? r(?P<start>\d+)(?:-r(?P<end>\d+))?$"),
    ),
    ("pdf-page", re.compile(r"^(?:pp?\.|page) ?(?P<page>\d+)(?:-\d+)?$")),
    ("docx-paragraph", re.compile(r"^(?:¶|para(?:graph)?\.?) ?(?P<paragraph>\d+)$")),
    ("docx-table", re.compile(rf"^table (?P<table>\d+), rows? {_RANGE}$")),
    ("xlsx-rows", re.compile(rf"^sheet \"(?P<sheet>.+)\", rows? {_RANGE}$")),
    ("csv-rows", re.compile(rf"^rows? {_RANGE}$")),
    ("pptx-slide", re.compile(r"^slide (?P<slide>\d+)$")),
    ("eml-headers", re.compile(r"^message headers$")),
    ("eml-body", re.compile(rf"^message body(?:, lines? {_RANGE})?$")),
    ("eml-attachment", re.compile(r"^attachment \"(?P<name>.+)\"$")),
    ("text-lines", re.compile(rf"^lines? {_RANGE}$")),
    ("image-region", re.compile(r"^region (?P<region>\d+)$")),
    ("vtt-cue", re.compile(r"^(?:(?P<h>\d{1,2}):)?(?P<m>\d{2}):(?P<s>\d{2})(?:-.*)?$")),
)


def _range(match: re.Match[str]) -> tuple[int, int]:
    start = int(match["start"])
    end = int(match["end"]) if match["end"] else start
    return start, max(start, end)


def _sheet_key(sheet: str, start: int, end: int, doc: ExtractedDoc | None) -> str:
    slug: str | None = None
    if doc is not None:
        for block in doc.blocks:
            locator = block.locator
            if isinstance(locator, XlsxRowsLocator) and locator.sheet == sheet:
                slug = locator.sheet_slug
                break
    return locator_key(XlsxRowsLocator(sheet=sheet, sheet_slug=slug, row_start=start, row_end=end))


def _query_table_key(table_id: str, start: int, end: int, doc: ExtractedDoc | None) -> str | None:
    if doc is None:
        return None
    try:
        table = doc.table(table_id)
    except KeyError:
        return None
    locator = table.locator
    if isinstance(locator, XlsxRowsLocator):
        return locator_key(locator.model_copy(update={"row_start": start, "row_end": end}))
    if isinstance(locator, CsvRowsLocator):
        return locator_key(CsvRowsLocator(row_start=start, row_end=end))
    if isinstance(locator, DocxTableLocator):
        return locator_key(DocxTableLocator(table=locator.table, row_start=start, row_end=end))
    return locator_key(locator)


def locator_key_from_label(label: str, *, doc: ExtractedDoc | None = None) -> str | None:
    """Locator key of a locator label (``p. 3`` -> ``p0003``, ``sheet "Stock", row 2`` ->
    ``sheet-stock-r0002-r0002``), for citations that carry a label but no sidecar path.

    ``table t01, rows r0002–r0004`` (rows returned by ``query_table``) needs the source's
    ExtractedDoc to know which sheet or table ``t01`` is. Returns ``None`` when unparseable.
    """
    text = _DASHES.sub("-", unicodedata.normalize("NFKC", label).strip().strip("`*_ "))
    lowered = text.casefold()
    for kind, pattern in _LABELS:
        match = pattern.match(text if kind in ("xlsx-rows", "eml-attachment") else lowered)
        if match is None:
            continue
        try:
            return _label_key(kind, match, doc)
        except ValueError:
            return None
    return None


def _label_key(kind: str, match: re.Match[str], doc: ExtractedDoc | None) -> str | None:
    match kind:
        case "query-table":
            start, end = _range(match)
            return _query_table_key(match["table"], start, end, doc)
        case "pdf-page":
            return f"p{int(match['page']):04d}"
        case "docx-paragraph":
            return f"para-{int(match['paragraph']):04d}"
        case "docx-table":
            start, end = _range(match)
            return locator_key(
                DocxTableLocator(table=int(match["table"]), row_start=start, row_end=end)
            )
        case "xlsx-rows":
            start, end = _range(match)
            return _sheet_key(match["sheet"], start, end, doc)
        case "csv-rows":
            start, end = _range(match)
            return locator_key(CsvRowsLocator(row_start=start, row_end=end))
        case "pptx-slide":
            return f"slide-{int(match['slide']):02d}"
        case "eml-headers":
            return "msg-headers"
        case "eml-body":
            if match["start"] is None:
                return "msg-body"
            start, end = _range(match)
            return locator_key(EmlPartLocator(part="body", line_start=start, line_end=end))
        case "eml-attachment":
            return locator_key(EmlPartLocator(part=f"attachment:{match['name']}"))
        case "text-lines":
            start, end = _range(match)
            return f"l{start:04d}-l{end:04d}"
        case "image-region":
            return f"img-b{int(match['region']):02d}"
        case "vtt-cue":
            hours = int(match["h"] or 0)
            return f"cue-{hours:02d}-{match['m']}-{match['s']}"
    return None  # pragma: no cover
