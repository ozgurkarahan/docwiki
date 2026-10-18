from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import BaseModel

from docwiki.llm import CallRecord, FakeLlmClient, LlmUsage, PriceTable, UsageLedger

PRICES = PriceTable.from_mapping(
    {
        "format": "docwiki.llm.prices/v1",
        "currency": "USD",
        "unit": "per_1m_tokens",
        "verified": True,
        "models": {
            "small-model": {"input": 1.0, "cached_input": 0.5, "output": 4.0},
            "large-model": {"input": 10.0, "output": 40.0, "verified": False},
        },
        "deployments": {"fast-dep": "small-model"},
    },
    name="test-prices.yaml",
)


def record(**overrides: object) -> CallRecord:
    values: dict[str, object] = {
        "tier": "fast",
        "deployment": "fast-dep",
        "model": "small-model-2025-01-01",
        "model_version": "2025-01-01",
        "schema_name": "classify",
        "prompt_version": "classify-v1",
        "request_hash": "0" * 64,
        "origin": "foundry",
        "usage": LlmUsage(input_tokens=1_000, output_tokens=100),
        "latency_s": 1.5,
        "metadata": {"stage": "classify"},
    }
    values.update(overrides)
    return CallRecord(**values)  # type: ignore[arg-type]


def test_cost_maths() -> None:
    ledger = UsageLedger(PRICES)
    cost = ledger.record(
        record(
            usage=LlmUsage(
                input_tokens=2_000_000, cached_input_tokens=500_000, output_tokens=250_000
            )
        )
    )
    assert cost == pytest.approx(1.5 * 1.0 + 0.5 * 0.5 + 0.25 * 4.0)


def test_receipt_aggregates_per_tier_deployment_stage_and_prompt() -> None:
    ledger = UsageLedger(PRICES)
    ledger.record(record())
    ledger.record(record(latency_s=2.5, retries=2, wait_s=4.0))
    ledger.record(
        record(ok=False, error="LlmInvalidOutput", attempts=2, usage=LlmUsage(input_tokens=500))
    )
    ledger.record(
        record(
            tier="smart",
            deployment="smart-dep",
            model="large-model-2025-02-02",
            model_version="2025-02-02",
            schema_name="compile",
            prompt_version="compile-v3",
            usage=LlmUsage(input_tokens=10_000, output_tokens=2_000),
            metadata={"stage": "compile"},
        )
    )
    ledger.record(
        record(tier="smart", deployment="mystery-dep", model="unknown-model", metadata={})
    )

    receipt = ledger.receipt()

    assert receipt.format == "docwiki.llm.receipt/v1"
    assert receipt.price_table.name == "test-prices.yaml"
    assert receipt.prices_verified is False
    lines = {(line.tier, line.deployment): line for line in receipt.lines}
    fast = lines[("fast", "fast-dep")]
    assert (fast.calls, fast.failed_calls, fast.retries, fast.attempts) == (3, 1, 2, 4)
    assert fast.input_tokens == 2_500
    assert fast.output_tokens == 200
    assert fast.latency_s == 5.5
    assert fast.max_latency_s == 2.5
    assert fast.wait_s == 4.0
    assert fast.estimated_cost_usd == pytest.approx((2_500 * 1.0 + 200 * 4.0) / 1e6)
    assert fast.priced_as == ["small-model"]
    assert fast.prices_verified is True
    assert fast.models == ["small-model-2025-01-01"]
    assert fast.model_versions == ["2025-01-01"]
    assert fast.origins == {"foundry": 3}
    smart = lines[("smart", "smart-dep")]
    assert smart.priced_as == ["large-model"]
    assert smart.prices_verified is False
    assert smart.estimated_cost_usd == pytest.approx((10_000 * 10.0 + 2_000 * 40.0) / 1e6)
    mystery = lines[("smart", "mystery-dep")]
    assert (mystery.unpriced_calls, mystery.estimated_cost_usd) == (1, 0.0)

    assert receipt.totals.calls == 5
    assert receipt.totals.unpriced_calls == 1
    assert receipt.totals.estimated_cost_usd == pytest.approx(
        fast.estimated_cost_usd + smart.estimated_cost_usd
    )
    assert set(receipt.stages) == {"classify", "compile"}
    assert receipt.stages["classify"].calls == 3
    assert [(p.schema_name, p.prompt_version, p.tier, p.calls) for p in receipt.prompts] == [
        ("classify", "classify-v1", "fast", 3),
        ("classify", "classify-v1", "smart", 1),
        ("compile", "compile-v3", "smart", 1),
    ]


def test_empty_receipt() -> None:
    receipt = UsageLedger(PRICES).receipt()
    assert receipt.lines == []
    assert receipt.totals.calls == 0
    assert receipt.totals.estimated_cost_usd == 0.0
    assert receipt.prices_verified is True


def test_packaged_prices_are_flagged_unverified_in_receipts() -> None:
    ledger = UsageLedger()
    ledger.record(record(deployment="any", model="gpt-4.1-mini-2025-04-14"))
    receipt = ledger.receipt()
    assert receipt.price_table.verified is False
    assert receipt.prices_verified is False
    assert receipt.lines[0].priced_as == ["gpt-4.1-mini"]


def test_receipt_is_plain_json_without_local_paths(tmp_path: Path) -> None:
    path = tmp_path / "prices.custom.yaml"
    path.write_text(
        "format: docwiki.llm.prices/v1\ncurrency: USD\nunit: per_1m_tokens\n"
        "models:\n  small-model:\n    input: 1\n    output: 2\n",
        encoding="utf-8",
    )
    ledger = UsageLedger(PriceTable.load(path))
    ledger.record(record())
    dumped = json.dumps(ledger.receipt().model_dump(mode="json"))
    assert str(tmp_path) not in dumped
    assert "prices.custom.yaml" in dumped


class Label(BaseModel):
    label: str


async def test_clients_feed_the_ledger() -> None:
    ledger = UsageLedger(PRICES)
    client = FakeLlmClient({"label": Label(label="ok")}, ledger=ledger)
    for _ in range(3):
        await client.structured("fast", "Label it.", "text", Label, "label", "label-v1", 50)
    receipt = ledger.receipt()
    assert receipt.totals.calls == 3
    assert receipt.lines[0].deployment == "fake-fast"
    assert receipt.lines[0].origins == {"fake": 3}
    assert receipt.totals.input_tokens == sum(r.usage.input_tokens for r in ledger.records())
