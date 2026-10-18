"""Live smoke test against a real Foundry deployment (excluded by default; run `pytest -m live`).

Requires DOCWIKI_FOUNDRY_PROJECT_ENDPOINT and DOCWIKI_FAST_DEPLOYMENT, plus an identity that
DefaultAzureCredential can use (`az login` locally) with the Azure AI User role on the project.
"""

from __future__ import annotations

import os

import pytest
from pydantic import BaseModel

from docwiki.llm import FoundryLlmClient, LlmSettings

REQUIRED = ("DOCWIKI_FOUNDRY_PROJECT_ENDPOINT", "DOCWIKI_FAST_DEPLOYMENT")

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        any(not os.environ.get(name) for name in REQUIRED),
        reason="set DOCWIKI_FOUNDRY_PROJECT_ENDPOINT and DOCWIKI_FAST_DEPLOYMENT to run",
    ),
]


class LiveCheck(BaseModel):
    status: str
    count: int


async def test_live_structured_call_on_the_fast_deployment() -> None:
    async with FoundryLlmClient(LlmSettings.from_env()) as client:
        result = await client.structured(
            "fast",
            "You are a test probe. Answer with the requested JSON object only.",
            "Set status to the word ready and count to the number 3.",
            LiveCheck,
            "live_check",
            "live-check-v1",
            2_000,
            {"stage": "live-test"},
        )
        receipt = client.ledger.receipt()

    assert result.output.count == 3
    assert result.output.status.strip().lower() == "ready"
    assert result.usage.input_tokens > 0
    assert result.usage.output_tokens > 0
    assert result.model
    assert result.origin == "foundry"
    assert receipt.totals.calls == 1
    assert receipt.totals.failed_calls == 0
