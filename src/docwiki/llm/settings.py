"""LLM settings, read from ``DOCWIKI_*`` environment variables."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from docwiki.llm.errors import LlmConfigurationError
from docwiki.llm.types import TIERS, Tier

DEFAULT_CONCURRENCY = 6
DEFAULT_TOKENS_PER_MINUTE = 100_000
DEFAULT_REQUESTS_PER_MINUTE = 600
DEFAULT_TIMEOUT_S = 600.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_MAX_RETRY_AFTER_S = 120.0
DEFAULT_EMBED_DIMENSIONS = 512
DEFAULT_EMBED_BATCH_SIZE = 64
MAX_EMBED_BATCH_SIZE = 2048

ENV_PROJECT_ENDPOINT = "DOCWIKI_FOUNDRY_PROJECT_ENDPOINT"
ENV_DEPLOYMENT = {"fast": "DOCWIKI_FAST_DEPLOYMENT", "smart": "DOCWIKI_SMART_DEPLOYMENT"}
ENV_MODEL = {"fast": "DOCWIKI_FAST_MODEL", "smart": "DOCWIKI_SMART_MODEL"}
ENV_TPM = {"fast": "DOCWIKI_FAST_TPM", "smart": "DOCWIKI_SMART_TPM"}
ENV_RPM = {"fast": "DOCWIKI_FAST_RPM", "smart": "DOCWIKI_SMART_RPM"}
ENV_CONCURRENCY = "DOCWIKI_LLM_CONCURRENCY"
ENV_TIMEOUT = "DOCWIKI_LLM_TIMEOUT_SECONDS"
ENV_MAX_RETRIES = "DOCWIKI_LLM_MAX_RETRIES"
ENV_MAX_RETRY_AFTER = "DOCWIKI_LLM_MAX_RETRY_AFTER_SECONDS"
ENV_PRICE_TABLE = "DOCWIKI_LLM_PRICE_TABLE"
ENV_MODE = "DOCWIKI_LLM_MODE"
ENV_FIXTURES = "DOCWIKI_LLM_FIXTURES"
ENV_EMBED_DEPLOYMENT = "DOCWIKI_EMBED_DEPLOYMENT"
ENV_EMBED_MODEL = "DOCWIKI_EMBED_MODEL"
ENV_EMBED_DIMENSIONS = "DOCWIKI_EMBED_DIMENSIONS"
ENV_EMBED_BATCH_SIZE = "DOCWIKI_EMBED_BATCH_SIZE"
ENV_EMBED_TPM = "DOCWIKI_EMBED_TPM"
ENV_EMBED_RPM = "DOCWIKI_EMBED_RPM"

LlmMode = Literal["foundry", "replay", "record"]


class RateLimit(BaseModel):
    """Client-side limits of one deployment; ``0`` disables a dimension."""

    model_config = ConfigDict(frozen=True)

    tokens_per_minute: int = Field(default=DEFAULT_TOKENS_PER_MINUTE, ge=0)
    requests_per_minute: int = Field(default=DEFAULT_REQUESTS_PER_MINUTE, ge=0)

    def merge(self, other: RateLimit) -> RateLimit:
        """The most restrictive combination (used when two tiers share one deployment)."""
        return RateLimit(
            tokens_per_minute=_min_enabled(self.tokens_per_minute, other.tokens_per_minute),
            requests_per_minute=_min_enabled(self.requests_per_minute, other.requests_per_minute),
        )


class LlmSettings(BaseModel):
    """Configuration of the LLM gateway. Build it with :meth:`from_env` in applications."""

    model_config = ConfigDict(frozen=True)

    project_endpoint: str | None = None
    fast_deployment: str | None = None
    smart_deployment: str | None = None
    fast_model: str | None = None
    smart_model: str | None = None
    concurrency: int = Field(default=DEFAULT_CONCURRENCY, ge=1, le=256)
    fast_rate_limit: RateLimit = RateLimit()
    smart_rate_limit: RateLimit = RateLimit()
    timeout_s: float = Field(default=DEFAULT_TIMEOUT_S, gt=0)
    max_retries: int = Field(default=DEFAULT_MAX_RETRIES, ge=0, le=10)
    max_retry_after_s: float = Field(default=DEFAULT_MAX_RETRY_AFTER_S, gt=0)
    price_table: Path | None = None
    mode: LlmMode = "foundry"
    fixtures_dir: Path | None = None
    embed_deployment: str | None = None
    embed_model: str | None = None
    embed_dimensions: int = Field(default=DEFAULT_EMBED_DIMENSIONS, ge=1, le=3072)
    embed_batch_size: int = Field(default=DEFAULT_EMBED_BATCH_SIZE, ge=1, le=MAX_EMBED_BATCH_SIZE)
    embed_rate_limit: RateLimit = RateLimit()

    @field_validator("project_endpoint")
    @classmethod
    def _check_endpoint(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().rstrip("/")
        if not value.startswith("https://"):
            raise ValueError("the Foundry project endpoint must be an https:// URL")
        return value

    @field_validator(
        "fast_deployment",
        "smart_deployment",
        "fast_model",
        "smart_model",
        "embed_deployment",
        "embed_model",
    )
    @classmethod
    def _strip_names(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> LlmSettings:
        """Read settings from ``environ`` (default ``os.environ``); empty values count as unset."""
        env = {
            key: value.strip()
            for key, value in (os.environ if environ is None else environ).items()
            if key.startswith("DOCWIKI_") and value and value.strip()
        }
        values: dict[str, Any] = {
            "project_endpoint": env.get(ENV_PROJECT_ENDPOINT),
            "concurrency": _int(env, ENV_CONCURRENCY, DEFAULT_CONCURRENCY),
            "timeout_s": _float(env, ENV_TIMEOUT, DEFAULT_TIMEOUT_S),
            "max_retries": _int(env, ENV_MAX_RETRIES, DEFAULT_MAX_RETRIES),
            "max_retry_after_s": _float(env, ENV_MAX_RETRY_AFTER, DEFAULT_MAX_RETRY_AFTER_S),
            "price_table": Path(env[ENV_PRICE_TABLE]) if ENV_PRICE_TABLE in env else None,
            "mode": env.get(ENV_MODE, "foundry").lower(),
            "fixtures_dir": Path(env[ENV_FIXTURES]) if ENV_FIXTURES in env else None,
            "embed_deployment": env.get(ENV_EMBED_DEPLOYMENT),
            "embed_model": env.get(ENV_EMBED_MODEL),
            "embed_dimensions": _int(env, ENV_EMBED_DIMENSIONS, DEFAULT_EMBED_DIMENSIONS),
            "embed_batch_size": _int(env, ENV_EMBED_BATCH_SIZE, DEFAULT_EMBED_BATCH_SIZE),
            "embed_rate_limit": {
                "tokens_per_minute": _int(env, ENV_EMBED_TPM, DEFAULT_TOKENS_PER_MINUTE),
                "requests_per_minute": _int(env, ENV_EMBED_RPM, DEFAULT_REQUESTS_PER_MINUTE),
            },
        }
        for tier in TIERS:
            values[f"{tier}_deployment"] = env.get(ENV_DEPLOYMENT[tier])
            values[f"{tier}_model"] = env.get(ENV_MODEL[tier])
            values[f"{tier}_rate_limit"] = {
                "tokens_per_minute": _int(env, ENV_TPM[tier], DEFAULT_TOKENS_PER_MINUTE),
                "requests_per_minute": _int(env, ENV_RPM[tier], DEFAULT_REQUESTS_PER_MINUTE),
            }
        try:
            return cls(**values)
        except ValidationError as exc:
            raise _configuration_error(exc) from None

    def deployment_name(self, tier: Tier) -> str | None:
        return self.fast_deployment if tier == "fast" else self.smart_deployment

    def deployment(self, tier: Tier) -> str:
        """The deployment configured for ``tier``; raises if it is not configured."""
        name = self.deployment_name(tier)
        if not name:
            raise LlmConfigurationError(
                f"No deployment configured for the '{tier}' tier: set {ENV_DEPLOYMENT[tier]}",
                tier=tier,
            )
        return name

    def model_for(self, tier: Tier) -> str | None:
        """Optional model id configured for ``tier`` (a pricing hint, see prices.yaml)."""
        return self.fast_model if tier == "fast" else self.smart_model

    def rate_limit(self, tier: Tier) -> RateLimit:
        return self.fast_rate_limit if tier == "fast" else self.smart_rate_limit

    def require_foundry(self, tiers: tuple[Tier, ...] = TIERS) -> None:
        """Raise :class:`LlmConfigurationError` unless live Foundry calls are possible."""
        if not self.project_endpoint:
            raise LlmConfigurationError(
                f"{ENV_PROJECT_ENDPOINT} is not set (Foundry project endpoint, "
                "https://<account>.services.ai.azure.com/api/projects/<project>)"
            )
        for tier in tiers:
            self.deployment(tier)

    def embedding_deployment(self) -> str:
        """The embedding deployment; raises if it is not configured."""
        if not self.embed_deployment:
            raise LlmConfigurationError(
                f"No embedding deployment configured: set {ENV_EMBED_DEPLOYMENT}", tier="embed"
            )
        return self.embed_deployment

    def require_embedding(self) -> None:
        """Raise :class:`LlmConfigurationError` unless live embedding calls are possible."""
        self.require_foundry(tiers=())
        self.embedding_deployment()

    def require_fixtures_dir(self) -> Path:
        if self.fixtures_dir is None:
            raise LlmConfigurationError(
                f"{ENV_FIXTURES} must point to the LLM fixtures directory in {self.mode} mode"
            )
        return self.fixtures_dir


def _min_enabled(left: int, right: int) -> int:
    enabled = [value for value in (left, right) if value > 0]
    return min(enabled) if enabled else 0


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name)
    if raw is None:
        return default
    try:
        return int(raw.replace("_", ""))
    except ValueError:
        raise LlmConfigurationError(f"{name} must be an integer") from None


def _float(env: Mapping[str, str], name: str, default: float) -> float:
    raw = env.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        raise LlmConfigurationError(f"{name} must be a number") from None


_FIELD_ENV = {
    "project_endpoint": ENV_PROJECT_ENDPOINT,
    "concurrency": ENV_CONCURRENCY,
    "timeout_s": ENV_TIMEOUT,
    "max_retries": ENV_MAX_RETRIES,
    "max_retry_after_s": ENV_MAX_RETRY_AFTER,
    "mode": ENV_MODE,
    "fixtures_dir": ENV_FIXTURES,
    "price_table": ENV_PRICE_TABLE,
    "embed_deployment": ENV_EMBED_DEPLOYMENT,
    "embed_model": ENV_EMBED_MODEL,
    "embed_dimensions": ENV_EMBED_DIMENSIONS,
    "embed_batch_size": ENV_EMBED_BATCH_SIZE,
    "embed_rate_limit.tokens_per_minute": ENV_EMBED_TPM,
    "embed_rate_limit.requests_per_minute": ENV_EMBED_RPM,
}
for _tier in TIERS:
    _FIELD_ENV[f"{_tier}_deployment"] = ENV_DEPLOYMENT[_tier]
    _FIELD_ENV[f"{_tier}_model"] = ENV_MODEL[_tier]
    _FIELD_ENV[f"{_tier}_rate_limit.tokens_per_minute"] = ENV_TPM[_tier]
    _FIELD_ENV[f"{_tier}_rate_limit.requests_per_minute"] = ENV_RPM[_tier]


def _configuration_error(exc: ValidationError) -> LlmConfigurationError:
    # Never echo raw values: endpoints are deployment-specific identifiers.
    problems = []
    for error in exc.errors(include_url=False, include_input=False):
        location = ".".join(str(part) for part in error["loc"])
        problems.append(f"{_FIELD_ENV.get(location, location)}: {error['msg']}")
    return LlmConfigurationError("Invalid LLM settings: " + "; ".join(problems))
