"""Client-side rate limiting: token buckets per deployment and a loop-safe semaphore."""

from __future__ import annotations

import asyncio
import math
import time
from collections.abc import Awaitable, Callable

from docwiki.llm.settings import RateLimit

Clock = Callable[[], float]
Sleep = Callable[[float], Awaitable[None]]

_EPSILON = 1e-9


class LoopLocal[V]:
    """Lazily creates one asyncio primitive per running event loop."""

    def __init__(self, factory: Callable[[], V]) -> None:
        self._factory = factory
        self._loop: asyncio.AbstractEventLoop | None = None
        self._value: V | None = None

    def get(self) -> V:
        loop = asyncio.get_running_loop()
        if self._value is None or self._loop is not loop:
            self._value = self._factory()
            self._loop = loop
        return self._value


class TokenBucket:
    """Continuously refilled token bucket (callers serialise access)."""

    def __init__(self, capacity: float, refill_per_second: float, *, now: float) -> None:
        if capacity <= 0 or refill_per_second <= 0:
            raise ValueError("capacity and refill rate must be positive")
        self.capacity = float(capacity)
        self.refill_per_second = float(refill_per_second)
        self._tokens = self.capacity
        self._updated = now

    def available(self, now: float) -> float:
        self._refill(now)
        return self._tokens

    def delay_for(self, amount: float, now: float) -> float:
        """Seconds to wait until ``amount`` tokens are available (amount capped at capacity)."""
        self._refill(now)
        needed = min(float(amount), self.capacity)
        if self._tokens >= needed:
            return 0.0
        return (needed - self._tokens) / self.refill_per_second

    def consume(self, amount: float, now: float) -> None:
        self._refill(now)
        self._tokens -= min(float(amount), self.capacity)

    def _refill(self, now: float) -> None:
        elapsed = now - self._updated
        if elapsed > 0:
            self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_per_second)
            self._updated = now


class DeploymentRateLimiter:
    """Token and request buckets for one deployment, plus a Retry-After pause.

    The token bucket holds one minute of tokens (Azure counts the estimated prompt tokens plus
    ``max_output_tokens`` per request). The request bucket holds ten seconds of requests, because
    Azure evaluates request rates over short windows. Waiters are served in FIFO order.
    """

    def __init__(
        self,
        deployment: str,
        limit: RateLimit,
        *,
        clock: Clock = time.monotonic,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self.deployment = deployment
        self.limit = limit
        self._clock = clock
        self._sleep = sleep
        now = clock()
        tpm = limit.tokens_per_minute
        rpm = limit.requests_per_minute
        self._tokens = TokenBucket(tpm, tpm / 60.0, now=now) if tpm > 0 else None
        self._requests = TokenBucket(max(1.0, rpm / 6.0), rpm / 60.0, now=now) if rpm > 0 else None
        self._blocked_until = -math.inf
        self._lock: LoopLocal[asyncio.Lock] = LoopLocal(asyncio.Lock)

    def penalize(self, seconds: float) -> None:
        """Block every caller of this deployment for ``seconds`` (server Retry-After)."""
        if seconds > 0:
            self._blocked_until = max(self._blocked_until, self._clock() + seconds)

    def blocked_for(self) -> float:
        return max(0.0, self._blocked_until - self._clock())

    def delay_for(self, tokens: int) -> float:
        now = self._clock()
        delay = self._blocked_until - now
        if self._tokens is not None:
            delay = max(delay, self._tokens.delay_for(tokens, now))
        if self._requests is not None:
            delay = max(delay, self._requests.delay_for(1, now))
        return max(0.0, delay)

    async def acquire(self, tokens: int) -> float:
        """Wait until a request of ``tokens`` estimated tokens may start; return seconds waited."""
        started = self._clock()
        async with self._lock.get():
            while True:
                delay = self.delay_for(tokens)
                if delay <= _EPSILON:
                    break
                await self._sleep(delay)
            now = self._clock()
            if self._tokens is not None:
                self._tokens.consume(tokens, now)
            if self._requests is not None:
                self._requests.consume(1, now)
        return max(0.0, now - started)
