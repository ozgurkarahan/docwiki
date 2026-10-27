"""Deploy the DocWiki Foundry agents (and the optional Librarian routine) idempotently.

    uv run python agents/deploy.py --dry-run          # exact request bodies, no Azure call
    uv run python agents/deploy.py                    # create agent versions that changed
    uv run python agents/deploy.py --routine enable   # also upsert the daily routine, enabled

Every agent version carries ``docwiki_definition_sha256`` in its metadata: the SHA-256 of the
resolved request body (name, description, model, instructions, tools and YAML metadata, after the
environment substitution). A new version is created only when this hash differs from the latest
version's, so re-running the script is safe.

Azure AI Projects SDK calls (``azure-ai-projects`` 2.9, async client, ``DefaultAzureCredential``):

* ``agents.get(name)`` -> the latest version and its metadata (404: the agent is new);
* ``agents.create_version(name, body)`` -> ``POST /agents/{name}/versions`` with the printed body;
* ``connections.get(name)`` -> the MCP project connection's target and auth type are checked;
* ``beta.routines.create_or_update(name, body)`` -> ``PUT /routines/{name}`` (routines are in
  preview; the SDK adds the ``Foundry-Features: Routines=V2Preview`` header).

Environment: ``DOCWIKI_FOUNDRY_PROJECT_ENDPOINT`` plus the variables named in the YAML files
(``DOCWIKI_SMART_DEPLOYMENT``, ``DOCWIKI_MCP_URL``, ``DOCWIKI_MCP_CONNECTION``).
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import importlib
import json
import os
import sys
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from docwiki import __version__
from docwiki.agents_client.definitions import (
    AUTH_METADATA_KEY,
    HASH_METADATA_KEY,
    ROLES_METADATA_KEY,
    VERSION_METADATA_KEY,
    LoadedAgent,
    LoadedRoutine,
    default_agents_dir,
    load_agents,
    load_routines,
)
from docwiki.agents_client.errors import (
    AgentConfigurationError,
    AgentDefinitionError,
    AgentsClientError,
    DeployError,
)

__all__ = [
    "PROJECT_ENDPOINT_ENV",
    "ROUTINE_FEATURE_HEADER",
    "AgentPayload",
    "DeployResult",
    "McpBinding",
    "RoutineResult",
    "build_agent_payload",
    "build_routine_body",
    "definition_hash",
    "deploy_agent",
    "deploy_routine",
    "main",
    "verify_connection",
]

PROJECT_ENDPOINT_ENV = "DOCWIKI_FOUNDRY_PROJECT_ENDPOINT"
ROUTINE_FEATURE_HEADER = {"Foundry-Features": "Routines=V2Preview"}
_UNHASHED_METADATA = (HASH_METADATA_KEY, VERSION_METADATA_KEY)
_SECRET_AUTH_TYPES = frozenset({"", "apikey", "customkeys", "sas", "none", "oauth2"})


@dataclass(frozen=True)
class McpBinding:
    """Where one MCP tool of an agent points to, and how Agent Service authenticates."""

    server_label: str
    server_url: str
    connection: str
    strategy: str
    server_url_env: str
    connection_env: str


@dataclass(frozen=True)
class AgentPayload:
    """The exact ``create_version`` request body of one agent, and its definition hash."""

    key: str
    agent_name: str
    body: dict[str, Any]
    definition_sha256: str
    bindings: tuple[McpBinding, ...]
    missing_env: tuple[str, ...] = ()

    def describe(self) -> dict[str, Any]:
        return {
            "agent": self.agent_name,
            "operation": "agents.create_version",
            "http": f"POST /agents/{self.agent_name}/versions?api-version=v1",
            "definition_sha256": self.definition_sha256,
            "body": self.body,
        }


@dataclass(frozen=True)
class DeployResult:
    key: str
    agent_name: str
    status: Literal["created", "unchanged"]
    version: str
    previous_version: str | None
    definition_sha256: str
    identity_principal_id: str | None = None
    identity_client_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RoutineResult:
    name: str
    agent: str
    enabled: bool
    cron: str
    time_zone: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class _Env:
    values: Mapping[str, str]
    allow_missing: bool
    missing: list[str] = field(default_factory=list)

    def get(self, name: str, purpose: str) -> str:
        value = (self.values.get(name) or "").strip()
        if value:
            return value
        if not self.allow_missing:
            raise AgentConfigurationError(f"environment variable {name} is not set ({purpose})")
        if name not in self.missing:
            self.missing.append(name)
        return "${" + name + "}"


def _check_server_url(url: str, env_name: str) -> None:
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        raise AgentConfigurationError(f"{env_name} must be an https URL of the MCP endpoint")
    if parts.username or parts.password or parts.query or parts.fragment:
        raise AgentConfigurationError(
            f"{env_name} must not contain credentials, a query or a fragment"
        )


def definition_hash(agent_name: str, body: Mapping[str, Any]) -> str:
    """SHA-256 of the canonical JSON of the request body (without the hash and version metadata)."""
    canonical = copy.deepcopy(dict(body))
    metadata = dict(canonical.get("metadata") or {})
    for key in _UNHASHED_METADATA:
        metadata.pop(key, None)
    canonical["metadata"] = metadata
    text = json.dumps(
        {"agent_name": agent_name, "body": canonical},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_agent_payload(
    agent: LoadedAgent, env: Mapping[str, str], *, allow_missing: bool = False
) -> AgentPayload:
    """Resolve an agent definition against the environment into a ``create_version`` body.

    With ``allow_missing`` (dry runs) unset variables become ``${NAME}`` placeholders and are
    listed in ``missing_env``; otherwise they raise :class:`AgentConfigurationError`.
    """
    definition = agent.definition
    values = _Env(env, allow_missing)
    model = definition.model
    if definition.model_env:
        model = values.get(definition.model_env, f"model deployment of {definition.name}")
    tools: list[dict[str, Any]] = []
    bindings: list[McpBinding] = []
    for tool in definition.tools:
        url = values.get(tool.server_url_env, f"MCP endpoint of {definition.name}")
        if not url.startswith("${"):
            _check_server_url(url, tool.server_url_env)
        connection = values.get(
            tool.auth.connection_env,
            f"project connection used by {definition.name} to authenticate to the MCP server",
        )
        tools.append(
            {
                "type": "mcp",
                "server_label": tool.server_label,
                "server_url": url,
                "allowed_tools": list(tool.allowed_tools),
                "require_approval": tool.require_approval.payload(),
                "project_connection_id": connection,
            }
        )
        bindings.append(
            McpBinding(
                server_label=tool.server_label,
                server_url=url,
                connection=connection,
                strategy=tool.auth.strategy,
                server_url_env=tool.server_url_env,
                connection_env=tool.auth.connection_env,
            )
        )
    strategies = sorted({tool.auth.strategy for tool in definition.tools})
    roles = sorted({role for tool in definition.tools for role in tool.auth.app_roles})
    metadata = {
        **definition.metadata,
        AUTH_METADATA_KEY: ",".join(strategies),
        ROLES_METADATA_KEY: " ".join(roles),
    }
    body: dict[str, Any] = {
        "definition": {
            "kind": "prompt",
            "model": model,
            "instructions": agent.instructions,
            "tools": tools,
            **(
                {"reasoning": {"effort": definition.reasoning_effort}}
                if definition.reasoning_effort
                else {}
            ),
        },
        "description": definition.description,
        "metadata": metadata,
    }
    digest = definition_hash(definition.name, body)
    metadata[HASH_METADATA_KEY] = digest
    metadata[VERSION_METADATA_KEY] = __version__
    return AgentPayload(
        key=agent.key,
        agent_name=definition.name,
        body=body,
        definition_sha256=digest,
        bindings=tuple(bindings),
        missing_env=tuple(values.missing),
    )


def build_routine_body(routine: LoadedRoutine, *, enabled: bool) -> dict[str, Any]:
    """The ``PUT /routines/{name}`` body: a schedule trigger invoking the agent's Responses API."""
    definition = routine.definition
    return {
        "description": definition.description,
        "enabled": enabled,
        "triggers": {
            "schedule": {
                "type": "schedule",
                "cron_expression": definition.trigger.cron,
                "time_zone": definition.trigger.time_zone,
            }
        },
        "action": {
            "type": "invoke_agent_responses_api",
            "agent_name": definition.agent,
            "input": definition.input,
        },
        "authorization": {"identity": definition.authorization.identity},
    }


def _get(item: Any, name: str, default: Any = None) -> Any:
    if item is None:
        return default
    if isinstance(item, Mapping):
        return item.get(name, default)
    return getattr(item, name, default)


def _azure_exceptions() -> Any:
    return importlib.import_module("azure.core.exceptions")


def _normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    return f"{parts.scheme.lower()}://{(parts.netloc or '').lower()}{parts.path.rstrip('/')}"


async def verify_connection(project: Any, binding: McpBinding) -> None:
    """Check that the project connection exists, targets the MCP URL and matches the strategy.

    Agent Service sends tool calls to the connection's target (it wins over ``server_url``) and
    authenticates with the connection's auth type: ``agentic-identity`` for
    ``per-agent-identity``, ``project-managed-identity`` for ``project-managed-identity``.
    """
    errors = _azure_exceptions()
    try:
        connection = await project.connections.get(binding.connection)
    except errors.ResourceNotFoundError as exc:
        raise AgentConfigurationError(
            f"project connection {binding.connection!r} ({binding.connection_env}) does not exist; "
            "create a remote-tool connection to the MCP server first (see agents/README.md)"
        ) from exc
    target = str(_get(connection, "target") or "")
    if _normalize_url(target) != _normalize_url(binding.server_url):
        raise AgentConfigurationError(
            f"project connection {binding.connection!r} targets {target!r} but "
            f"{binding.server_url_env} is {binding.server_url!r}; they must be the same endpoint"
        )
    auth_type = str(_get(_get(connection, "credentials"), "type") or "")
    normalized = auth_type.replace("-", "").replace("_", "").casefold()
    agentic = normalized.startswith("agenticidentity")
    if binding.strategy == "per-agent-identity" and not agentic:
        raise AgentConfigurationError(
            f"project connection {binding.connection!r} uses auth type {auth_type!r}; the "
            "per-agent-identity strategy needs an agentic-identity connection"
        )
    if binding.strategy == "project-managed-identity" and (
        agentic or normalized in _SECRET_AUTH_TYPES
    ):
        raise AgentConfigurationError(
            f"project connection {binding.connection!r} uses auth type {auth_type!r}; the "
            "project-managed-identity strategy needs a project-managed-identity connection"
        )


def _identity(*items: Any) -> tuple[str | None, str | None]:
    """``(principal_id, client_id)`` of the first ``instance_identity`` found (ADR 0003)."""
    for item in items:
        identity = _get(item, "instance_identity")
        principal, client = _get(identity, "principal_id"), _get(identity, "client_id")
        if principal or client:
            return (str(principal) if principal else None, str(client) if client else None)
    return None, None


async def deploy_agent(project: Any, payload: AgentPayload) -> DeployResult:
    """Create a new agent version unless the latest one already has the same definition hash.

    The result carries the agent's Entra agent identity (``instance_identity`` principal and
    client IDs): the infrastructure hook assigns the MCP app roles to the principal and adds the
    client ID to the Container Apps ``allowedApplications`` list (ADR 0003).
    """
    if payload.missing_env:
        raise AgentConfigurationError(f"unresolved environment variables {payload.missing_env}")
    errors = _azure_exceptions()
    details: Any = None
    latest: Any = None
    try:
        details = await project.agents.get(payload.agent_name)
        latest = _get(_get(details, "versions"), "latest")
    except errors.ResourceNotFoundError:
        latest = None
    previous = str(_get(latest, "version")) if latest is not None else None
    deployed_hash = _get(_get(latest, "metadata") or {}, HASH_METADATA_KEY)
    if latest is not None and deployed_hash == payload.definition_sha256:
        principal, client = _identity(details, latest)
        return DeployResult(
            key=payload.key,
            agent_name=payload.agent_name,
            status="unchanged",
            version=str(previous),
            previous_version=previous,
            definition_sha256=payload.definition_sha256,
            identity_principal_id=principal,
            identity_client_id=client,
        )
    created = await project.agents.create_version(payload.agent_name, payload.body)
    principal, client = _identity(created)
    if principal is None and client is None:
        # The identity belongs to the agent object; a new agent may only show it there.
        try:
            details = await project.agents.get(payload.agent_name)
        except errors.ResourceNotFoundError:
            details = None
        principal, client = _identity(details, _get(_get(details, "versions"), "latest"))
    return DeployResult(
        key=payload.key,
        agent_name=payload.agent_name,
        status="created",
        version=str(_get(created, "version")),
        previous_version=previous,
        definition_sha256=payload.definition_sha256,
        identity_principal_id=principal,
        identity_client_id=client,
    )


async def deploy_routine(project: Any, routine: LoadedRoutine, *, enabled: bool) -> RoutineResult:
    """Create or replace the routine (idempotent ``PUT``) with the requested enabled state."""
    body = build_routine_body(routine, enabled=enabled)
    result = await project.beta.routines.create_or_update(routine.name, body)
    trigger = routine.definition.trigger
    return RoutineResult(
        name=routine.name,
        agent=routine.definition.agent,
        enabled=bool(_get(result, "enabled", enabled)),
        cron=trigger.cron,
        time_zone=trigger.time_zone,
    )


@asynccontextmanager
async def _project_client(endpoint: str, injected: Any | None) -> AsyncIterator[Any]:
    if injected is not None:
        yield injected
        return
    try:
        projects_aio = importlib.import_module("azure.ai.projects.aio")
        identity_aio = importlib.import_module("azure.identity.aio")
    except ImportError as exc:
        raise AgentConfigurationError(
            "deploying needs the azure extra (uv sync --extra azure)"
        ) from exc
    credential = identity_aio.DefaultAzureCredential()
    project = projects_aio.AIProjectClient(
        endpoint=endpoint, credential=credential, user_agent=f"docwiki/{__version__}"
    )
    try:
        yield project
    finally:
        await project.close()
        await credential.close()


def _select(agents: Mapping[str, LoadedAgent], wanted: Sequence[str] | None) -> list[LoadedAgent]:
    if not wanted:
        return list(agents.values())
    selected: list[LoadedAgent] = []
    for item in wanted:
        agent = agents.get(item) or next((a for a in agents.values() if a.name == item), None)
        if agent is None:
            raise AgentDefinitionError(f"unknown agent {item!r} (known: {sorted(agents)})")
        if agent not in selected:
            selected.append(agent)
    return selected


def _dry_run(
    agents: Sequence[LoadedAgent],
    routines: Sequence[LoadedRoutine],
    env: Mapping[str, str],
    *,
    enable_routine: bool,
) -> dict[str, Any]:
    payloads = [build_agent_payload(agent, env, allow_missing=True) for agent in agents]
    missing: list[str] = []
    if not (env.get(PROJECT_ENDPOINT_ENV) or "").strip():
        missing.append(PROJECT_ENDPOINT_ENV)
    for payload in payloads:
        missing.extend(name for name in payload.missing_env if name not in missing)
    return {
        "dry_run": True,
        "missing_env": missing,
        "agents": [payload.describe() for payload in payloads],
        "routines": [
            {
                "routine": routine.name,
                "operation": "beta.routines.create_or_update",
                "http": f"PUT /routines/{routine.name}?api-version=v1",
                "headers": ROUTINE_FEATURE_HEADER,
                "body": build_routine_body(routine, enabled=enable_routine),
            }
            for routine in routines
        ],
    }


async def _deploy(
    agents: Sequence[LoadedAgent],
    routines: Sequence[LoadedRoutine],
    env: Mapping[str, str],
    *,
    enable_routine: bool,
    check_connections: bool,
    project_client: Any | None,
    report: Callable[[DeployResult | RoutineResult], None],
) -> None:
    endpoint = (env.get(PROJECT_ENDPOINT_ENV) or "").strip()
    if not endpoint and project_client is None:
        raise AgentConfigurationError(f"environment variable {PROJECT_ENDPOINT_ENV} is not set")
    payloads = [build_agent_payload(agent, env) for agent in agents]
    errors = _azure_exceptions()
    async with _project_client(endpoint, project_client) as project:
        for payload in payloads:
            try:
                if check_connections:
                    for binding in payload.bindings:
                        await verify_connection(project, binding)
                report(await deploy_agent(project, payload))
            except errors.AzureError as exc:
                raise DeployError(f"{payload.agent_name}: {_azure_message(exc)}") from exc
        for routine in routines:
            try:
                report(await deploy_routine(project, routine, enabled=enable_routine))
            except errors.AzureError as exc:
                raise DeployError(f"routine {routine.name}: {_azure_message(exc)}") from exc


def _azure_message(exc: Exception) -> str:
    status = getattr(exc, "status_code", None)
    message = getattr(exc, "message", None) or str(exc)
    return f"HTTP {status}: {message}" if status else str(message)


def _print_result(result: DeployResult | RoutineResult) -> None:
    if isinstance(result, RoutineResult):
        state = "enabled" if result.enabled else "disabled"
        print(
            f"routine {result.name}: {state} (agent {result.agent}, "
            f"cron '{result.cron}' {result.time_zone})"
        )
        return
    if result.status == "created":
        change = f"created version {result.version}"
        if result.previous_version:
            change += f" (previous {result.previous_version})"
    else:
        change = f"unchanged at version {result.version}"
    print(f"{result.agent_name}: {change}; definition sha256 {result.definition_sha256[:12]}")
    if result.identity_principal_id or result.identity_client_id:
        print(
            f"  agent identity: principal {result.identity_principal_id or '?'}, "
            f"client {result.identity_client_id or '?'}"
        )


def _utf8_stdout() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None and (sys.stdout.encoding or "").lower() not in ("utf-8", "utf8"):
        reconfigure(encoding="utf-8")


def _parser(agents_dir: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agents/deploy.py",
        description="Create or update the DocWiki Foundry agents (one version per change).",
    )
    parser.add_argument("--agents-dir", type=Path, default=agents_dir, help="agent definitions")
    parser.add_argument(
        "--agent",
        action="append",
        metavar="KEY",
        help="deploy only this agent (folder name or agent name); repeatable",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the exact request bodies without calling Azure",
    )
    parser.add_argument(
        "--routine",
        choices=("enable", "disable"),
        help="also create or update the routines (routine.yaml), enabled or disabled",
    )
    parser.add_argument(
        "--skip-connection-check",
        action="store_true",
        help="do not read the MCP project connection before deploying",
    )
    parser.add_argument("--json", action="store_true", help="print the results as JSON")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    agents_dir: Path | None = None,
    env: Mapping[str, str] | None = None,
    project_client: Any | None = None,
) -> int:
    """Command-line entry point; returns 0 on success, 1 on Azure errors, 2 on invalid input."""
    args = _parser(agents_dir or default_agents_dir()).parse_args(argv)
    values = os.environ if env is None else env
    _utf8_stdout()
    collected: list[DeployResult | RoutineResult] = []
    report: Callable[[DeployResult | RoutineResult], None] = (
        collected.append if args.json else _print_result
    )
    try:
        agents = load_agents(args.agents_dir)
        selected = _select(agents, args.agent)
        routines = load_routines(agents, args.agents_dir) if args.routine else []
        if args.dry_run:
            plan = _dry_run(selected, routines, values, enable_routine=args.routine == "enable")
            print(json.dumps(plan, indent=2, ensure_ascii=False))
            if plan["missing_env"]:
                print(
                    "warning: unset environment variables are shown as ${NAME}: "
                    + ", ".join(plan["missing_env"]),
                    file=sys.stderr,
                )
            return 0
        asyncio.run(
            _deploy(
                selected,
                routines,
                values,
                enable_routine=args.routine == "enable",
                check_connections=not args.skip_connection_check,
                project_client=project_client,
                report=report,
            )
        )
    except (AgentDefinitionError, AgentConfigurationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except AgentsClientError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        output = {
            "agents": [item.to_dict() for item in collected if isinstance(item, DeployResult)],
            "routines": [item.to_dict() for item in collected if isinstance(item, RoutineResult)],
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0
