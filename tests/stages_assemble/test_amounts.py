"""Amounts written the French trade way (v1.7, slice D): 2 390,00 € HT."""

from __future__ import annotations

from pathlib import Path

import pytest

from docwiki.contracts import Page
from docwiki.stages.amounts import NBSP, THIN, format_amounts, format_page_amounts


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("subtotal 8646,00 € excluding VAT.", f"subtotal 8{THIN}646,00{NBSP}€{NBSP}HT."),
        ("2247,18€ including VAT", f"2{THIN}247,18{NBSP}€{NBSP}TTC"),
        ("39783,00 € (excluding VAT)", f"39{THIN}783,00{NBSP}€{NBSP}HT"),
        ("price 79,20 € HT", f"price 79,20{NBSP}€{NBSP}HT"),
        ("12500 € in all", f"12{THIN}500{NBSP}€ in all"),
        ("FA-2026-0217 of 2026-03-16", "FA-2026-0217 of 2026-03-16"),
        ("1234567,00 €", f"1{THIN}234{THIN}567,00{NBSP}€"),
    ],
)
def test_format_amounts(text: str, expected: str) -> None:
    assert format_amounts(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2390 HT ordered", f"2{THIN}390,00{NBSP}€{NBSP}HT ordered"),
        ("4386.5 HT", f"4{THIN}386,50{NBSP}€{NBSP}HT"),
        ("15157.3 HT", f"15{THIN}157,30{NBSP}€{NBSP}HT"),
        (
            "3320 HT ordered, 996 HT invoiced",
            f"3{THIN}320,00{NBSP}€{NBSP}HT ordered, 996,00{NBSP}€{NBSP}HT invoiced",
        ),
        ("2390,5 € TTC", f"2{THIN}390,50{NBSP}€{NBSP}TTC"),
        ("47271.60€ TTC", f"47{THIN}271,60{NBSP}€{NBSP}TTC"),
        ("total 2390 HT.[^c3]", f"total 2{THIN}390,00{NBSP}€{NBSP}HT.[^c3]"),
        ("2390 HT[^c3]", f"2{THIN}390,00{NBSP}€{NBSP}HT[^c3]"),
        # already formatted: unchanged
        (f"2{THIN}390,00{NBSP}€{NBSP}HT", f"2{THIN}390,00{NBSP}€{NBSP}HT"),
    ],
)
def test_numbers_before_ht_or_ttc_are_amounts(text: str, expected: str) -> None:
    assert format_amounts(text) == expected
    assert format_amounts(expected) == expected


@pytest.mark.parametrize(
    "text",
    [
        "see [^12] HT notes",  # footnote marker
        "fact[^2] TTC",
        "[2390 HT](../topics/budget.md)",  # link text
        "`2390 HT`",  # code
        "dated 16/03/2026 HT",  # dates
        "dated 2026-03-16 TTC",
        "tarif 2026 HT",  # a year
        "BC-2026-009 HT",  # document numbers
        "DEV-2026-014 TTC",
        "FA-2026-0158 HT",
        "lot 5 HT",  # lot numbers
        "Lot 12 TTC",
        "n° 4 HT",
        "TVA 20 % HT",  # percentages
        "5,5% TTC",
        'the line reads "2390 HT"',  # quoted text from a document
        "« 4386,5 HT »",
        "HTML 2390 HTTP",  # not the words HT or TTC
        "2,390 HT",  # thousands with a comma: ambiguous, left alone
    ],
)
def test_vat_amount_non_cases_are_left_as_written(text: str) -> None:
    assert format_amounts(text) == text


def test_vat_amounts_in_pages_skip_tables_quotes_and_footnote_definitions() -> None:
    body = "\n".join(
        [
            "Ordered 2390 HT, invoiced 996 HT.[^c1]",
            "| Lot 3 | 2390 HT |",
            "> Montant : 2390 HT",
            '[^c1]: "2390 HT" — order, row 3',
        ]
    )
    page = Page(
        path="topics/budget.md", frontmatter=_query_frontmatter("Ordered 2390 HT"), body=body
    )
    out = format_page_amounts(page)
    lines = out.body.split("\n")
    assert lines[0] == (
        f"Ordered 2{THIN}390,00{NBSP}€{NBSP}HT, invoiced 996,00{NBSP}€{NBSP}HT.[^c1]"
    )
    assert lines[1:] == body.split("\n")[1:]
    assert out.frontmatter.summary == f"Ordered 2{THIN}390,00{NBSP}€{NBSP}HT"


def test_quotes_tables_and_footnotes_keep_the_documents_text() -> None:
    from docwiki.stages.amounts import format_page_amounts as fmt

    body = "\n".join(
        [
            "The total is 47271,60 € including VAT.[^1]",
            "> Montant total : 47271,60 € TTC",
            "| Poste | 4140,00 € |",
            '[^1]: "47271,60 € TTC" — contract, p. 2',
            "```",
            "4140,00 €",
            "```",
        ]
    )
    page = Page(
        path="sources/total.md",
        frontmatter=_query_frontmatter("Total 47271,60 € including VAT"),
        body=body,
    )
    out = fmt(page)
    lines = out.body.split("\n")
    assert lines[0] == f"The total is 47{THIN}271,60{NBSP}€{NBSP}TTC.[^1]"
    assert lines[1:] == body.split("\n")[1:]
    assert out.frontmatter.summary == f"Total 47{THIN}271,60{NBSP}€{NBSP}TTC"
    plain = _query_frontmatter("No amount.")
    unchanged = Page(path=page.path, frontmatter=plain, body="No amount here.")
    assert format_page_amounts(unchanged) is unchanged


def _query_frontmatter(summary: str) -> object:
    """A real page's frontmatter (a source page of the mock release) with this summary."""
    root = Path(__file__).resolve().parents[2] / "samples" / "fixtures" / "mock-release"
    path = next(root.glob("releases/*/wiki/sources/pln-2026-003-indice-b-*.md"))
    page = Page.parse(path.read_text(encoding="utf-8"), "sources/" + path.name)
    return page.frontmatter.model_copy(update={"summary": summary})
