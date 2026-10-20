"""Deterministic citation verification (evidence-contract §4)."""

from __future__ import annotations

import pytest
from compile_testkit import amendment_doc, plan_doc, quote_b_doc

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
def quote() -> DocIndex:
    return DocIndex(quote_b_doc())


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
        ("\ufb01nitions ＨＴ", "finitions ht"),
        ("Straße", "strasse"),
        ("\u00abLa baie\u00bb \u2018F1\u2019 \u201cposée\u201d", '"la baie" \'f1\' "posée"'),
        ("a\n\t  b ", "a b"),
        ("menui\u00adseries", "menuiseries"),
        ("\u22125 \u2013 30", "-5 - 30"),
        ("30,00\u00a0m²", "30,00 m2"),
        ("zero\u200bwidth", "zerowidth"),
    ],
)
def test_normalize_text(raw: str, expected: str) -> None:
    assert normalize_text(raw) == expected


@pytest.mark.parametrize(
    ("text", "values"),
    [
        ("2,500 kg", {"2500", "2.5"}),
        ("0,5 mm", {"0.5"}),
        ("1.234,5 kg", {"1234.5"}),
        ("12\u202f500,00 €", {"12500"}),
        ("\u22125 °C", {"-5"}),
        ("BC-2026-009", {"2026", "9"}),
        ("T07 delivery", {"7"}),
        ("30cm", {"30"}),
        ("10\u201312 cm", {"10", "12"}),
    ],
)
def test_number_values(text: str, values: set[str]) -> None:
    assert number_values(text) == values


def test_number_specs_and_quantities() -> None:
    spec = parse_number_spec("-5 °C")
    assert spec is not None and spec.values == (frozenset({"-5"}),) and spec.units == ("°c",)
    assert parse_number_spec("bloc béton 20450").units == ("bloc", "béton")  # type: ignore[union-attr]
    assert parse_number_spec("no digits") is None
    found = [spec.raw for spec in find_quantities("Delivery in 6 weeks at -5 °C; 3,00 m, 5%.")]
    assert found == ["6 weeks", "-5 °C", "3,00 m", "5%"]
    assert find_quantities("DEV-2026-014 indice B of 2026-03") == []


def test_resolve_ids(quote: DocIndex) -> None:
    assert quote.resolve("b3").ref == "b0003"
    assert quote.resolve("B0003").ref == "b0003"
    assert quote.resolve("[[cite:b0003]]").ref == "b0003"
    both = quote.resolve("b0004, b0003")
    assert both.ref == "b0003,b0004" and both.block_ids == ("b0003", "b0004")
    assert quote.resolve("b0003-b0004").block_ids == ("b0003", "b0004")
    row = quote.resolve("t1:r2")
    assert (row.kind, row.ref, row.rows) == (
        "table-rows",
        "t01:r0002",
        (("Baie F1", "5.1", "4140,00 €"),),
    )
    assert quote.resolve("t01").kind == "table"
    figure = quote.resolve("f01")
    assert figure.kind == "figure" and figure.provenance == "model-description"
    assert figure.locator.bbox == [0.2, 0.5, 0.6, 0.8]  # type: ignore[union-attr]
    for bad in ("b0099", "t01:r0099", "t09", "f09", "b0003,t01:r0002", "x12", ""):
        with pytest.raises(CitationRefError):
            quote.resolve(bad)


def test_verified_quote_after_normalisation(quote: DocIndex) -> None:
    text = "“LES TRAVAUX DE MAÇONNERIE SONT SUSPENDUS”"
    check = verify_fact(quote, kf("The masonry work is suspended in frost.", ("b0003", text)))
    assert check.kept
    assert [c.status for c in check.checks] == ["verified"]
    assert check.fact.citations[0].quote == "LES TRAVAUX DE MAÇONNERIE SONT SUSPENDUS"


def test_quote_across_cited_blocks(quote: DocIndex) -> None:
    check = verify_fact(
        quote,
        kf(
            "The bay window F1 is installed first.",
            ("b0003,b0004", "La baie F1 est posée en premier. La baie F1 passe"),
        ),
    )
    assert check.kept and check.checks[0].cited.block_ids == ("b0003", "b0004")  # type: ignore[union-attr]


def test_multi_block_quote_is_narrowed_to_the_quoted_block() -> None:
    check = verify_fact(
        DocIndex(amendment_doc()),
        kf(
            "The amendment amounts to 2328,00 € TTC.",
            ("b0001,b0002", "Le montant de l'avenant n°1 est de 2328,00 € TTC"),
            numbers=("2328,00 €",),
        ),
    )
    assert check.kept
    [citation] = check.checks
    assert citation.status == "verified" and citation.cited is not None
    assert citation.cited.block_ids == ("b0002",)
    assert citation.cited.locator == DocxParagraphLocator(paragraph=2)
    assert check.fact.citations == [
        Citation(block_id="b0002", quote="Le montant de l'avenant n°1 est de 2328,00 € TTC")
    ]


def test_quote_running_across_paragraphs_keeps_the_spanned_blocks() -> None:
    check = verify_fact(
        DocIndex(amendment_doc()),
        kf(
            "The roof opening is checked before the amendment amount is stated.",
            ("b0001-b0003", "contrôler l'ouverture de la toiture. Le montant de l'avenant"),
        ),
    )
    assert check.kept and check.checks[0].cited is not None
    assert check.checks[0].cited.block_ids == ("b0001", "b0002")
    assert locator_key(check.checks[0].cited.locator) == "para-0001"
    assert check.fact.citations[0].block_id == "b0001,b0002"


def test_narrowing_keeps_the_cited_blocks_holding_the_quantities() -> None:
    check = verify_fact(
        DocIndex(amendment_doc()),
        kf(
            "After the roof opening check the amendment amounts to 2328,00 € TTC.",
            ("b0001,b0002,b0003", "contrôler l'ouverture de la toiture"),
            numbers=("2328,00 €",),
        ),
    )
    assert check.kept and check.checks[0].cited is not None
    assert check.checks[0].cited.block_ids == ("b0001", "b0002")


def test_narrowing_on_one_pdf_page_keeps_the_quoted_box(quote: DocIndex) -> None:
    check = verify_fact(
        quote,
        kf(
            "The bay window F1 is widened to 3,00 m.",
            ("b0003,b0004", "La baie F1 passe à 3,00 m de large"),
            numbers=("3,00 m",),
        ),
    )
    assert check.kept and check.checks[0].cited is not None
    assert check.checks[0].cited.block_ids == ("b0004",)
    assert check.checks[0].cited.locator == PdfPageLocator(page=1, bbox=[0.1, 0.45, 0.9, 0.5])


def test_bad_quote_fails_and_drops_the_fact(quote: DocIndex) -> None:
    check = verify_fact(quote, kf("Heat the slab.", ("b0004", "chauffer la dalle à 25 °C")))
    assert not check.kept
    assert check.checks[0].status == "failed"
    assert check.checks[0].reason == "quote not found in the cited text"


def test_unknown_block_fails(quote: DocIndex) -> None:
    check = verify_fact(quote, kf("Something.", ("b0042", "Something")))
    assert not check.kept and check.checks[0].reason == "unknown block id b0042"


def test_paraphrase_rules(quote: DocIndex) -> None:
    plain = verify_fact(quote, kf("The bay window F1 goes first.", ("b0003", None)))
    assert plain.kept and plain.checks[0].status == "unverified-paraphrase"
    numbers = verify_fact(
        quote, kf("The bay window F1 is 3,00 m wide.", ("b0004", None), numbers=("3,00 m",))
    )
    assert numbers.kept and numbers.checks[0].status == "unverified-paraphrase"
    wrong = verify_fact(
        quote, kf("The bay window F1 is 3,00 m wide.", ("b0003", None), numbers=("3,00 m",))
    )
    assert not wrong.kept and wrong.checks[0].status == "failed"


def test_numbers_must_appear_in_cited_text(quote: DocIndex) -> None:
    mismatch = verify_fact(
        quote,
        kf(
            "The bay window F1 is 3,50 m wide.",
            ("b0004", "La baie F1 passe"),
            numbers=("3,50 m",),
        ),
    )
    assert not mismatch.kept
    assert mismatch.checks[0].status == "failed"
    assert "3,50 m" in (mismatch.reason or "")
    unit = verify_fact(quote, kf("Width.", ("b0004", "La baie F1 passe"), numbers=("3,00 km",)))
    assert not unit.kept
    minus = verify_fact(
        quote,
        kf("Below -5 °C.", ("b0003", "les travaux de maçonnerie"), numbers=("-5 °C",)),
    )
    assert minus.kept
    in_text = verify_fact(
        quote, kf("The bay window F1 is 4,00 m wide.", ("b0004", "La baie F1 passe"))
    )
    assert not in_text.kept, "quantities stated in the fact text are checked too"


def test_table_row_cells(quote: DocIndex, plan: DocIndex) -> None:
    ok = verify_fact(
        quote, kf("Price.", ("t01:r0002", "Baie F1 | 4140,00 €"), numbers=("4140,00 €",))
    )
    assert ok.kept and ok.checks[0].status == "verified"
    wrong_row = verify_fact(quote, kf("Price.", ("t01:r0002", "Baie F1 | 1020,00 €")))
    assert not wrong_row.kept
    boundary = verify_fact(plan, kf("Twenty.", ("t01:r0002", "20")))
    assert not boundary.kept, "a cell value must match on word boundaries"
    narrowed = verify_fact(quote, kf("The window F2 costs 1020,00 €.", ("t01", "1020,00 €")))
    assert narrowed.kept and narrowed.checks[0].cited.row_ids == ("r0003",)  # type: ignore[union-attr]
    row = verify_fact(plan, kf("Window F2.", ("t01:r0004", "Fenêtre F2 PVC")))
    locator = row.checks[0].cited.locator  # type: ignore[union-attr]
    assert isinstance(locator, XlsxRowsLocator)
    assert (locator.sheet, locator.row_start, locator.row_end) == ("Achats", 4, 4)
    assert row.checks[0].cited.provenance == "deterministic-table"  # type: ignore[union-attr]


def test_figure_caption_and_description(quote: DocIndex) -> None:
    caption = verify_fact(quote, kf("Bay window F1.", ("f01", "Plan de la baie F1")))
    assert caption.kept and caption.checks[0].cited.provenance == "native-text"  # type: ignore[union-attr]
    description = verify_fact(quote, kf("Bay window F1.", ("f01", "sliding bay window")))
    assert description.checks[0].cited.provenance == "model-description"  # type: ignore[union-attr]


def test_short_quotes_count_as_paraphrase_and_duplicates_collapse(quote: DocIndex) -> None:
    check = verify_fact(
        quote, kf("The bay window F1 goes first.", ("b0003", "“ ”"), ("b0003", None))
    )
    assert [c.status for c in check.checks] == ["unverified-paraphrase"]
    assert check.fact.citations == [Citation(block_id="b0003", quote=None)]


def test_section_markers(quote: DocIndex) -> None:
    body = (
        "Masonry is suspended in frost.[[cite:b3]][[cite:b0003]] Invented step.[[cite:b0099]]\n"
        "- The bay window F1 is 3,00 m wide.[cite:b0004]\n"
        "- The bay window F1 is 4,00 m wide.[[cite:b0004]]\n"
        "The room measures 300 m. The bay window F1 is 3,00 m wide.\n"
        "```\nraw [[cite:b0099]] 999 m\n```"
    )
    result = verify_section_body(quote, body)
    assert result.body == (
        "Masonry is suspended in frost.[[cite:b0003]]\n"
        "- The bay window F1 is 3,00 m wide.[[cite:b0004]]\n"
        "The bay window F1 is 3,00 m wide.\n"
        "```\nraw [[cite:b0099]] 999 m\n```"
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
    assert (
        strip_markers("The bay window is 3,00 m wide [[cite:b0004]].")
        == "The bay window is 3,00 m wide."
    )
