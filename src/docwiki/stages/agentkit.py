"""Stage 9 — ``agentkit``: ``AGENTS.md`` and the Agent Skills of the wiki (pipeline §1, ADR 0005).

Skills are rendered **only** from reviewed Jinja2 templates: the four core templates under
``skills/templates/<name>/SKILL.md.j2`` (plus ``skills/templates/AGENTS.md.j2``) and at most
three templates of the domain pack. Rendering uses a sandboxed environment with
``StrictUndefined``; every printed value is escaped for Markdown unless it is a validated path or
identifier, and the variables come only from validated catalog values and the domain pack
(wiki title, counts, topic titles of the pack, entity types, paths) — never from document text.

Rendered files are checked (frontmatter ``name``/``description``, size limits, Markdown safety,
canaries) and written identically to ``wiki/.agents/skills``, ``wiki/.claude/skills`` and
``wiki/.github/skills``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import StrictUndefined, TemplateError, Undefined
from jinja2.sandbox import SandboxedEnvironment
from pydantic import ValidationError

from docwiki.contracts.frontmatter import FrontmatterError
from docwiki.contracts.layout import CORE_SKILLS, SKILL_PROJECTIONS, WikiFiles, skill_path
from docwiki.contracts.pages import (
    DocwikiStamp,
    EntityFrontmatter,
    Page,
    QueryFrontmatter,
    SkillFile,
    SourceFrontmatter,
    TopicFrontmatter,
)
from docwiki.contracts.safety import find_violations
from docwiki.domain.models import DomainPack
from docwiki.stages.indexes import meta_page
from docwiki.stages.links import md_escape, plural

__all__ = [
    "AGENTS_TEMPLATE",
    "MCP_OPERATE_TOOLS",
    "MCP_READ_TOOLS",
    "STAGE_VERSION",
    "AgentKit",
    "AgentKitError",
    "Safe",
    "build_agent_kit",
    "default_templates_dir",
    "kit_context",
    "render_template",
    "write_agent_kit",
]

STAGE_VERSION = "1"
AGENTS_TEMPLATE = "AGENTS.md.j2"
SKILL_TEMPLATE = "SKILL.md.j2"
MCP_READ_TOOLS = (
    "search",
    "read_page",
    "get_index",
    "get_links",
    "glossary",
    "get_evidence",
    "query_table",
    "get_skill",
    "list_skills",
    "recent_changes",
)
MCP_OPERATE_TOOLS = (
    "ingest_start",
    "run_status",
    "list_sources",
    "quality_report",
    "explain_source",
    "recompile",
    "list_proposals",
    "decide_proposal",
    "write_health_report",
)


class AgentKitError(ValueError):
    """A template is missing, does not render or renders an invalid file."""


class Safe(str):
    """A validated value (path, identifier, number) printed without Markdown escaping."""

    __slots__ = ()


def default_templates_dir() -> Path:
    """``skills/templates`` of the repository (templates are reviewed files, not package data)."""
    return Path(__file__).resolve().parents[3] / "skills" / "templates"


def _finalize(value: Any) -> str:
    if isinstance(value, Undefined):
        return str(value)  # StrictUndefined raises UndefinedError naming the variable
    if isinstance(value, Safe):
        return str(value)
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, str):
        return md_escape(value)
    if value is None:
        raise AgentKitError("template printed an undefined value (None)")
    raise AgentKitError(f"templates may only print strings and numbers, not {type(value).__name__}")


def _environment() -> SandboxedEnvironment:
    environment = SandboxedEnvironment(
        undefined=StrictUndefined,
        autoescape=False,
        finalize=_finalize,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    environment.filters["plural"] = lambda word, count: plural(str(word), int(count))
    return environment


def render_template(source: str, context: Mapping[str, Any], *, name: str) -> str:
    """Render one template (``AgentKitError`` names the template on failure)."""
    try:
        text = _environment().from_string(source).render(**context)
    except (TemplateError, AgentKitError, TypeError) as exc:
        raise AgentKitError(f"{name}: {exc}") from exc
    return text.replace("\r\n", "\n").rstrip("\n") + "\n"


def kit_context(
    pages: Sequence[Page],
    pack: DomainPack,
    *,
    audience: str,
    release_id: str,
    max_steps: int = 12,
    skills: Sequence[tuple[str, str]] = (),
) -> dict[str, Any]:
    """Template variables (validated values only; see the module docstring)."""
    sources = [p for p in pages if isinstance(p.frontmatter, SourceFrontmatter)]
    entities = [p for p in pages if isinstance(p.frontmatter, EntityFrontmatter)]
    topic_pages = {
        p.frontmatter.topic_slug: p for p in pages if isinstance(p.frontmatter, TopicFrontmatter)
    }
    queries = [p for p in pages if isinstance(p.frontmatter, QueryFrontmatter)]
    current = sum(
        1
        for p in sources
        if isinstance(p.frontmatter, SourceFrontmatter) and p.frontmatter.status == "current"
    )
    topics = [
        {"slug": Safe(topic.slug), "title": topic.title, "path": Safe(topic_pages[topic.slug].path)}
        for topic in pack.topics.topics
        if topic.slug in topic_pages
    ]
    type_counts: dict[str, int] = {}
    for page in entities:
        fm = page.frontmatter
        assert isinstance(fm, EntityFrontmatter)
        type_counts[fm.entity_type] = type_counts.get(fm.entity_type, 0) + 1
    entity_types = [
        {
            "key": Safe(item.key),
            "title": item.title,
            "plural": item.title,
            "path": Safe(f"entities/{item.key}/index.md"),
            "count": type_counts[item.key],
        }
        for item in pack.entities.types
        if item.key in type_counts
    ]
    category_counts: dict[str, int] = {}
    for page in sources:
        fm = page.frontmatter
        assert isinstance(fm, SourceFrontmatter)
        category_counts[fm.category] = category_counts.get(fm.category, 0) + 1
    categories = [
        {"key": Safe(item.key), "title": item.title, "count": category_counts[item.key]}
        for item in pack.taxonomy.categories
        if item.key in category_counts
    ]
    info = pack.info
    return {
        "wiki_title": info.wiki_title,
        "domain_name": Safe(info.name),
        "domain_title": info.title,
        "domain_description": info.description.strip() or info.title,
        "fictional": info.fictional,
        "banner": info.banner or "",
        "audience": Safe(audience),
        "release_id": Safe(release_id),
        "languages": [Safe(lang) for lang in info.languages],
        "resolution_order": [Safe(item) for item in pack.resolution.order],
        "max_steps": max_steps,
        "counts": {
            "sources": len(sources),
            "current_sources": current,
            "superseded_sources": len(sources) - current,
            "entities": len(entities),
            "topics": len(topic_pages),
            "queries": len(queries),
            "glossary_terms": len(pack.glossary.terms),
        },
        "topics": topics,
        "entity_types": entity_types,
        "categories": categories,
        "paths": {
            # `paths.index` is the documented name (docs/skills.md, domain pack skills);
            # `paths.home` is kept for templates written against the earlier name.
            "index": Safe(WikiFiles.INDEX),
            "home": Safe(WikiFiles.INDEX),
            "agents": Safe(WikiFiles.AGENTS),
            "llms": Safe(WikiFiles.LLMS),
            "log": Safe(WikiFiles.LOG),
            "glossary": Safe(WikiFiles.GLOSSARY),
            "catalog": Safe(WikiFiles.CATALOG),
            "sources_index": Safe(WikiFiles.SOURCES_INDEX),
            "entities_index": Safe(WikiFiles.ENTITIES_INDEX),
            "topics_index": Safe(WikiFiles.TOPICS_INDEX),
            "queries_index": Safe(WikiFiles.QUERIES_INDEX),
            "quality": Safe(WikiFiles.QUALITY),
            "runs": Safe(WikiFiles.RUNS_DIR),
            "evidence": Safe("evidence/<source_id>/<locator_key>.md"),
            "search_db": Safe("search.db"),
        },
        "skill_dirs": [Safe(projection) for projection in SKILL_PROJECTIONS],
        "skills": [
            {"name": Safe(name), "description": description} for name, description in skills
        ],
        "mcp_read_tools": [Safe(tool) for tool in MCP_READ_TOOLS],
        "mcp_operate_tools": [Safe(tool) for tool in MCP_OPERATE_TOOLS],
    }


def _check_text(text: str, name: str, canaries: Iterable[str]) -> None:
    problems = find_violations(text, allow_markers=False)
    if problems:
        details = "; ".join(f"line {item.line}: {item.message}" for item in problems[:5])
        raise AgentKitError(f"{name} renders unsafe Markdown: {details}")
    for canary in canaries:
        if canary and canary in text:
            raise AgentKitError(f"{name} contains an injection canary")


@dataclass
class AgentKit:
    """Rendered agent kit: ``AGENTS.md`` and ``SKILL.md`` texts by skill name."""

    agents: Page
    skills: dict[str, str]


def _skill_sources(templates_dir: Path, pack: DomainPack) -> dict[str, str]:
    sources: dict[str, str] = {}
    for name in CORE_SKILLS:
        path = templates_dir / name / SKILL_TEMPLATE
        if not path.is_file():
            raise AgentKitError(f"core skill template missing: {name}/{SKILL_TEMPLATE}")
        sources[name] = path.read_text(encoding="utf-8")
    for name, source in sorted(pack.skill_templates.items()):
        if name in sources:
            raise AgentKitError(f"domain skill {name!r} clashes with a core skill")
        sources[name] = source
    return sources


def build_agent_kit(
    pages: Sequence[Page],
    pack: DomainPack,
    *,
    stamp: DocwikiStamp,
    updated: date,
    sensitivity: str,
    audience: str,
    max_steps: int = 12,
    templates_dir: Path | None = None,
    canaries: Iterable[str] = (),
) -> AgentKit:
    """Render ``AGENTS.md`` and every skill; raises :class:`AgentKitError` on any problem."""
    base = templates_dir or default_templates_dir()
    canary_list = [canary for canary in canaries if canary]
    context = kit_context(
        pages, pack, audience=audience, release_id=stamp.release, max_steps=max_steps
    )
    skills: dict[str, str] = {}
    described: list[tuple[str, str]] = []
    for name, source in _skill_sources(base, pack).items():
        text = render_template(source, context, name=f"{name}/{SKILL_TEMPLATE}")
        try:
            skill = SkillFile.parse(text, name)
        except (FrontmatterError, ValidationError, ValueError) as exc:
            raise AgentKitError(
                f"{name}/{SKILL_TEMPLATE} renders an invalid SKILL.md: {exc}"
            ) from exc
        _check_text(text, f"{name}/SKILL.md", canary_list)
        skills[name] = text
        described.append((name, skill.frontmatter.description))
    agents_template = base / AGENTS_TEMPLATE
    if not agents_template.is_file():
        raise AgentKitError(f"template missing: {AGENTS_TEMPLATE}")
    context = kit_context(
        pages,
        pack,
        audience=audience,
        release_id=stamp.release,
        max_steps=max_steps,
        skills=described,
    )
    body = render_template(
        agents_template.read_text(encoding="utf-8"), context, name=AGENTS_TEMPLATE
    )
    _check_text(body, WikiFiles.AGENTS, canary_list)
    agents = meta_page(
        "meta:agents",
        WikiFiles.AGENTS,
        "Agent guide",
        "How agents should use this wiki: page types, navigation, citations, skills and safety.",
        body,
        stamp=stamp,
        updated=updated,
        sensitivity=sensitivity,
    )
    return AgentKit(agents=agents, skills=skills)


def write_agent_kit(kit: AgentKit, write: Any) -> list[str]:
    """Write the skill projections with ``write(path, text)``; returns the wiki paths."""
    written: list[str] = []
    for name, text in sorted(kit.skills.items()):
        for projection in SKILL_PROJECTIONS:
            path = skill_path(name, projection)
            write(path, text)
            written.append(path)
    return written
