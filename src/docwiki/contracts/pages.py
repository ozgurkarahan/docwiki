"""Page frontmatter (one model per page type), pages, evidence sidecars and skill files.

Frontmatter follows wiki-contract §3. ``Frontmatter`` is a discriminated union on ``type``;
use :func:`parse_frontmatter` for dicts loaded from YAML and :class:`Page` for whole files.
"""

# Pydantic copies mutable defaults per instance, so `= []` / `= {}` field defaults are safe.
# ruff: noqa: RUF012

from __future__ import annotations

import re
from typing import Annotated, Any, Literal, Self

from pydantic import Field, TypeAdapter, field_validator, model_validator

from docwiki.contracts._base import (
    ContractModel,
    IsoDate,
    Kebab,
    LangCode,
    MediaType,
    NonEmptyStr,
    RelPath,
    Sha256Ref,
)
from docwiki.contracts.enums import (
    AskedBy,
    Confidence,
    ExtractionAdapter,
    Provenance,
    Sensitivity,
    SourceStatus,
)
from docwiki.contracts.frontmatter import read_frontmatter, write_frontmatter
from docwiki.contracts.ids import (
    QUERY_ID_RE,
    RELEASE_ID_RE,
    SOURCE_ID_RE,
    format_entity_id,
    format_topic_id,
    is_entity_id,
)
from docwiki.contracts.locators import Locator, locator_key

__all__ = [
    "Alias",
    "DocwikiStamp",
    "EntityFrontmatter",
    "EvidenceFrontmatter",
    "EvidenceIndexFrontmatter",
    "EvidencePage",
    "ExtractionSummary",
    "Frontmatter",
    "GlossaryFrontmatter",
    "HubFrontmatter",
    "IndexFrontmatter",
    "LogFrontmatter",
    "MetaFrontmatter",
    "Page",
    "QueryFrontmatter",
    "SkillFile",
    "SkillFrontmatter",
    "SourceFrontmatter",
    "TopicFrontmatter",
    "parse_frontmatter",
]

SourceId = Annotated[str, Field(pattern=SOURCE_ID_RE.pattern)]
ReleaseId = Annotated[str, Field(pattern=RELEASE_ID_RE.pattern)]
TopicId = Annotated[
    str, Field(pattern=r"^topic:(?:[a-z0-9]+(?:-[a-z0-9]+)*/)?[a-z0-9]+(?:-[a-z0-9]+)*$")
]
Tag = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:[-_/][a-z0-9]+)*$")]
INDEX_ID_RE = re.compile(
    r"^index:(home|sources|entities|topics|queries"
    r"|entities/[a-z0-9]+(?:-[a-z0-9]+)*|hubs/[a-z0-9]+(?:-[a-z0-9]+)*)$"
)
HUB_ID_RE = re.compile(r"^hub:[a-z0-9]+(?:-[a-z0-9]+)*/[a-z0-9]+(?:-[a-z0-9]+)*$")
META_ID_RE = re.compile(r"^meta:[a-z0-9]+(?:[-/][a-z0-9]+)*$")


def _sorted_unique(values: list[str], field: str) -> list[str]:
    if values != sorted(set(values)):
        raise ValueError(f"{field} must be sorted and free of duplicates")
    return values


class DocwikiStamp(ContractModel):
    """``docwiki: {schema: 1, release: <release_id>}``."""

    schema_version: Literal[1] = Field(1, alias="schema")
    release: ReleaseId


class Alias(ContractModel):
    """Alternative name with a language tag (``{text, lang}``)."""

    text: NonEmptyStr
    lang: LangCode


class _BaseFrontmatter(ContractModel):
    id: NonEmptyStr
    type: str
    title: NonEmptyStr
    summary: str
    lang: Literal["en"] = "en"
    sensitivity: Sensitivity
    updated: IsoDate
    tags: list[Tag] = []
    docwiki: DocwikiStamp

    @field_validator("tags")
    @classmethod
    def _tags(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value, "tags")

    @field_validator("summary")
    @classmethod
    def _summary(cls, value: str) -> str:
        if "\n" in value:
            raise ValueError("summary must be a single line")
        return value


class ExtractionSummary(ContractModel):
    """``extraction: {adapter, version, provenance_mix}``; the mix counts blocks per provenance."""

    adapter: ExtractionAdapter
    version: NonEmptyStr
    provenance_mix: dict[Provenance, Annotated[int, Field(ge=0)]] = {}


class SourceFrontmatter(_BaseFrontmatter):
    type: Literal["source"] = "source"
    source_id: SourceId
    source_path: RelPath
    source_hash: Sha256Ref
    media_type: MediaType
    doc_type: Kebab
    category: Kebab
    doc_number: str | None = None
    revision: str | None = None
    scope: Kebab | None = None
    """The scope value the document belongs to (``moreau``, or the default ``entreprise``), from
    its raw path; ``None`` when the pack declares no scopes (v1.7, ADR 0011)."""
    phase: str | None = None
    lot: str | None = None
    status: SourceStatus
    supersedes: list[SourceId] = []
    superseded_by: list[SourceId] = []
    original_lang: LangCode
    pages: Annotated[int, Field(ge=1)] | None = None
    entities: list[str] = []
    topics: list[TopicId] = []
    authority: Annotated[int, Field(ge=1, le=10)]
    extraction: ExtractionSummary

    @field_validator("supersedes", "superseded_by", "topics")
    @classmethod
    def _sorted_ids(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value, "id lists")

    @field_validator("entities")
    @classmethod
    def _entities(cls, value: list[str]) -> list[str]:
        for entity_id in value:
            if not is_entity_id(entity_id):
                raise ValueError(f"invalid entity id {entity_id!r}")
        return _sorted_unique(value, "entities")

    @model_validator(mode="after")
    def _consistency(self) -> Self:
        if self.id != self.source_id:
            raise ValueError("source page id must equal source_id")
        if self.status == "superseded" and not self.superseded_by:
            raise ValueError("superseded sources must list superseded_by")
        if self.status == "current" and self.superseded_by:
            raise ValueError("current sources must not list superseded_by")
        if self.source_id in self.supersedes or self.source_id in self.superseded_by:
            raise ValueError("a source cannot supersede itself")
        return self


class EntityFrontmatter(_BaseFrontmatter):
    type: Literal["entity"] = "entity"
    entity_type: Kebab
    key: Kebab
    aliases: list[Alias] = []
    sources: list[SourceId] = []

    @field_validator("sources")
    @classmethod
    def _sources(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value, "sources")

    @model_validator(mode="after")
    def _consistency(self) -> Self:
        if self.id != format_entity_id(self.entity_type, self.key):
            raise ValueError("entity page id must be '<entity_type>:<key>'")
        seen = [(alias.text, alias.lang) for alias in self.aliases]
        if len(seen) != len(set(seen)):
            raise ValueError("aliases must be unique")
        return self


class TopicFrontmatter(_BaseFrontmatter):
    type: Literal["topic"] = "topic"
    topic_slug: Kebab
    scope: Kebab | None = None
    """For a topic written once per scope (``per_scope`` in the catalog): its scope value."""
    sources: list[SourceId] = []
    confidence: Confidence
    contradictions: Annotated[int, Field(ge=0)] = 0
    superseded_claims: Annotated[int, Field(ge=0)] = 0

    @field_validator("sources")
    @classmethod
    def _sources(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value, "sources")

    @model_validator(mode="after")
    def _consistency(self) -> Self:
        if self.id != format_topic_id(self.topic_slug, self.scope):
            raise ValueError("topic page id must be 'topic:[<scope>/]<topic_slug>'")
        return self


class HubFrontmatter(_BaseFrontmatter):
    """The hub page of one scope value (v1.7, ADR 0011), built by code: ``hub:<folder>/<key>``
    at ``<folder>/<key>.md`` (``chantiers/moreau.md``)."""

    type: Literal["hub"] = "hub"
    scope_type: Kebab
    scope: Kebab
    sources: list[SourceId] = []

    @field_validator("sources")
    @classmethod
    def _sources(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value, "sources")

    @model_validator(mode="after")
    def _consistency(self) -> Self:
        if not HUB_ID_RE.match(self.id) or not self.id.endswith(f"/{self.scope}"):
            raise ValueError("hub page id must be 'hub:<folder>/<scope>'")
        return self


class QueryFrontmatter(_BaseFrontmatter):
    type: Literal["query"] = "query"
    question: NonEmptyStr
    asked_by: AskedBy
    sources: list[SourceId] = []
    approved_by: NonEmptyStr

    @field_validator("sources")
    @classmethod
    def _sources(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value, "sources")

    @model_validator(mode="after")
    def _consistency(self) -> Self:
        if not QUERY_ID_RE.match(self.id):
            raise ValueError("query page id must be 'query:<yyyy-mm-dd>-<slug>'")
        return self


class IndexFrontmatter(_BaseFrontmatter):
    """Index pages: ``index:home``, ``index:sources``, ``index:entities``,
    ``index:entities/<type>``,
    ``index:topics``, ``index:queries``."""

    type: Literal["index"] = "index"

    @model_validator(mode="after")
    def _consistency(self) -> Self:
        if not INDEX_ID_RE.match(self.id):
            raise ValueError("index page id must be 'index:<scope>'")
        return self


class MetaFrontmatter(_BaseFrontmatter):
    """Meta pages: ``meta:agents`` (AGENTS.md), ``meta:quality``, ``meta:runs/<run_id>``."""

    type: Literal["meta"] = "meta"

    @model_validator(mode="after")
    def _consistency(self) -> Self:
        if not META_ID_RE.match(self.id):
            raise ValueError("meta page id must be 'meta:<name>'")
        return self


class GlossaryFrontmatter(_BaseFrontmatter):
    type: Literal["glossary"] = "glossary"
    id: Literal["glossary"] = "glossary"


class LogFrontmatter(_BaseFrontmatter):
    type: Literal["log"] = "log"
    id: Literal["log"] = "log"


Frontmatter = Annotated[
    SourceFrontmatter
    | EntityFrontmatter
    | TopicFrontmatter
    | HubFrontmatter
    | QueryFrontmatter
    | IndexFrontmatter
    | MetaFrontmatter
    | GlossaryFrontmatter
    | LogFrontmatter,
    Field(discriminator="type"),
]
_FRONTMATTER_ADAPTER: TypeAdapter[Any] = TypeAdapter(Frontmatter)


def parse_frontmatter(data: dict[str, Any]) -> Frontmatter:
    """Validate a frontmatter mapping into the model for its ``type``."""
    return _FRONTMATTER_ADAPTER.validate_python(data)


class Page(ContractModel):
    """A wiki page: path (relative to the wiki root), frontmatter and Markdown body."""

    path: RelPath
    frontmatter: Frontmatter
    body: str

    @classmethod
    def parse(cls, text: str, path: str) -> Page:
        data, body = read_frontmatter(text, where=path)
        return cls(path=path, frontmatter=parse_frontmatter(data), body=body)

    def render(self) -> str:
        """File text with LF line endings and stable frontmatter key order."""
        data = self.frontmatter.model_dump(mode="python", by_alias=True)
        return write_frontmatter(data, self.body)


class EvidenceFrontmatter(ContractModel):
    """Evidence sidecar frontmatter (evidence-contract §5)."""

    id: NonEmptyStr
    type: Literal["evidence"] = "evidence"
    title: NonEmptyStr
    source_id: SourceId
    locator: Locator
    provenance: Provenance
    sensitivity: Sensitivity

    @model_validator(mode="after")
    def _consistency(self) -> Self:
        expected = f"evidence:{self.source_id}:{locator_key(self.locator)}"
        if self.id != expected:
            raise ValueError(f"evidence id must be {expected!r}")
        return self

    @property
    def locator_key(self) -> str:
        return locator_key(self.locator)


class EvidenceIndexFrontmatter(ContractModel):
    """Frontmatter of ``evidence/<source_id>/index.md``."""

    id: NonEmptyStr
    type: Literal["evidence-index"] = "evidence-index"
    title: NonEmptyStr
    source_id: SourceId
    sensitivity: Sensitivity
    document_date: IsoDate | None = None
    """The document's own date when its extraction found one (v1.7): the date it was written,
    sent or created, never the date it was compiled."""

    @model_validator(mode="after")
    def _consistency(self) -> Self:
        if self.id != f"evidence:{self.source_id}":
            raise ValueError("evidence index id must be 'evidence:<source_id>'")
        return self


class EvidencePage(ContractModel):
    """An evidence sidecar or evidence index (path in the content namespace)."""

    path: RelPath
    frontmatter: Annotated[
        EvidenceFrontmatter | EvidenceIndexFrontmatter, Field(discriminator="type")
    ]
    body: str

    @classmethod
    def parse(cls, text: str, path: str) -> EvidencePage:
        data, body = read_frontmatter(text, where=path)
        return cls.model_validate({"path": path, "frontmatter": data, "body": body})

    def render(self) -> str:
        return write_frontmatter(
            self.frontmatter.model_dump(mode="python", by_alias=True), self.body
        )


MAX_SKILL_BODY_WORDS = 5000


class SkillFrontmatter(ContractModel):
    """``SKILL.md`` frontmatter (Agent Skills): kebab ``name`` ≤ 64, ``description`` ≤ 1024."""

    name: Kebab
    description: Annotated[str, Field(min_length=1, max_length=1024)]


class SkillFile(ContractModel):
    """A parsed ``SKILL.md``; ``parse`` enforces the folder name and the 5,000-word body limit."""

    name: Kebab
    frontmatter: SkillFrontmatter
    body: str

    @classmethod
    def parse(cls, text: str, name: str) -> SkillFile:
        data, body = read_frontmatter(text, where=f"{name}/SKILL.md")
        skill = cls(name=name, frontmatter=SkillFrontmatter.model_validate(data), body=body)
        if skill.frontmatter.name != name:
            raise ValueError(
                f"skill name {skill.frontmatter.name!r} must match its folder {name!r}"
            )
        if len(body.split()) > MAX_SKILL_BODY_WORDS:
            raise ValueError(f"skill {name!r} body exceeds {MAX_SKILL_BODY_WORDS} words")
        return skill

    def render(self) -> str:
        return write_frontmatter(self.frontmatter.model_dump(mode="python"), self.body)
