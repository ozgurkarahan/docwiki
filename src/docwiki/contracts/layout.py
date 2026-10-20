"""Fixed names and paths of the wiki, the release folder and the storage layout.

Wiki paths are relative to the wiki root. Release paths are relative to ``releases/<release_id>/``.
Storage keys are POSIX keys whose first segment is the container (``raw``, ``work``, ``releases``),
used identically by the folder and the Blob implementations of
:class:`~docwiki.contracts.storage.Storage`.
"""

from __future__ import annotations

from docwiki.contracts.ids import PROPOSAL_ID_RE, RUN_ID_RE, SOURCE_ID_RE, is_kebab

__all__ = [
    "CORE_SKILLS",
    "EVIDENCE_MOUNT",
    "REQUIRED_WIKI_FILES",
    "SKILL_PROJECTIONS",
    "ReleaseFiles",
    "StorageKeys",
    "WikiFiles",
    "artifact_prefix",
    "evidence_index_path",
    "evidence_path",
    "health_report_key",
    "proposal_key",
    "release_prefix",
    "run_report_key",
    "skill_path",
    "source_state_key",
]


class WikiFiles:
    """Fixed wiki files (paths relative to the wiki root)."""

    INDEX = "index.md"
    AGENTS = "AGENTS.md"
    LLMS = "llms.txt"
    LOG = "log.md"
    GLOSSARY = "glossary.md"
    CATALOG = "catalog.json"
    SOURCES_INDEX = "sources/index.md"
    ENTITIES_INDEX = "entities/index.md"
    TOPICS_INDEX = "topics/index.md"
    QUERIES_INDEX = "queries/index.md"
    QUALITY = "_meta/quality.md"
    RUNS_DIR = "_meta/runs"


REQUIRED_WIKI_FILES: tuple[str, ...] = (
    WikiFiles.INDEX,
    WikiFiles.AGENTS,
    WikiFiles.LLMS,
    WikiFiles.LOG,
    WikiFiles.GLOSSARY,
    WikiFiles.CATALOG,
    WikiFiles.SOURCES_INDEX,
    WikiFiles.ENTITIES_INDEX,
    WikiFiles.TOPICS_INDEX,
    WikiFiles.QUALITY,
)

CORE_SKILLS: tuple[str, ...] = (
    "wiki-navigator",
    "cite-sources",
    "deep-research",
    "wiki-maintainer",
)
SKILL_PROJECTIONS: tuple[str, ...] = (".agents/skills", ".claude/skills", ".github/skills")
"""Skill folders in the wiki; ``.agents/skills`` is canonical, the others are identical copies."""

EVIDENCE_MOUNT = "evidence"
"""Links are resolved in the *content namespace*: the wiki root with the release's ``evidence/``
folder mounted at ``evidence/`` (exactly the Quartz ``content/`` layout). ``evidence`` is therefore
a reserved name at the wiki root."""


class ReleaseFiles:
    """Fixed files and folders inside ``releases/<release_id>/``."""

    MANIFEST = "manifest.json"
    CATALOG = "catalog.json"
    SEARCH_DB = "search.db"
    WIKI_DIR = "wiki"
    EVIDENCE_DIR = "evidence"
    TABLES_DIR = "tables"
    SITE_DIR = "site"


class StorageKeys:
    """Storage layout of architecture §3 (first segment = container)."""

    RAW = "raw"
    WORK = "work"
    RELEASES = "releases"
    CURRENT = "releases/current.json"
    LEASE = "work/state/lease"
    OVERLAY = "work/state/overlay.yaml"
    DOMAIN_PACK = "work/state/domain-pack.json"
    SOURCE_STATE_DIR = "work/state/sources"
    ARTIFACTS_DIR = "work/artifacts"
    RUNS_DIR = "work/runs"
    PROPOSALS_DIR = "work/proposals"
    REPORTS_DIR = "work/reports"
    INBOX_QUERIES = "work/inbox/queries"
    """Reviewed research answers waiting for the next run (ADR 0007), one query page each."""
    INBOX_REJECTED = "work/inbox/rejected"
    """Inbox items a run could not merge, kept with the reason for the owner."""


def source_state_key(source_id: str) -> str:
    if not SOURCE_ID_RE.match(source_id):
        raise ValueError(f"invalid source_id: {source_id!r}")
    return f"{StorageKeys.SOURCE_STATE_DIR}/{source_id}.json"


def artifact_prefix(stage: str, key: str) -> str:
    if not is_kebab(stage) or len(key) != 64:
        raise ValueError("artifact prefix needs a kebab stage name and a 64-hex cache key")
    return f"{StorageKeys.ARTIFACTS_DIR}/{stage}/{key}/"


def run_report_key(run_id: str) -> str:
    if not RUN_ID_RE.match(run_id):
        raise ValueError(f"invalid run id: {run_id!r}")
    return f"{StorageKeys.RUNS_DIR}/{run_id}/report.json"


def proposal_key(proposal_id: str) -> str:
    if not PROPOSAL_ID_RE.match(proposal_id):
        raise ValueError(f"invalid proposal id: {proposal_id!r}")
    return f"{StorageKeys.PROPOSALS_DIR}/{proposal_id}.json"


def health_report_key(day: str) -> str:
    """``work/reports/health-<yyyy-mm-dd>.md``."""
    return f"{StorageKeys.REPORTS_DIR}/health-{day}.md"


def release_prefix(release_id: str) -> str:
    return f"{StorageKeys.RELEASES}/{release_id}/"


def evidence_path(source_id: str, locator_key: str) -> str:
    """Content-namespace path of an evidence sidecar: ``evidence/<source_id>/<locator_key>.md``."""
    if not SOURCE_ID_RE.match(source_id):
        raise ValueError(f"invalid source_id: {source_id!r}")
    return f"{EVIDENCE_MOUNT}/{source_id}/{locator_key}.md"


def evidence_index_path(source_id: str) -> str:
    if not SOURCE_ID_RE.match(source_id):
        raise ValueError(f"invalid source_id: {source_id!r}")
    return f"{EVIDENCE_MOUNT}/{source_id}/index.md"


def skill_path(name: str, projection: str = ".agents/skills") -> str:
    if projection not in SKILL_PROJECTIONS:
        raise ValueError(f"unknown skill projection: {projection!r}")
    if not is_kebab(name):
        raise ValueError(f"invalid skill name: {name!r}")
    return f"{projection}/{name}/SKILL.md"
