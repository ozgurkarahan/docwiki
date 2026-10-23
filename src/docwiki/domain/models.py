"""Schema models for every file of a domain pack (domain-and-corpus §1)."""

# Pydantic copies mutable defaults per instance, so `= []` / `= {}` field defaults are safe.
# ruff: noqa: RUF012

from __future__ import annotations

import re
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from docwiki.contracts._base import (
    ContractModel,
    Kebab,
    LangCode,
    NonEmptyStr,
    canonical_json,
    sha256_hex,
)
from docwiki.contracts.enums import Sensitivity
from docwiki.contracts.i18n import CORE_STRINGS, STRUCTURAL_KEYS, Strings
from docwiki.contracts.ids import RESERVED_ENTITY_TYPES
from docwiki.contracts.layout import CORE_SKILLS

__all__ = [
    "AmendmentRule",
    "ArbitrationPair",
    "Category",
    "DocType",
    "DocTypeRule",
    "DomainPack",
    "EntitiesFile",
    "EntityAlias",
    "EntityType",
    "GlossaryFile",
    "GlossaryTerm",
    "LockedTerm",
    "PackInfo",
    "PhaseDef",
    "RegistryEntry",
    "ResolutionFile",
    "ScopeDefault",
    "ScopePath",
    "ScopesFile",
    "SensitivityFile",
    "SensitivityRule",
    "SupersessionFile",
    "TaxonomyFile",
    "TermsFile",
    "TopicDef",
    "TopicsFile",
    "UpdateRule",
    "ViewDef",
    "ViewsFile",
    "locked_terms_note",
]

Scalar = str | int | float | bool | None
Authority = Annotated[int, Field(ge=1, le=10)]


def _check_regex(value: str | None) -> str | None:
    if value is not None:
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError(f"invalid regex: {exc}") from exc
    return value


def _unique(values: list[str], what: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"duplicate {what} {value!r}")
        seen.add(value)


class PackInfo(ContractModel):
    """``pack.yaml``."""

    name: Kebab
    title: NonEmptyStr
    description: str = ""
    default_audience: Sensitivity
    languages: Annotated[list[LangCode], Field(min_length=1)]
    wiki_title: NonEmptyStr
    fictional: bool = False
    banner: str | None = None
    wiki_languages: Annotated[list[LangCode], Field(min_length=1)] = ["en"]
    """The languages of the wiki (v1.7, ADR 0012): the first is canonical (the language the
    pages are compiled in), the others get a mirror written by the ``translate`` stage under
    ``wiki/<lang>/``. A pack that does not declare it keeps the English-only wiki."""

    @field_validator("languages", "wiki_languages")
    @classmethod
    def _languages(cls, value: list[str]) -> list[str]:
        _unique(value, "language")
        return value


class Category(ContractModel):
    key: Kebab
    title: NonEmptyStr
    description: str = ""


class DocTypeRule(ContractModel):
    """A rule matches when every regex it defines matches (``filename_regex`` on the file name,
    ``text_regex`` on the first ``first_chars`` characters of the extracted text)."""

    filename_regex: str | None = None
    text_regex: str | None = None
    first_chars: Annotated[int, Field(ge=1)] = 2000

    @field_validator("filename_regex", "text_regex")
    @classmethod
    def _regex(cls, value: str | None) -> str | None:
        return _check_regex(value)

    @model_validator(mode="after")
    def _one_condition(self) -> Self:
        if self.filename_regex is None and self.text_regex is None:
            raise ValueError("a rule needs filename_regex and/or text_regex")
        return self


class DocType(ContractModel):
    key: Kebab
    title: NonEmptyStr
    category: Kebab
    authority: Authority
    rules: list[DocTypeRule] = []
    label: NonEmptyStr | None = None
    """Short display label (``PV de réception``) for the Documents register and the source page
    header; the title when absent. Never derived from the key."""

    @property
    def display_label(self) -> str:
        return self.label or self.title


class TaxonomyFile(ContractModel):
    """``taxonomy.yaml``."""

    categories: Annotated[list[Category], Field(min_length=1)]
    doc_types: Annotated[list[DocType], Field(min_length=1)]

    @model_validator(mode="after")
    def _references(self) -> Self:
        _unique([c.key for c in self.categories], "category")
        _unique([d.key for d in self.doc_types], "doc type")
        known = {c.key for c in self.categories}
        for doc_type in self.doc_types:
            if doc_type.category not in known:
                raise ValueError(
                    f"doc type {doc_type.key!r} uses unknown category {doc_type.category!r}"
                )
        return self


class EntityAlias(ContractModel):
    text: NonEmptyStr
    lang: LangCode


class EntityType(ContractModel):
    key: Kebab
    title: NonEmptyStr
    """Plural display title (``Spare parts``): entity index title and related-section label."""
    description: str = ""
    attribute_labels: dict[NonEmptyStr, NonEmptyStr] = {}
    """Display label of each registry attribute key, in display order (``maitre_d_oeuvre`` →
    ``Maître d'œuvre``). When given, the hub page shows only the labelled attributes."""

    @field_validator("key")
    @classmethod
    def _not_reserved(cls, value: str) -> str:
        if value in RESERVED_ENTITY_TYPES:
            raise ValueError(f"entity type {value!r} is reserved")
        return value


class RegistryEntry(ContractModel):
    type: Kebab
    key: Kebab
    label: NonEmptyStr
    aliases: list[EntityAlias] = []
    attributes: dict[str, Scalar] = {}

    @property
    def id(self) -> str:
        return f"{self.type}:{self.key}"


class EntitiesFile(ContractModel):
    """``entities.yaml``."""

    types: Annotated[list[EntityType], Field(min_length=1)]
    registry: list[RegistryEntry] = []

    @model_validator(mode="after")
    def _references(self) -> Self:
        _unique([t.key for t in self.types], "entity type")
        known = {t.key for t in self.types}
        for entry in self.registry:
            if entry.type not in known:
                raise ValueError(f"registry entry {entry.id!r} uses unknown type {entry.type!r}")
        _unique([entry.id for entry in self.registry], "entity")
        return self


class TopicDef(ContractModel):
    slug: Kebab
    title: NonEmptyStr
    description: str = ""
    keywords: list[NonEmptyStr] = []
    aliases: list[EntityAlias] = []
    min_score: Annotated[float, Field(gt=0)] | None = None
    min_sources: Annotated[int, Field(ge=1)] | None = None
    per_scope: bool = False
    """Written once per scope that has sources for it (``topics/<scope>/<slug>.md``) when the pack
    declares scopes (v1.7, ADR 0011); otherwise one company-wide page."""

    @model_validator(mode="after")
    def _terms(self) -> Self:
        if not self.keywords and not self.aliases:
            raise ValueError(f"topic {self.slug!r} needs keywords or aliases")
        return self


class TopicsFile(ContractModel):
    """``topics.yaml``."""

    topics: list[TopicDef] = []

    @model_validator(mode="after")
    def _unique_slugs(self) -> Self:
        _unique([t.slug for t in self.topics], "topic")
        return self


class GlossaryTerm(ContractModel):
    term: NonEmptyStr
    definition: NonEmptyStr
    synonyms: dict[LangCode, list[NonEmptyStr]] = {}
    see_also: list[str] = []


class GlossaryFile(ContractModel):
    """``glossary.yaml``."""

    terms: list[GlossaryTerm] = []

    @model_validator(mode="after")
    def _unique_terms(self) -> Self:
        _unique([t.term.casefold() for t in self.terms], "glossary term")
        return self


SCOPE_GROUPS = frozenset({"scope", "phase", "type", "lot"})
"""Named groups a scope path regex may capture."""


RESERVED_WIKI_FOLDERS = frozenset({"sources", "entities", "topics", "queries", "evidence"})
"""Wiki folders the hubs' folder (``scopes.plural``) may not take."""


class ScopePath(ContractModel):
    """A raw-path regex; its named groups give the scope value and the axes."""

    regex: NonEmptyStr

    @field_validator("regex")
    @classmethod
    def _regex(cls, value: str) -> str:
        try:
            compiled = re.compile(value)
        except re.error as exc:
            raise ValueError(f"invalid regex: {exc}") from exc
        unknown = set(compiled.groupindex) - SCOPE_GROUPS
        if unknown:
            raise ValueError(f"unknown named groups {sorted(unknown)}; use {sorted(SCOPE_GROUPS)}")
        return value


class PhaseDef(ContractModel):
    key: NonEmptyStr
    title: NonEmptyStr


class ScopeDefault(ContractModel):
    key: Kebab
    title: NonEmptyStr


class ScopesFile(ContractModel):
    """``scopes.yaml`` (v1.7, ADR 0011): the pack's one scope dimension (a chantier), read from
    the raw path, never from a model."""

    name: Kebab
    """The scope type (``chantier``): the registry entity type that describes each scope value."""
    title: NonEmptyStr
    plural: Kebab
    """The wiki folder of the hub pages (``chantiers``)."""
    default: ScopeDefault
    """The scope of a document no path regex matches (``entreprise``)."""
    paths: list[ScopePath] = []
    phases: list[PhaseDef] = []
    lot_regex: str | None = None
    """A regex with a ``lot`` group, tried on the file name when no path regex gave a lot."""

    @field_validator("plural")
    @classmethod
    def _plural(cls, value: str) -> str:
        if value in RESERVED_WIKI_FOLDERS:
            raise ValueError(f"plural {value!r} is a reserved wiki folder")
        return value

    @field_validator("lot_regex")
    @classmethod
    def _lot(cls, value: str | None) -> str | None:
        _check_regex(value)
        if value is not None and "lot" not in re.compile(value).groupindex:
            raise ValueError("lot_regex needs a named group 'lot'")
        return value

    def phase_title(self, key: str | None) -> str | None:
        return next((phase.title for phase in self.phases if phase.key == key), None)


class LockedTerm(ContractModel):
    """A trade term the wiki keeps in the documents' language (v1.7, ADR 0012): never translated
    or paraphrased; the English gloss is given once, on first use; the banned renderings are the
    translations that change its meaning (verify gate G16)."""

    term: NonEmptyStr
    forms: list[NonEmptyStr] = []
    """Other written forms of the same term (feminine, plural, abbreviation)."""
    gloss: NonEmptyStr
    banned: list[NonEmptyStr] = []
    avoid_senses: list[NonEmptyStr] = []
    """Everyday senses of the same word that the term must not carry, each with the word to use
    instead (v1.7, slice G), e.g. for « réception »: "receiving an invoice or a situation: write
    « remise »". The compile, entity and topic prompts receive them with the term."""


class TermsFile(ContractModel):
    """``terms.yaml``: the locked trade vocabulary."""

    terms: list[LockedTerm] = []


class SensitivityRule(ContractModel):
    tier: Sensitivity
    path_glob: str | None = None
    doc_type: Kebab | None = None

    @model_validator(mode="after")
    def _one_condition(self) -> Self:
        if self.path_glob is None and self.doc_type is None:
            raise ValueError("a sensitivity rule needs path_glob and/or doc_type")
        return self


class SensitivityFile(ContractModel):
    """``sensitivity.yaml``; when several rules match, the highest tier wins."""

    default: Literal["public", "internal"]
    rules: list[SensitivityRule] = []


class SupersessionFile(ContractModel):
    """``supersession.yaml``. Regexes may use named groups ``number`` / ``rev``."""

    doc_number_regex: NonEmptyStr
    revision_regex: NonEmptyStr
    revision_order: list[NonEmptyStr] | Literal["numeric"]
    explicit_reference_regex: str | None = None

    @field_validator("doc_number_regex", "revision_regex", "explicit_reference_regex")
    @classmethod
    def _regex(cls, value: str | None) -> str | None:
        return _check_regex(value)

    @field_validator("revision_order")
    @classmethod
    def _order(cls, value: list[str] | str) -> list[str] | str:
        if isinstance(value, list):
            if not value:
                raise ValueError("revision_order must not be empty")
            _unique(value, "revision")
        return value


class AmendmentRule(ContractModel):
    """Doc types whose documents change the terms of others (v1.7): a document of an
    ``amending`` type may change the terms of the documents of an ``amended`` type of the same
    scope (an amendment or a service order and the contract they relate to)."""

    amending: Annotated[list[Kebab], Field(min_length=1)]
    amended: Annotated[list[Kebab], Field(min_length=1)]

    @field_validator("amending", "amended")
    @classmethod
    def _unique_types(cls, value: list[str]) -> list[str]:
        _unique(value, "doc type")
        return value

    @model_validator(mode="after")
    def _disjoint(self) -> Self:
        both = sorted(set(self.amending) & set(self.amended))
        if both:
            raise ValueError(f"doc types both amending and amended: {', '.join(both)}")
        return self


class UpdateRule(ContractModel):
    """Doc types whose later documents report what happened since earlier ones (v1.7, slice G):
    a document of a ``later`` type dated after a document of an ``earlier`` type of the same
    scope updates it (a delivery postponed, a date moved, a réserve lifted). A disagreement
    between them is an update, shown with both dates, not a contradiction for the rule to
    decide by authority."""

    earlier: Annotated[list[Kebab], Field(min_length=1)]
    later: Annotated[list[Kebab], Field(min_length=1)]

    @field_validator("earlier", "later")
    @classmethod
    def _unique_types(cls, value: list[str]) -> list[str]:
        _unique(value, "doc type")
        return value


class ArbitrationPair(ContractModel):
    """Two doc types the resolution rule does not decide between (v1.7): a contradiction between
    a document of each is stated as to arbitrate, with the pack's ``reason``."""

    types: Annotated[list[Kebab], Field(min_length=2, max_length=2)]
    reason: NonEmptyStr

    @field_validator("reason")
    @classmethod
    def _one_line(cls, value: str) -> str:
        if "\n" in value.strip():
            raise ValueError("reason must be a single line")
        return value.strip()


class ResolutionFile(ContractModel):
    """``resolution.yaml``: contradiction policy, stated on topic pages (never silently applied).

    ``amendments`` and ``arbitrate`` (v1.7, optional) refine how the rule is stated: a
    contradiction between an amended document and an amending document of the same scope is a
    change, not a contradiction; a winner of an amended type is to review when its scope has
    amending documents; a pair of ``arbitrate`` types is never decided by the rule. ``updates``
    (v1.7, slice G, optional): a later report of the same scope updates an earlier document.
    """

    order: Annotated[list[Literal["authority", "recency"]], Field(min_length=1)] = [
        "authority",
        "recency",
    ]
    amendments: list[AmendmentRule] = []
    arbitrate: list[ArbitrationPair] = []
    updates: list[UpdateRule] = []
    notes: str = ""

    @field_validator("order")
    @classmethod
    def _order(cls, value: list[str]) -> list[str]:
        _unique(value, "resolution criterion")
        return value

    @field_validator("arbitrate")
    @classmethod
    def _pairs(cls, value: list[ArbitrationPair]) -> list[ArbitrationPair]:
        _unique(["\n".join(sorted(pair.types)) for pair in value], "arbitrate pair")
        return value

    def amendment(self, amending: str, amended: str) -> bool:
        """Whether documents of type ``amending`` may change those of type ``amended``."""
        return any(
            amending in rule.amending and amended in rule.amended for rule in self.amendments
        )

    def update(self, earlier: str, later: str) -> bool:
        """Whether a later document of type ``later`` reports news on one of type ``earlier``."""
        return any(earlier in rule.earlier and later in rule.later for rule in self.updates)

    def amending_types(self, amended: str) -> set[str]:
        """The doc types that may change the documents of type ``amended``."""
        return {key for rule in self.amendments if amended in rule.amended for key in rule.amending}

    def arbitration(self, first: str, second: str) -> ArbitrationPair | None:
        """The ``arbitrate`` entry for two doc types (in either order), if any."""
        return next(
            (pair for pair in self.arbitrate if sorted(pair.types) == sorted([first, second])),
            None,
        )


ViewColumn = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=48)]
ViewAmountUnit = Literal["HT", "TTC", "€"]
VIEW_SYSTEM_COLUMNS: tuple[str, ...] = ("_source_id", "_table_id", "_row_id", "_scope")
"""Columns the engine adds to the ``rows`` relation of a view (v1.7, ADR 0011)."""


class ViewDef(ContractModel):
    """One computed view of ``views.yaml`` (v1.7, ADR 0011): a read-only SQL ``SELECT`` over the
    relation ``rows``, the union of the tables of the current documents of ``doc_types`` with
    their columns renamed by header (``columns``: output name → header aliases, matched without
    case or accents), plus ``_source_id``, ``_table_id``, ``_row_id`` and ``_scope``. The result
    must keep ``_source_id`` and ``_row_id`` so every row stays cited; ``totals`` are result
    columns summed by code (per scope when ``per_scope``)."""

    slug: Kebab
    title: NonEmptyStr
    description: str = ""
    doc_types: Annotated[list[Kebab], Field(min_length=1)]
    columns: Annotated[dict[ViewColumn, list[NonEmptyStr]], Field(min_length=1)]
    sql: NonEmptyStr
    per_scope: bool = False
    totals: list[ViewColumn] = []
    labels: dict[ViewColumn, NonEmptyStr] = {}
    """Column header of each result column (``marche_ht`` → ``Marché HT``), in the pack's
    language conventions; a result column without a label shows its name."""
    amounts: dict[ViewColumn, ViewAmountUnit] = {}
    """Result columns that are amounts in euros, with their basis: ``HT``, ``TTC`` or ``€``
    (neither). Their cells and totals are written ``184 490,00 € HT``."""
    scope_columns: list[ViewColumn] = []
    """Result columns whose values are scope values (``autre_chantier``): shown with the scope's
    label, linked to its hub page."""

    @field_validator("doc_types", "totals", "scope_columns")
    @classmethod
    def _unique_lists(cls, value: list[str]) -> list[str]:
        _unique(value, "entry")
        return value

    @field_validator("description")
    @classmethod
    def _one_line(cls, value: str) -> str:
        if "\n" in value.strip():
            raise ValueError("description must be a single line")
        return value.strip()


class ViewsFile(ContractModel):
    """``views.yaml``: computed views, cross-document figures computed by code from the
    documents' tables, every row cited (v1.7, ADR 0011)."""

    views: list[ViewDef] = []

    @field_validator("views")
    @classmethod
    def _slugs(cls, value: list[ViewDef]) -> list[ViewDef]:
        _unique([view.slug for view in value], "view slug")
        return value


class DomainPack(ContractModel):
    """A validated domain pack (optionally with the runtime overlay applied)."""

    info: PackInfo
    taxonomy: TaxonomyFile
    entities: EntitiesFile
    topics: TopicsFile
    glossary: GlossaryFile
    terms: TermsFile = Field(default_factory=TermsFile)
    scopes: ScopesFile | None = None
    views: ViewsFile | None = None
    sensitivity: SensitivityFile
    supersession: SupersessionFile | None = None
    resolution: ResolutionFile = Field(default_factory=ResolutionFile)
    hints: str | None = None
    skill_templates: dict[str, str] = {}
    i18n: dict[LangCode, dict[NonEmptyStr, str]] = {}
    """Pack overrides of the generated wiki strings, ``i18n/<lang>.yaml`` (v1.7, ADR 0012):
    language → key → template; structural keys (headings) cannot be overridden."""
    overlay_applied: bool = False

    @field_validator("skill_templates")
    @classmethod
    def _skills(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 3:
            raise ValueError("a domain pack defines at most 3 skill templates")
        for name in value:
            if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", name) or len(name) > 64:
                raise ValueError(f"invalid skill name {name!r}")
            if name in CORE_SKILLS:
                raise ValueError(f"skill {name!r} clashes with a core skill")
        return value

    @field_validator("i18n")
    @classmethod
    def _i18n(cls, value: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
        known = set(CORE_STRINGS["en"])
        for lang, table in value.items():
            for key in table:
                if key in STRUCTURAL_KEYS:
                    raise ValueError(f"{lang}: {key!r} is a structural heading and cannot change")
                if key not in known:
                    raise ValueError(f"{lang}: unknown string key {key!r}")
        return value

    @property
    def name(self) -> str:
        return self.info.name

    @property
    def wiki_languages(self) -> list[str]:
        """The wiki languages, canonical first (``["en"]`` unless the pack declares them)."""
        return list(self.info.wiki_languages)

    @property
    def canonical_lang(self) -> str:
        """The language the wiki is compiled in (``wiki_languages[0]``)."""
        return self.info.wiki_languages[0]

    @property
    def mirror_langs(self) -> list[str]:
        """The languages of the mirrors written by the ``translate`` stage (may be empty)."""
        return list(self.info.wiki_languages[1:])

    def strings(self, lang: str | None = None) -> Strings:
        """The generated-text table of ``lang`` (default: canonical) with the pack overrides."""
        chosen = lang or self.canonical_lang
        return Strings(chosen, self.i18n.get(chosen))

    def content_hash(self) -> str:
        """SHA-256 of the canonical pack content (overlay included) — the ``domain_pack_hash``."""
        return sha256_hex(canonical_json(self.to_json_dict()))

    def doc_type(self, key: str) -> DocType:
        for doc_type in self.taxonomy.doc_types:
            if doc_type.key == key:
                return doc_type
        raise KeyError(key)

    def entity(self, entity_id: str) -> RegistryEntry:
        for entry in self.entities.registry:
            if entry.id == entity_id:
                return entry
        raise KeyError(entity_id)

    def topic(self, slug: str) -> TopicDef:
        for topic in self.topics.topics:
            if topic.slug == slug:
                return topic
        raise KeyError(slug)

    @property
    def entity_ids(self) -> list[str]:
        return [entry.id for entry in self.entities.registry]

    @property
    def topic_ids(self) -> list[str]:
        return [f"topic:{topic.slug}" for topic in self.topics.topics]


def locked_terms_note(pack: DomainPack) -> str:
    """The locked trade vocabulary as an instruction for the prompts that write the canonical
    pages (empty without terms).

    In English the terms keep their gloss in brackets on first use. In another language (the
    documents' own, ADR 0012) they are simply kept as written: no English gloss, and the English
    renderings are banned in a separate list, never next to the term, so that a model copying the
    note cannot paste the ban into a page.
    """
    terms = pack.terms.terms
    if not terms:
        return ""
    english = pack.canonical_lang == "en"
    if english:
        lines = [
            "Locked trade terms (keep them in French, exactly as written; give the English gloss "
            "in brackets the first time each appears on a page, never translate or paraphrase "
            "them):",
        ]
    else:
        lines = [
            "Locked trade terms (write them exactly as below; never translate, paraphrase or "
            "gloss them, and add no bracketed explanation after them):",
        ]
    for term in terms:
        forms = f" (also {', '.join(term.forms)})" if term.forms else ""
        line = f"- {term.term}{forms}: {term.gloss}" if english else f"- {term.term}{forms}"
        if term.avoid_senses:
            line += "; never for " + "; ".join(sense.rstrip(".") for sense in term.avoid_senses)
        lines.append(line)
    lines.append(
        "A locked term keeps its trade meaning only: where a document uses the same word in an "
        "everyday sense (receiving a letter or an invoice, taking delivery of goods), write the "
        "everyday word of the wiki language instead, never the locked term."
    )
    banned = sorted({rendering for term in terms for rendering in term.banned})
    if banned:
        lines.append(
            "Banned English renderings (never use these words in a page): "
            + ", ".join(repr(rendering) for rendering in banned)
            + "."
        )
    return "\n".join(lines)
