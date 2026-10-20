import pytest
from pydantic import TypeAdapter, ValidationError

from docwiki.contracts.locators import (
    CsvRowsLocator,
    DocxParagraphLocator,
    DocxTableLocator,
    EmlPartLocator,
    ImageRegionLocator,
    Locator,
    PdfPageLocator,
    PptxSlideLocator,
    TextLinesLocator,
    VttCueLocator,
    XlsxRowsLocator,
    is_locator_key,
    locator_key,
    locator_label,
    parse_locator_key,
)

CASES = [
    (PdfPageLocator(page=3, bbox=[0.1, 0.2, 0.5, 0.4]), "p0003", "p. 3"),
    (DocxParagraphLocator(paragraph=42), "para-0042", "¶ 42"),
    (DocxTableLocator(table=2, row_start=3, row_end=7), "tbl-02-r0003-r0007", "table 2, rows 3–7"),
    (DocxTableLocator(table=2, row_start=3, row_end=3), "tbl-02-r0003-r0003", "table 2, row 3"),
    (
        XlsxRowsLocator(sheet="Planning", row_start=12, row_end=20),
        "sheet-planning-r0012-r0020",
        'sheet "Planning", rows 12–20',
    ),
    (
        XlsxRowsLocator(
            sheet="Résumé 2026", sheet_slug="resume-2026-2", row_start=2, row_end=2, cols=["B", "D"]
        ),
        "sheet-resume-2026-2-r0002-r0002",
        'sheet "Résumé 2026", row 2',
    ),
    (
        XlsxRowsLocator(sheet="計画", row_start=1, row_end=4),
        "sheet-sheet-r0001-r0004",
        'sheet "計画", rows 1–4',
    ),
    (CsvRowsLocator(row_start=12, row_end=20), "r0012-r0020", "rows 12–20"),
    (PptxSlideLocator(slide=5), "slide-05", "slide 5"),
    (PptxSlideLocator(slide=123, shape="Title 1"), "slide-123", "slide 123"),
    (
        EmlPartLocator(part="body", line_start=10, line_end=18),
        "msg-body-l0010-l0018",
        "message body, lines 10–18",
    ),
    (EmlPartLocator(part="headers"), "msg-headers", "message headers"),
    (
        EmlPartLocator(part="attachment:Rapport final.pdf"),
        "msg-att-rapport-final-pdf",
        'attachment "Rapport final.pdf"',
    ),
    (VttCueLocator(cue_start="00:03:15", cue_end="00:03:42"), "cue-00-03-15", "03:15–03:42"),
    (VttCueLocator(cue_start="01:03:15", cue_end="01:04:00"), "cue-01-03-15", "01:03:15–01:04:00"),
    (ImageRegionLocator(region=7, bbox=[0, 0, 1, 1]), "img-b07", "region 7"),
    (TextLinesLocator(line_start=10, line_end=18), "l0010-l0018", "lines 10–18"),
    (TextLinesLocator(line_start=4, line_end=4), "l0004-l0004", "line 4"),
]


@pytest.mark.parametrize(("locator", "key", "label"), CASES)
def test_locator_key_label_and_round_trip(locator: Locator, key: str, label: str) -> None:
    assert locator_key(locator) == key
    assert locator_label(locator) == label
    parts = parse_locator_key(key)
    assert parts.kind == locator.kind
    assert parts.key == key
    assert is_locator_key(key)


def test_parse_locator_key_recovers_encoded_fields() -> None:
    parts = parse_locator_key("sheet-r0001-r0012-r0020")
    assert (parts.sheet_slug, parts.row_start, parts.row_end) == ("r0001", 12, 20)
    parts = parse_locator_key("msg-body-l0010-l0018")
    assert (parts.part, parts.line_start, parts.line_end) == ("body", 10, 18)
    assert parse_locator_key("cue-00-03-15").cue_start == "00:03:15"
    assert parse_locator_key("p12345").page == 12345


def test_attachment_names_cannot_collide_with_line_suffix() -> None:
    tricky = EmlPartLocator(part="attachment:x l0001 l0002")
    key = locator_key(tricky)
    assert key == "msg-att-x-l0001-l0002-f"
    parts = parse_locator_key(key)
    assert parts.part == "att-x-l0001-l0002-f" and parts.line_start is None
    with_lines = EmlPartLocator(part="attachment:x", line_start=1, line_end=2)
    parts = parse_locator_key(locator_key(with_lines))
    assert (parts.part, parts.line_start, parts.line_end) == ("att-x", 1, 2)


@pytest.mark.parametrize(
    "key",
    [
        "",
        "p3",
        "p0000",
        "P0003",
        "page-0003",
        "r0012-r0010",
        "slide-5",
        "cue-00-61-00",
        "img-b7",
        "sheet--r0001-r0002",
        "l0001",
    ],
)
def test_invalid_locator_keys(key: str) -> None:
    assert not is_locator_key(key)
    with pytest.raises(ValueError):
        parse_locator_key(key)


def test_locator_validation_errors() -> None:
    with pytest.raises(ValidationError):
        CsvRowsLocator(row_start=5, row_end=4)
    with pytest.raises(ValidationError):
        PdfPageLocator(page=0)
    with pytest.raises(ValidationError):
        PdfPageLocator(page=1, bbox=[0.5, 0.5, 0.4, 0.6])
    with pytest.raises(ValidationError):
        PdfPageLocator(page=1, bbox=[0, 0, 2, 1])
    with pytest.raises(ValidationError):
        EmlPartLocator(part="footer")
    with pytest.raises(ValidationError):
        EmlPartLocator(part="body", line_start=3)
    with pytest.raises(ValidationError):
        VttCueLocator(cue_start="00:03:15", cue_end="00:03:14")
    with pytest.raises(ValidationError):
        ImageRegionLocator.model_validate(
            {"kind": "image-region", "page": 2, "region": 1, "bbox": [0, 0, 1, 1]}
        )
    with pytest.raises(ValidationError):
        XlsxRowsLocator(sheet="Planning", sheet_slug="Planning", row_start=1, row_end=2)


def test_locator_union_requires_kind_and_is_strict() -> None:
    adapter: TypeAdapter[Locator] = TypeAdapter(Locator)
    parsed = adapter.validate_python({"kind": "pptx-slide", "slide": 2})
    assert isinstance(parsed, PptxSlideLocator)
    assert adapter.validate_json('{"kind": "pdf-page", "page": 4}') == PdfPageLocator(page=4)
    for bad in (
        {"page": 4},
        {"kind": "pdf-page", "page": "4"},
        {"kind": "pdf-page", "page": 4, "extra": 1},
    ):
        with pytest.raises(ValidationError):
            adapter.validate_python(bad)
