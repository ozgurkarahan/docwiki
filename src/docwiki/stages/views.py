"""Computed views (v1.7, ADR 0011 decision 5): cross-document figures computed by code.

A domain pack's optional ``views.yaml`` declares views. For each view this stage builds one
DuckDB relation ``rows``: the union of the tables of the current documents whose type is in
the view's ``doc_types``, their columns renamed by matching the table headers to the view's
aliases (without case or accents), plus the system columns ``_source_id``, ``_table_id``,
``_row_id`` and ``_scope``. Every cell is the text exactly as extracted; ``parse_amount`` and
``parse_date`` read numbers and dates deterministically inside the query. The view's single
``SELECT`` runs in the same locked-down DuckDB as ``query_table``.

Each result row keeps the source and row it came from: the page ``views/<slug>.md`` renders it
with a footnote to the evidence sidecar of exactly that row, and the cited row locators go to
the evidence stage. Totals are summed by code with :class:`~decimal.Decimal` from the cited
rows (per scope when the view asks for it). No language model reads or adds these numbers.

Only tables located by rows (XLSX sheets, CSV files, DOCX tables) and parsed deterministically
take part: a result row must point at one row of one document. Other tables, and tables that
lack one of the view's columns, are skipped with a run warning.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from docwiki.contracts.enums import max_sensitivity
from docwiki.contracts.extracted import ExtractedDoc, Table
from docwiki.contracts.ids import (
    format_hub_id,
    format_view_id,
    hub_page_path,
    index_page_path,
    view_page_path,
)
from docwiki.contracts.locators import CsvRowsLocator, DocxTableLocator, Locator, XlsxRowsLocator
from docwiki.contracts.markdown import relative_link
from docwiki.contracts.pages import (
    DocwikiStamp,
    IndexFrontmatter,
    Page,
    SourceFrontmatter,
    ViewFrontmatter,
)
from docwiki.domain.models import VIEW_SYSTEM_COLUMNS, DomainPack, ViewDef
from docwiki.engine_types import CitedLocator
from docwiki.release.tables import TableQueryError, connect_rows, parse_amount, run_select
from docwiki.stages.amounts import NBSP, format_number
from docwiki.stages.hubs import scope_label
from docwiki.stages.render import (
    Footnotes,
    banner_line,
    clean_inline,
    escape_document_text,
    release_date,
)

__all__ = [
    "MAX_VIEW_ROWS",
    "ViewBuild",
    "ViewError",
    "ViewResult",
    "ViewRow",
    "ViewSource",
    "ViewTotal",
    "amount_unit",
    "build_view_pages",
    "build_views_index",
    "column_label",
    "compute_view",
    "normalize_header",
    "view_sources",
]

MAX_VIEW_ROWS = 500
"""Rows shown (and cited) per view; a longer result is cut and the page and the run say so."""

_ROW_LOCATORS = (XlsxRowsLocator, CsvRowsLocator, DocxTableLocator)
_NON_ALNUM_RE = re.compile(r"[^0-9a-z]+")


class ViewError(ValueError):
    """A view that cannot be computed (its query fails or loses the cited row)."""


@dataclass(frozen=True)
class ViewSource:
    """A current document of the release, as the views see it (redacted tables)."""

    source_id: str
    title: str
    page_path: str
    doc_type: str
    scope: str | None
    sensitivity: str
    tables: tuple[Table, ...] = ()


@dataclass(frozen=True)
class ViewRow:
    """One result row: the displayed values and the exact row of the document it comes from."""

    source_id: str
    table_id: str
    row_id: str
    scope: str | None
    locator: Locator
    values: tuple[Any, ...]


@dataclass(frozen=True)
class ViewTotal:
    """Sums of the ``totals`` columns over the cited rows of one scope (``None``: all rows)."""

    scope: str | None
    rows: int
    values: dict[str, Decimal]
    skipped: dict[str, int]
    """Non-empty cells of a totals column that are not a number (left out of the sum)."""


@dataclass
class ViewResult:
    view: ViewDef
    columns: list[str]
    """Displayed result columns (the system columns are hidden)."""
    rows: list[ViewRow]
    totals: list[ViewTotal]
    """Per scope (sorted) when ``per_scope``, then the total of all rows."""
    sources: list[str]
    """Every document whose tables formed ``rows`` (the page's ``sources``)."""
    units: dict[str, str | None]
    truncated: bool
    warnings: list[str] = field(default_factory=list)


@dataclass
class ViewBuild:
    pages: list[Page]
    cited: list[CitedLocator]
    results: list[ViewResult]
    warnings: list[str]


def normalize_header(text: str) -> str:
    """A table header or alias compared without case, accents or punctuation."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return _NON_ALNUM_RE.sub(" ", plain).strip()


def _row_locator(table: Table, row_id: str) -> Locator:
    number = int(row_id[1:])
    update: dict[str, object] = {"row_start": number, "row_end": number}
    if isinstance(table.locator, XlsxRowsLocator):
        update["cols"] = None
    return table.locator.model_copy(update=update)


def _match_columns(view: ViewDef, table: Table) -> tuple[list[int | None], list[str]]:
    """For each view column, the index of the table column whose header matches (or None)."""
    headers = [normalize_header(header) for header in table.columns]
    found: list[int | None] = []
    missing: list[str] = []
    for name, aliases in view.columns.items():
        wanted = {normalize_header(alias) for alias in [name.replace("_", " "), *aliases]}
        index = next((i for i, header in enumerate(headers) if header in wanted), None)
        found.append(index)
        if index is None:
            missing.append(name)
    return found, missing


def _cell(value: str) -> str | None:
    return value if value.strip() else None


def compute_view(view: ViewDef, sources: Sequence[ViewSource]) -> ViewResult:
    """Run one view over the current documents; raise :class:`ViewError` when it fails."""
    warnings: list[str] = []
    tables: dict[tuple[str, str], Table] = {}
    table_rows: dict[tuple[str, str], set[str]] = {}
    by_source = {source.source_id: source for source in sources}
    records: list[list[str | None]] = []
    read: list[str] = []
    for source in sorted(sources, key=lambda item: item.source_id):
        if source.doc_type not in view.doc_types:
            continue
        used = False
        for table in sorted(source.tables, key=lambda item: item.id):
            where = f"views: {view.slug}: {source.title} ({source.source_id}) table {table.id}"
            if (
                not isinstance(table.locator, _ROW_LOCATORS)
                or table.provenance != "deterministic-table"
            ):
                warnings.append(f"{where} skipped (its rows cannot be cited one by one)")
                continue
            indexes, missing = _match_columns(view, table)
            if missing:
                warnings.append(f"{where} skipped (no column for {', '.join(missing)})")
                continue
            used = True
            tables[(source.source_id, table.id)] = table
            table_rows[(source.source_id, table.id)] = {row.row_id for row in table.rows}
            for row in table.rows:
                cells = [_cell(row.cells[i]) if i is not None else None for i in indexes]
                records.append(
                    [*cells, source.source_id, table.id, row.row_id, source.scope or None]
                )
        if used:
            read.append(source.source_id)
    conn = connect_rows([*view.columns, *VIEW_SYSTEM_COLUMNS], records)
    try:
        result = run_select(conn, view.sql, max_rows=MAX_VIEW_ROWS)
    except TableQueryError as exc:
        raise ViewError(f"view {view.slug!r}: {exc}") from exc
    finally:
        conn.close()
    names = result.columns
    missing = [name for name in ("_source_id", "_row_id") if name not in names]
    if missing:
        raise ViewError(
            f"view {view.slug!r}: the query must return {' and '.join(missing)} "
            "so every row stays cited"
        )
    shown = [index for index, name in enumerate(names) if not name.startswith("_")]
    columns = [names[index] for index in shown]
    rows: list[ViewRow] = []
    for values in result.rows:
        record = dict(zip(names, values, strict=True))
        source_id, row_id = str(record["_source_id"]), str(record["_row_id"])
        table_id = record.get("_table_id")
        candidates = [
            tables[key]
            for key, row_ids in table_rows.items()
            if key[0] == source_id
            and (table_id is None or key[1] == table_id)
            and row_id in row_ids
        ]
        if len(candidates) != 1:
            problem = "is not a row of" if not candidates else "is ambiguous in"
            raise ViewError(
                f"view {view.slug!r}: result row {source_id}/{row_id} {problem} the view's "
                "tables (return _table_id with _source_id and _row_id)"
            )
        table = candidates[0]
        scope = record.get("_scope", by_source[source_id].scope)
        rows.append(
            ViewRow(
                source_id=source_id,
                table_id=table.id,
                row_id=row_id,
                scope=str(scope) if scope else None,
                locator=_row_locator(table, row_id),
                values=tuple(values[index] for index in shown),
            )
        )
    unknown = [name for name in view.totals if name not in columns]
    if unknown:
        raise ViewError(f"view {view.slug!r}: totals {unknown} are not result columns")
    totals = _totals(view, columns, rows, warnings)
    if result.truncated:
        warnings.append(
            f"views: {view.slug}: only the first {MAX_VIEW_ROWS} rows are shown and summed"
        )
    units = {
        name: amount_unit(view, name)
        if view.amounts
        else _unit(name, [row.values[columns.index(name)] for row in rows])
        for name in view.totals
    }
    return ViewResult(
        view=view,
        columns=columns,
        rows=rows,
        totals=totals,
        sources=read,
        units=units,
        truncated=result.truncated,
        warnings=warnings,
    )


def _totals(
    view: ViewDef, columns: list[str], rows: list[ViewRow], warnings: list[str]
) -> list[ViewTotal]:
    if not view.totals:
        return []
    groups: list[tuple[str | None, list[ViewRow]]] = []
    if view.per_scope:
        scopes = sorted({row.scope for row in rows if row.scope})
        groups += [(scope, [row for row in rows if row.scope == scope]) for scope in scopes]
    groups.append((None, rows))
    out: list[ViewTotal] = []
    for scope, members in groups:
        values: dict[str, Decimal] = {}
        skipped: dict[str, int] = {}
        for name in view.totals:
            index = columns.index(name)
            total = Decimal(0)
            for row in members:
                cell = row.values[index]
                number = parse_amount(cell)
                if number is not None:
                    total += number
                elif cell is not None and str(cell).strip():
                    skipped[name] = skipped.get(name, 0) + 1
            values[name] = total
        out.append(ViewTotal(scope=scope, rows=len(members), values=values, skipped=skipped))
    whole = out[-1]
    for name, count in sorted(whole.skipped.items()):
        warnings.append(
            f"views: {view.slug}: {count} cell(s) of {name} are not numbers and are not summed"
        )
    return out


def amount_unit(view: ViewDef, name: str) -> str | None:
    """The unit the pack declares for an amount column (``€ HT``, ``€ TTC``, ``€``), else
    ``None`` (not an amount)."""
    basis = view.amounts.get(name)
    if basis is None:
        return None
    return "€" if basis == "€" else f"€{NBSP}{basis}"


def _unit(name: str, cells: Sequence[Any]) -> str | None:
    """``€``, ``€ HT`` or ``€ TTC`` when the cited cells are in euros, else nothing (a view
    whose pack declares no ``amounts``)."""
    euros = any(isinstance(cell, str) and ("€" in cell or "eur" in cell.lower()) for cell in cells)
    if not euros and not re.search(r"(?:^|_)(?:ht|ttc)$", name):
        return None
    if name.endswith("_ht") or name == "ht":
        return f"€{NBSP}HT"
    if name.endswith("_ttc") or name == "ttc":
        return f"€{NBSP}TTC"
    return "€"


# --------------------------------------------------------------------------- page


_CENTS = Decimal("0.01")


def _cell_text(text: str) -> str:
    return escape_document_text(text).replace("|", "\\|")


def column_label(view: ViewDef, name: str) -> str:
    """The header of a result column: the pack's label, else the column name."""
    return view.labels.get(name) or name.replace("_", " ")


def _header(view: ViewDef, name: str) -> str:
    return _cell_text(column_label(view, name))


def _value(value: Any, unit: str | None = None) -> str:
    """A result cell as one safe table cell: document text verbatim (escaped), computed numbers
    the French way, dates in ISO form. An amount column (``unit``) writes every number with two
    decimals and its unit (``184 490,00 € HT``); a cell that is not a number stays as it is."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if unit is not None:
        number = parse_amount(value)
        if number is not None:
            return format_number(number.quantize(_CENTS), unit=unit)
    if isinstance(value, int | float | Decimal):
        number = value if isinstance(value, Decimal) else parse_amount(value)
        return format_number(number) if number is not None else str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    return _cell_text(str(value))


def _total(value: Decimal, unit: str | None) -> str:
    return format_number(value.quantize(_CENTS) if unit else value, unit=unit)


@dataclass(frozen=True)
class _Scopes:
    """How a view page names a scope value: its label, linked to its hub page when it has one."""

    pack: DomainPack
    hubs: frozenset[str]
    path: str

    def cell(self, scope: Any) -> str:
        if scope is None or not str(scope).strip():
            return "—"
        value = str(scope).strip()
        label = _cell_text(scope_label(self.pack, value))
        scopes = self.pack.scopes
        if scopes is None or value not in self.hubs:
            return label
        target = hub_page_path(format_hub_id(scopes.plural, value))
        return f"[{label}]({relative_link(self.path, target)})"


def _render(
    pack: DomainPack,
    result: ViewResult,
    sources: Mapping[str, ViewSource],
    *,
    stamp: DocwikiStamp,
    hubs: frozenset[str] = frozenset(),
) -> tuple[Page, list[CitedLocator]]:
    view = result.view
    path = view_page_path(format_view_id(view.slug))
    titles = {sid: source.title for sid, source in sources.items()}
    notes = Footnotes(path, titles)
    names = _Scopes(pack, hubs, path)
    with_scope = pack.scopes is not None
    scope_title = _cell_text(pack.scopes.title) if pack.scopes is not None else ""
    lines = [f"# {escape_document_text(view.title)}", ""]
    banner = banner_line(pack)
    if banner:
        lines += [banner, ""]
    description = clean_inline(view.description)
    if description:
        lines += [description, ""]
    cited_sources = sorted({row.source_id for row in result.rows})
    lines += [
        f"These figures were computed by code, not by a language model, from {len(result.rows)} "
        f"cited table row(s) of {len(cited_sources)} document(s); every row links to the "
        "evidence of exactly that row, and the totals are sums of the cited rows.",
        "",
        "## Rows",
        "",
    ]
    if result.rows:
        # The scope and the cited document first: on a narrow screen they stay in view.
        header = [
            *([scope_title] if with_scope else []),
            "Document",
            *(_header(view, name) for name in result.columns),
        ]
        units = [amount_unit(view, name) for name in result.columns]
        scoped = [name in view.scope_columns for name in result.columns]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join("---" for _ in header) + " |")
        for row in result.rows:
            source = sources[row.source_id]
            ref = notes.ref(
                row.source_id,
                row.locator,
                "deterministic-table",
                "verified",
                block_ids=(f"{row.table_id}:{row.row_id}",),
            )
            link = f"[{_cell_text(source.title)}]({relative_link(path, source.page_path)})"
            cells = [
                *([names.cell(row.scope)] if with_scope else []),
                f"{link}{ref}",
                *(
                    names.cell(value) if is_scope else _value(value, unit)
                    for value, unit, is_scope in zip(row.values, units, scoped, strict=True)
                ),
            ]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
        if result.truncated:
            lines += [f"Only the first {MAX_VIEW_ROWS} rows are shown and summed.", ""]
    else:
        lines += ["No row of the documents matches this view.", ""]
    if result.totals:
        lines += _totals_section(pack, result, names)
    lines += notes.sources_section()
    sensitivity = (
        max_sensitivity(*(sources[sid].sensitivity for sid in result.sources))
        if (result.sources)
        else "public"
    )
    summary = description or (
        f"{len(result.rows)} rows computed by code from the documents' tables, cited row by row."
    )
    frontmatter = ViewFrontmatter(
        id=format_view_id(view.slug),
        title=clean_inline(view.title) or view.slug,
        summary=summary,
        sensitivity=sensitivity,  # type: ignore[arg-type]
        updated=release_date(stamp),
        docwiki=stamp,
        view_slug=view.slug,
        sources=sorted(result.sources),
        rows=len(result.rows),
    )
    return Page(path=path, frontmatter=frontmatter, body="\n".join(lines)), notes.cited_locators()


def _totals_section(pack: DomainPack, result: ViewResult, names: _Scopes) -> list[str]:
    view = result.view
    scope_title = _cell_text(pack.scopes.title) if pack.scopes is not None else "Scope"
    header = [
        *([scope_title] if view.per_scope else []),
        "Rows",
        *(_header(view, name) for name in view.totals),
    ]
    lines = [
        "## Totals",
        "",
        "Sums computed by code from the cited rows above"
        + (", per " + scope_title.lower() if view.per_scope else "")
        + ".",
        "",
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for total in result.totals:
        name = "**All**" if total.scope is None else names.cell(total.scope)
        cells = [
            *([name] if view.per_scope else []),
            str(total.rows),
            *(_total(total.values[col], result.units.get(col)) for col in view.totals),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    skipped = result.totals[-1].skipped
    if skipped:
        parts = [
            f"{count} cell(s) of {_header(view, name)}" for name, count in sorted(skipped.items())
        ]
        lines += [f"Not summed because they are not numbers: {', '.join(parts)}.", ""]
    return lines


def view_sources(
    source_pages: Mapping[str, Page],
    docs: Mapping[str, ExtractedDoc],
    scopes: Mapping[str, str | None],
) -> list[ViewSource]:
    """The current documents of the release with their (redacted) tables; ``scopes`` are the
    scope values of the classifications (from the raw path)."""
    found: list[ViewSource] = []
    for source_id, page in sorted(source_pages.items()):
        fm = page.frontmatter
        if not isinstance(fm, SourceFrontmatter) or fm.status != "current":
            continue
        doc = docs.get(source_id)
        found.append(
            ViewSource(
                source_id=source_id,
                title=fm.title,
                page_path=page.path,
                doc_type=fm.doc_type,
                scope=scopes.get(source_id) or fm.scope,
                sensitivity=fm.sensitivity,
                tables=tuple(doc.tables) if doc is not None else (),
            )
        )
    return found


def build_view_pages(
    pack: DomainPack,
    sources: Sequence[ViewSource],
    *,
    stamp: DocwikiStamp,
    hub_scopes: Iterable[str] = (),
) -> ViewBuild:
    """The page of every view of the pack (none without ``views.yaml``), their cited row
    locators (for the evidence stage), the computed results and the run warnings.

    ``hub_scopes`` are the scope values that have a hub page in this release: the view pages
    name every scope by its label and link the ones listed here to their hub."""
    build = ViewBuild(pages=[], cited=[], results=[], warnings=[])
    if pack.views is None:
        return build
    by_id = {source.source_id: source for source in sources}
    hubs = frozenset(hub_scopes)
    for view in pack.views.views:
        result = compute_view(view, sources)
        page, cited = _render(pack, result, by_id, stamp=stamp, hubs=hubs)
        build.pages.append(page)
        build.cited.extend(cited)
        build.results.append(result)
        build.warnings.extend(result.warnings)
    return build


def build_views_index(
    view_pages: Sequence[Page], *, stamp: DocwikiStamp, updated: date
) -> Page | None:
    """``views/index.md`` (``index:views``): one line per computed view with its row count;
    ``None`` without views."""
    pages = sorted(
        (page for page in view_pages if isinstance(page.frontmatter, ViewFrontmatter)),
        key=lambda page: (page.frontmatter.title.casefold(), page.path),
    )
    if not pages:
        return None
    path = index_page_path("views")
    body = [
        "# Computed views",
        "",
        "Figures computed by code, not by a language model, from the tables of the documents; "
        "every row is cited to the row of the document it comes from.",
        "",
    ]
    for page in pages:
        fm = page.frontmatter
        assert isinstance(fm, ViewFrontmatter)
        link = f"[{clean_inline(fm.title)}]({relative_link(path, page.path)})"
        line = f"- {link}: {fm.rows} {'row' if fm.rows == 1 else 'rows'}"
        summary = clean_inline(fm.summary)
        body.append(f"{line}. {summary}" if summary else line)
    return Page(
        path=path,
        frontmatter=IndexFrontmatter(
            id="index:views",
            title="Computed views",
            summary="Every computed view: figures computed by code, every row cited.",
            sensitivity=max_sensitivity(  # type: ignore[arg-type]
                *(page.frontmatter.sensitivity for page in pages)
            ),
            updated=updated,
            docwiki=stamp,
        ),
        body="\n".join(body) + "\n",
    )
