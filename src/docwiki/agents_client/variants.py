"""Evaluation variants of the Researcher and of the MCP app it reads: ``agents/variants.yaml``.

An evaluation compares several arms, as the knowledge-access study did; each arm is one MCP app
(Bicep ``evalMcpVariants``, ``DOCWIKI_*`` settings on top of the production ones) read by one
evaluation Researcher agent (``docwiki-researcher-<name>``) that differs from the production
Researcher only by its instructions, reasoning effort, model deployment and MCP endpoint.

Schema of ``variants.yaml``::

    mcp_variants:                          # value of the azd setting DOCWIKI_EVAL_MCP_VARIANTS
      raw: {DOCWIKI_MCP_WIKI_ABLATION: raw}
      wide: {DOCWIKI_MCP_MAX_CHARS: "${DOCWIKI_EVAL_MAX_CHARS}"}   # ${NAME}: from the environment
    agents:
      - name: r1                           # agent docwiki-researcher-r1
        base: researcher
        mcp_variant: raw
        instructions: null                 # null = the base instructions, or agents/variants/...md
        reasoning_effort: null             # null = the base setting (production: unset)
        model_env: DOCWIKI_EVAL_SMART_DEPLOYMENT

Variants are opt-in: the ordinary deploy, the post-provision hook and the teardown never read them.
"""

from __future__ import annotations

import base64
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Annotated, Any, Literal

from pydantic import StringConstraints, ValidationError, field_validator, model_validator

from docwiki.agents_client.definitions import (
    MAX_INSTRUCTIONS_CHARS,
    RESERVED_METADATA_KEYS,
    AgentDefinition,
    EnvName,
    LoadedAgent,
    _read_yaml,
    _Strict,
    normalize_text,
)
from docwiki.agents_client.errors import (
    AgentConfigurationError,
    AgentDefinitionError,
)

__all__ = [
    "ALL_VARIANTS",
    "PROTECTED_MCP_ENV",
    "VARIANTS_FILE",
    "VARIANTS_OUT_ENV",
    "AgentVariant",
    "McpEndpoint",
    "VariantsFile",
    "build_variant_agent",
    "encode_mcp_variants",
    "load_variants",
    "parse_variants_out",
    "resolve_mcp_variants",
    "variant_agent_name",
    "variant_env_names",
    "variant_environment",
]

VARIANTS_FILE = "variants.yaml"
VARIANTS_OUT_ENV = "DOCWIKI_EVAL_MCP_VARIANTS_OUT"
ALL_VARIANTS = "all"
DEFAULT_MODEL_ENV = "DOCWIKI_EVAL_SMART_DEPLOYMENT"
URL_ENV_PREFIX = "DOCWIKI_EVAL_MCP_URL_"
CONNECTION_ENV_PREFIX = "DOCWIKI_EVAL_MCP_CONNECTION_"
VARIANT_METADATA_KEY = "docwiki_variant"
MCP_VARIANT_METADATA_KEY = "docwiki_mcp_variant"

# A variant sets DOCWIKI_MCP_* settings of the server, never its authentication (the Bicep
# template drops these too).
PROTECTED_MCP_ENV: tuple[str, ...] = (
    "DOCWIKI_MCP_AUDIENCE",
    "DOCWIKI_MCP_TENANT_ID",
    "DOCWIKI_MCP_TOKEN_VALIDATION",
    "DOCWIKI_MCP_ALLOWED_CLIENT_IDS",
)

VariantName = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]{1,8}$")]
McpEnvName = Annotated[str, StringConstraints(pattern=r"^DOCWIKI_MCP_[A-Z0-9_]+$")]
_PLACEHOLDER = re.compile(r"\$\{(DOCWIKI_[A-Z0-9_]+)\}")


class AgentVariant(_Strict):
    """One evaluation Researcher: its instructions, effort, model and MCP variant."""

    name: VariantName
    base: Literal["researcher"] = "researcher"
    mcp_variant: VariantName
    instructions: str | None = None
    reasoning_effort: Literal["low", "medium", "high"] | None = None
    model_env: EnvName = DEFAULT_MODEL_ENV

    @field_validator("instructions")
    @classmethod
    def _instructions(cls, value: str | None) -> str | None:
        if value is None:
            return None
        path = PurePosixPath(value)
        if "\\" in value or path.is_absolute() or ".." in path.parts or path.suffix != ".md":
            raise ValueError("instructions must be a relative POSIX path to a .md file or null")
        return value


class VariantsFile(_Strict):
    """Validated content of ``variants.yaml``."""

    mcp_variants: dict[VariantName, dict[McpEnvName, str]]
    agents: tuple[AgentVariant, ...]

    @field_validator("mcp_variants")
    @classmethod
    def _env(cls, value: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
        for name, env in value.items():
            protected = sorted(set(env) & set(PROTECTED_MCP_ENV))
            if protected:
                raise ValueError(f"mcp variant {name!r} sets authentication settings {protected}")
        return value

    @model_validator(mode="after")
    def _check(self) -> VariantsFile:
        names = [agent.name for agent in self.agents]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ValueError(f"duplicate agent variants {duplicates}")
        unknown = sorted({a.mcp_variant for a in self.agents} - set(self.mcp_variants))
        if unknown:
            raise ValueError(f"agents use undeclared mcp_variants {unknown}")
        return self

    def select(self, wanted: Sequence[str]) -> list[AgentVariant]:
        """The variants named in ``wanted`` (``all`` selects every one), in declaration order."""
        if ALL_VARIANTS in wanted:
            return list(self.agents)
        known = {agent.name: agent for agent in self.agents}
        unknown = [name for name in wanted if name not in known]
        if unknown:
            raise AgentConfigurationError(
                f"unknown variant {unknown} (declared in {VARIANTS_FILE}: {sorted(known)})"
            )
        return [known[name] for name in dict.fromkeys(wanted)]


def load_variants(path: Path) -> VariantsFile:
    """Read and validate ``variants.yaml``."""
    data = _read_yaml(path)
    try:
        return VariantsFile.model_validate(data)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc']) or '<root>'}: {error['msg']}"
            for error in exc.errors()
        )
        raise AgentDefinitionError(f"{path}: {details}") from exc


def variant_agent_name(base: LoadedAgent, variant: AgentVariant) -> str:
    """Foundry name of a variant agent (``docwiki-researcher-<name>``)."""
    return f"{base.definition.name}-{variant.name}"


def variant_env_names(variant: AgentVariant) -> tuple[str, str]:
    """Environment variables carrying the MCP URL and project connection of a variant agent."""
    suffix = variant.name.upper()
    return URL_ENV_PREFIX + suffix, CONNECTION_ENV_PREFIX + suffix


def build_variant_agent(variant: AgentVariant, base: LoadedAgent, repo_root: Path) -> LoadedAgent:
    """The evaluation agent of ``variant``: the base definition with its own name, model,
    reasoning effort, optional instructions and MCP endpoint variables.

    Raises :class:`AgentConfigurationError` when its instructions file does not exist (yet).
    """
    instructions = base.instructions
    if variant.instructions is not None:
        path = repo_root / variant.instructions
        if not path.is_file():
            raise AgentConfigurationError(
                f"variant {variant.name}: instructions file {variant.instructions} does not "
                f"exist (looked in {repo_root}); create it or set instructions: null"
            )
        instructions = normalize_text(path.read_text(encoding="utf-8"))
        if not instructions:
            raise AgentConfigurationError(f"{variant.instructions}: instructions are empty")
        if len(instructions) > MAX_INSTRUCTIONS_CHARS:
            raise AgentConfigurationError(
                f"{variant.instructions}: instructions exceed {MAX_INSTRUCTIONS_CHARS} characters"
            )
    url_env, connection_env = variant_env_names(variant)
    data = base.definition.model_dump()
    data["name"] = variant_agent_name(base, variant)
    data["model"] = "${" + variant.model_env + "}"
    if variant.reasoning_effort is not None:
        data["reasoning_effort"] = variant.reasoning_effort
    metadata = dict(data["metadata"])
    for key in (VARIANT_METADATA_KEY, MCP_VARIANT_METADATA_KEY):
        if key in RESERVED_METADATA_KEYS or key in metadata:
            raise AgentDefinitionError(f"{base.name}: metadata key {key!r} is reserved")
    metadata[VARIANT_METADATA_KEY] = variant.name
    metadata[MCP_VARIANT_METADATA_KEY] = variant.mcp_variant
    data["metadata"] = metadata
    for tool in data["tools"]:
        tool["server_url_env"] = url_env
        tool["auth"]["connection_env"] = connection_env
    try:
        definition = AgentDefinition.model_validate(data)
    except ValueError as exc:
        raise AgentDefinitionError(f"{base.name}: no valid variant {variant.name}: {exc}") from None
    return LoadedAgent(
        key=base.key, path=base.path, definition=definition, instructions=instructions
    )


@dataclass(frozen=True)
class McpEndpoint:
    """URL and project connection of one evaluation MCP app (Bicep output)."""

    url: str
    connection: str


def parse_variants_out(env: Mapping[str, str]) -> dict[str, McpEndpoint]:
    """``DOCWIKI_EVAL_MCP_VARIANTS_OUT``: the Bicep output, JSON ``name -> {url, connection}``."""
    text = (env.get(VARIANTS_OUT_ENV) or "").strip()
    if not text:
        raise AgentConfigurationError(
            f"environment variable {VARIANTS_OUT_ENV} is not set: provision the evaluation MCP "
            "apps first (DOCWIKI_EVAL_MCP_VARIANTS, agents/README.md)"
        )
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise AgentConfigurationError(f"{VARIANTS_OUT_ENV} is not valid JSON: {exc}") from exc
    endpoints: dict[str, McpEndpoint] = {}
    if not isinstance(data, dict):
        raise AgentConfigurationError(f"{VARIANTS_OUT_ENV} must be a JSON object")
    for name, entry in data.items():
        url = entry.get("url") if isinstance(entry, dict) else None
        connection = entry.get("connection") if isinstance(entry, dict) else None
        if not isinstance(url, str) or not isinstance(connection, str) or not url or not connection:
            raise AgentConfigurationError(
                f"{VARIANTS_OUT_ENV}[{name!r}] needs a url and a connection"
            )
        endpoints[str(name)] = McpEndpoint(url=url, connection=connection)
    return endpoints


def variant_environment(
    env: Mapping[str, str], variants: Iterable[AgentVariant], *, strict: bool
) -> dict[str, str]:
    """``env`` plus the MCP URL and connection variables of every selected variant.

    Strict (a real deploy): a variant whose MCP app is not in ``DOCWIKI_EVAL_MCP_VARIANTS_OUT``
    is an error. Not strict (dry run): the variables stay unset and show as ``${NAME}``.
    """
    merged = dict(env)
    chosen = list(variants)
    if not strict and not (env.get(VARIANTS_OUT_ENV) or "").strip():
        return merged
    endpoints = parse_variants_out(env)
    for variant in chosen:
        endpoint = endpoints.get(variant.mcp_variant)
        if endpoint is None:
            if strict:
                raise AgentConfigurationError(
                    f"variant {variant.name}: the MCP variant {variant.mcp_variant!r} is not in "
                    f"{VARIANTS_OUT_ENV} (provisioned: {sorted(endpoints)})"
                )
            continue
        url_env, connection_env = variant_env_names(variant)
        merged[url_env], merged[connection_env] = endpoint.url, endpoint.connection
    return merged


def resolve_mcp_variants(
    declared: VariantsFile, env: Mapping[str, str], names: Sequence[str] | None = None
) -> list[dict[str, Any]]:
    """The ``DOCWIKI_EVAL_MCP_VARIANTS`` array: ``[{"name", "env"}]`` with ``${NAME}`` filled in.

    ``names`` defaults to the MCP variants used by the declared agents.
    """
    wanted = list(names) if names else list(dict.fromkeys(a.mcp_variant for a in declared.agents))
    unknown = [name for name in wanted if name not in declared.mcp_variants]
    if unknown:
        raise AgentConfigurationError(
            f"unknown mcp variant {unknown} (declared: {sorted(declared.mcp_variants)})"
        )
    missing: list[str] = []

    def fill(match: re.Match[str]) -> str:
        value = (env.get(match.group(1)) or "").strip()
        if not value:
            missing.append(match.group(1))
        return value

    resolved = [
        {
            "name": name,
            "env": {
                key: _PLACEHOLDER.sub(fill, value)
                for key, value in declared.mcp_variants[name].items()
            },
        }
        for name in wanted
    ]
    if missing:
        raise AgentConfigurationError(
            f"environment variables {sorted(set(missing))} are not set (used by {VARIANTS_FILE})"
        )
    return resolved


def encode_mcp_variants(variants: Sequence[Mapping[str, Any]]) -> str:
    """Base64 of the compact JSON array: the azd value that survives the parameters file."""
    text = json.dumps(list(variants), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return base64.b64encode(text.encode("utf-8")).decode("ascii")
