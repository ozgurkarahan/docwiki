"""Deterministic citation verification (evidence-contract §4)."""

from __future__ import annotations

import pytest
from compile_testkit import plan_doc, sop_b_doc, yaw_doc

from docwiki.contracts.compiled import Citation, KeyFact
from docwiki.contracts.locators import (
    DocxParagraphLocator,
    PdfPageLocator,
    XlsxRowsLocator,
    locator_key,
)
from docwiki.stages.verify_citations import (
    CitationRefError,
    DocIndex,
    find_quantities,
    normalize_text,
    number_values,
    parse_number_spec,
    split_sentences,
    strip_markers,
    verify_fact,
    verify_section_body,
)


@pytest.fixture(scope="module")
def sop() -> DocIndex:
    return DocIndex(sop_b_doc())


@pytest.fixture(scope="module")
def plan() -> DocIndex:
    return DocIndex(plan_doc())


def kf(text: str, *citations: tuple[str, str | None], numbers: tuple[str, ...] = ()) -> KeyFact:
    return KeyFact(
        text=text,
        citations=[Citation(block_id=block_id, quote=quote) for block_id, quote in citations],
        numbers=list(numbers),
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("\ufb01lter ＩＳＯ", "filter iso"),
        ("Straße", "strasse"),
        ("\u201cUse\u201d \u2018it\u2019 \u00abnow\u00bb", '"use" \'it\' "now"'),
        ("a\n\t  b ", "a b"),
        ("lubri\u00adcation", "lubrication"),
        ("\u221220 \u2013 30", "-20 - 30"),
        ("45\u00a0Nm", "45 nm"),
        ("zero\u200bwidth", "zerowidth"),
    ],
)
def test_normalize_text(raw: str, expected: str) -> None:
    assert normalize_text(raw) == expected


@pytest.mark.parametrize(
    ("text", "values"),
    [
        ("1,500 rpm", {"1500", "1.5"}),
        ("0,5 mm", {"0.5"}),
        ("1.234,5 kg", {"1234.5"}),
        ("1\u202f500 l", {"1500"}),
        ("\u221220 °C", {"-20"}),
        ("WTG-07", {"7"}),
        ("M20 bolts", {"20"}),
        ("12Nm", {"12"}),
        ("10\u201312 Nm", {"10", "12"}),
    ],
)
def test_number_values(text: str, values: set[str]) -> None:
    assert number_values(text) == values


def test_number_specs_and_quantities() -> None:
    spec = parse_number_spec("-20 °C")
    assert spec is not None and spec.values == (frozenset({"-20"}),) and spec.units == ("°c",)
    assert parse_number_spec("ISO VG 320").units == ("iso", "vg")  # type: ignore[union-attr]
    assert parse_number_spec("no digits") is None
    found = [spec.raw for spec in find_quantities("Drain for 6 hours at -20 °C; 45 Nm, 5%.")]
    assert found == ["6 hours", "-20 °C", "45 Nm", "5%"]
    assert find_quantities("SOP-GBX-010 revision B of 2026-03") == []


def test_resolve_ids(sop: DocIndex) -> None:
    assert sop.resolve("b3").ref == "b0003"
    assert sop.resolve("B0003").ref == "b0003"
    assert sop.resolve("[[cite:b0003]]").ref == "b0003"
    both = sop.resolve("b0004, b0003")
    assert both.ref == "b0003,b0004" and both.block_ids == ("b0003", "b0004")
    assert sop.resolve("b0003-b0004").block_ids == ("b0003", "b0004")
    row = sop.resolve("t1:r2")
    assert (row.kind, row.ref, row.rows) == (
        "table-rows",
        "t01:r0002",
        (("WTG-07", "ISO VG 220", "12 months"),),
    )
    assert sop.resolve("t01").kind == "table"
    figure = sop.resolve("f01")
    assert figure.kind == "figure" and figure.provenance == "model-description"
    assert figure.locator.bbox == [0.2, 0.5, 0.6, 0.8]  # type: ignore[union-attr]
    for bad in ("b0099", "t01:r0099", "t09", "f09", "b0003,t01:r0002", "x12", ""):
        with pytest.raises(CitationRefError):
            sop.resolve(bad)


def test_verified_quote_after_normalisation(sop: DocIndex) -> None:
    quote = "“USE ISO VG 220 GEARBOX OIL”"
    check = verify_fact(sop, kf("Cold sites use ISO VG 220.", ("b0003", quote)))
    assert check.kept
    assert [c.status for c in check.checks] == ["verified"]
    assert check.fact.citations[0].quote == "USE ISO VG 220 GEARBOX OIL"


def test_quote_across_cited_blocks(sop: DocIndex) -> None:
    check = verify_fact(
        sop,
        kf("WTG-07 switches first.", ("b0003,b0004", "WTG-07 switches first. Tighten the drain")),
    )
    assert check.kept and check.checks[0].cited.block_ids == ("b0003", "b0004")  # type: ignore[union-attr]


def test_multi_block_quote_is_narrowed_to_the_quoted_block() -> None:
    check = verify_fact(
        DocIndex(yaw_doc()),
        kf(
            "The yaw bolts are tightened to 450 Nm.",
            ("b0001,b0002", "Tighten the yaw bolts to 450 Nm"),
            numbers=("450 Nm",),
        ),
    )
    assert check.kept
    [citation] = check.checks
    assert citation.status == "verified" and citation.cited is not None
    assert citation.cited.block_ids == ("b0002",)
    assert citation.cited.locator == DocxParagraphLocator(paragraph=2)
    assert check.fact.citations == [
        Citation(block_id="b0002", quote="Tighten the yaw bolts to 450 Nm")
    ]


def test_quote_running_across_paragraphs_keeps_the_spanned_blocks() -> None:
    check = verify_fact(
        DocIndex(yaw_doc()),
        kf(
            "The main bearing is checked before the yaw bolts are tightened.",
            ("b0001-b0003", "check the main bearing. Tighten the yaw bolts"),
        ),
    )
    assert check.kept and check.checks[0].cited is not None
    assert check.checks[0].cited.block_ids == ("b0001", "b0002")
    assert locator_key(check.checks[0].cited.locator) == "para-0001"
    assert check.fact.citations[0].block_id == "b0001,b0002"


def test_narrowing_keeps_the_cited_blocks_holding_the_quantities() -> None:
    check = verify_fact(
        DocIndex(yaw_doc()),
        kf(
            "After the main bearing check the yaw bolts are tightened to 450 Nm.",
            ("b0001,b0002,b0003", "check the main bearing"),
            numbers=("450 Nm",),
        ),
    )
    assert check.kept and check.checks[0].cited is not None
    assert check.checks[0].cited.block_ids == ("b0001", "b0002")


def test_narrowing_on_one_pdf_page_keeps_the_quoted_box(sop: DocIndex) -> None:
    check = verify_fact(
        sop,
        kf(
            "The drain plug is tightened to 45 Nm.",
            ("b0003,b0004", "Tighten the drain plug to 45 Nm"),
            numbers=("45 Nm",),
        ),
    )
    assert check.kept and check.checks[0].cited is not None
    assert check.checks[0].cited.block_ids == ("b0004",)
    assert check.checks[0].cited.locator == PdfPageLocator(page=1, bbox=[0.1, 0.45, 0.9, 0.5])


def test_bad_quote_fails_and_drops_the_fact(sop: DocIndex) -> None:
    check = verify_fact(sop, kf("Heat the oil.", ("b0004", "heat the oil to 80 °C")))
    assert not check.kept
    assert check.checks[0].status == "failed"
    assert check.checks[0].reason == "quote not found in the cited text"


def test_unknown_block_fails(sop: DocIndex) -> None:
    check = verify_fact(sop, kf("Something.", ("b0042", "Something")))
    assert not check.kept and check.checks[0].reason == "unknown block id b0042"


def test_paraphrase_rules(sop: DocIndex) -> None:
    plain = verify_fact(sop, kf("WTG-07 goes first.", ("b0003", None)))
    assert plain.kept and plain.checks[0].status == "unverified-paraphrase"
    numbers = verify_fact(sop, kf("The plug takes 45 Nm.", ("b0004", None), numbers=("45 Nm",)))
    assert numbers.kept and numbers.checks[0].status == "unverified-paraphrase"
    wrong = verify_fact(sop, kf("The plug takes 45 Nm.", ("b0003", None), numbers=("45 Nm",)))
    assert not wrong.kept and wrong.checks[0].status == "failed"


def test_numbers_must_appear_in_cited_text(sop: DocIndex) -> None:
    mismatch = verify_fact(
        sop,
        kf(
            "The plug is tightened to 50 Nm.",
            ("b0004", "Tighten the drain plug"),
            numbers=("50 Nm",),
        ),
    )
    assert not mismatch.kept
    assert mismatch.checks[0].status == "failed"
    assert "50 Nm" in (mismatch.reason or "")
    unit = verify_fact(sop, kf("Torque.", ("b0004", "Tighten the drain plug"), numbers=("45 kNm",)))
    assert not unit.kept
    minus = verify_fact(sop, kf("Below -20 °C.", ("b0003", "use ISO VG 220"), numbers=("-20 °C",)))
    assert minus.kept
    in_text = verify_fact(sop, kf("Tighten to 60 Nm.", ("b0004", "Tighten the drain plug")))
    assert not in_text.kept, "quantities stated in the fact text are checked too"


def test_table_row_cells(sop: DocIndex, plan: DocIndex) -> None:
    ok = verify_fact(
        sop, kf("Interval.", ("t01:r0002", "WTG-07 | 12 months"), numbers=("12 months",))
    )
    assert ok.kept and ok.checks[0].status == "verified"
    wrong_row = verify_fact(sop, kf("Interval.", ("t01:r0002", "WTG-07 | 18 months")))
    assert not wrong_row.kept
    boundary = verify_fact(plan, kf("Two hours.", ("t01:r0002", "2")))
    assert not boundary.kept, "a cell value must match on word boundaries"
    narrowed = verify_fact(sop, kf("WTG-12 uses ISO VG 320.", ("t01", "ISO VG 320")))
    assert narrowed.kept and narrowed.checks[0].cited.row_ids == ("r0003",)  # type: ignore[union-attr]
    row = verify_fact(plan, kf("WTG-12 oil.", ("t01:r0004", "ISO VG 220")))
    locator = row.checks[0].cited.locator  # type: ignore[union-attr]
    assert isinstance(locator, XlsxRowsLocator)
    assert (locator.sheet, locator.row_start, locator.row_end) == ("Plan", 4, 4)
    assert row.checks[0].cited.provenance == "deterministic-table"  # type: ignore[union-attr]


def test_figure_caption_and_description(sop: DocIndex) -> None:
    caption = verify_fact(sop, kf("Drain plug.", ("f01", "Drain plug location")))
    assert caption.kept and caption.checks[0].cited.provenance == "native-text"  # type: ignore[union-attr]
    description = verify_fact(sop, kf("Drain plug.", ("f01", "gearbox drain plug")))
    assert description.checks[0].cited.provenance == "model-description"  # type: ignore[union-attr]


def test_short_quotes_count_as_paraphrase_and_duplicates_collapse(sop: DocIndex) -> None:
    check = verify_fact(sop, kf("WTG-07 goes first.", ("b0003", "“ ”"), ("b0003", None)))
    assert [c.status for c in check.checks] == ["unverified-paraphrase"]
    assert check.fact.citations == [Citation(block_id="b0003", quote=None)]


def test_section_markers(sop: DocIndex) -> None:
    body = (
        "Cold sites use ISO VG 220.[[cite:b3]][[cite:b0003]] Invented step.[[cite:b0099]]\n"
        "- The plug takes 45 Nm.[cite:b0004]\n"
        "- The plug takes 60 Nm.[[cite:b0004]]\n"
        "The sump holds 300 l. Torque is 45 Nm.\n"
        "```\nraw [[cite:b0099]] 999 l\n```"
    )
    result = verify_section_body(sop, body)
    assert result.body == (
        "Cold sites use ISO VG 220.[[cite:b0003]]\n"
        "- The plug takes 45 Nm.[[cite:b0004]]\n"
        "Torque is 45 Nm.\n"
        "```\nraw [[cite:b0099]] 999 l\n```"
    )
    assert [m.cited.ref for m in result.markers] == ["b0003", "b0004"]  # type: ignore[union-attr]
    assert all(m.status == "unverified-paraphrase" for m in result.markers)
    assert {m.raw_id for m in result.failed} == {"b0099", "b0004"}
    assert all(m.status == "failed" for m in result.failed)
    assert result.dropped_sentences == 3


def test_sentence_helpers() -> None:
    assert split_sentences("One.[[cite:b0001]] Two [[cite:b0002]]. Three") == [
        "One.[[cite:b0001]]",
        " Two [[cite:b0002]].",
        " Three",
    ]
    assert strip_markers("Oil is ISO VG 220 [[cite:b0003]].") == "Oil is ISO VG 220."
