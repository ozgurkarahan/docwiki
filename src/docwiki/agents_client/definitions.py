"""Foundry agent definitions as code: ``agents/<key>/agent.yaml`` and ``agents/<key>/routine.yaml``.

``docs/spec/mcp-and-agents.md`` §1 lists the DocWiki MCP tools and the app role each one needs; §2
defines the two prompt agents and the optional routine. The YAML files are validated here (unknown
fields are errors) before anything is deployed, and the safety rules are enforced in code:

* every allowed tool has an explicit approval policy (``always`` or ``never``);
* the mutating tools (``ingest_start``, ``recompile``, ``decide_proposal``) always need approval;
* an agent declares the MCP app roles its principal needs, and only those (least privilege);
* a routine prompt only uses tools that never need approval.

Schema of ``agent.yaml``::

    name: docwiki-researcher               # Foundry agent name
    description: ...
    model: ${DOCWIKI_SMART_DEPLOYMENT}     # deployment name, or a ${DOCWIKI_*} placeholder
    instructions_file: instructions.md     # relative to the YAML file
    tools:
      - type: mcp
        server_label: docwiki
        server_url_env: DOCWIKI_MCP_URL    # environment variable holding the MCP endpoint
        allowed_tools: [search, ...]
        require_approval: {always: [...], never: [...]}
        auth:
          strategy: per-agent-identity     # or project-managed-identity
          connection_env: DOCWIKI_MCP_CONNECTION   # optional (this is the default)
          app_roles: [Wiki.Read]
    metadata: {docwiki_agent: researcher}  # string values, see Foundry metadata limits
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Annotated, Any, Literal, get_args

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)

from docwiki.agents_client.errors import AgentDefinitionError

__all__ = [
    "AGENT_FILE",
    "AGENT_KEYS",
    "APPROVAL_REQUIRED_TOOLS",
    "APP_ROLES",
    "AUTH_METADATA_KEY",
    "AUTH_STRATEGIES",
    "DEFAULT_CONNECTION_ENV",
    "HASH_METADATA_KEY",
    "KNOWN_TOOLS",
    "OPS_TOOLS",
    "READ_TOOLS",
    "RESERVED_METADATA_KEYS",
    "ROLES_METADATA_KEY",
    "ROUTINE_FILE",
    "ROUTINE_TOOLS",
    "TOOL_ROLES",
    "VERSION_METADATA_KEY",
    "AgentDefinition",
    "ApprovalPolicy",
    "AuthStrategy",
    "LoadedAgent",
    "LoadedRoutine",
    "McpAuth",
    "McpToolDefinition",
    "RoutineDefinition",
    "ScheduleTrigger",
    "default_agents_dir",
    "foundry_agent_name",
    "load_agent",
    "load_agents",
    "load_routine",
    "load_routines",
    "normalize_text",
]

READ_TOOLS: tuple[str, ...] = (
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
"""MCP read tools (role ``Wiki.Read``)."""

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
"""MCP operations tools (role ``Wiki.Operate``)."""

KNOWN_TOOLS: tuple[str, ...] = READ_TOOLS + OPS_TOOLS
APPROVAL_REQUIRED_TOOLS: tuple[str, ...] = ("ingest_start", "recompile", "decide_proposal")
"""Tools that change the system: human approval is mandatory for every agent."""

ROUTINE_TOOLS: tuple[str, ...] = (
    "run_status",
    "quality_report",
    "list_sources",
    "list_proposals",
    "write_health_report",
)
"""The only tools a scheduled routine may use (nobody is there to approve a call)."""

READ_ROLE = "Wiki.Read"
OPERATE_ROLE = "Wiki.Operate"
APP_ROLES: tuple[str, ...] = (READ_ROLE, OPERATE_ROLE)
TOOL_ROLES: dict[str, str] = {
    **dict.fromkeys(READ_TOOLS, READ_ROLE),
    **dict.fromkeys(OPS_TOOLS, OPERATE_ROLE),
}

AuthStrategy = Literal["per-agent-identity", "project-managed-identity"]
AUTH_STRATEGIES: tuple[str, ...] = get_args(AuthStrategy)
AppRole = Literal["Wiki.Read", "Wiki.Operate"]

AGENT_FILE = "agent.yaml"
ROUTINE_FILE = "routine.yaml"
DEFAULT_CONNECTION_ENV = "DOCWIKI_MCP_CONNECTION"
AGENT_KEYS: tuple[str, ...] = ("researcher", "librarian")
AGENT_NAME_PREFIX = "docwiki-"

HASH_METADATA_KEY = "docwiki_definition_sha256"
VERSION_METADATA_KEY = "docwiki_version"
AUTH_METADATA_KEY = "docwiki_mcp_auth"
ROLES_METADATA_KEY = "docwiki_mcp_roles"
RESERVED_METADATA_KEYS: tuple[str, ...] = (
    HASH_METADATA_KEY,
    VERSION_METADATA_KEY,
    AUTH_METADATA_KEY,
    ROLES_METADATA_KEY,
)
"""Metadata written by the deploy script; YAML files cannot set them."""

MAX_METADATA_ENTRIES = 16  # Foundry limit (keys <= 64 chars, values <= 512 chars)
MAX_METADATA_VALUE_CHARS = 512
MAX_INSTRUCTIONS_CHARS = 32_000
MAX_ROUTINE_INPUT_CHARS = 4_000

_AGENT_NAME_PATTERN = r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$"
AgentName = Annotated[str, StringConstraints(pattern=_AGENT_NAME_PATTERN)]
EnvName = Annotated[str, StringConstraints(pattern=r"^DOCWIKI_[A-Z0-9_]+$")]
ServerLabel = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_-]{0,63}$")]
Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=512)]

_PLACEHOLDER_RE = re.compile(r"^\$\{(?P<env>DOCWIKI_[A-Z0-9_]+)\}$")
_DEPLOYMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_METADATA_KEY_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_CRON_FIELD_RE = re.compile(r"^[0-9A-Za-z*/,?-]+$")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _duplicates(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return duplicates


def _mentions(text: str, tool: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(tool)}(?![A-Za-z0-9_])", text) is not None


class ApprovalPolicy(_Strict):
    """Per-tool approval policy; serialised as the MCP tool's ``require_approval`` filter."""

    always: tuple[str, ...] = ()
    never: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> ApprovalPolicy:
        for field in ("always", "never"):
            duplicates = _duplicates(getattr(self, field))
            if duplicates:
                raise ValueError(f"require_approval.{field} lists {duplicates} more than once")
        both = sorted(set(self.always) & set(self.never))
        if both:
            raise ValueError(f"tools in both require_approval.always and .never: {both}")
        return self

    def payload(self) -> dict[str, Any]:
        """``{"always": {"tool_names": [...]}, "never": {...}}``, empty lists omitted."""
        payload: dict[str, Any] = {}
        if self.always:
            payload["always"] = {"tool_names": list(self.always)}
        if self.never:
            payload["never"] = {"tool_names": list(self.never)}
        return payload


class McpAuth(_Strict):
    """How Agent Service authenticates to the DocWiki MCP server.

    Both strategies use a Foundry project connection (kind ``remote-tool``) whose name is read from
    ``connection_env``; the connection's auth type must match the strategy (``agentic-identity`` or
    ``project-managed-identity``, audience = the MCP API application ID URI). ``app_roles`` are the
    MCP API app roles the calling principal must hold.

    ADR 0003 (docs/adr/0003-mcp-agent-identity.md, accepted) chose ``per-agent-identity``: each
    agent calls with its own Entra agent identity through one ``AgenticIdentityToken``
    connection. ``project-managed-identity`` remains supported but is not adopted (it would need
    one Foundry project per agent to keep the roles apart).
    """

    strategy: AuthStrategy
    connection_env: EnvName = DEFAULT_CONNECTION_ENV
    app_roles: tuple[AppRole, ...] = Field(min_length=1)

    @field_validator("app_roles")
    @classmethod
    def _unique_roles(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        duplicates = _duplicates(value)
        if duplicates:
            raise ValueError(f"app_roles lists {duplicates} more than once")
        return value


class McpToolDefinition(_Strict):
    """The DocWiki MCP tool of a prompt agent."""

    type: Literal["mcp"]
    server_label: ServerLabel
    server_url_env: EnvName
    allowed_tools: tuple[str, ...] = Field(min_length=1)
    require_approval: ApprovalPolicy
    auth: McpAuth

    @model_validator(mode="after")
    def _check(self) -> McpToolDefinition:
        named = (*self.allowed_tools, *self.require_approval.always, *self.require_approval.never)
        unknown = sorted({tool for tool in named if tool not in KNOWN_TOOLS})
        if unknown:
            raise ValueError(f"unknown DocWiki MCP tools {unknown} (known: {list(KNOWN_TOOLS)})")
        duplicates = _duplicates(self.allowed_tools)
        if duplicates:
            raise ValueError(f"allowed_tools lists {duplicates} more than once")
        policy = set(self.require_approval.always) | set(self.require_approval.never)
        missing = [tool for tool in self.allowed_tools if tool not in policy]
        if missing:
            raise ValueError(
                f"every allowed tool needs an explicit approval policy (always or never): {missing}"
            )
        extra = sorted(policy - set(self.allowed_tools))
        if extra:
            raise ValueError(f"approval policy for tools that are not allowed: {extra}")
        unsafe = [
            tool
            for tool in APPROVAL_REQUIRED_TOOLS
            if tool in self.allowed_tools and tool not in self.require_approval.always
        ]
        if unsafe:
            raise ValueError(f"mutating tools must always require approval: {unsafe}")
        needed = {TOOL_ROLES[tool] for tool in self.allowed_tools}
        declared = set(self.auth.app_roles)
        if needed - declared:
            raise ValueError(
                f"allowed tools need app roles {sorted(needed - declared)} that auth.app_roles "
                "does not declare"
            )
        if declared - needed:
            raise ValueError(
                f"auth.app_roles declares {sorted(declared - needed)} but no allowed tool needs "
                "it (least privilege)"
            )
        return self


class AgentDefinition(_Strict):
    """Validated content of an ``agent.yaml`` file (a Foundry prompt agent)."""

    name: AgentName
    description: Description
    model: str
    instructions_file: str
    tools: tuple[McpToolDefinition, ...] = Field(min_length=1)
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("model")
    @classmethod
    def _model(cls, value: str) -> str:
        if not (_PLACEHOLDER_RE.match(value) or _DEPLOYMENT_RE.match(value)):
            raise ValueError(
                "model must be a deployment name or a ${DOCWIKI_...} environment placeholder"
            )
        return value

    @field_validator("instructions_file")
    @classmethod
    def _instructions_file(cls, value: str) -> str:
        path = PurePosixPath(value)
        if "\\" in value or path.is_absolute() or ".." in path.parts or path.suffix != ".md":
            raise ValueError("instructions_file must be a relative POSIX path to a .md file")
        return value

    @field_validator("metadata")
    @classmethod
    def _metadata(cls, value: dict[str, str]) -> dict[str, str]:
        for key, item in value.items():
            if not _METADATA_KEY_RE.match(key):
                raise ValueError(f"metadata key {key!r} must match {_METADATA_KEY_RE.pattern}")
            if key in RESERVED_METADATA_KEYS:
                raise ValueError(f"metadata key {key!r} is written by the deploy script")
            if len(item) > MAX_METADATA_VALUE_CHARS:
                raise ValueError(f"metadata value of {key!r} exceeds {MAX_METADATA_VALUE_CHARS}")
        limit = MAX_METADATA_ENTRIES - len(RESERVED_METADATA_KEYS)
        if len(value) > limit:
            raise ValueError(f"at most {limit} metadata entries (Foundry allows 16 in total)")
        return value

    @model_validator(mode="after")
    def _check(self) -> AgentDefinition:
        duplicates = _duplicates(tool.server_label for tool in self.tools)
        if duplicates:
            raise ValueError(f"duplicate MCP server_label {duplicates}")
        return self

    @property
    def model_env(self) -> str | None:
        """Environment variable named by a ``${...}`` model placeholder (``None`` for a literal)."""
        match = _PLACEHOLDER_RE.match(self.model)
        return match["env"] if match else None

    @property
    def allowed_tools(self) -> tuple[str, ...]:
        tools: list[str] = []
        for tool in self.tools:
            tools.extend(name for name in tool.allowed_tools if name not in tools)
        return tuple(tools)

    @property
    def approval_tools(self) -> tuple[str, ...]:
        """Tools that need a human approval for every call."""
        return tuple(name for tool in self.tools for name in tool.require_approval.always)


class ScheduleTrigger(_Strict):
    type: Literal["schedule"]
    cron: str
    time_zone: str = Field(default="UTC", min_length=1, max_length=64)

    @field_validator("cron")
    @classmethod
    def _cron(cls, value: str) -> str:
        fields = value.split()
        if len(fields) != 5 or not all(_CRON_FIELD_RE.match(field) for field in fields):
            raise ValueError("cron must be a 5-field cron expression such as '0 6 * * *'")
        return " ".join(fields)


class RoutineAuthorization(_Strict):
    identity: Literal["agent"] = "agent"


class RoutineDefinition(_Strict):
    """Validated content of a ``routine.yaml`` file (a Foundry routine invoking an agent)."""

    name: AgentName
    description: Description
    enabled: bool = False
    agent: AgentName
    trigger: ScheduleTrigger
    tools: tuple[str, ...] = Field(min_length=1)
    authorization: RoutineAuthorization = Field(default_factory=RoutineAuthorization)
    input: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_ROUTINE_INPUT_CHARS),
    ]

    @model_validator(mode="after")
    def _check(self) -> RoutineDefinition:
        not_allowed = [tool for tool in self.tools if tool not in ROUTINE_TOOLS]
        if not_allowed:
            raise ValueError(
                f"a routine may only use tools without approval {list(ROUTINE_TOOLS)}; "
                f"got {not_allowed}"
            )
        duplicates = _duplicates(self.tools)
        if duplicates:
            raise ValueError(f"tools lists {duplicates} more than once")
        if "write_health_report" not in self.tools:
            raise ValueError("the routine writes a health report: include write_health_report")
        approval = [tool for tool in APPROVAL_REQUIRED_TOOLS if _mentions(self.input, tool)]
        if approval:
            raise ValueError(f"the routine prompt must not mention approval tools {approval}")
        other = [
            tool
            for tool in KNOWN_TOOLS
            if "_" in tool and tool not in self.tools and _mentions(self.input, tool)
        ]
        if other:
            raise ValueError(f"the routine prompt mentions tools outside routine.tools: {other}")
        unnamed = [tool for tool in self.tools if not _mentions(self.input, tool)]
        if unnamed:
            raise ValueError(f"the routine prompt must name every tool it may use: {unnamed}")
        return self


@dataclass(frozen=True)
class LoadedAgent:
    """An agent definition with its instructions (line endings normalised to LF)."""

    key: str
    path: Path
    definition: AgentDefinition
    instructions: str

    @property
    def name(self) -> str:
        return self.definition.name


@dataclass(frozen=True)
class LoadedRoutine:
    path: Path
    definition: RoutineDefinition
    agent: LoadedAgent

    @property
    def name(self) -> str:
        return self.definition.name


def default_agents_dir() -> Path:
    """``agents/`` of the source checkout (``uv sync`` installs DocWiki in editable mode)."""
    return Path(__file__).resolve().parents[3] / "agents"


def foundry_agent_name(agent: str) -> str:
    """Foundry agent name for a logical key (``researcher`` -> ``docwiki-researcher``).

    Any other value is taken as a Foundry agent name and must be a valid one.
    """
    if agent in AGENT_KEYS:
        return AGENT_NAME_PREFIX + agent
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", agent):
        raise AgentDefinitionError(f"invalid agent name {agent!r}")
    return agent


def normalize_text(text: str) -> str:
    """LF line endings and no surrounding blank space, so the definition hash is OS-independent."""
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AgentDefinitionError(f"cannot read {path}: {exc}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise AgentDefinitionError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise AgentDefinitionError(f"{path}: expected a mapping at the top level")
    return data


def _validate[M: BaseModel](model: type[M], data: Mapping[str, Any], path: Path) -> M:
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc']) or '<root>'}: {error['msg']}"
            for error in exc.errors()
        )
        raise AgentDefinitionError(f"{path}: {details}") from exc


def load_agent(path: Path) -> LoadedAgent:
    """Load and validate ``agent.yaml`` (the file or its folder) and its instructions."""
    yaml_path = path / AGENT_FILE if path.is_dir() else path
    definition = _validate(AgentDefinition, _read_yaml(yaml_path), yaml_path)
    instructions_path = yaml_path.parent / definition.instructions_file
    try:
        instructions = normalize_text(instructions_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise AgentDefinitionError(f"{yaml_path}: cannot read instructions: {exc}") from exc
    if not instructions:
        raise AgentDefinitionError(f"{instructions_path}: instructions are empty")
    if len(instructions) > MAX_INSTRUCTIONS_CHARS:
        raise AgentDefinitionError(
            f"{instructions_path}: instructions exceed {MAX_INSTRUCTIONS_CHARS} characters"
        )
    return LoadedAgent(
        key=yaml_path.parent.name, path=yaml_path, definition=definition, instructions=instructions
    )


def load_agents(agents_dir: Path | None = None) -> dict[str, LoadedAgent]:
    """Every ``<agents_dir>/<key>/agent.yaml``, keyed by folder name."""
    root = agents_dir if agents_dir is not None else default_agents_dir()
    files = sorted(root.glob(f"*/{AGENT_FILE}"))
    if not files:
        raise AgentDefinitionError(f"no */{AGENT_FILE} under {root}")
    agents: dict[str, LoadedAgent] = {}
    seen: dict[str, Path] = {}
    for file in files:
        agent = load_agent(file)
        if agent.name in seen:
            raise AgentDefinitionError(
                f"agent name {agent.name!r} is defined in {seen[agent.name]} and {file}"
            )
        seen[agent.name] = file
        agents[agent.key] = agent
    return agents


def load_routine(path: Path, agents: Mapping[str, LoadedAgent]) -> LoadedRoutine:
    """Load ``routine.yaml`` and check it against the agent it invokes."""
    definition = _validate(RoutineDefinition, _read_yaml(path), path)
    agent = next((item for item in agents.values() if item.name == definition.agent), None)
    if agent is None:
        known = sorted(item.name for item in agents.values())
        raise AgentDefinitionError(f"{path}: agent {definition.agent!r} is not defined ({known})")
    missing = [tool for tool in definition.tools if tool not in agent.definition.allowed_tools]
    if missing:
        raise AgentDefinitionError(f"{path}: {agent.name} is not allowed to use {missing}")
    approval = [tool for tool in definition.tools if tool in agent.definition.approval_tools]
    if approval:
        raise AgentDefinitionError(f"{path}: {approval} require approval for {agent.name}")
    return LoadedRoutine(path=path, definition=definition, agent=agent)


def load_routines(
    agents: Mapping[str, LoadedAgent], agents_dir: Path | None = None
) -> list[LoadedRoutine]:
    """Every ``<agents_dir>/<key>/routine.yaml``."""
    root = agents_dir if agents_dir is not None else default_agents_dir()
    return [load_routine(path, agents) for path in sorted(root.glob(f"*/{ROUTINE_FILE}"))]
