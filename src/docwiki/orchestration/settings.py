"""Engine settings from ``DOCWIKI_*`` environment variables and an optional local ``.env``.

Keys come from :class:`docwiki.contracts.settings.SettingsKeys`; the engine adds keys that are
not (yet) in the contracts: ``DOCWIKI_ORCHESTRATOR`` (``af`` for the Microsoft Agent Framework
workflow, ``async`` for the plain-asyncio fallback) and ``DOCWIKI_SITE_BUILD`` (build the Quartz
site into each release; default ``true`` in azure mode and ``false`` in local mode, where
``docwiki run --site`` asks for it). The ``.env`` file is a developer convenience and is never
committed (it is git-ignored).
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

from docwiki.contracts.enums import SENSITIVITIES
from docwiki.contracts.settings import SETTINGS_DEFAULTS, SettingsKeys

__all__ = [
    "CANARIES_KEY",
    "ORCHESTRATOR_KEY",
    "SITE_BUILD_KEY",
    "EngineSettings",
    "SettingsError",
    "load_dotenv",
    "parse_dotenv",
    "resolve_pack_path",
]

CANARIES_KEY = SettingsKeys.CANARIES
ORCHESTRATOR_KEY = "DOCWIKI_ORCHESTRATOR"
SITE_BUILD_KEY = "DOCWIKI_SITE_BUILD"
_DOTENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


class SettingsError(ValueError):
    """Invalid or missing engine setting (the message names the variable)."""


def parse_dotenv(text: str) -> dict[str, str]:
    """``KEY=VALUE`` lines (``export`` prefix, comments and quotes allowed)."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _DOTENV_LINE.match(line)
        if not match:
            continue
        key, value = match.group(1), match.group(2)
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        else:
            value = value.split(" #", 1)[0].strip()
        values[key] = value
    return values


def load_dotenv(
    path: str | Path = ".env", *, environ: MutableMapping[str, str] | None = None
) -> dict[str, str]:
    """Load ``path`` into ``environ`` without overriding variables that are already set."""
    target = os.environ if environ is None else environ
    file = Path(path)
    if not file.is_file():
        return {}
    values = parse_dotenv(file.read_text(encoding="utf-8"))
    for key, value in values.items():
        target.setdefault(key, value)
    return values


def _get(env: Mapping[str, str], key: str) -> str | None:
    value = env.get(key)
    if value is None or not value.strip():
        default = SETTINGS_DEFAULTS.get(key)
        return default
    return value.strip()


def _int(env: Mapping[str, str], key: str, minimum: int = 0) -> int:
    raw = _get(env, key)
    try:
        value = int(raw) if raw is not None else minimum
    except ValueError:
        raise SettingsError(f"{key} must be an integer") from None
    if value < minimum:
        raise SettingsError(f"{key} must be >= {minimum}")
    return value


def _float(env: Mapping[str, str], key: str, minimum: float = 0.0) -> float:
    raw = _get(env, key)
    try:
        value = float(raw) if raw is not None else minimum
    except ValueError:
        raise SettingsError(f"{key} must be a number") from None
    if value < minimum:
        raise SettingsError(f"{key} must be >= {minimum}")
    return value


def _bool(env: Mapping[str, str], key: str) -> bool:
    raw = (_get(env, key) or "false").lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    raise SettingsError(f"{key} must be true or false")


def _optional_bool(env: Mapping[str, str], key: str) -> bool | None:
    return _bool(env, key) if _get(env, key) is not None else None


def _canaries(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    return tuple(dict.fromkeys(item.strip() for item in raw.split(",") if item.strip()))


@dataclass(frozen=True)
class EngineSettings:
    """Resolved settings of one engine process (CLI command, worker or test)."""

    mode: Literal["local", "azure"] = "local"
    work_dir: Path = Path(".local")
    input_dir: Path | None = None
    domain: str | None = None
    audience: str = "internal"
    storage_account: str | None = None
    raw_container: str = "raw"
    work_container: str = "work"
    releases_container: str = "releases"
    queue_name: str = "ingest"
    poison_queue_name: str = "ingest-poison"
    debounce_s: float = 30.0
    lease_s: float = 60.0
    retention: int = 10
    max_pages: int = 300
    extract_concurrency: int = 4
    llm_concurrency: int = 6
    research_max_tool_calls: int = 12
    content_understanding: bool = False
    foundry_endpoint: str | None = None
    site_base_url: str | None = None
    build_site: bool | None = None
    canaries: tuple[str, ...] = ()
    orchestrator: Literal["af", "async"] | None = None
    max_dequeue: int = 5
    visibility_timeout_s: int = 300
    max_cycles: int = 3
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None, **overrides: Any) -> EngineSettings:
        """Read ``DOCWIKI_*`` variables (``os.environ`` by default); ``overrides`` win."""
        source = dict(os.environ if env is None else env)
        mode = (_get(source, SettingsKeys.MODE) or "local").lower()
        if mode not in ("local", "azure"):
            raise SettingsError(f"{SettingsKeys.MODE} must be 'local' or 'azure'")
        audience = (_get(source, SettingsKeys.AUDIENCE) or "internal").lower()
        if audience not in SENSITIVITIES:
            raise SettingsError(
                f"{SettingsKeys.AUDIENCE} must be one of {', '.join(SENSITIVITIES)}"
            )
        orchestrator = (source.get(ORCHESTRATOR_KEY) or "").strip().lower() or None
        if orchestrator not in (None, "af", "async"):
            raise SettingsError(f"{ORCHESTRATOR_KEY} must be 'af' or 'async'")
        settings = cls(
            mode=mode,  # type: ignore[arg-type]
            work_dir=Path(_get(source, SettingsKeys.WORK_DIR) or ".local"),
            domain=_get(source, SettingsKeys.DOMAIN),
            audience=audience,
            storage_account=_get(source, SettingsKeys.STORAGE_ACCOUNT),
            raw_container=_get(source, SettingsKeys.RAW_CONTAINER) or "raw",
            work_container=_get(source, SettingsKeys.WORK_CONTAINER) or "work",
            releases_container=_get(source, SettingsKeys.RELEASES_CONTAINER) or "releases",
            queue_name=_get(source, SettingsKeys.QUEUE_NAME) or "ingest",
            poison_queue_name=_get(source, SettingsKeys.POISON_QUEUE_NAME) or "ingest-poison",
            debounce_s=_float(source, SettingsKeys.DEBOUNCE_SECONDS),
            lease_s=_float(source, SettingsKeys.LEASE_SECONDS, 1.0),
            retention=_int(source, SettingsKeys.RELEASE_RETENTION, 1),
            max_pages=_int(source, SettingsKeys.MAX_PAGES_PER_DOCUMENT, 1),
            extract_concurrency=_int(source, SettingsKeys.EXTRACT_CONCURRENCY, 1),
            llm_concurrency=_int(source, SettingsKeys.LLM_CONCURRENCY, 1),
            research_max_tool_calls=_int(source, SettingsKeys.RESEARCH_MAX_TOOL_CALLS, 1),
            content_understanding=_bool(source, SettingsKeys.CONTENT_UNDERSTANDING),
            foundry_endpoint=_get(source, SettingsKeys.FOUNDRY_PROJECT_ENDPOINT),
            site_base_url=_get(source, SettingsKeys.SITE_BASE_URL),
            build_site=_optional_bool(source, SITE_BUILD_KEY),
            canaries=_canaries(source.get(CANARIES_KEY)),
            orchestrator=orchestrator,  # type: ignore[arg-type]
        )
        clean = {key: value for key, value in overrides.items() if value is not None}
        return replace(settings, **clean) if clean else settings

    def with_overrides(self, **overrides: Any) -> EngineSettings:
        clean = {key: value for key, value in overrides.items() if value is not None}
        return replace(self, **clean) if clean else self

    @property
    def site_enabled(self) -> bool:
        """Whether runs build the site (``DOCWIKI_SITE_BUILD``, else azure mode only)."""
        return self.build_site if self.build_site is not None else self.mode == "azure"

    @property
    def blob_account_url(self) -> str:
        return _account_url(self.storage_account, "blob")

    @property
    def queue_account_url(self) -> str:
        return _account_url(self.storage_account, "queue")


def _account_url(account: str | None, service: Literal["blob", "queue"]) -> str:
    if not account:
        raise SettingsError(f"{SettingsKeys.STORAGE_ACCOUNT} is required in azure mode")
    value = account.strip().rstrip("/")
    if value.startswith("https://"):
        return re.sub(r"\.(blob|queue)\.", f".{service}.", value, count=1)
    if not re.fullmatch(r"[a-z0-9]{3,24}", value):
        raise SettingsError(
            f"{SettingsKeys.STORAGE_ACCOUNT} must be an account name or an https URL"
        )
    return f"https://{value}.{service}.core.windows.net"


def resolve_pack_path(domain: str | None, *, search: tuple[Path, ...] = ()) -> Path:
    """Folder of the domain pack: an existing path, or ``domains/<name>`` (cwd or repository)."""
    if not domain:
        raise SettingsError(f"set {SettingsKeys.DOMAIN} or pass --domain")
    direct = Path(domain)
    if direct.is_dir():
        return direct
    repo_root = Path(__file__).resolve().parents[3]
    for base in (*search, Path.cwd() / "domains", repo_root / "domains"):
        candidate = base / domain
        if candidate.is_dir():
            return candidate
    raise SettingsError(
        f"domain pack {domain!r} not found (looked in ./domains and the repository)"
    )
