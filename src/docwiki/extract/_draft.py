"""Adapter output before ids are assigned, and its conversion into the ExtractedDoc contract.

Adapters append blocks and figures to :class:`Draft` in reading order. Ids are assigned only in
:func:`finalize`, after the optional figure descriptions are known, so that ``figure-ref`` blocks
sit at the figure's reading-order position and ids stay sequential (``b0001``…, ``t01``…,
``f01``…).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from docwiki.contracts import Block, ExtractedDoc, Figure, Locator, Table, TableRow, row_id_for
from docwiki.contracts.enums import BlockKind, ExtractionAdapter, Provenance
from docwiki.contracts.extracted import DocMetadata, ExtractionInfo
from docwiki.extract._text import guess_lang

__all__ = [
    "ADAPTER_VERSION",
    "CU_ADAPTER_VERSION",
    "Draft",
    "DraftBlock",
    "DraftFigure",
    "DraftTable",
    "finalize",
    "round_bbox",
]

ADAPTER_VERSION = "1.0.0"
"""Version of DocWiki's extraction logic (block segmentation, locators). Bump on any change that
alters the ExtractedDoc of an unchanged input."""

CU_API_VERSION = "2025-11-01"
CU_ADAPTER_VERSION = f"{ADAPTER_VERSION}+cu.{CU_API_VERSION}"

TableProvenance = Literal["deterministic-table", "native-text", "ocr"]


def round_bbox(values: tuple[float, float, float, float] | list[float]) -> list[float] | None:
    """Clamp to ``[0, 1]``, order and round a normalised box; None when it is degenerate."""
    x0, y0, x1, y1 = (min(1.0, max(0.0, float(v))) for v in values)
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    box = [round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)]
    if box[2] - box[0] <= 0.0 or box[3] - box[1] <= 0.0:
        return None
    return box


@dataclass
class DraftBlock:
    kind: BlockKind
    text: str
    locator: Locator
    provenance: Provenance
    level: int | None = None
    confidence: float | None = None


@dataclass
class DraftFigure:
    locator: Locator
    png: bytes
    caption: str | None = None
    bbox: list[float] | None = None


@dataclass
class DraftTable:
    locator: Locator
    provenance: TableProvenance
    columns: list[str]
    rows: list[tuple[int, list[str]]] = field(default_factory=list)


@dataclass
class Draft:
    """Everything an adapter found, in reading order."""

    adapter: ExtractionAdapter = "local"
    adapter_version: str = ADAPTER_VERSION
    analyzer: str | None = None
    items: list[DraftBlock | DraftFigure] = field(default_factory=list)
    tables: list[DraftTable] = field(default_factory=list)
    page_images: dict[int, bytes] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    title_hint: str | None = None
    lang: str | None = None
    authored: date | None = None
    page_count: int | None = None
    model: str | None = None

    def block(
        self,
        kind: BlockKind,
        text: str,
        locator: Locator,
        provenance: Provenance,
        *,
        level: int | None = None,
        confidence: float | None = None,
    ) -> None:
        self.items.append(DraftBlock(kind, text, locator, provenance, level, confidence))

    def figure(
        self,
        locator: Locator,
        png: bytes,
        *,
        caption: str | None = None,
        bbox: list[float] | None = None,
    ) -> None:
        self.items.append(DraftFigure(locator, png, caption, bbox))

    def table(
        self,
        locator: Locator,
        provenance: TableProvenance,
        columns: list[str],
        rows: list[tuple[int, list[str]]],
    ) -> DraftTable:
        table = DraftTable(locator, provenance, columns, rows)
        self.tables.append(table)
        return table

    def warn(self, code: str, message: str) -> None:
        """Record a recoverable issue as ``"<code>: <message>"`` (shown in diagnostics)."""
        entry = f"{code}: {message}"
        if entry not in self.warnings:
            self.warnings.append(entry)

    @property
    def figures(self) -> list[DraftFigure]:
        return [item for item in self.items if isinstance(item, DraftFigure)]

    @property
    def blocks(self) -> list[DraftBlock]:
        return [item for item in self.items if isinstance(item, DraftBlock)]


def finalize(
    draft: Draft,
    *,
    source_id: str,
    source_path: str,
    source_hash: str,
    media_type: str,
    descriptions: Mapping[int, str] | None = None,
) -> tuple[ExtractedDoc, dict[str, bytes]]:
    """Assign ids and build the validated :class:`ExtractedDoc` plus ``{figure_id: png}``.

    ``descriptions`` maps the 0-based figure index (order of appearance) to a generated
    description; each described figure gets a ``figure-ref`` block (provenance
    ``model-description``) at its reading-order position.
    """
    descriptions = descriptions or {}
    blocks: list[Block] = []
    figures: list[Figure] = []
    figure_png: dict[str, bytes] = {}

    def add_block(item: DraftBlock) -> None:
        blocks.append(
            Block(
                id=f"b{len(blocks) + 1:04d}",
                kind=item.kind,
                text=item.text,
                level=item.level,
                locator=item.locator,
                provenance=item.provenance,
                confidence=item.confidence,
            )
        )

    for item in draft.items:
        if isinstance(item, DraftBlock):
            add_block(item)
            continue
        index = len(figures)
        figure_id = f"f{index + 1:02d}"
        description = descriptions.get(index)
        figures.append(
            Figure(
                id=figure_id,
                locator=item.locator,
                image=f"figures/{figure_id}.png",
                caption=item.caption,
                description=description,
                description_provenance="model-description" if description else None,
                bbox=item.bbox,
            )
        )
        figure_png[figure_id] = item.png
        if description:
            add_block(DraftBlock("figure-ref", description, item.locator, "model-description"))

    tables: list[Table] = []
    for index, draft_table in enumerate(draft.tables, 1):
        table_id = f"t{index:02d}"
        tables.append(
            Table(
                id=table_id,
                locator=draft_table.locator,
                provenance=draft_table.provenance,
                columns=draft_table.columns,
                rows=[
                    TableRow(row_id=row_id_for(number), cells=cells)
                    for number, cells in draft_table.rows
                ],
                artifact=f"tables/{table_id}.parquet",
            )
        )

    text = "\n".join(block.text for block in blocks if block.provenance != "model-description")
    lang = draft.lang or guess_lang(text)
    doc = ExtractedDoc(
        schema=1,
        source_id=source_id,
        source_path=source_path,
        source_hash=source_hash,
        media_type=media_type,
        lang=lang,
        title_hint=draft.title_hint or None,
        metadata=DocMetadata(authored=draft.authored, page_count=draft.page_count),
        blocks=blocks,
        tables=tables,
        figures=figures,
        extraction=ExtractionInfo(
            adapter=draft.adapter,
            adapter_version=draft.adapter_version,
            analyzer=draft.analyzer,
            model=draft.model,
            warnings=list(draft.warnings),
        ),
    )
    return doc, figure_png
