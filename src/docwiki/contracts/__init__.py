"""DocWiki v1 contracts: the frozen, code-level interface shared by every lane.

See ``CONTRACT.md`` in this folder for the summary. Import from the submodules or from here.
"""

from docwiki.contracts._base import (
    ContractModel,
    canonical_json,
    dumps_json,
    sha256_bytes,
    sha256_hex,
)
from docwiki.contracts.catalog import (
    Catalog,
    CatalogEdge,
    CatalogGlossaryEntry,
    CatalogPage,
    CatalogSource,
    catalog_page_for,
    catalog_source_for,
)
from docwiki.contracts.compiled import CompiledSource
from docwiki.contracts.enums import (
    allowed_for_audience,
    badge_for,
    max_sensitivity,
    sensitivity_rank,
)
from docwiki.contracts.extracted import Block, ExtractedDoc, Figure, Table, TableRow, row_id_for
from docwiki.contracts.frontmatter import (
    FrontmatterError,
    read_frontmatter,
    render_frontmatter,
    write_frontmatter,
)
from docwiki.contracts.gates import GATES, GateResult, Violation, gate_results
from docwiki.contracts.ids import (
    assign_source_slugs,
    assign_unique_slugs,
    cache_key,
    format_entity_id,
    format_query_id,
    format_topic_id,
    new_run_id,
    parse_entity_id,
    parse_query_id,
    parse_topic_id,
    slugify_ascii,
    source_id_for,
)
from docwiki.contracts.locators import (
    Locator,
    locator_key,
    locator_label,
    parse_locator_key,
)
from docwiki.contracts.manifest import CurrentPointer, FileEntry, ReleaseInputs, ReleaseManifest
from docwiki.contracts.markdown import (
    extract_headings,
    extract_links,
    heading_anchor,
    relative_link,
    resolve_href,
)
from docwiki.contracts.pages import (
    EvidenceFrontmatter,
    EvidencePage,
    Frontmatter,
    Page,
    SkillFile,
    parse_frontmatter,
)
from docwiki.contracts.proposals import Proposal, parse_proposal
from docwiki.contracts.queue import QueueMessage, parse_queue_message
from docwiki.contracts.runs import CostReceipt, RunReport, VersionInfo
from docwiki.contracts.safety import (
    Finding,
    detect_injection,
    find_violations,
    neutralize_injections,
    sanitize_markdown,
)
from docwiki.contracts.settings import SETTINGS_DEFAULTS, SettingsKeys
from docwiki.contracts.state import SourceState, StageState
from docwiki.contracts.storage import FolderStorage, Storage
from docwiki.contracts.strict_schema import strict_json_schema, strict_response_format

__all__ = [
    "GATES",
    "SETTINGS_DEFAULTS",
    "Block",
    "Catalog",
    "CatalogEdge",
    "CatalogGlossaryEntry",
    "CatalogPage",
    "CatalogSource",
    "CompiledSource",
    "ContractModel",
    "CostReceipt",
    "CurrentPointer",
    "EvidenceFrontmatter",
    "EvidencePage",
    "ExtractedDoc",
    "Figure",
    "FileEntry",
    "Finding",
    "FolderStorage",
    "Frontmatter",
    "FrontmatterError",
    "GateResult",
    "Locator",
    "Page",
    "Proposal",
    "QueueMessage",
    "ReleaseInputs",
    "ReleaseManifest",
    "RunReport",
    "SettingsKeys",
    "SkillFile",
    "SourceState",
    "StageState",
    "Storage",
    "Table",
    "TableRow",
    "VersionInfo",
    "Violation",
    "allowed_for_audience",
    "assign_source_slugs",
    "assign_unique_slugs",
    "badge_for",
    "cache_key",
    "canonical_json",
    "catalog_page_for",
    "catalog_source_for",
    "detect_injection",
    "dumps_json",
    "extract_headings",
    "extract_links",
    "find_violations",
    "format_entity_id",
    "format_query_id",
    "format_topic_id",
    "gate_results",
    "heading_anchor",
    "locator_key",
    "locator_label",
    "max_sensitivity",
    "neutralize_injections",
    "new_run_id",
    "parse_entity_id",
    "parse_frontmatter",
    "parse_locator_key",
    "parse_proposal",
    "parse_query_id",
    "parse_queue_message",
    "parse_topic_id",
    "read_frontmatter",
    "relative_link",
    "render_frontmatter",
    "resolve_href",
    "row_id_for",
    "sanitize_markdown",
    "sensitivity_rank",
    "sha256_bytes",
    "sha256_hex",
    "slugify_ascii",
    "source_id_for",
    "strict_json_schema",
    "strict_response_format",
    "write_frontmatter",
]
