"""Model failures a stage absorbs for one item, and failures that abort the whole run.

Systemic failures (authentication, configuration, rate limits, timeouts, service errors, missing
replay fixtures) concern every call of the run: they propagate so that the orchestrator stops and
retries the run (the same classes as ``docwiki.orchestration.pipeline.SYSTEMIC_ERRORS``). The
other :class:`~docwiki.llm.LlmError` subclasses concern one request (content filtering or a
refusal, output that is still invalid after the client's repair, output cut at
``max_output_tokens``): they fail again deterministically on the next run, so a stage degrades
that one item instead and records why.
"""

from __future__ import annotations

from docwiki.llm import (
    LlmAuthError,
    LlmConfigurationError,
    LlmContentFiltered,
    LlmError,
    LlmRateLimited,
    LlmReplayMissing,
    LlmServiceError,
    LlmTimeout,
)

__all__ = ["SYSTEMIC_LLM_ERRORS", "describe_failure", "is_systemic"]

SYSTEMIC_LLM_ERRORS: tuple[type[LlmError], ...] = (
    LlmAuthError,
    LlmConfigurationError,
    LlmRateLimited,
    LlmTimeout,
    LlmServiceError,
    LlmReplayMissing,
)


def is_systemic(exc: BaseException) -> bool:
    """True for failures that must abort the run instead of degrading one item."""
    return isinstance(exc, SYSTEMIC_LLM_ERRORS)


def describe_failure(exc: LlmError) -> str:
    """Error class (and filter reason) only: never document or model text, safe to log."""
    name = type(exc).__name__
    if isinstance(exc, LlmContentFiltered) and exc.reason:
        return f"{name} ({exc.reason})"
    return name
