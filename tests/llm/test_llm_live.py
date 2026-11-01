"""Live smoke test against a real Foundry deployment (excluded by default; run `pytest -m live`).

Requires DOCWIKI_FOUNDRY_PROJECT_ENDPOINT and DOCWIKI_FAST_DEPLOYMENT (DOCWIKI_EMBED_DEPLOYMENT for
the embedding check), plus an identity that DefaultAzureCredential can use (`az login` locally) with
the Azure AI User role on the project.
"""

from __future__ import annotations

import os

import pytest
from pydantic import BaseModel

from docwiki.llm import FoundryEmbeddingClient, FoundryLlmClient, LlmSettings, build_embed_input

REQUIRED = ("DOCWIKI_FOUNDRY_PROJECT_ENDPOINT", "DOCWIKI_FAST_DEPLOYMENT")

pytestmark = pytest.mark.live
needs_fast = pytest.mark.skipif(
    any(not os.environ.get(name) for name in REQUIRED),
    reason="set DOCWIKI_FOUNDRY_PROJECT_ENDPOINT and DOCWIKI_FAST_DEPLOYMENT to run",
)
needs_embed = pytest.mark.skipif(
    not os.environ.get("DOCWIKI_FOUNDRY_PROJECT_ENDPOINT")
    or not os.environ.get("DOCWIKI_EMBED_DEPLOYMENT"),
    reason="set DOCWIKI_FOUNDRY_PROJECT_ENDPOINT and DOCWIKI_EMBED_DEPLOYMENT to run",
)


class LiveCheck(BaseModel):
    status: str
    count: int


@needs_fast
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


@needs_embed
async def test_live_embedding_call_returns_unit_vectors_and_prices_them() -> None:
    texts = [
        build_embed_input("Kestrel", "Torque", "Tighten the flange bolts in a star pattern.").text,
        build_embed_input(None, None, "Comment serrer les boulons de bride ?").text,
    ]
    async with FoundryEmbeddingClient(LlmSettings.from_env()) as client:
        info = await client.describe()
        result = await client.embed(texts, "document", "embed-input-v1", {"stage": "live-test"})
        receipt = client.ledger.receipt()

    assert info.model_name and info.model_name.startswith("text-embedding-3")
    assert len(result.vectors) == 2
    assert all(len(vector) == client.dimensions for vector in result.vectors)
    assert all(abs(sum(v * v for v in vector) - 1.0) < 1e-3 for vector in result.vectors)
    assert result.usage.input_tokens > 0 and result.origin == "foundry"
    assert receipt.totals.calls == 1 and receipt.totals.failed_calls == 0
    assert receipt.lines[0].tier == "embed"