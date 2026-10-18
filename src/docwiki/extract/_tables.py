"""Shared table handling: grid normalisation, row texts and table-ref blocks."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from docwiki.contracts import Locator
from docwiki.contracts.enums import Provenance
from docwiki.extract._draft import Draft, TableProvenance
from docwiki.extract._text import one_line

__all__ = ["MAX_TABLE_COLUMNS", "MAX_TABLE_ROWS", "emit_table", "row_text"]

MAX_TABLE_ROWS = 100_000
"""Rows kept per table (sheet, CSV file, document table); beyond that a warning is recorded."""
MAX_TABLE_COLUMNS = 500


def row_text(columns: Sequence[str], cells: Sequence[str]) -> str:
    """``"Asset: WTG-07; Task: Gearbox oil change"`` (empty cells skipped)."""
    parts: list[str] = []
    for index, cell in enumerate(cells):
        value = one_line(cell)
        if not value:
            continue
        name = one_line(columns[index]) if index < len(columns) else ""
        parts.append(f"{name}: {value}" if name else value)
    return "; ".join(parts)


def emit_table(
    draft: Draft,
    *,
    header: list[str],
    rows: list[tuple[int, list[str]]],
    locator: Locator,
    provenance: TableProvenance,
    row_locator: Callable[[int], Locator],
    what: str,
    block_provenance: Provenance | None = None,
) -> None:
    """Add a table (header = row 1) and one ``table-ref`` block per non-empty data row.

    ``rows`` holds ``(original row number, cells)``; numbers become ``row_id``s. Widths are
    normalised (short rows padded, extra cells get unnamed columns).
    """
    width = max([len(header), *(len(cells) for _, cells in rows)], default=0)
    if width == 0:
        return
    if width > MAX_TABLE_COLUMNS:
        draft.warn("table-truncated", f"{what}: kept the first {MAX_TABLE_COLUMNS} columns")
        width = MAX_TABLE_COLUMNS
    columns = (header + [""] * width)[:width]
    data = [
        (number, (cells + [""] * width)[:width])
        for number, cells in rows
        if any(cell.strip() for cell in cells)
    ]
    if len(data) > MAX_TABLE_ROWS:
        draft.warn("table-truncated", f"{what}: kept the first {MAX_TABLE_ROWS} rows")
        data = data[:MAX_TABLE_ROWS]
    if not data and not any(column.strip() for column in columns):
        return
    draft.table(locator, provenance, columns, data)
    block_prov: Provenance = block_provenance or provenance
    if not data:
        text = " | ".join(one_line(column) for column in columns if column.strip())
        draft.block("table-ref", text, row_locator(1), block_prov)
        return
    for number, cells in data:
        draft.block("table-ref", row_text(columns, cells), row_locator(number), block_prov)
