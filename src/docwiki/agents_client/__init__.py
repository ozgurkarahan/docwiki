"""Client side of the DocWiki Foundry agents (docs/spec/mcp-and-agents.md §2).

* :func:`ask` / :class:`AgentClient` - call the deployed Researcher or Librarian through the
  project's Responses API (used by ``docwiki ask`` and the evaluation runner);
* :func:`parse_answer` - parse the ``[n]`` citation format into :class:`Source` entries;
* :mod:`docwiki.agents_client.definitions` - ``agents/*/agent.yaml`` schema and loaders;
* :mod:`docwiki.agents_client.deploy` - idempotent deployment (``agents/deploy.py``).
"""

from __future__ import annotations

from docwiki.agents_client.citations import (
    Source,
    inline_citations,
    normalize_path,
    normalize_provenance,
    parse_answer,
    parse_source_line,
    split_answer,
)
from docwiki.agents_client.client import (
    AgentAnswer,
    AgentClient,
    AgentClientSettings,
    AgentUsage,
    ApprovalCallback,
    ApprovalDecision,
    ApprovalRequest,
    ToolCall,
    ask,
    format_answer,
    prompt_approval,
)
from docwiki.agents_client.definitions import (
    AgentDefinition,
    LoadedAgent,
    LoadedRoutine,
    RoutineDefinition,
    foundry_agent_name,
    load_agent,
    load_agents,
    load_routine,
    load_routines,
)
from docwiki.agents_client.errors import (
    AgentAuthError,
    AgentConfigurationError,
    AgentDefinitionError,
    AgentInvocationError,
    AgentNotFoundError,
    AgentsClientError,
    DeployError,
)

__all__ = [
    "AgentAnswer",
    "AgentAuthError",
    "AgentClient",
    "AgentClientSettings",
    "AgentConfigurationError",
    "AgentDefinition",
    "AgentDefinitionError",
    "AgentInvocationError",
    "AgentNotFoundError",
    "AgentUsage",
    "AgentsClientError",
    "ApprovalCallback",
    "ApprovalDecision",
    "ApprovalRequest",
    "DeployError",
    "LoadedAgent",
    "LoadedRoutine",
    "RoutineDefinition",
    "Source",
    "ToolCall",
    "ask",
    "format_answer",
    "foundry_agent_name",
    "inline_citations",
    "load_agent",
    "load_agents",
    "load_routine",
    "load_routines",
    "normalize_path",
    "normalize_provenance",
    "parse_answer",
    "parse_source_line",
    "prompt_approval",
    "split_answer",
]
