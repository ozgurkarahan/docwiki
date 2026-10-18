"""Test helpers for docwiki.llm (no network: HTTP is served by httpx2.MockTransport)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any

import httpx2
from azure.core.credentials import AccessToken, AccessTokenInfo

TEST_ENDPOINT = "https://example.com/api/projects/demo"
TOKEN_EXPIRY = 4_102_444_800  # 2100-01-01, far in the future
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24


class FakeTime:
    """Deterministic clock whose sleep advances time instantly."""

    def __init__(self, start: float = 1_000.0) -> None:
        self.now = start
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds
        await asyncio.sleep(0)


class StaticCredential:
    """AsyncTokenCredential returning a fixed fake token; records requested scopes."""

    def __init__(self) -> None:
        self.scopes: list[tuple[str, ...]] = []
        self.closed = False

    async def get_token(self, *scopes: str, **kwargs: Any) -> AccessToken:
        self.scopes.append(scopes)
        return AccessToken("unit-test-token", TOKEN_EXPIRY)

    async def get_token_info(self, *scopes: str, options: Any = None) -> AccessTokenInfo:
        self.scopes.append(scopes)
        return AccessTokenInfo("unit-test-token", TOKEN_EXPIRY)

    async def close(self) -> None:
        self.closed = True


def response_body(
    output: dict[str, Any] | str | None = None,
    *,
    model: str = "gpt-4.1-mini-2025-04-14",
    input_tokens: int = 100,
    output_tokens: int = 20,
    cached_tokens: int = 0,
    status: str = "completed",
    incomplete_reason: str | None = None,
    refusal: str | None = None,
    error: dict[str, str] | None = None,
) -> dict[str, Any]:
    """A Responses API JSON body as returned by the service."""
    if refusal is not None:
        content = [{"type": "refusal", "refusal": refusal}]
    else:
        text = output if isinstance(output, str) else json.dumps(output or {})
        content = [{"type": "output_text", "text": text, "annotations": []}]
    return {
        "id": "resp_test",
        "object": "response",
        "created_at": 1_700_000_000,
        "status": status,
        "model": model,
        "error": error,
        "incomplete_details": {"reason": incomplete_reason} if incomplete_reason else None,
        "output": [
            {
                "type": "message",
                "id": "msg_test",
                "status": "completed",
                "role": "assistant",
                "content": content,
            }
        ],
        "usage": {
            "input_tokens": input_tokens,
            "input_tokens_details": {"cached_tokens": cached_tokens, "cache_write_tokens": 0},
            "output_tokens": output_tokens,
            "output_tokens_details": {"reasoning_tokens": 0},
            "total_tokens": input_tokens + output_tokens,
        },
        "parallel_tool_calls": False,
        "tool_choice": "none",
        "tools": [],
    }


def ok(output: dict[str, Any] | str, **kwargs: Any) -> httpx2.Response:
    return httpx2.Response(200, json=response_body(output, **kwargs))


def status_error(
    status: int, *, code: str | None = None, headers: dict[str, str] | None = None, **extra: Any
) -> httpx2.Response:
    error = {"code": code or str(status), "message": f"simulated HTTP {status}", **extra}
    return httpx2.Response(status, headers=headers or {}, json={"error": error})


Step = httpx2.Response | Exception | Callable[[httpx2.Request], httpx2.Response]


class Script:
    """MockTransport handler serving scripted steps in order (the last step repeats)."""

    def __init__(self, *steps: Step, delay: float = 0.0) -> None:
        if not steps:
            raise ValueError("a script needs at least one step")
        self.steps = list(steps)
        self.delay = delay
        self.requests: list[httpx2.Request] = []
        self.bodies: list[dict[str, Any]] = []
        self.in_flight = 0
        self.max_in_flight = 0

    async def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        self.bodies.append(json.loads(request.content))
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
            step = self.steps.pop(0) if len(self.steps) > 1 else self.steps[0]
            if isinstance(step, Exception):
                raise step
            if callable(step) and not isinstance(step, httpx2.Response):
                return step(request)
            return step
        finally:
            self.in_flight -= 1
