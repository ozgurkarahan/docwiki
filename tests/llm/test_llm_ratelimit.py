from __future__ import annotations

import asyncio
import random
from datetime import UTC, datetime
from email.utils import format_datetime

import pytest
from llm_testkit import FakeTime

from docwiki.llm import (
    DeploymentRateLimiter,
    RateLimit,
    RetryPolicy,
    TokenBucket,
    parse_retry_after,
)


def test_token_bucket_refills_continuously() -> None:
    bucket = TokenBucket(capacity=600, refill_per_second=10, now=0.0)
    assert bucket.delay_for(600, now=0.0) == 0.0
    bucket.consume(600, now=0.0)
    assert bucket.delay_for(100, now=0.0) == pytest.approx(10.0)
    assert bucket.delay_for(100, now=4.0) == pytest.approx(6.0)
    assert bucket.available(now=1_000.0) == pytest.approx(600.0)


def test_requests_larger_than_capacity_are_capped() -> None:
    bucket = TokenBucket(capacity=100, refill_per_second=1, now=0.0)
    assert bucket.delay_for(10_000, now=0.0) == 0.0
    bucket.consume(10_000, now=0.0)
    assert bucket.available(now=0.0) == pytest.approx(0.0)


async def test_token_limit_delays_the_next_call(fake_time: FakeTime) -> None:
    limiter = DeploymentRateLimiter(
        "dep",
        RateLimit(tokens_per_minute=600, requests_per_minute=0),
        clock=fake_time.clock,
        sleep=fake_time.sleep,
    )
    assert await limiter.acquire(600) == 0.0
    waited = await limiter.acquire(100)
    assert waited == pytest.approx(10.0)
    assert fake_time.sleeps == [pytest.approx(10.0)]


async def test_request_limit_allows_ten_second_bursts(fake_time: FakeTime) -> None:
    limiter = DeploymentRateLimiter(
        "dep",
        RateLimit(tokens_per_minute=0, requests_per_minute=60),
        clock=fake_time.clock,
        sleep=fake_time.sleep,
    )
    waits = [await limiter.acquire(1) for _ in range(12)]
    assert waits[:10] == [0.0] * 10
    assert waits[10] == pytest.approx(1.0)
    assert waits[11] == pytest.approx(1.0)


async def test_penalize_blocks_every_caller(fake_time: FakeTime) -> None:
    limiter = DeploymentRateLimiter(
        "dep", RateLimit(), clock=fake_time.clock, sleep=fake_time.sleep
    )
    start = fake_time.now
    limiter.penalize(5.0)
    assert limiter.blocked_for() == pytest.approx(5.0)

    async def started_at() -> float:
        await limiter.acquire(10)
        return fake_time.now

    finished = await asyncio.gather(started_at(), started_at())
    assert all(moment >= start + 5.0 for moment in finished)
    assert fake_time.sleeps == [pytest.approx(5.0)]
    assert limiter.blocked_for() == 0.0


async def test_unlimited_limiter_never_waits(fake_time: FakeTime) -> None:
    limiter = DeploymentRateLimiter(
        "dep",
        RateLimit(tokens_per_minute=0, requests_per_minute=0),
        clock=fake_time.clock,
        sleep=fake_time.sleep,
    )
    assert [await limiter.acquire(1_000_000) for _ in range(50)] == [0.0] * 50
    assert fake_time.sleeps == []


def test_parse_retry_after_variants() -> None:
    assert parse_retry_after({"retry-after-ms": "1500", "retry-after": "9"}) == 1.5
    assert parse_retry_after({"Retry-After": "7"}) == 7.0
    assert parse_retry_after({"retry-after": "2.5"}) == 2.5
    assert parse_retry_after({"retry-after": "soon"}) is None
    assert parse_retry_after({}) is None
    assert parse_retry_after(None) is None
    now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    http_date = format_datetime(datetime(2026, 1, 1, 12, 0, 30, tzinfo=UTC), usegmt=True)
    assert parse_retry_after({"retry-after": http_date}, now=now.timestamp()) == pytest.approx(30)


def test_backoff_is_exponential_with_bounded_jitter() -> None:
    policy = RetryPolicy(base_delay_s=1.0, max_delay_s=30.0)
    rng = random.Random(7)
    for index, ceiling in enumerate([1.0, 2.0, 4.0, 8.0, 16.0, 30.0, 30.0]):
        for _ in range(50):
            delay = policy.delay(index, None, rng)
            assert ceiling / 2 <= delay <= ceiling


def test_retry_after_is_honoured_with_small_positive_jitter() -> None:
    policy = RetryPolicy()
    rng = random.Random(3)
    for retry_after in (0.2, 2.0, 30.0):
        for _ in range(50):
            delay = policy.delay(0, retry_after, rng)
            assert retry_after <= delay <= retry_after + min(1.0, retry_after / 10)
    assert policy.allows_retry_after(120.0)
    assert not policy.allows_retry_after(121.0)
    assert policy.allows_retry_after(None)
