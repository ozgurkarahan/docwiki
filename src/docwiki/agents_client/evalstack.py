"""Operator helpers of the evaluation stack: the variant agents' identities and their MCP access.

Used by ``scripts/eval_stack.py`` (agents/README.md, "Evaluation variants"):

* :func:`fetch_identities` reads the Entra agent identity of each deployed variant agent, whose
  client IDs go into ``DOCWIKI_EVAL_MCP_ALLOWED_CLIENT_IDS`` (:func:`allowlist_value`);
* :func:`grant_wiki_read` assigns the ``Wiki.Read`` app role of the MCP API to those identities
  (Microsoft Graph ``servicePrincipals/{api}/appRoleAssignedTo``), idempotently, with a dry run.
  The production hook does the same for the production agents only.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from docwiki import __version__
from docwiki.agents_client.definitions import default_agents_dir, load_agents
from docwiki.agents_client.deploy import (
    PROJECT_ENDPOINT_ENV,
    _azure_exceptions,
    _get,
    _identity,
    _project_client,
)
from docwiki.agents_client.errors import (
    AgentConfigurationError,
    AgentDefinitionError,
    AgentsClientError,
    DeployError,
)
from docwiki.agents_client.variants import (
    ALL_VARIANTS,
    VARIANTS_FILE,
    encode_mcp_variants,
    load_variants,
    resolve_mcp_variants,
    variant_agent_name,
)

__all__ = [
    "GRAPH",
    "READ_ROLE",
    "AgentIdentity",
    "GrantResult",
    "allowlist_value",
    "fetch_identities",
    "grant_wiki_read",
    "graph_request",
    "main",
    "require_env",
]

GRAPH = "https://graph.microsoft.com/v1.0"
READ_ROLE = "Wiki.Read"
_GUID = re.compile(r"^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$")

GraphRequest = Callable[[str, str, "dict[str, Any] | None"], "dict[str, Any] | None"]


@dataclass(frozen=True)
class AgentIdentity:
    agent_name: str
    principal_id: str | None
    client_id: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GrantResult:
    agent_name: str
    principal_id: str
    status: Literal["granted", "exists", "would-grant"]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


async def fetch_identities(
    endpoint: str, agent_names: Sequence[str], *, project_client: Any | None = None
) -> list[AgentIdentity]:
    """Entra agent identity of each deployed agent; fails when an agent does not exist."""
    errors = _azure_exceptions()
    identities: list[AgentIdentity] = []
    async with _project_client(endpoint, project_client) as project:
        for name in agent_names:
            try:
                details = await project.agents.get(name)
            except errors.ResourceNotFoundError as exc:
                raise AgentConfigurationError(
                    f"agent {name} does not exist: deploy it first (agents/deploy.py --variant ...)"
                ) from exc
            except errors.AzureError as exc:
                raise DeployError(f"{name}: {exc}") from exc
            principal, client = _identity(details, _get(_get(details, "versions"), "latest"))
            identities.append(AgentIdentity(name, principal, client))
    return identities


def allowlist_value(identities: Sequence[AgentIdentity]) -> str:
    """The value of ``DOCWIKI_EVAL_MCP_ALLOWED_CLIENT_IDS``: the client IDs, sorted and unique."""
    missing = [item.agent_name for item in identities if not item.client_id]
    if missing:
        raise AgentConfigurationError(f"agents without an identity client ID: {missing}")
    return ",".join(sorted({str(item.client_id) for item in identities}))


def graph_request(
    method: str, url: str, body: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """One Microsoft Graph call with a ``DefaultAzureCredential`` token (no secret is stored)."""
    import importlib

    identity = importlib.import_module("azure.identity")
    token = identity.DefaultAzureCredential().get_token("https://graph.microsoft.com/.default")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json",
            "User-Agent": f"docwiki/{__version__}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise DeployError(f"Microsoft Graph {method} {url}: HTTP {exc.code}: {detail}") from exc
    return json.loads(payload) if payload else None


def _check_guid(value: str, what: str) -> str:
    if not _GUID.match(value):
        raise AgentConfigurationError(f"{what} must be a GUID, got {value!r}")
    return value


def _assignments(graph: GraphRequest, api_sp_id: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    url: str | None = f"{GRAPH}/servicePrincipals/{api_sp_id}/appRoleAssignedTo?$top=999"
    while url:
        page = graph("GET", url, None) or {}
        items.extend(page.get("value", []))
        url = page.get("@odata.nextLink")
    return items


def grant_wiki_read(
    graph: GraphRequest,
    *,
    mcp_api_client_id: str,
    identities: Sequence[AgentIdentity],
    dry_run: bool,
) -> list[GrantResult]:
    """Assign ``Wiki.Read`` of the MCP API to each identity's service principal, once."""
    _check_guid(mcp_api_client_id, "DOCWIKI_MCP_API_CLIENT_ID")
    missing = [item.agent_name for item in identities if not item.principal_id]
    if missing:
        raise AgentConfigurationError(f"agents without an identity principal ID: {missing}")
    api = graph("GET", f"{GRAPH}/servicePrincipals(appId='{mcp_api_client_id}')", None) or {}
    api_sp_id = _check_guid(str(api.get("id") or ""), "MCP API service principal id")
    role = next((r for r in api.get("appRoles", []) if r.get("value") == READ_ROLE), None)
    if role is None or not role.get("id"):
        raise AgentConfigurationError(f"the MCP API does not define the {READ_ROLE} app role")
    role_id = _check_guid(str(role["id"]), f"{READ_ROLE} app role id")
    granted = {
        (item.get("principalId"), item.get("appRoleId")) for item in _assignments(graph, api_sp_id)
    }
    results: list[GrantResult] = []
    for item in identities:
        principal = _check_guid(str(item.principal_id), f"{item.agent_name} principal id")
        if (principal, role_id) in granted:
            results.append(GrantResult(item.agent_name, principal, "exists"))
            continue
        if not dry_run:
            body = {"principalId": principal, "resourceId": api_sp_id, "appRoleId": role_id}
            graph("POST", f"{GRAPH}/servicePrincipals/{api_sp_id}/appRoleAssignedTo", body)
            granted.add((principal, role_id))
        results.append(
            GrantResult(item.agent_name, principal, "would-grant" if dry_run else "granted")
        )
    return results


def require_env(env: Mapping[str, str], name: str) -> str:
    value = (env.get(name) or "").strip()
    if not value:
        raise AgentConfigurationError(f"environment variable {name} is not set")
    return value


def _parser(agents_dir: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/eval_stack.py",
        description="Operator helpers of the evaluation stack (agents/README.md).",
    )
    parser.add_argument("--agents-dir", type=Path, default=agents_dir)
    parser.add_argument("--variants-file", type=Path, help="default: agents/variants.yaml")
    sub = parser.add_subparsers(dest="command", required=True)
    encode = sub.add_parser(
        "encode", help="print the azd value DOCWIKI_EVAL_MCP_VARIANTS (base64 of the JSON array)"
    )
    encode.add_argument(
        "--mcp-variant",
        action="append",
        metavar="NAME",
        help="MCP variants to include (default: those used by the declared agents)",
    )
    encode.add_argument("--json", action="store_true", help="print the decoded JSON instead")
    for name, text in (
        (
            "identities",
            "print the variant agents' identities and DOCWIKI_EVAL_MCP_ALLOWED_CLIENT_IDS",
        ),
        ("grant", f"grant {READ_ROLE} on the MCP API to the variant agents' identities"),
    ):
        command = sub.add_parser(name, help=text)
        command.add_argument(
            "--variant", action="append", metavar="NAME", help=f"default: {ALL_VARIANTS}"
        )
        command.add_argument("--json", action="store_true", help="print the results as JSON")
        if name == "grant":
            command.add_argument(
                "--dry-run", action="store_true", help="list the assignments without creating them"
            )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    agents_dir: Path | None = None,
    env: Mapping[str, str] | None = None,
    project_client: Any | None = None,
    graph: GraphRequest | None = None,
) -> int:
    """Command-line entry point; 0 on success, 1 on Azure/Graph errors, 2 on invalid input."""
    args = _parser(agents_dir or default_agents_dir()).parse_args(argv)
    values = os.environ if env is None else env
    try:
        declared = load_variants(args.variants_file or args.agents_dir / VARIANTS_FILE)
        if args.command == "encode":
            resolved = resolve_mcp_variants(declared, values, args.mcp_variant)
            print(
                json.dumps(resolved, indent=2, sort_keys=True)
                if args.json
                else encode_mcp_variants(resolved)
            )
            return 0
        agents = load_agents(args.agents_dir)
        base = agents.get("researcher")
        if base is None:
            raise AgentDefinitionError(f"no researcher agent under {args.agents_dir}")
        names = [
            variant_agent_name(base, variant)
            for variant in declared.select(args.variant or [ALL_VARIANTS])
        ]
        identities = asyncio.run(
            fetch_identities(
                (values.get(PROJECT_ENDPOINT_ENV) or "").strip(),
                names,
                project_client=project_client,
            )
        )
        if args.command == "identities":
            allowlist = allowlist_value(identities)
            if args.json:
                payload = {
                    "agents": [item.to_dict() for item in identities],
                    "DOCWIKI_EVAL_MCP_ALLOWED_CLIENT_IDS": allowlist,
                }
                print(json.dumps(payload, indent=2))
            else:
                for item in identities:
                    print(
                        f"{item.agent_name}: client {item.client_id}, principal {item.principal_id}"
                    )
                print(f"DOCWIKI_EVAL_MCP_ALLOWED_CLIENT_IDS={allowlist}")
            return 0
        results = grant_wiki_read(
            graph or graph_request,
            mcp_api_client_id=require_env(values, "DOCWIKI_MCP_API_CLIENT_ID"),
            identities=identities,
            dry_run=args.dry_run,
        )
        if args.json:
            print(json.dumps([item.to_dict() for item in results], indent=2))
        else:
            for result in results:
                print(f"{result.agent_name}: {READ_ROLE} {result.status} ({result.principal_id})")
        return 0
    except (AgentDefinitionError, AgentConfigurationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except AgentsClientError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
