"""ExtractedDoc: the single evidence contract returned by every extractor (evidence-contract §1)."""

# Pydantic copies mutable defaults per instance, so `= []` / `= {}` field defaults are safe.
# ruff: noqa: RUF012

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from docwiki.contracts._base import (
    BBox,
    ContractModel,
    IsoDate,
    LangCode,
    MediaType,
    NonEmptyStr,
    RelPath,
    Sha256Ref,
)
from docwiki.contracts.enums import BlockKind, ExtractionAdapter, Provenance
from docwiki.contracts.ids import SOURCE_ID_RE
from docwiki.contracts.locators import Locator, locator_key

__all__ = [
    "Block",
    "DocMetadata",
    "ExtractedDoc",
    "ExtractionInfo",
    "Figure",
    "Table",
    "TableRow",
    "row_id_for",
]

BlockId = Annotated[str, Field(pattern=r"^b\d{4,}$")]
TableId = Annotated[str, Field(pattern=r"^t\d{2,}$")]
FigureId = Annotated[str, Field(pattern=r"^f\d{2,}$")]
RowId = Annotated[str, Field(pattern=r"^r\d{4,}$")]


def row_id_for(row_number: int) -> str:
    """``r`` + 4-digit 1-based row number in the original sheet/CSV/table (header = row 1)."""
    if row_number < 1:
        raise ValueError("row numbers are 1-based")
    return f"r{row_number:04d}"


class Block(ContractModel):
    """A unit of extracted content in reading order."""

    id: BlockId
    kind: BlockKind
    text: str
    level: Annotated[int, Field(ge=1, le=9)] | None = None
    locator: Locator
    provenance: Provenance
    lang: LangCode | None = None
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] | None = None

    @property
    def locator_key(self) -> str:
        return locator_key(self.locator)


class TableRow(ContractModel):
    """One data row. ``row_id`` encodes the original 1-based row number (``r0012``)."""

    row_id: RowId
    cells: list[str]


class Table(ContractModel):
    """A table parsed deterministically (XLSX/CSV) or by layout analysis (PDF/DOCX/PPTX)."""

    id: TableId
    locator: Locator
    provenance: Literal["deterministic-table", "native-text", "ocr"]
    columns: list[str]
    rows: list[TableRow]
    artifact: RelPath

    @model_validator(mode="after")
    def _shape(self) -> Self:
        width = len(self.columns)
        if width == 0:
            raise ValueError("a table needs at least one column")
        seen: set[str] = set()
        for row in self.rows:
            if len(row.cells) != width:
                raise ValueError(f"row {row.row_id} has {len(row.cells)} cells, expected {width}")
            if row.row_id in seen:
                raise ValueError(f"duplicate row_id {row.row_id}")
            seen.add(row.row_id)
        return self


class Figure(ContractModel):
    """A figure region; ``description`` (if any) is model-generated and labelled as such."""

    id: FigureId
    locator: Locator
    image: RelPath
    caption: str | None = None
    description: str | None = None
    description_provenance: Literal["model-description"] | None = None
    bbox: BBox | None = None

    @model_validator(mode="after")
    def _description(self) -> Self:
        if (self.description is None) != (self.description_provenance is None):
            raise ValueError("description and description_provenance go together")
        return self


class DocMetadata(ContractModel):
    doc_number: str | None = None
    revision: str | None = None
    authored: IsoDate | None = None
    page_count: Annotated[int, Field(ge=0)] | None = None


class ExtractionInfo(ContractModel):
    adapter: ExtractionAdapter
    adapter_version: NonEmptyStr
    analyzer: str | None = None
    model: str | None = None
    warnings: list[str] = []


class ExtractedDoc(ContractModel):
    """Output of the ``extract`` stage, stored as JSON in the extract artifact."""

    schema_version: Literal[1] = Field(1, alias="schema")
    source_id: Annotated[str, Field(pattern=SOURCE_ID_RE.pattern)]
    source_path: RelPath
    source_hash: Sha256Ref
    media_type: MediaType
    lang: LangCode
    title_hint: str | None = None
    metadata: DocMetadata = Field(default_factory=DocMetadata)
    blocks: list[Block] = []
    tables: list[Table] = []
    figures: list[Figure] = []
    extraction: ExtractionInfo

    @model_validator(mode="after")
    def _unique_ids(self) -> Self:
        for label, ids in (
            ("block", [block.id for block in self.blocks]),
            ("table", [table.id for table in self.tables]),
            ("figure", [figure.id for figure in self.figures]),
        ):
            if len(ids) != len(set(ids)):
                raise ValueError(f"{label} ids must be unique")
        return self

    def block(self, block_id: str) -> Block:
        for block in self.blocks:
            if block.id == block_id:
                return block
        raise KeyError(block_id)

    def table(self, table_id: str) -> Table:
        for table in self.tables:
            if table.id == table_id:
                return table
        raise KeyError(table_id)

    def text(self) -> str:
        """Concatenated block text in reading order (used by rules and size estimates)."""
        return "\n".join(block.text for block in self.blocks if block.text)
