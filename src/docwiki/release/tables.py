"""Per-source tables inside a release: ``tables/<source_id>/<table_id>.parquet`` + ``index.json``.

Each Parquet file has a ``row_id`` column (``r0012`` = original row 12, header = row 1) followed by
the table's columns under ASCII snake_case names. Column types are inferred conservatively:
``BIGINT`` / ``DOUBLE`` only when every non-empty cell is a plain number without leading zeros,
otherwise ``VARCHAR`` (cell text exactly as extracted). ``index.json`` maps names to the original
headers and records the locator, provenance, row count and row ids of each table.

The same locked-down DuckDB runs the computed views of a domain pack (v1.7, ADR 0011): one
relation ``rows`` of text cells (:func:`connect_rows`), the deterministic ``parse_amount`` and
``parse_date`` functions, and the same single-``SELECT`` guard (:func:`check_select`).
"""

# Pydantic copies mutable defaults per instance, so `= []` / `= {}` field defaults are safe.
# ruff: noqa: RUF012

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field

from docwiki.contracts._base import ContractModel, NonEmptyStr
from docwiki.contracts.enums import Sensitivity
from docwiki.contracts.extracted import Table
from docwiki.contracts.ids import SOURCE_ID_RE, slugify_ascii
from docwiki.contracts.locators import Locator

__all__ = [
    "TABLES_DIR",
    "SourceTablesIndex",
    "TableColumn",
    "TableIndexEntry",
    "TableQueryError",
    "TableQueryResult",
    "check_select",
    "column_names",
    "connect_rows",
    "connect_tables",
    "connect_tables_at",
    "parse_amount",
    "parse_date",
    "query_tables",
    "query_tables_at",
    "read_tables_index",
    "read_tables_index_at",
    "rows_query_columns",
    "run_select",
    "tables_dir",
    "write_source_tables",
]

TABLES_DIR = "tables"
ColumnType = Literal["VARCHAR", "BIGINT", "DOUBLE"]
_INT_RE = re.compile(r"^-?(?:0|[1-9]\d{0,17})$")
_FLOAT_RE = re.compile(r"^-?(?:0|[1-9]\d*)\.\d+$")


class TableColumn(ContractModel):
    name: Annotated[str, Field(pattern=r"^[a-z_][a-z0-9_]*$")]
    header: str
    type: ColumnType


class TableIndexEntry(ContractModel):
    id: Annotated[str, Field(pattern=r"^t\d{2,}$")]
    file: NonEmptyStr
    locator: Locator
    provenance: Literal["deterministic-table", "native-text", "ocr"]
    columns: list[TableColumn]
    row_count: Annotated[int, Field(ge=0)]
    row_ids: list[str]


class SourceTablesIndex(ContractModel):
    schema_version: Literal[1] = Field(1, alias="schema")
    source_id: Annotated[str, Field(pattern=SOURCE_ID_RE.pattern)]
    sensitivity: Sensitivity
    tables: list[TableIndexEntry] = []

    def entry(self, table_id: str) -> TableIndexEntry:
        for table in self.tables:
            if table.id == table_id:
                return table
        raise KeyError(table_id)


def column_names(headers: list[str]) -> list[str]:
    """Unique ASCII snake_case column names (``row_id`` is reserved)."""
    used = {"row_id"}
    names: list[str] = []
    for index, header in enumerate(headers, 1):
        base = slugify_ascii(header, 48).replace("-", "_") or f"col_{index}"
        if base[0].isdigit():
            base = f"c_{base}"
        name = base
        counter = 2
        while name in used:
            name = f"{base}_{counter}"
            counter += 1
        used.add(name)
        names.append(name)
    return names


def _infer(values: list[str]) -> ColumnType:
    filled = [value.strip() for value in values if value.strip()]
    if not filled:
        return "VARCHAR"
    if all(_INT_RE.match(value) for value in filled):
        return "BIGINT"
    if all(_INT_RE.match(value) or _FLOAT_RE.match(value) for value in filled):
        return "DOUBLE"
    return "VARCHAR"


def _convert(value: str, kind: ColumnType) -> Any:
    if kind == "VARCHAR":
        return value
    stripped = value.strip()
    if not stripped:
        return None
    return int(stripped) if kind == "BIGINT" else float(stripped)


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def write_source_tables(
    release_root: str | Path, source_id: str, tables: list[Table], sensitivity: str
) -> SourceTablesIndex:
    """Write the Parquet files and ``index.json`` of one source (DuckDB ``COPY``)."""
    import duckdb

    if not SOURCE_ID_RE.match(source_id):
        raise ValueError(f"invalid source_id: {source_id!r}")
    folder = Path(release_root) / TABLES_DIR / source_id
    folder.mkdir(parents=True, exist_ok=True)
    entries: list[TableIndexEntry] = []
    conn = duckdb.connect(":memory:")
    try:
        for table in sorted(tables, key=lambda item: item.id):
            names = column_names(table.columns)
            types = [
                _infer([row.cells[i] for row in table.rows]) for i in range(len(table.columns))
            ]
            columns_sql = ", ".join(
                [
                    "row_id VARCHAR",
                    *(f'"{name}" {kind}' for name, kind in zip(names, types, strict=True)),
                ]
            )
            conn.execute("DROP TABLE IF EXISTS t")
            conn.execute(f"CREATE TABLE t ({columns_sql})")
            if table.rows:
                placeholders = ", ".join("?" * (len(names) + 1))
                conn.executemany(
                    f"INSERT INTO t VALUES ({placeholders})",
                    [
                        [
                            row.row_id,
                            *(
                                _convert(cell, kind)
                                for cell, kind in zip(row.cells, types, strict=True)
                            ),
                        ]
                        for row in table.rows
                    ],
                )
            file_name = f"{table.id}.parquet"
            target = (folder / file_name).as_posix()
            conn.execute(
                f"COPY (SELECT * FROM t ORDER BY rowid) TO {_sql_string(target)} (FORMAT parquet)"
            )
            entries.append(
                TableIndexEntry(
                    id=table.id,
                    file=file_name,
                    locator=table.locator,
                    provenance=table.provenance,
                    columns=[
                        TableColumn(name=name, header=header, type=kind)
                        for name, header, kind in zip(names, table.columns, types, strict=True)
                    ],
                    row_count=len(table.rows),
                    row_ids=[row.row_id for row in table.rows],
                )
            )
    finally:
        conn.close()
    index = SourceTablesIndex(source_id=source_id, sensitivity=sensitivity, tables=entries)  # type: ignore[arg-type]
    (folder / "index.json").write_text(index.to_json(), encoding="utf-8", newline="\n")
    return index


def tables_dir(root: str | Path) -> Path:
    """Tables folder of a release folder (``tables/``) or a portable folder
    (``.docwiki/tables/``)."""
    base = Path(root)
    portable = base / ".docwiki"
    if (portable / "manifest.json").is_file():
        return portable / TABLES_DIR
    return base / TABLES_DIR


def read_tables_index_at(tables_root: str | Path, source_id: str) -> SourceTablesIndex:
    """``index.json`` of a source, given the tables folder itself."""
    if not SOURCE_ID_RE.match(source_id):
        raise ValueError(f"invalid source_id: {source_id!r}")
    path = Path(tables_root) / source_id / "index.json"
    if not path.is_file():
        raise KeyError(f"no tables for {source_id}")
    return SourceTablesIndex.from_json(path.read_bytes())


def read_tables_index(release_root: str | Path, source_id: str) -> SourceTablesIndex:
    """``index.json`` of a source in a release folder or a portable folder."""
    return read_tables_index_at(tables_dir(release_root), source_id)


class TableQueryError(ValueError):
    """Rejected or failed table query."""


@dataclass(frozen=True)
class TableQueryResult:
    columns: list[str]
    rows: list[list[Any]]
    truncated: bool


def connect_tables_at(tables_root: str | Path, source_id: str) -> Any:
    """In-memory DuckDB with one table per source table (named ``t01``…), then locked down:
    no file or network access and no configuration changes."""
    import duckdb

    index = read_tables_index_at(tables_root, source_id)
    folder = Path(tables_root) / source_id
    conn = duckdb.connect(":memory:")
    for entry in index.tables:
        parquet = (folder / entry.file).as_posix()
        conn.execute(
            f"CREATE TABLE {entry.id} AS SELECT * FROM read_parquet({_sql_string(parquet)})"
        )
    conn.execute("SET enable_external_access = false")
    conn.execute("SET lock_configuration = true")
    return conn


def connect_tables(release_root: str | Path, source_id: str) -> Any:
    """:func:`connect_tables_at` for a release folder or a portable folder."""
    return connect_tables_at(tables_dir(release_root), source_id)


def check_select(conn: Any, sql: str) -> None:
    """Accept exactly one ``SELECT`` statement (``WITH … SELECT`` included); raise
    :class:`TableQueryError` otherwise."""
    import duckdb

    try:
        statements = conn.extract_statements(sql)
    except duckdb.Error as exc:
        raise TableQueryError(f"invalid SQL: {exc}") from exc
    if len(statements) != 1 or statements[0].type != duckdb.StatementType.SELECT:
        raise TableQueryError("only a single SELECT statement is allowed")


def run_select(conn: Any, sql: str, *, max_rows: int = 200) -> TableQueryResult:
    """Run one read-only ``SELECT`` on a locked-down connection; at most ``max_rows`` rows."""
    import duckdb

    check_select(conn, sql)
    try:
        cursor = conn.execute(sql)
        rows = cursor.fetchmany(max_rows + 1)
    except duckdb.Error as exc:
        raise TableQueryError(str(exc)) from exc
    columns = [column[0] for column in cursor.description or []]
    return TableQueryResult(columns, [list(row) for row in rows[:max_rows]], len(rows) > max_rows)


def query_tables_at(
    tables_root: str | Path, source_id: str, sql: str, *, max_rows: int = 200
) -> TableQueryResult:
    """Run one read-only ``SELECT`` over a source's tables; at most ``max_rows`` rows."""
    conn = connect_tables_at(tables_root, source_id)
    try:
        return run_select(conn, sql, max_rows=max_rows)
    finally:
        conn.close()


def query_tables(
    release_root: str | Path, source_id: str, sql: str, *, max_rows: int = 200
) -> TableQueryResult:
    """:func:`query_tables_at` for a release folder or a portable folder."""
    return query_tables_at(tables_dir(release_root), source_id, sql, max_rows=max_rows)


# --------------------------------------------------------------------------- computed views

_SPACES_RE = re.compile(r"[\s\u00a0\u202f\u2007']+")
_AMOUNT_NOISE_RE = re.compile(r"(?i)(?:€|eur(?:os?)?\b|ht\b|ttc\b)")
_NUMBER_RE = re.compile(r"^[+-]?\d+(?:\.\d+)?$")
_DMY_RE = re.compile(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$")
_ISO_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ][0-9:.]+)?$")


def parse_amount(value: object) -> Decimal | None:
    """A number written in a document cell, exactly, as a :class:`~decimal.Decimal`, or ``None``.

    Deterministic: currency words (``€``, ``EUR``) and ``HT``/``TTC`` are dropped, spaces of
    any kind group thousands, a minus sign (``-`` or ``−``) or parentheses make it negative.
    When both ``,`` and ``.`` appear the last one is the decimal separator; a single separator
    that appears once is the decimal separator (``2390,00``, ``2390.5``), one that appears
    several times groups thousands (``1.234.567``). ``"2 390,00 € HT"`` → ``Decimal("2390.00")``;
    ``"n/a"`` → ``None``.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(repr(value))
    text = unicodedata.normalize("NFKC", str(value)).strip().replace("\u2212", "-")
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    text = _SPACES_RE.sub("", _AMOUNT_NOISE_RE.sub("", text))
    if not text:
        return None
    commas, dots = text.count(","), text.count(".")
    if commas and dots:
        thousands = "." if text.rfind(",") > text.rfind(".") else ","
        text = text.replace(thousands, "").replace(",", ".")
    elif commas > 1 or dots > 1:
        text = text.replace(",", "").replace(".", "")
    else:
        text = text.replace(",", ".")
    if not _NUMBER_RE.match(text):
        return None
    try:
        number = Decimal(text)
    except InvalidOperation:  # pragma: no cover - guarded by the regex
        return None
    return -number if negative else number


def parse_date(value: object) -> date | None:
    """A date written in a document cell (``2026-03-15``, ``15/03/2026``, ``15.03.2026``,
    ``2026-03-15 00:00:00``), or ``None``. Day first, as in French documents."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    try:
        if match := _ISO_RE.match(text):
            return date(int(match[1]), int(match[2]), int(match[3]))
        if match := _DMY_RE.match(text):
            return date(int(match[3]), int(match[2]), int(match[1]))
    except ValueError:
        return None
    return None


def _sql_amount(value: str | None) -> float | None:
    number = parse_amount(value)
    return None if number is None else float(number)


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def connect_rows(columns: Sequence[str], records: Iterable[Sequence[str | None]]) -> Any:
    """In-memory DuckDB with one table ``rows`` of text columns, the functions
    ``parse_amount(text) → DOUBLE`` and ``parse_date(text) → DATE``, then locked down like
    :func:`connect_tables_at` (no file or network access, no configuration changes)."""
    import duckdb

    if not columns:
        raise ValueError("rows needs at least one column")
    conn = duckdb.connect(":memory:")
    conn.create_function(
        "parse_amount", _sql_amount, ["VARCHAR"], "DOUBLE", null_handling="special"
    )
    conn.create_function("parse_date", parse_date, ["VARCHAR"], "DATE", null_handling="special")
    conn.execute(
        "CREATE TABLE rows (" + ", ".join(f"{_quote_ident(c)} VARCHAR" for c in columns) + ")"
    )
    batch = [list(record) for record in records]
    if batch:
        placeholders = ", ".join("?" * len(columns))
        conn.executemany(f"INSERT INTO rows VALUES ({placeholders})", batch)
    conn.execute("SET enable_external_access = false")
    conn.execute("SET lock_configuration = true")
    return conn


def rows_query_columns(columns: Sequence[str], sql: str) -> list[str]:
    """The result columns of ``sql`` over an empty ``rows`` relation with ``columns``: checks
    the single-``SELECT`` guard and every name the query uses (``TableQueryError``)."""
    conn = connect_rows(columns, [])
    try:
        return run_select(conn, sql, max_rows=0).columns
    finally:
        conn.close()
