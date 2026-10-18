"""Typed exceptions raised by ``docwiki.llm``.

Every failure surfaces as an :class:`LlmError` subclass carrying the call context (tier,
deployment, schema, request hash, attempts and the tokens already consumed) so the caller can
quarantine the input and the usage ledger can still account for billed tokens.
"""

from __future__ import annotations

from typing import Any, Self

from docwiki.llm.types import LlmUsage


class LlmError(Exception):
    """Base class of every error raised by ``docwiki.llm``."""

    def __init__(
        self,
        message: str,
        *,
        tier: str | None = None,
        deployment: str | None = None,
        schema_name: str | None = None,
        request_hash: str | None = None,
        model: str | None = None,
        status_code: int | None = None,
        request_id: str | None = None,
        retries: int = 0,
        attempts: int = 0,
        usage: LlmUsage | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.tier = tier
        self.deployment = deployment
        self.schema_name = schema_name
        self.request_hash = request_hash
        self.model = model
        self.status_code = status_code
        self.request_id = request_id
        self.retries = retries
        self.attempts = attempts
        self.usage = usage if usage is not None else LlmUsage()

    def with_context(self, **values: Any) -> Self:
        """Fill context attributes that are still unset (``None`` or zero) and return ``self``."""
        for name, value in values.items():
            if value is None:
                continue
            current = getattr(self, name, None)
            if current is None or current == 0 or current == LlmUsage():
                setattr(self, name, value)
        return self

    def __str__(self) -> str:
        return self.message


class LlmConfigurationError(LlmError):
    """Settings are missing or invalid (endpoint, deployment names, limits, price table...)."""


class LlmAuthError(LlmError):
    """Entra authentication or authorization failed (credential error, HTTP 401/403)."""


class LlmRateLimited(LlmError):
    """The deployment kept answering HTTP 429 after the retry budget was spent."""

    def __init__(self, message: str, *, retry_after_s: float | None = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.retry_after_s = retry_after_s


class LlmTimeout(LlmError):
    """The request timed out (client timeout or HTTP 408) after the retry budget was spent."""


class LlmServiceError(LlmError):
    """Any other service failure: 5xx/connection errors after retries, or a non-retryable 4xx."""

    def __init__(self, message: str, *, code: str | None = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.code = code


class LlmContentFiltered(LlmError):
    """The prompt or the completion was blocked by content filtering, or the model refused."""

    def __init__(self, message: str, *, reason: str = "content_filter", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.reason = reason


class LlmInvalidOutput(LlmError):
    """The model output did not validate against the requested schema (after one repair)."""

    def __init__(
        self,
        message: str,
        *,
        errors: tuple[str, ...] = (),
        raw_output: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.errors = errors
        self.raw_output = raw_output


class LlmOutputTruncated(LlmInvalidOutput):
    """The output hit ``max_output_tokens`` before the JSON object was complete."""


class LlmReplayMissing(LlmError):
    """``ReplayLlmClient`` has no recording for the request."""

    def __init__(self, message: str, *, fixture: str | None = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.fixture = fixture


class LlmFakeHandlerMissing(LlmConfigurationError):
    """``FakeLlmClient`` has no handler registered for the requested schema name."""
