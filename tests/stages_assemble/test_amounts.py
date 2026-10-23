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
        ("price 79,20 € HT", "price 79,20 € HT"),
        ("12500 € in all", f"12{THIN}500{NBSP}€ in all"),
        ("FA-2026-0217 of 2026-03-16", "FA-2026-0217 of 2026-03-16"),
        ("1234567,00 €", f"1{THIN}234{THIN}567,00{NBSP}€"),
    ],
)
def test_format_amounts(text: str, expected: str) -> None:
    assert format_amounts(text) == expected


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
