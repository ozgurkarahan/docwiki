"""Settings of the MCP server, read from ``DOCWIKI_*`` environment variables.

Keys come from :class:`docwiki.contracts.settings.SettingsKeys`. The role mapping is configurable
(``DOCWIKI_ROLE_CLAIM``, ``DOCWIKI_READ_ROLE``, ``DOCWIKI_OPERATE_ROLE``, comma-separated lists);
the contract between the platform and this server is the app-role claims of the caller
(docs/adr/0003-mcp-agent-identity.md: per-agent Entra identities, roles in the long-form role
claim named by the principal's ``role_typ``). In ``easyauth`` mode the server also validates the
bearer token that built-in authentication forwards (``DOCWIKI_MCP_TENANT_ID``,
``DOCWIKI_MCP_AUDIENCE``, ``DOCWIKI_MCP_ALLOWED_CLIENT_IDS``, ``DOCWIKI_MCP_TOKEN_VALIDATION``).
"""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Literal

from docwiki.contracts.settings import SETTINGS_DEFAULTS, SettingsKeys

__all__ = [
    "LONG_ROLE_CLAIM",
    "MAX_QUERY_ROWS",
    "MAX_REPORT_CHARS",
    "MIN_MAX_CHARS",
    "McpConfig",
    "RoleConfig",
    "is_loopback",
]

AuthMode = Literal["none", "easyauth"]
Level = Literal["read", "operate"]
TokenValidation = Literal["required", "off"]

_TENANT_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

LONG_ROLE_CLAIM = "http://schemas.microsoft.com/ws/2008/06/identity/claims/role"
"""Long-form role claim type used by App Service / Container Apps authentication."""

MAX_QUERY_ROWS = 200
"""Hard cap of ``query_table`` rows (spec: at most 200)."""

MIN_MAX_CHARS = 2000
"""Lower bound of the output budget: smaller budgets cannot carry a useful result."""

MAX_REPORT_CHARS = 20000
"""Size limit of a health report written by ``write_health_report``."""


def _split(value: str | None) -> tuple[str, ...]:
    """Comma-separated list, trimmed, empty items dropped, order kept, duplicates removed."""
    return tuple(dict.fromkeys(part.strip() for part in (value or "").split(",") if part.strip()))


@dataclass(frozen=True)
class RoleConfig:
    """Which claim types carry app roles and which roles grant each access level."""

    claim_types: tuple[str, ...] = ("roles", LONG_ROLE_CLAIM)
    read_roles: frozenset[str] = frozenset({"Wiki.Read"})
    operate_roles: frozenset[str] = frozenset({"Wiki.Operate"})

    def levels_for(self, roles: frozenset[str]) -> frozenset[Level]:
        """Access levels granted by a set of app roles (no implication between levels)."""
        levels: set[Level] = set()
        if roles & self.read_roles:
            levels.add("read")
        if roles & self.operate_roles:
            levels.add("operate")
        return frozenset(levels)

    def role_names(self, level: Level) -> str:
        roles = self.read_roles if level == "read" else self.operate_roles
        return " or ".join(sorted(roles))


def is_loopback(host: str) -> bool:
    """True for loopback bind addresses (``127.0.0.0/8``, ``::1``, ``localhost``)."""
    value = host.strip().strip("[]").lower()
    if value == "localhost":
        return True
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


@dataclass(frozen=True)
class McpConfig:
    """Effective server configuration (environment defaults overridden by CLI flags)."""

    auth_mode: AuthMode = "none"
    allow_ops: bool = False
    """Register and grant operations tools without an authenticated principal (local dev)."""
    max_chars: int = 12000
    pointer_ttl_s: float = 30.0
    query_max_rows: int = MAX_QUERY_ROWS
    roles: RoleConfig = field(default_factory=RoleConfig)
    mode: Literal["local", "azure"] = "local"
    work_dir: str = ".local"
    storage_account: str | None = None
    work_container: str = "work"
    releases_container: str = "releases"
    queue_name: str = "ingest"
    tenant_id: str | None = None
    """Entra tenant (GUID) issuing the MCP API tokens: token issuer and signing keys derive
    from it."""
    audiences: tuple[str, ...] = ()
    """Accepted ``aud`` values of the bearer token (application ID URI and client ID)."""
    allowed_client_ids: tuple[str, ...] = ()
    """Caller client IDs (``azp``, or ``appid`` in v1 tokens) the server accepts; empty: any."""
    token_validation: TokenValidation = "required"
    """``required``: in ``easyauth`` mode every HTTP call needs a valid bearer token; ``off``:
    trust the platform's principal header alone (explicit opt-out)."""
    answer_context_coverage: bool = False
    """``DOCWIKI_ANSWER_CONTEXT_COVERAGE=on``: ``answer_context`` without ``within`` adds
    ``coverage`` and ``gaps`` (per-scope counts, named scopes without hits); ``off`` (default)
    keeps its output unchanged."""

    def __post_init__(self) -> None:
        if self.auth_mode not in ("none", "easyauth"):
            raise ValueError(f"unknown {SettingsKeys.AUTH_MODE}: {self.auth_mode!r}")
        if self.max_chars < MIN_MAX_CHARS:
            raise ValueError(f"{SettingsKeys.MCP_MAX_CHARS} must be >= {MIN_MAX_CHARS}")
        if not 0 <= self.pointer_ttl_s <= 3600:
            raise ValueError(f"{SettingsKeys.MCP_POINTER_TTL_SECONDS} must be in [0, 3600]")
        if not 1 <= self.query_max_rows <= MAX_QUERY_ROWS:
            raise ValueError(
                f"{SettingsKeys.QUERY_TABLE_MAX_ROWS} must be in [1, {MAX_QUERY_ROWS}]"
            )
        if not self.roles.read_roles or not self.roles.operate_roles:
            raise ValueError("read and operate role lists must not be empty")
        if self.token_validation not in ("required", "off"):
            raise ValueError(
                f"{SettingsKeys.MCP_TOKEN_VALIDATION} must be 'required' or 'off', "
                f"got {self.token_validation!r}"
            )
        if self.tenant_id is not None and not _TENANT_ID.fullmatch(self.tenant_id):
            raise ValueError(
                f"{SettingsKeys.MCP_TENANT_ID} must be a tenant ID (a lower-case GUID)"
            )

    @property
    def local_levels(self) -> frozenset[Level]:
        """Levels of an unauthenticated local caller (stdio or loopback with auth mode none)."""
        return frozenset({"read", "operate"}) if self.allow_ops else frozenset({"read"})

    @property
    def validates_tokens(self) -> bool:
        """Whether HTTP callers must present a valid bearer token (``easyauth`` unless off)."""
        return self.auth_mode == "easyauth" and self.token_validation == "required"

    def token_settings_problem(self) -> str | None:
        """Why bearer tokens cannot be validated with this configuration (None when they can)."""
        if not self.validates_tokens:
            return None
        missing = [
            key
            for key, value in (
                (SettingsKeys.MCP_TENANT_ID, self.tenant_id),
                (SettingsKeys.MCP_AUDIENCE, self.audiences),
            )
            if not value
        ]
        if not missing:
            return None
        return (
            f"{SettingsKeys.AUTH_MODE}=easyauth validates the bearer token forwarded by "
            f"Container Apps built-in authentication: set {' and '.join(missing)} (or set "
            f"{SettingsKeys.MCP_TOKEN_VALIDATION}=off to trust the principal header alone)"
        )

    def with_overrides(self, **changes: object) -> McpConfig:
        return replace(self, **changes)  # type: ignore[arg-type]

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> McpConfig:
        """Configuration from ``DOCWIKI_*`` variables (``env`` defaults to ``os.environ``)."""
        import os

        source = os.environ if env is None else env

        def get(key: str, default: str | None = None) -> str | None:
            value = source.get(key)
            if value is None or not value.strip():
                return SETTINGS_DEFAULTS.get(key, default)
            return value.strip()

        def number(key: str, default: str) -> float:
            raw = get(key, default) or default
            try:
                return float(raw)
            except ValueError:
                raise ValueError(f"{key} must be a number, got {raw!r}") from None

        defaults = RoleConfig()
        roles = RoleConfig(
            claim_types=_split(get(SettingsKeys.ROLE_CLAIM)) or defaults.claim_types,
            read_roles=frozenset(_split(get(SettingsKeys.READ_ROLE))) or defaults.read_roles,
            operate_roles=frozenset(_split(get(SettingsKeys.OPERATE_ROLE)))
            or defaults.operate_roles,
        )
        mode = (get(SettingsKeys.MODE, "local") or "local").lower()
        if mode not in ("local", "azure"):
            raise ValueError(f"unknown {SettingsKeys.MODE}: {mode!r}")
        tenant = get(SettingsKeys.MCP_TENANT_ID)
        coverage = (get(SettingsKeys.ANSWER_CONTEXT_COVERAGE, "off") or "off").lower()
        if coverage not in ("on", "off"):
            raise ValueError(
                f"{SettingsKeys.ANSWER_CONTEXT_COVERAGE} must be 'on' or 'off', "
                f"got {source.get(SettingsKeys.ANSWER_CONTEXT_COVERAGE)!r}"
            )
        return cls(
            auth_mode=(get(SettingsKeys.AUTH_MODE, "none") or "none").lower(),  # type: ignore[arg-type]
            max_chars=int(number(SettingsKeys.MCP_MAX_CHARS, "12000")),
            pointer_ttl_s=number(SettingsKeys.MCP_POINTER_TTL_SECONDS, "30"),
            query_max_rows=int(number(SettingsKeys.QUERY_TABLE_MAX_ROWS, "200")),
            roles=roles,
            mode=mode,  # type: ignore[arg-type]
            work_dir=get(SettingsKeys.WORK_DIR, ".local") or ".local",
            storage_account=get(SettingsKeys.STORAGE_ACCOUNT),
            work_container=get(SettingsKeys.WORK_CONTAINER, "work") or "work",
            releases_container=get(SettingsKeys.RELEASES_CONTAINER, "releases") or "releases",
            queue_name=get(SettingsKeys.QUEUE_NAME, "ingest") or "ingest",
            tenant_id=tenant.lower() if tenant else None,
            audiences=_split(get(SettingsKeys.MCP_AUDIENCE)),
            allowed_client_ids=_split(get(SettingsKeys.MCP_ALLOWED_CLIENT_IDS)),
            token_validation=(
                get(SettingsKeys.MCP_TOKEN_VALIDATION, "required") or "required"
            ).lower(),  # type: ignore[arg-type]
            answer_context_coverage=coverage == "on",
        )
