"""Domain pack loader: ``load_pack(path) -> DomainPack`` with errors naming the file and key."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, TemplateSyntaxError
from pydantic import BaseModel, ValidationError

from docwiki.contracts.frontmatter import FrontmatterError, load_yaml_mapping
from docwiki.contracts.ids import is_entity_id
from docwiki.domain.models import (
    DomainPack,
    EntitiesFile,
    GlossaryFile,
    PackInfo,
    ResolutionFile,
    ScopesFile,
    SensitivityFile,
    SupersessionFile,
    TaxonomyFile,
    TermsFile,
    TopicsFile,
    ViewsFile,
)

__all__ = ["PACK_FILES", "PackError", "PackValidationError", "format_location", "load_pack"]

PACK_FILES: dict[str, tuple[type[BaseModel], bool]] = {
    "pack.yaml": (PackInfo, True),
    "taxonomy.yaml": (TaxonomyFile, True),
    "entities.yaml": (EntitiesFile, True),
    "topics.yaml": (TopicsFile, True),
    "glossary.yaml": (GlossaryFile, True),
    "sensitivity.yaml": (SensitivityFile, True),
    "supersession.yaml": (SupersessionFile, False),
    "resolution.yaml": (ResolutionFile, False),
    "terms.yaml": (TermsFile, False),
    "scopes.yaml": (ScopesFile, False),
    "views.yaml": (ViewsFile, False),
}
"""File name → (schema model, required)."""

_IGNORED_FILES = frozenset(
    {"README.md", "LICENSE", "LICENSE.md", "hints.md", ".gitkeep", "canaries.txt"}
)


@dataclass(frozen=True)
class PackError:
    file: str
    location: str
    message: str

    def __str__(self) -> str:
        where = f"{self.file}: {self.location}" if self.location else self.file
        return f"{where}: {self.message}"


class PackValidationError(ValueError):
    """All problems found while loading a pack; each names the file and key path."""

    def __init__(self, errors: list[PackError]) -> None:
        self.errors = errors
        super().__init__("invalid domain pack:\n" + "\n".join(f"  - {error}" for error in errors))


def format_location(loc: tuple[Any, ...]) -> str:
    """``("doc_types", 2, "rules", 0, "text_regex")`` → ``doc_types[2].rules[0].text_regex``."""
    out = ""
    for part in loc:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += f".{part}" if out else str(part)
    return out


def errors_from_validation(file: str, exc: ValidationError) -> list[PackError]:
    errors: list[PackError] = []
    for error in exc.errors(include_url=False):
        message = str(error.get("msg", "invalid value"))
        message = message.removeprefix("Value error, ")
        errors.append(PackError(file, format_location(tuple(error.get("loc", ()))), message))
    return errors


def _validate_file(path: Path, model: type[BaseModel], errors: list[PackError]) -> BaseModel | None:
    try:
        data = load_yaml_mapping(path.read_text(encoding="utf-8"), where=path.name)
    except FrontmatterError as exc:
        errors.append(PackError(path.name, "", str(exc).removeprefix(f"{path.name}: ")))
        return None
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        errors.extend(errors_from_validation(path.name, exc))
        return None


def _cross_checks(pack: DomainPack, errors: list[PackError]) -> None:
    languages = set(pack.info.languages)
    entity_ids = set(pack.entity_ids)
    topic_ids = set(pack.topic_ids)
    doc_types = {doc_type.key for doc_type in pack.taxonomy.doc_types}
    for index, entry in enumerate(pack.entities.registry):
        for alias_index, alias in enumerate(entry.aliases):
            if alias.lang not in languages:
                errors.append(
                    PackError(
                        "entities.yaml",
                        f"registry[{index}].aliases[{alias_index}].lang",
                        f"language {alias.lang!r} is not listed in pack.yaml languages",
                    )
                )
    for index, topic in enumerate(pack.topics.topics):
        for alias_index, alias in enumerate(topic.aliases):
            if alias.lang not in languages:
                errors.append(
                    PackError(
                        "topics.yaml",
                        f"topics[{index}].aliases[{alias_index}].lang",
                        f"language {alias.lang!r} is not listed in pack.yaml languages",
                    )
                )
    for index, term in enumerate(pack.glossary.terms):
        for lang in term.synonyms:
            if lang not in languages:
                errors.append(
                    PackError(
                        "glossary.yaml",
                        f"terms[{index}].synonyms.{lang}",
                        f"language {lang!r} is not listed in pack.yaml languages",
                    )
                )
        for ref_index, ref in enumerate(term.see_also):
            if ref not in topic_ids and not (is_entity_id(ref) and ref in entity_ids):
                errors.append(
                    PackError(
                        "glossary.yaml",
                        f"terms[{index}].see_also[{ref_index}]",
                        f"unknown entity or topic id {ref!r}",
                    )
                )
    for index, amendment in enumerate(pack.resolution.amendments):
        for field in ("amending", "amended"):
            for type_index, key in enumerate(getattr(amendment, field)):
                if key not in doc_types:
                    errors.append(
                        PackError(
                            "resolution.yaml",
                            f"amendments[{index}].{field}[{type_index}]",
                            f"unknown doc type {key!r}",
                        )
                    )
    for index, pair in enumerate(pack.resolution.arbitrate):
        for type_index, key in enumerate(pair.types):
            if key not in doc_types:
                errors.append(
                    PackError(
                        "resolution.yaml",
                        f"arbitrate[{index}].types[{type_index}]",
                        f"unknown doc type {key!r}",
                    )
                )
    for index, rule in enumerate(pack.sensitivity.rules):
        if rule.doc_type is not None and rule.doc_type not in doc_types:
            errors.append(
                PackError(
                    "sensitivity.yaml",
                    f"rules[{index}].doc_type",
                    f"unknown doc type {rule.doc_type!r}",
                )
            )


def _check_views(pack: DomainPack, errors: list[PackError]) -> None:
    """Each view's SQL is one ``SELECT`` that resolves over an empty ``rows`` relation and
    keeps ``_source_id``, ``_row_id`` and its ``totals`` columns (v1.7, ADR 0011)."""
    if pack.views is None:
        return
    from docwiki.domain.models import VIEW_SYSTEM_COLUMNS
    from docwiki.release.tables import TableQueryError, rows_query_columns

    doc_types = {doc_type.key for doc_type in pack.taxonomy.doc_types}
    if pack.scopes is not None and pack.scopes.plural == "views":
        errors.append(PackError("scopes.yaml", "plural", "'views' is the folder of the views"))
    for index, view in enumerate(pack.views.views):
        where = f"views[{index}]"
        for type_index, doc_type in enumerate(view.doc_types):
            if doc_type not in doc_types:
                errors.append(
                    PackError(
                        "views.yaml",
                        f"{where}.doc_types[{type_index}]",
                        f"unknown doc type {doc_type!r}",
                    )
                )
        try:
            result = rows_query_columns([*view.columns, *VIEW_SYSTEM_COLUMNS], view.sql)
        except TableQueryError as exc:
            errors.append(PackError("views.yaml", f"{where}.sql", str(exc)))
            continue
        missing = [name for name in ("_source_id", "_row_id") if name not in result]
        if missing:
            errors.append(
                PackError(
                    "views.yaml",
                    f"{where}.sql",
                    f"the query must return {' and '.join(missing)} so every row stays cited",
                )
            )
        for total_index, name in enumerate(view.totals):
            if name not in result:
                errors.append(
                    PackError(
                        "views.yaml",
                        f"{where}.totals[{total_index}]",
                        f"{name!r} is not a column of the query result",
                    )
                )
        for field_name, names in (
            ("labels", list(view.labels)),
            ("amounts", list(view.amounts)),
            ("scope_columns", view.scope_columns),
        ):
            for name in names:
                if name not in result or name.startswith("_"):
                    errors.append(
                        PackError(
                            "views.yaml",
                            f"{where}.{field_name}.{name}",
                            f"{name!r} is not a displayed column of the query result",
                        )
                    )


def _load_skills(root: Path, errors: list[PackError]) -> dict[str, str]:
    templates: dict[str, str] = {}
    skills_dir = root / "skills"
    if not skills_dir.exists():
        return templates
    environment = Environment(autoescape=False)
    for child in sorted(skills_dir.iterdir()):
        rel = f"skills/{child.name}"
        template = child / "SKILL.md.j2"
        if not child.is_dir() or not template.is_file():
            errors.append(PackError(rel, "", "expected a folder containing SKILL.md.j2"))
            continue
        extra = sorted(p.name for p in child.iterdir() if p.name != "SKILL.md.j2")
        if extra:
            errors.append(PackError(rel, "", f"unexpected files {extra}"))
        source = template.read_text(encoding="utf-8")
        try:
            environment.parse(source)
        except TemplateSyntaxError as exc:
            errors.append(
                PackError(f"{rel}/SKILL.md.j2", f"line {exc.lineno}", exc.message or "syntax error")
            )
            continue
        templates[child.name] = source
    return templates


I18N_DIR = "i18n"
"""Optional pack folder of generated-string overrides, one ``<lang>.yaml`` per language."""


def _load_i18n(root: Path, errors: list[PackError]) -> dict[str, dict[str, str]]:
    """``i18n/<lang>.yaml`` files: flat mappings of string key → template (v1.7, ADR 0012)."""
    from docwiki.contracts.i18n import CORE_STRINGS, STRUCTURAL_KEYS

    folder = root / I18N_DIR
    tables: dict[str, dict[str, str]] = {}
    if not folder.is_dir():
        return tables
    known = set(CORE_STRINGS["en"])
    for child in sorted(folder.iterdir()):
        rel = f"{I18N_DIR}/{child.name}"
        if not child.is_file() or child.suffix != ".yaml":
            errors.append(PackError(rel, "", "expected <lang>.yaml files only"))
            continue
        try:
            data = load_yaml_mapping(child.read_text(encoding="utf-8"), where=rel)
        except FrontmatterError as exc:
            errors.append(PackError(rel, "", str(exc)))
            continue
        table: dict[str, str] = {}
        for key, value in data.items():
            if not isinstance(value, str):
                errors.append(PackError(rel, key, "expected a string"))
            elif key in STRUCTURAL_KEYS:
                errors.append(PackError(rel, key, "structural headings cannot be overridden"))
            elif key not in known:
                errors.append(PackError(rel, key, "unknown string key"))
            else:
                table[key] = value
        tables[child.stem] = table
    return tables


def load_pack(path: str | Path, *, overlay: str | Path | None = None) -> DomainPack:
    """Load and validate the pack folder ``path``; apply ``overlay`` (``overlay.yaml``) if given.

    Raises :class:`PackValidationError` listing every problem (file, key path, message).
    """
    root = Path(path)
    if not root.is_dir():
        raise PackValidationError(
            [PackError(str(root.name or root), "", "domain pack folder not found")]
        )
    errors: list[PackError] = []
    for child in sorted(root.iterdir()):
        if child.is_dir():
            if child.name not in ("skills", I18N_DIR):
                errors.append(PackError(child.name, "", "unknown folder in domain pack"))
        elif child.name not in PACK_FILES and child.name not in _IGNORED_FILES:
            errors.append(PackError(child.name, "", "unknown file in domain pack"))
    parsed: dict[str, Any] = {}
    for name, (model, required) in PACK_FILES.items():
        file_path = root / name
        if not file_path.is_file():
            if required:
                errors.append(PackError(name, "", "required file is missing"))
            continue
        result = _validate_file(file_path, model, errors)
        if result is not None:
            parsed[name] = result
    hints_path = root / "hints.md"
    hints = hints_path.read_text(encoding="utf-8") if hints_path.is_file() else None
    skills = _load_skills(root, errors)
    i18n = _load_i18n(root, errors)
    if errors:
        raise PackValidationError(errors)
    try:
        pack = DomainPack(
            info=parsed["pack.yaml"],
            taxonomy=parsed["taxonomy.yaml"],
            entities=parsed["entities.yaml"],
            topics=parsed["topics.yaml"],
            glossary=parsed["glossary.yaml"],
            terms=parsed.get("terms.yaml", TermsFile()),
            scopes=parsed.get("scopes.yaml"),
            views=parsed.get("views.yaml"),
            sensitivity=parsed["sensitivity.yaml"],
            supersession=parsed.get("supersession.yaml"),
            resolution=parsed.get("resolution.yaml", ResolutionFile()),
            hints=hints,
            skill_templates=skills,
            i18n=i18n,
        )
    except ValidationError as exc:
        raise PackValidationError(errors_from_validation("skills", exc)) from exc
    for lang in pack.i18n:
        if lang not in pack.wiki_languages:
            errors.append(
                PackError(
                    f"{I18N_DIR}/{lang}.yaml",
                    "",
                    f"{lang!r} is not one of the wiki_languages of pack.yaml",
                )
            )
    _cross_checks(pack, errors)
    _check_views(pack, errors)
    if errors:
        raise PackValidationError(errors)
    if overlay is not None:
        from docwiki.domain.overlay import apply_overlay, load_overlay

        pack = apply_overlay(pack, load_overlay(overlay))
    return pack


def validate_cross_references(pack: DomainPack, file: str = "overlay.yaml") -> None:
    """Re-run the cross-file checks (used after an overlay is applied)."""
    errors: list[PackError] = []
    _cross_checks(pack, errors)
    if errors:
        raise PackValidationError(
            [PackError(file, f"{e.file}:{e.location}", e.message) for e in errors]
        )
