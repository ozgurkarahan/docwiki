"""Structured tool failures: recoverable problems are results, not protocol errors.

Microsoft Foundry aborts the whole agent turn (HTTP 400 ``tool_user_error``) when an MCP tool
answers with a JSON-RPC error *or* an ``isError: true`` result, and the model never sees why
(docs/adr/0003-mcp-agent-identity.md, spike finding F3). DocWiki therefore returns every tool
outcome as a normal, successful MCP result whose JSON body says whether it worked::

    {"ok": true, ...payload...}
    {"ok": false, "tool": "read_page", "error": {"code": "not_found", "message": "...",
     "retryable": false, "details": {...}}}

The message tells the model what to do next. Only transport-level authentication failures stay
outside this contract (HTTP 401 before any MCP processing).
"""

from __future__ import annotations

from typing import Any, Literal, get_args

__all__ = [
    "ERROR_CODES",
    "RETRYABLE_CODES",
    "ErrorCode",
    "ToolFailure",
    "failure_payload",
]

ErrorCode = Literal[
    "invalid_argument",
    "not_found",
    "forbidden",
    "conflict",
    "too_large",
    "unavailable",
    "timeout",
    "internal",
]
ERROR_CODES: tuple[str, ...] = get_args(ErrorCode)
"""
* ``invalid_argument`` - malformed or out-of-range arguments, non-``SELECT`` SQL, wrong tool.
* ``not_found`` - the page, section, source, sidecar, table, skill, run, proposal, release or
  tool does not exist (the message suggests where to look).
* ``forbidden`` - the caller lacks the app role the tool requires (do not retry).
* ``conflict`` - the object changed concurrently or a final decision was already taken.
* ``too_large`` - an input exceeds its size limit or a result cannot fit the output budget.
* ``unavailable`` - no release is served yet, or storage / the queue failed (retry later).
* ``timeout`` - an upstream call timed out (retry later).
* ``internal`` - unexpected server error; details are only in the server log.
"""

RETRYABLE_CODES = frozenset({"unavailable", "timeout"})


class ToolFailure(Exception):
    """An anticipated, agent-correctable failure returned to the agent as ``ok: false``."""

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode = "invalid_argument",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        if code not in ERROR_CODES:
            raise ValueError(f"unknown tool error code: {code!r}")
        self.code: ErrorCode = code
        self.message = message
        self.details = details or {}


def failure_payload(
    code: ErrorCode,
    message: str,
    *,
    tool: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The JSON body of a failed tool call (``ok`` is always the first key)."""
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "retryable": code in RETRYABLE_CODES,
    }
    if details:
        error["details"] = details
    payload: dict[str, Any] = {"ok": False}
    if tool:
        payload["tool"] = tool
    payload["error"] = error
    return payload
