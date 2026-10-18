"""CSV/TSV via the csv module: one deterministic table, rows numbered as records (header = 1).

Row numbers count every record of the file, blank ones included, so they match the row numbers
a spreadsheet shows when it opens the file (a quoted field spanning lines stays one row).
"""

from __future__ import annotations

import csv
import io

from docwiki.contracts.locators import CsvRowsLocator
from docwiki.extract._draft import Draft
from docwiki.extract._tables import MAX_TABLE_ROWS, emit_table
from docwiki.extract._text import clean_text, decode_text

__all__ = ["extract_csv"]

_SNIFF_BYTES = 64 * 1024
_FIELD_LIMIT = 16 * 1024 * 1024
_DELIMITERS = ",;\t|"


def _dialect(sample: str, tab_separated: bool) -> type[csv.Dialect] | csv.Dialect:
    if tab_separated:
        return csv.excel_tab
    try:
        return csv.Sniffer().sniff(sample, delimiters=_DELIMITERS)
    except csv.Error:
        return csv.excel


def extract_csv(data: bytes, draft: Draft, *, tab_separated: bool = False) -> None:
    text, encoding = decode_text(data)
    if encoding == "cp1252":
        draft.warn("encoding", "the file is not valid UTF-8; decoded as Windows-1252")
    dialect = _dialect(text[:_SNIFF_BYTES], tab_separated)
    if csv.field_size_limit() < _FIELD_LIMIT:
        csv.field_size_limit(_FIELD_LIMIT)
    reader = csv.reader(io.StringIO(text, newline=""), dialect)
    records: list[tuple[int, list[str]]] = []
    try:
        for number, record in enumerate(reader, 1):
            if number > MAX_TABLE_ROWS + 1:
                draft.warn("table-truncated", f"kept the first {MAX_TABLE_ROWS} data rows")
                break
            records.append((number, [clean_text(cell) for cell in record]))
    except csv.Error as exc:
        draft.warn("csv-parse", f"stopped at record {len(records) + 1}: {exc}")
    if not records:
        draft.warn("empty", "the file has no records")
        return
    header = records[0][1] if records[0][0] == 1 else []
    rows = [(number, cells) for number, cells in records if number > 1]
    last = records[-1][0]
    emit_table(
        draft,
        header=header,
        rows=rows,
        locator=CsvRowsLocator(row_start=1, row_end=last),
        provenance="deterministic-table",
        row_locator=lambda row: CsvRowsLocator(row_start=row, row_end=row),
        what="CSV",
    )
