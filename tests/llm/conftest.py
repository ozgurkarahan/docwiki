"""Fixtures for the docwiki.llm tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx2
import pytest
from llm_testkit import TEST_ENDPOINT, FakeTime, Script, StaticCredential

from docwiki.llm import FoundryLlmClient, LlmSettings, RetryPolicy, UsageLedger


@pytest.fixture
def fake_time() -> FakeTime:
    return FakeTime()


@pytest.fixture
def credential() -> StaticCredential:
    return StaticCredential()


@pytest.fixture
def settings() -> LlmSettings:
    return LlmSettings(
        project_endpoint=TEST_ENDPOINT,
        fast_deployment="fast-deployment",
        smart_deployment="smart-deployment",
    )


@pytest.fixture
async def make_client(
    settings: LlmSettings, credential: StaticCredential, fake_time: FakeTime
) -> AsyncIterator[Callable[..., FoundryLlmClient]]:
    """FoundryLlmClient wired to a Script through the real AIProjectClient/OpenAI SDK path."""
    clients: list[FoundryLlmClient] = []

    def factory(script: Script, **overrides: Any) -> FoundryLlmClient:
        options: dict[str, Any] = {
            "credential": credential,
            "http_client": httpx2.AsyncClient(transport=httpx2.MockTransport(script)),
            "clock": fake_time.clock,
            "sleep": fake_time.sleep,
            "retry_policy": RetryPolicy(),
            "ledger": UsageLedger(),
        }
        options.update(overrides)
        client_settings = options.pop("settings", settings)
        client = FoundryLlmClient(client_settings, **options)
        clients.append(client)
        return client

    yield factory
    for client in clients:
        await client.aclose()
