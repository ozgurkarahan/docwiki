"""Create or update the identity-spike prompt agents and print their Entra agent identities.

Reference snippet for the agents and infra lanes (ADR 0003). Each new prompt agent receives its own
Entra agent identity (``instance_identity``) and blueprint; new versions keep the same identity.
The MCP tool authenticates through a project connection with ``authType=AgenticIdentityToken``
(see ``mcp-connection.bicep``), so the MCP server sees one principal per agent.

Usage::

    PROJECT_ENDPOINT=https://<account>.services.ai.azure.com/api/projects/<project> \
    MCP_URL=https://<mcp-app-fqdn>/mcp \
    python agents_with_identity.py --prefix spike- > agent-identities.json

The printed JSON drives the app role assignments and the Easy Auth allowlist
(``allowedApplications`` = every ``client_id``).
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MCPTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential

INSTRUCTIONS = (
    "You are an identity test agent. When the user asks you to call tools, call the docwiki MCP "
    "tools exactly in the order requested, then report each tool's raw JSON result or raw error "
    "message verbatim in a fenced block. Do not retry a failed call and do not invent results."
)

# Agent base name -> MCP app roles it must hold. The spike gave both agents both tools so that
# the server-side check is what blocks the researcher; real agents also restrict allowed_tools.
AGENT_ROLES: dict[str, list[str]] = {
    "researcher": ["Wiki.Read"],
    "librarian": ["Wiki.Read", "Wiki.Operate"],
}


def upsert_agent(
    project: AIProjectClient, name: str, model: str, mcp_url: str, connection_id: str
) -> dict[str, Any]:
    tool = MCPTool(
        server_label="docwiki",
        server_url=mcp_url,
        require_approval="never",
        allowed_tools=["whoami", "operate"],
        project_connection_id=connection_id,
    )
    version = project.agents.create_version(
        agent_name=name,
        definition=PromptAgentDefinition(model=model, instructions=INSTRUCTIONS, tools=[tool]),
        description="DocWiki identity spike agent",
    )
    details = project.agents.get(name)
    identity = details.get("instance_identity") or {}
    if not identity.get("principal_id"):
        raise RuntimeError(f"agent {name} has no instance_identity (legacy agent?)")
    return {
        "version": version.version,
        "principal_id": identity["principal_id"],
        "client_id": identity["client_id"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--prefix", default="", help="agent name prefix, for example 'spike-'")
    parser.add_argument("--model", default=os.environ.get("MODEL_DEPLOYMENT", "smart"))
    parser.add_argument("--connection", default=os.environ.get("MCP_CONNECTION", "docwiki-mcp"))
    args = parser.parse_args()

    project = AIProjectClient(
        endpoint=os.environ["PROJECT_ENDPOINT"], credential=DefaultAzureCredential()
    )
    connection = project.connections.get(args.connection)
    result: dict[str, Any] = {}
    for base, roles in AGENT_ROLES.items():
        name = f"{args.prefix}{base}"
        result[name] = upsert_agent(
            project, name, args.model, os.environ["MCP_URL"], connection.id
        ) | {"roles": roles}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
