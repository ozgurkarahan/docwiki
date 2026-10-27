"""DocWiki MCP server: read and operations tools over the current wiki release.

Entry points live in :mod:`docwiki.mcp.server` (``main`` for stdio/HTTP, ``create_app`` for an
ASGI app). This package is imported lazily by the CLI, so importing it must stay cheap.
"""

from __future__ import annotations

__all__ = ["OPS_TOOLS", "READ_TOOLS"]

READ_TOOLS: tuple[str, ...] = (
    "answer_context",
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
"""Tools that need the ``Wiki.Read`` app role (docs/spec/mcp-and-agents.md §1)."""

OPS_TOOLS: tuple[str, ...] = (
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
"""Tools that need the ``Wiki.Operate`` app role."""
