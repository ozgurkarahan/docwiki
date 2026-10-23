"""Computed views (v1.7, ADR 0011): figures computed by code from the documents' tables."""

from __future__ import annotations

import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from assemble_helpers import STAMP

from docwiki.contracts.extracted import Table, TableRow
from docwiki.contracts.locators import CsvRowsLocator, PdfPageLocator, XlsxRowsLocator, locator_key
from docwiki.domain.loader import PackValidationError, load_pack
from docwiki.release.tables import TableQueryError, parse_amount, parse_date, rows_query_columns
from docwiki.stages.amounts import format_number
from docwiki.stages.views import (
    ViewError,
    ViewSource,
    build_view_pages,
    compute_view,
    normalize_header,
)

PACK = Path(__file__).resolve().parents[1] / "orchestration" / "fixtures" / "test-pack"

TYPES = """
  - key: equipment-register
    title: Equipment register
    category: schedule-and-purchases
    authority: 4
  - key: situation
    title: Situation de travaux
    category: contract-documents
    authority: 7
"""

VIEWS = """
views:
  - slug: situations
    title: Situations par chantier
    doc_types: [situation]
    columns:
      lot: [Lot]
      designation: ["Désignation", "Libellé"]
      montant_ht: ["Montant HT"]
    sql: >-
      SELECT lot, designation, montant_ht, _source_id, _table_id, _row_id, _scope
      FROM rows ORDER BY _scope, _source_id, _row_id
    per_scope: true
    totals: [montant_ht]
"""


def _pack_dir(tmp_path: Path, views: str | None = VIEWS) -> Path:
    target = tmp_path / "pack"
    shutil.copytree(PACK, target)
    taxonomy = target / "taxonomy.yaml"
    taxonomy.write_text(taxonomy.read_text(encoding="utf-8") + TYPES, encoding="utf-8")
    if views is not None:
        (target / "views.yaml").write_text(views, encoding="utf-8")
    return target


def _table(table_id: str, locator, columns: list[str], rows: list[list[str]]) -> Table:
    return Table(
        id=table_id,
        locator=locator,
        provenance="deterministic-table",
        columns=columns,
        rows=[TableRow(row_id=f"r{n + 2:04d}", cells=cells) for n, cells in enumerate(rows)],
        artifact=f"tables/{table_id}.parquet",
    )


def _sources() -> list[ViewSource]:
    xlsx = _table(
        "t01",
        XlsxRowsLocator(sheet="Situation n°1", row_start=1, row_end=3),
        ["Lot", "Désignation", "Montant HT"],
        [["1", "Installation de chantier", "1 350,00 €"], ["2", "Maçonnerie", "2390,00"]],
    )
    csv = _table(
        "t01",
        CsvRowsLocator(row_start=1, row_end=2),
        ["LOT", "Libelle", "montant ht"],
        [["1", "Installation", "1 000,50 €"]],
    )
    return [
        ViewSource(
            source_id="src-aaaaaaaaaaa1",
            title="Situation 1 Moreau",
            page_path="sources/situation-1-moreau.md",
            doc_type="situation",
            scope="moreau",
            sensitivity="internal",
            tables=(xlsx,),
        ),
        ViewSource(
            source_id="src-aaaaaaaaaaa2",
            title="Situation 1 école",
            page_path="sources/situation-1-ecole.md",
            doc_type="situation",
            scope="ecole",
            sensitivity="public",
            tables=(csv,),
        ),
        ViewSource(
            source_id="src-aaaaaaaaaaa3",
            title="Purchase plan",
            page_path="sources/purchase-plan.md",
            doc_type="schedule",
            scope="moreau",
            sensitivity="public",
            tables=(csv,),
        ),
    ]


def test_parse_amount_reads_the_trade_notations() -> None:
    assert parse_amount("2 390,00 € HT") == Decimal("2390.00")
    assert parse_amount("2 390,00 €") == Decimal("2390.00")
    assert parse_amount("2390,00") == Decimal("2390.00")
    assert parse_amount("2390.5") == Decimal("2390.5")
    assert parse_amount("1.234.567") == Decimal("1234567")
    assert parse_amount("1.234,56") == Decimal("1234.56")
    assert parse_amount("1,234.56") == Decimal("1234.56")
    assert parse_amount("-12,5") == Decimal("-12.5")
    assert parse_amount("(40,00)") == Decimal("-40.00")
    assert parse_amount("2390EUR") == Decimal("2390")
    assert parse_amount(7) == Decimal(7)
    for value in ("n/a", "", None, "12 jours", "1,2,3.4.5"):
        assert parse_amount(value) is None
    assert format_number(Decimal("4740.50"), unit="€ HT") == "4 740,50 € HT"
    assert format_number(Decimal("-1350")) == "-1 350"


def test_parse_date_is_day_first() -> None:
    assert parse_date("15/03/2026") == date(2026, 3, 15)
    assert parse_date("2026-03-15 00:00:00") == date(2026, 3, 15)
    assert parse_date("01.12.2026") == date(2026, 12, 1)
    assert parse_date("31/02/2026") is None
    assert parse_date("next week") is None


def test_headers_match_without_case_or_accents() -> None:
    assert normalize_header(" Désignation ") == normalize_header("DESIGNATION")
    assert normalize_header("Montant H.T.") == "montant h t"


def test_view_rows_keep_their_row_and_totals_are_summed_by_code(tmp_path: Path) -> None:
    pack = load_pack(_pack_dir(tmp_path))
    assert pack.views is not None
    sources = _sources()
    result = compute_view(pack.views.views[0], sources)
    assert result.columns == ["lot", "designation", "montant_ht"]
    assert result.sources == ["src-aaaaaaaaaaa1", "src-aaaaaaaaaaa2"]  # not the schedule
    assert [(row.scope, row.source_id, row.row_id) for row in result.rows] == [
        ("ecole", "src-aaaaaaaaaaa2", "r0002"),
        ("moreau", "src-aaaaaaaaaaa1", "r0002"),
        ("moreau", "src-aaaaaaaaaaa1", "r0003"),
    ]
    # each row is located by exactly its own row of the sheet or the CSV
    assert [locator_key(row.locator) for row in result.rows] == [
        "r0002-r0002",
        "sheet-situation-n1-r0002-r0002",
        "sheet-situation-n1-r0003-r0003",
    ]
    assert [(total.scope, total.values["montant_ht"]) for total in result.totals] == [
        ("ecole", Decimal("1000.50")),
        ("moreau", Decimal("3740.00")),
        (None, Decimal("4740.50")),
    ]
    assert result.units == {"montant_ht": "€ HT"}

    build = build_view_pages(pack, sources, stamp=STAMP)
    (page,) = build.pages
    assert page.path == "views/situations.md"
    fm = page.frontmatter
    assert fm.id == "view:situations" and fm.type == "view" and fm.rows == 3
    assert fm.sources == ["src-aaaaaaaaaaa1", "src-aaaaaaaaaaa2"]
    assert fm.sensitivity == "internal"  # the highest tier of the documents it reads
    body = page.body
    assert "computed by code, not by a language model" in body
    link = "[Situation 1 école](../sources/situation-1-ecole.md)"
    assert f"| 1 | Installation | 1 000,50 € | {link}[^c1] |" in body
    assert (
        '[^c2]: [Situation 1 Moreau — sheet "Situation n°1", row 2]'
        "(../evidence/src-aaaaaaaaaaa1/sheet-situation-n1-r0002-r0002.md) · table" in body
    )
    assert "| moreau | 2 | 3 740,00 € HT |" in body
    assert "| **All** | 3 | 4 740,50 € HT |" in body
    assert [(c.source_id, c.key, c.block_ids) for c in build.cited] == [
        ("src-aaaaaaaaaaa2", "r0002-r0002", ("t01:r0002",)),
        ("src-aaaaaaaaaaa1", "sheet-situation-n1-r0002-r0002", ("t01:r0002",)),
        ("src-aaaaaaaaaaa1", "sheet-situation-n1-r0003-r0003", ("t01:r0003",)),
    ]
    assert build.warnings == []


def test_tables_without_a_column_or_a_row_locator_are_skipped_with_a_warning(
    tmp_path: Path,
) -> None:
    pack = load_pack(_pack_dir(tmp_path))
    assert pack.views is not None
    sources = _sources()
    notes = _table("t02", CsvRowsLocator(row_start=1, row_end=2), ["Lot", "Remarque"], [["1", "x"]])
    scan = _table("t03", PdfPageLocator(page=2), ["Lot", "Désignation", "Montant HT"], [])
    first = sources[0]
    sources[0] = ViewSource(**{**first.__dict__, "tables": (*first.tables, notes, scan)})
    result = compute_view(pack.views.views[0], sources)
    assert len(result.rows) == 3
    assert result.warnings == [
        "views: situations: Situation 1 Moreau (src-aaaaaaaaaaa1) table t02 skipped "
        "(no column for designation, montant_ht)",
        "views: situations: Situation 1 Moreau (src-aaaaaaaaaaa1) table t03 skipped "
        "(its rows cannot be cited one by one)",
    ]


def test_a_row_that_two_tables_share_needs_the_table_id(tmp_path: Path) -> None:
    views = VIEWS.replace("_source_id, _table_id, _row_id", "_source_id, _row_id")
    pack = load_pack(_pack_dir(tmp_path, views))
    assert pack.views is not None
    sources = _sources()
    first = sources[0]
    twin = first.tables[0].model_copy(
        update={"id": "t02", "locator": XlsxRowsLocator(sheet="Avenant", row_start=1, row_end=3)}
    )
    sources[0] = ViewSource(**{**first.__dict__, "tables": (*first.tables, twin)})
    with pytest.raises(ViewError, match="ambiguous"):
        compute_view(pack.views.views[0], sources)


def test_a_query_that_fails_on_the_data_fails_the_view(tmp_path: Path) -> None:
    views = VIEWS.replace("SELECT lot,", "SELECT CAST(montant_ht AS INTEGER) AS n, lot,")
    pack = load_pack(_pack_dir(tmp_path, views))  # valid over an empty relation
    assert pack.views is not None
    with pytest.raises(ViewError, match="situations"):
        compute_view(pack.views.views[0], _sources())


SQL = """SELECT lot, designation, montant_ht, _source_id, _table_id, _row_id, _scope
      FROM rows ORDER BY _scope, _source_id, _row_id"""


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ((SQL, "DROP TABLE rows"), "only a single SELECT"),
        ((SQL, "DELETE FROM rows; " + SQL), "only a single SELECT"),
        ((SQL, "COPY (" + SQL + ") TO 'out.csv'"), "only a single SELECT"),
        ((SQL, "SELEKT 1"), "invalid SQL"),
        (("_source_id, _table_id, _row_id, _scope", "_scope"), "must return _source_id and _row"),
        (("SELECT lot,", "SELECT prix,"), "prix"),
        (("totals: [montant_ht]", "totals: [lot_total]"), "not a column of the query result"),
        (("doc_types: [situation]", "doc_types: [invoice]"), "unknown doc type 'invoice'"),
    ],
)
def test_bad_views_fail_the_pack_load(
    tmp_path: Path, change: tuple[str, str], message: str
) -> None:
    views = VIEWS.replace(*change)
    assert views != VIEWS
    with pytest.raises(PackValidationError, match=message) as caught:
        load_pack(_pack_dir(tmp_path, views))
    assert "views.yaml" in str(caught.value)


def test_rows_queries_are_locked_down() -> None:
    with pytest.raises(TableQueryError):
        rows_query_columns(["a"], "SELECT * FROM read_csv('secrets.csv')")
    assert rows_query_columns(["a"], "SELECT a, parse_amount(a) AS n FROM rows") == ["a", "n"]


def test_a_pack_without_views_yaml_is_unchanged(tmp_path: Path) -> None:
    pack = load_pack(_pack_dir(tmp_path, views=None))
    assert pack.views is None
    build = build_view_pages(pack, _sources(), stamp=STAMP)
    assert (build.pages, build.cited, build.results, build.warnings) == ([], [], [], [])
