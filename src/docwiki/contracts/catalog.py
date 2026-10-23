"""Machine catalog ``catalog.json`` (wiki-contract §6), schema 1."""

# Pydantic copies mutable defaults per instance, so `= []` / `= {}` field defaults are safe.
# ruff: noqa: RUF012

from __future__ import annotations

from typing import Annotated, Any, Literal, Self

from pydantic import Field, model_validator

from docwiki.contracts._base import (
    ContractModel,
    Kebab,
    MediaType,
    NonEmptyStr,
    RelPath,
    Sha256Ref,
    UtcDateTime,
)
from docwiki.contracts.enums import EdgeKind, PageType, Sensitivity, SourceStatus
from docwiki.contracts.ids import RELEASE_ID_RE, SOURCE_ID_RE
from docwiki.contracts.pages import (
    EntityFrontmatter,
    HubFrontmatter,
    QueryFrontmatter,
    SourceFrontmatter,
    TopicFrontmatter,
)

__all__ = [
    "Catalog",
    "CatalogEdge",
    "CatalogGlossaryEntry",
    "CatalogPage",
    "CatalogSource",
    "catalog_page_for",
    "catalog_source_for",
]

SourceId = Annotated[str, Field(pattern=SOURCE_ID_RE.pattern)]


class CatalogPage(ContractModel):
    id: NonEmptyStr
    type: PageType
    path: RelPath
    title: NonEmptyStr
    summary: str
    sensitivity: Sensitivity
    status: SourceStatus | None = None
    tags: list[str] = []
    entities: list[str] = []
    topics: list[str] = []
    sources: list[SourceId] = []
    scope: Kebab | None = None
    """The scope value of a source, scoped topic or hub page (v1.7, ADR 0011)."""
    lang: Literal["en"] = "en"


class CatalogEdge(ContractModel):
    """Directed relation between two pages (see CONTRACT.md for the meaning of each kind)."""

    from_: NonEmptyStr = Field(alias="from")
    to: NonEmptyStr
    kind: EdgeKind


class CatalogSource(ContractModel):
    source_id: SourceId
    path: RelPath
    hash: Sha256Ref
    media_type: MediaType
    status: SourceStatus
    doc_number: str | None = None
    revision: str | None = None
    scope: Kebab | None = None
    phase: str | None = None


class CatalogGlossaryEntry(ContractModel):
    term: NonEmptyStr
    synonyms: dict[str, list[str]] = {}
    page: Annotated[str, Field(pattern=r"^glossary\.md#[^\s#]+$")]


class Catalog(ContractModel):
    schema_version: Literal[1] = Field(1, alias="schema")
    release_id: Annotated[str, Field(pattern=RELEASE_ID_RE.pattern)]
    audience: Sensitivity
    generated_at: UtcDateTime
    pages: list[CatalogPage] = []
    edges: list[CatalogEdge] = []
    sources: list[CatalogSource] = []
    glossary: list[CatalogGlossaryEntry] = []

    @model_validator(mode="after")
    def _consistency(self) -> Self:
        ids = [page.id for page in self.pages]
        if len(ids) != len(set(ids)):
            raise ValueError("catalog page ids must be unique")
        paths = [page.path for page in self.pages]
        if len(paths) != len(set(paths)):
            raise ValueError("catalog page paths must be unique")
        known = set(ids)
        for edge in self.edges:
            if edge.from_ not in known or edge.to not in known:
                raise ValueError(f"edge {edge.from_} -> {edge.to} references an unknown page")
        keys = [(edge.from_, edge.to, edge.kind) for edge in self.edges]
        if len(keys) != len(set(keys)):
            raise ValueError("catalog edges must be unique")
        source_ids = [source.source_id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("catalog source ids must be unique")
        return self

    def page_by_id(self) -> dict[str, CatalogPage]:
        return {page.id: page for page in self.pages}

    def page_by_path(self) -> dict[str, CatalogPage]:
        return {page.path: page for page in self.pages}


def catalog_page_for(frontmatter: Any, path: str) -> CatalogPage:
    """The catalog entry of a page, derived only from its frontmatter (single source of truth).

    ``sources``: a source page lists itself; entity/topic/query pages list their ``sources``.
    ``entities``/``topics``: copied from source pages, empty for other types.
    ``status``: the source status for source pages, else ``None``.
    """
    sources: list[str] = []
    entities: list[str] = []
    topics: list[str] = []
    status = None
    if isinstance(frontmatter, SourceFrontmatter):
        sources = [frontmatter.source_id]
        entities = list(frontmatter.entities)
        topics = list(frontmatter.topics)
        status = frontmatter.status
    elif isinstance(
        frontmatter, EntityFrontmatter | TopicFrontmatter | QueryFrontmatter | HubFrontmatter
    ):
        sources = list(frontmatter.sources)
    scope = getattr(frontmatter, "scope", None)
    return CatalogPage(
        id=frontmatter.id,
        type=frontmatter.type,
        path=path,
        title=frontmatter.title,
        summary=frontmatter.summary,
        sensitivity=frontmatter.sensitivity,
        status=status,
        tags=list(frontmatter.tags),
        entities=entities,
        topics=topics,
        sources=sources,
        scope=scope,
        lang=frontmatter.lang,
    )


def catalog_source_for(frontmatter: SourceFrontmatter) -> CatalogSource:
    return CatalogSource(
        source_id=frontmatter.source_id,
        path=frontmatter.source_path,
        hash=frontmatter.source_hash,
        media_type=frontmatter.media_type,
        status=frontmatter.status,
        doc_number=frontmatter.doc_number,
        revision=frontmatter.revision,
        scope=frontmatter.scope,
        phase=frontmatter.phase,
    )
