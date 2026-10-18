"""Locators: precise positions of extracted content, their keys and labels (evidence-contract §2).

Every locator variant carries a ``kind`` discriminator. ``locator_key`` is the file stem of the
evidence sidecar (``evidence/<source_id>/<locator_key>.md``); ``locator_label`` is the human label
used in footnotes. ``parse_locator_key`` reverses a key into its parts (lossy only for the parts
that are not encoded in the key, such as the bounding box or the exact sheet name).
"""

from __future__ import annotations

import re
from typing import Annotated, Literal, get_args

from pydantic import Field, model_validator

from docwiki.contracts._base import BBox, ContractModel, Kebab, NonEmptyStr
from docwiki.contracts.ids import slugify_ascii

__all__ = [
    "LOCATOR_KINDS",
    "CsvRowsLocator",
    "DocxParagraphLocator",
    "DocxTableLocator",
    "EmlPartLocator",
    "ImageRegionLocator",
    "Locator",
    "LocatorKeyParts",
    "LocatorKind",
    "PdfPageLocator",
    "PptxSlideLocator",
    "TextLinesLocator",
    "VttCueLocator",
    "XlsxRowsLocator",
    "is_locator_key",
    "locator_key",
    "locator_label",
    "parse_locator_key",
]

LocatorKind = Literal[
    "pdf-page",
    "docx-paragraph",
    "docx-table",
    "xlsx-rows",
    "csv-rows",
    "pptx-slide",
    "eml-part",
    "vtt-cue",
    "image-region",
    "text-lines",
]
LOCATOR_KINDS: tuple[str, ...] = get_args(LocatorKind)

PositiveInt = Annotated[int, Field(ge=1)]
CueTime = Annotated[str, Field(pattern=r"^\d{2,}:[0-5]\d:[0-5]\d$")]
ColumnLetters = Annotated[str, Field(pattern=r"^[A-Z]{1,3}$")]


def _check_range(start: int | None, end: int | None, what: str) -> None:
    if (start is None) != (end is None):
        raise ValueError(f"{what}_start and {what}_end must be given together")
    if start is not None and end is not None and end < start:
        raise ValueError(f"{what}_end must be >= {what}_start")


class PdfPageLocator(ContractModel):
    """PDF page (text layer or scan). ``bbox`` is normalised, origin top-left."""

    kind: Literal["pdf-page"] = "pdf-page"
    page: PositiveInt
    bbox: BBox | None = None


class DocxParagraphLocator(ContractModel):
    """DOCX body paragraph, 1-based index over body paragraphs."""

    kind: Literal["docx-paragraph"] = "docx-paragraph"
    paragraph: PositiveInt


class DocxTableLocator(ContractModel):
    """DOCX table (1-based) and row range (1-based, header row = 1)."""

    kind: Literal["docx-table"] = "docx-table"
    table: PositiveInt
    row_start: PositiveInt
    row_end: PositiveInt

    @model_validator(mode="after")
    def _rows(self) -> DocxTableLocator:
        _check_range(self.row_start, self.row_end, "row")
        return self


class XlsxRowsLocator(ContractModel):
    """XLSX sheet rows (1-based, header = row 1).

    ``sheet_slug`` is the collision-free slug assigned per workbook by the extractor
    (``assign_unique_slugs(sheet_names, max_len=40, fallback="sheet")``); when omitted the slug is
    derived from ``sheet``.
    """

    kind: Literal["xlsx-rows"] = "xlsx-rows"
    sheet: NonEmptyStr
    sheet_slug: Kebab | None = None
    row_start: PositiveInt
    row_end: PositiveInt
    cols: list[ColumnLetters] | None = None

    @model_validator(mode="after")
    def _rows(self) -> XlsxRowsLocator:
        _check_range(self.row_start, self.row_end, "row")
        return self


class CsvRowsLocator(ContractModel):
    """CSV rows (1-based, header = row 1)."""

    kind: Literal["csv-rows"] = "csv-rows"
    row_start: PositiveInt
    row_end: PositiveInt

    @model_validator(mode="after")
    def _rows(self) -> CsvRowsLocator:
        _check_range(self.row_start, self.row_end, "row")
        return self


class PptxSlideLocator(ContractModel):
    """PPTX slide (1-based) and optional shape name/id."""

    kind: Literal["pptx-slide"] = "pptx-slide"
    slide: PositiveInt
    shape: str | None = None


_EML_PART_RE = re.compile(r"^(headers|body|attachment:.+)$", re.DOTALL)


class EmlPartLocator(ContractModel):
    """E-mail part (``headers``, ``body`` or ``attachment:<name>``) and optional line range."""

    kind: Literal["eml-part"] = "eml-part"
    part: NonEmptyStr
    line_start: PositiveInt | None = None
    line_end: PositiveInt | None = None

    @model_validator(mode="after")
    def _part(self) -> EmlPartLocator:
        if not _EML_PART_RE.match(self.part):
            raise ValueError("part must be 'headers', 'body' or 'attachment:<name>'")
        _check_range(self.line_start, self.line_end, "line")
        return self


class VttCueLocator(ContractModel):
    """Transcript cue range, ``HH:MM:SS`` (milliseconds truncated by the extractor)."""

    kind: Literal["vtt-cue"] = "vtt-cue"
    cue_start: CueTime
    cue_end: CueTime

    @model_validator(mode="after")
    def _times(self) -> VttCueLocator:
        if _seconds(self.cue_end) < _seconds(self.cue_start):
            raise ValueError("cue_end must be >= cue_start")
        return self


class ImageRegionLocator(ContractModel):
    """Region of a scanned image or photo (``page`` is always 1)."""

    kind: Literal["image-region"] = "image-region"
    page: Literal[1] = 1
    region: PositiveInt
    bbox: BBox


class TextLinesLocator(ContractModel):
    """Line range of a Markdown or plain-text file (1-based)."""

    kind: Literal["text-lines"] = "text-lines"
    line_start: PositiveInt
    line_end: PositiveInt

    @model_validator(mode="after")
    def _lines(self) -> TextLinesLocator:
        _check_range(self.line_start, self.line_end, "line")
        return self


Locator = Annotated[
    PdfPageLocator
    | DocxParagraphLocator
    | DocxTableLocator
    | XlsxRowsLocator
    | CsvRowsLocator
    | PptxSlideLocator
    | EmlPartLocator
    | VttCueLocator
    | ImageRegionLocator
    | TextLinesLocator,
    Field(discriminator="kind"),
]
"""Discriminated union of all locator variants (``kind`` is required in serialised form)."""


def _seconds(cue: str) -> int:
    hours, minutes, seconds = (int(part) for part in cue.split(":"))
    return hours * 3600 + minutes * 60 + seconds


def _sheet_slug(locator: XlsxRowsLocator) -> str:
    return locator.sheet_slug or slugify_ascii(locator.sheet, 40) or "sheet"


_LINES_SUFFIX_RE = re.compile(r"-l\d{4,}-l\d{4,}$")


def _eml_part_slug(part: str) -> str:
    if part in ("headers", "body"):
        return part
    name = part.removeprefix("attachment:")
    slug = "att-" + (slugify_ascii(name, 40) or "file")
    if _LINES_SUFFIX_RE.search(slug):
        slug += "-f"  # keep keys unambiguous with the optional line-range suffix
    return slug


def locator_key(locator: Locator) -> str:
    """Stable sidecar key of a locator (``p0003``, ``sheet-plan-r0012-r0020``…)."""
    match locator:
        case PdfPageLocator():
            return f"p{locator.page:04d}"
        case DocxParagraphLocator():
            return f"para-{locator.paragraph:04d}"
        case DocxTableLocator():
            return f"tbl-{locator.table:02d}-r{locator.row_start:04d}-r{locator.row_end:04d}"
        case XlsxRowsLocator():
            return f"sheet-{_sheet_slug(locator)}-r{locator.row_start:04d}-r{locator.row_end:04d}"
        case CsvRowsLocator():
            return f"r{locator.row_start:04d}-r{locator.row_end:04d}"
        case PptxSlideLocator():
            return f"slide-{locator.slide:02d}"
        case EmlPartLocator():
            key = f"msg-{_eml_part_slug(locator.part)}"
            if locator.line_start is not None:
                key += f"-l{locator.line_start:04d}-l{locator.line_end:04d}"
            return key
        case VttCueLocator():
            return "cue-" + locator.cue_start.replace(":", "-")
        case ImageRegionLocator():
            return f"img-b{locator.region:02d}"
        case TextLinesLocator():
            return f"l{locator.line_start:04d}-l{locator.line_end:04d}"
    raise TypeError(f"not a locator: {locator!r}")  # pragma: no cover


def _range(noun: str, start: int, end: int) -> str:
    return f"{noun} {start}" if start == end else f"{noun}s {start}–{end}"


def _cue_label(start: str, end: str) -> str:
    def short(value: str) -> str:
        hours, rest = value.split(":", 1)
        return rest if int(hours) == 0 else value

    if start.startswith("00:") and end.startswith("00:"):
        return f"{short(start)}–{short(end)}"
    return f"{start}–{end}"


def locator_label(locator: Locator) -> str:
    """Human label used in footnotes and sidecar headings (``p. 3``, ``slide 5``…)."""
    match locator:
        case PdfPageLocator():
            return f"p. {locator.page}"
        case DocxParagraphLocator():
            return f"¶ {locator.paragraph}"
        case DocxTableLocator():
            return f"table {locator.table}, {_range('row', locator.row_start, locator.row_end)}"
        case XlsxRowsLocator():
            rows = _range("row", locator.row_start, locator.row_end)
            return f'sheet "{locator.sheet}", {rows}'
        case CsvRowsLocator():
            return _range("row", locator.row_start, locator.row_end)
        case PptxSlideLocator():
            return f"slide {locator.slide}"
        case EmlPartLocator():
            if locator.part == "headers":
                label = "message headers"
            elif locator.part == "body":
                label = "message body"
            else:
                label = f'attachment "{locator.part.removeprefix("attachment:")}"'
            if locator.line_start is not None and locator.line_end is not None:
                label += ", " + _range("line", locator.line_start, locator.line_end)
            return label
        case VttCueLocator():
            return _cue_label(locator.cue_start, locator.cue_end)
        case ImageRegionLocator():
            return f"region {locator.region}"
        case TextLinesLocator():
            return _range("line", locator.line_start, locator.line_end)
    raise TypeError(f"not a locator: {locator!r}")  # pragma: no cover


class LocatorKeyParts(ContractModel):
    """Parsed form of a locator key (only the information encoded in the key)."""

    kind: LocatorKind
    page: int | None = None
    paragraph: int | None = None
    table: int | None = None
    row_start: int | None = None
    row_end: int | None = None
    sheet_slug: str | None = None
    slide: int | None = None
    part: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    cue_start: str | None = None
    region: int | None = None

    @property
    def key(self) -> str:
        """Re-format the key (``parse_locator_key(k).key == k`` for every valid key)."""
        match self.kind:
            case "pdf-page":
                return f"p{self.page:04d}"
            case "docx-paragraph":
                return f"para-{self.paragraph:04d}"
            case "docx-table":
                return f"tbl-{self.table:02d}-r{self.row_start:04d}-r{self.row_end:04d}"
            case "xlsx-rows":
                return f"sheet-{self.sheet_slug}-r{self.row_start:04d}-r{self.row_end:04d}"
            case "csv-rows":
                return f"r{self.row_start:04d}-r{self.row_end:04d}"
            case "pptx-slide":
                return f"slide-{self.slide:02d}"
            case "eml-part":
                key = f"msg-{self.part}"
                if self.line_start is not None:
                    key += f"-l{self.line_start:04d}-l{self.line_end:04d}"
                return key
            case "vtt-cue":
                return "cue-" + (self.cue_start or "").replace(":", "-")
            case "image-region":
                return f"img-b{self.region:02d}"
            case "text-lines":
                return f"l{self.line_start:04d}-l{self.line_end:04d}"
        raise ValueError(f"unknown locator kind {self.kind!r}")  # pragma: no cover


_SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_KEY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("pdf-page", re.compile(r"^p(?P<page>\d{4,})$")),
    ("docx-paragraph", re.compile(r"^para-(?P<paragraph>\d{4,})$")),
    (
        "docx-table",
        re.compile(r"^tbl-(?P<table>\d{2,})-r(?P<row_start>\d{4,})-r(?P<row_end>\d{4,})$"),
    ),
    (
        "xlsx-rows",
        re.compile(
            rf"^sheet-(?P<sheet_slug>{_SLUG})-r(?P<row_start>\d{{4,}})-r(?P<row_end>\d{{4,}})$"
        ),
    ),
    ("csv-rows", re.compile(r"^r(?P<row_start>\d{4,})-r(?P<row_end>\d{4,})$")),
    ("pptx-slide", re.compile(r"^slide-(?P<slide>\d{2,})$")),
    (
        "eml-part",
        re.compile(
            rf"^msg-(?P<part>headers|body|att-{_SLUG}?)(?:-l(?P<line_start>\d{{4,}})-l(?P<line_end>\d{{4,}}))?$"
        ),
    ),
    ("vtt-cue", re.compile(r"^cue-(?P<h>\d{2,})-(?P<m>[0-5]\d)-(?P<s>[0-5]\d)$")),
    ("image-region", re.compile(r"^img-b(?P<region>\d{2,})$")),
    ("text-lines", re.compile(r"^l(?P<line_start>\d{4,})-l(?P<line_end>\d{4,})$")),
)
_INT_FIELDS = (
    "page",
    "paragraph",
    "table",
    "row_start",
    "row_end",
    "slide",
    "line_start",
    "line_end",
    "region",
)


def parse_locator_key(key: str) -> LocatorKeyParts:
    """Parse a sidecar key; raises ``ValueError`` when it is not a canonical key."""
    for kind, pattern in _KEY_PATTERNS:
        match = pattern.match(key)
        if not match:
            continue
        groups = {name: value for name, value in match.groupdict().items() if value is not None}
        values: dict[str, object] = {"kind": kind}
        for name, value in groups.items():
            if name in _INT_FIELDS:
                values[name] = int(value)
            elif name not in ("h", "m", "s"):
                values[name] = value
        if kind == "vtt-cue":
            values["cue_start"] = f"{groups['h']}:{groups['m']}:{groups['s']}"
        parts = LocatorKeyParts.model_validate(values)
        if parts.key != key:
            raise ValueError(f"locator key is not canonical: {key!r} (expected {parts.key!r})")
        for start, end in (("row_start", "row_end"), ("line_start", "line_end")):
            low, high = getattr(parts, start), getattr(parts, end)
            if low is not None and (low < 1 or high < low):
                raise ValueError(f"invalid range in locator key {key!r}")
        for name in ("page", "paragraph", "table", "slide", "region"):
            value = getattr(parts, name)
            if value is not None and value < 1:
                raise ValueError(f"locator numbers are 1-based: {key!r}")
        return parts
    raise ValueError(f"unknown locator key format: {key!r}")


def is_locator_key(key: str) -> bool:
    try:
        parse_locator_key(key)
    except ValueError:
        return False
    return True
