"""Retry policy: exponential backoff with jitter that honours Retry-After headers."""

from __future__ import annotations

import email.utils
import math
import random
import time
from collections.abc import Mapping
from dataclasses import dataclass

from docwiki.llm.settings import LlmSettings


@dataclass(frozen=True)
class RetryPolicy:
    """At most ``max_retries`` retries; delays grow ``base * 2**n`` up to ``max_delay_s``."""

    max_retries: int = 3
    base_delay_s: float = 1.0
    max_delay_s: float = 30.0
    max_retry_after_s: float = 120.0
    retry_after_jitter_s: float = 1.0

    @classmethod
    def from_settings(cls, settings: LlmSettings) -> RetryPolicy:
        return cls(max_retries=settings.max_retries, max_retry_after_s=settings.max_retry_after_s)

    def delay(self, retry_index: int, retry_after_s: float | None, rng: random.Random) -> float:
        """Delay before retry number ``retry_index`` (0-based).

        A server-provided Retry-After is honoured (plus up to 10 % / ``retry_after_jitter_s`` of
        jitter so that blocked callers do not wake up together); otherwise the delay is a random
        value between half and all of the exponential backoff ("equal jitter").
        """
        if retry_after_s is not None and retry_after_s > 0:
            jitter = min(self.retry_after_jitter_s, retry_after_s / 10)
            return retry_after_s + rng.uniform(0.0, jitter)
        backoff = min(self.max_delay_s, self.base_delay_s * (2.0 ** max(retry_index, 0)))
        return rng.uniform(backoff / 2.0, backoff)

    def allows_retry_after(self, retry_after_s: float | None) -> bool:
        return retry_after_s is None or retry_after_s <= self.max_retry_after_s


def parse_retry_after(
    headers: Mapping[str, str] | None, *, now: float | None = None
) -> float | None:
    """Seconds requested by ``retry-after-ms`` / ``retry-after`` (seconds or HTTP date)."""
    if headers is None:
        return None
    for name, divisor in (("retry-after-ms", 1000.0), ("retry-after", 1.0)):
        raw = _header(headers, name)
        if raw is None:
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        if math.isfinite(value) and value >= 0:
            return value / divisor
    raw = _header(headers, "retry-after")
    if raw is None:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        return None
    if parsed is None or parsed.tzinfo is None:
        return None
    current = time.time() if now is None else now
    return max(0.0, parsed.timestamp() - current)


def _header(headers: Mapping[str, str], name: str) -> str | None:
    value = headers.get(name)
    if value is None:
        lowered = {key.lower(): item for key, item in headers.items()}
        value = lowered.get(name)
    if value is None:
        return None
    value = str(value).strip()
    return value or None
