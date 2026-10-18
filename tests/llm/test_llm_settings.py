from __future__ import annotations

from pathlib import Path

import pytest

from docwiki.llm import (
    LlmConfigurationError,
    LlmSettings,
    LlmUsage,
    PriceTable,
    RateLimit,
)

ENDPOINT = "https://example.com/api/projects/demo"


def test_defaults_without_environment() -> None:
    settings = LlmSettings.from_env({})
    assert settings.project_endpoint is None
    assert settings.concurrency == 6
    assert settings.max_retries == 3
    assert settings.mode == "foundry"
    assert settings.fast_rate_limit == RateLimit(tokens_per_minute=100_000, requests_per_minute=600)
    assert settings.price_table is None


def test_values_are_read_from_docwiki_variables() -> None:
    settings = LlmSettings.from_env(
        {
            "DOCWIKI_FOUNDRY_PROJECT_ENDPOINT": ENDPOINT + "/",
            "DOCWIKI_FAST_DEPLOYMENT": " fast-dep ",
            "DOCWIKI_SMART_DEPLOYMENT": "smart-dep",
            "DOCWIKI_FAST_MODEL": "gpt-4.1-mini",
            "DOCWIKI_LLM_CONCURRENCY": "3",
            "DOCWIKI_FAST_TPM": "50_000",
            "DOCWIKI_FAST_RPM": "300",
            "DOCWIKI_SMART_TPM": "0",
            "DOCWIKI_LLM_TIMEOUT_SECONDS": "90",
            "DOCWIKI_LLM_MAX_RETRIES": "2",
            "DOCWIKI_LLM_PRICE_TABLE": "prices.local.yaml",
            "DOCWIKI_LLM_MODE": "Replay",
            "DOCWIKI_LLM_FIXTURES": "tests/fixtures/llm",
            "UNRELATED": "ignored",
        }
    )
    assert settings.project_endpoint == ENDPOINT
    assert settings.deployment("fast") == "fast-dep"
    assert settings.deployment("smart") == "smart-dep"
    assert settings.model_for("fast") == "gpt-4.1-mini"
    assert settings.model_for("smart") is None
    assert settings.concurrency == 3
    assert settings.rate_limit("fast") == RateLimit(
        tokens_per_minute=50_000, requests_per_minute=300
    )
    assert settings.rate_limit("smart").tokens_per_minute == 0
    assert settings.timeout_s == 90.0
    assert settings.max_retries == 2
    assert settings.price_table == Path("prices.local.yaml")
    assert settings.mode == "replay"
    assert settings.require_fixtures_dir() == Path("tests/fixtures/llm")


def test_empty_values_count_as_unset() -> None:
    settings = LlmSettings.from_env(
        {"DOCWIKI_FAST_DEPLOYMENT": "  ", "DOCWIKI_LLM_CONCURRENCY": ""}
    )
    assert settings.fast_deployment is None
    assert settings.concurrency == 6


@pytest.mark.parametrize(
    ("environ", "variable"),
    [
        ({"DOCWIKI_LLM_CONCURRENCY": "many"}, "DOCWIKI_LLM_CONCURRENCY"),
        ({"DOCWIKI_LLM_CONCURRENCY": "0"}, "DOCWIKI_LLM_CONCURRENCY"),
        ({"DOCWIKI_FAST_TPM": "-1"}, "DOCWIKI_FAST_TPM"),
        ({"DOCWIKI_LLM_MODE": "live"}, "DOCWIKI_LLM_MODE"),
        ({"DOCWIKI_FOUNDRY_PROJECT_ENDPOINT": "http://insecure.example.com"}, "DOCWIKI_FOUNDRY"),
    ],
)
def test_invalid_values_raise_configuration_errors(environ: dict[str, str], variable: str) -> None:
    with pytest.raises(LlmConfigurationError, match=variable) as raised:
        LlmSettings.from_env(environ)
    assert "insecure.example.com" not in str(raised.value)


def test_missing_deployment_and_endpoint_are_explicit() -> None:
    settings = LlmSettings.from_env({})
    with pytest.raises(LlmConfigurationError, match="DOCWIKI_SMART_DEPLOYMENT"):
        settings.deployment("smart")
    with pytest.raises(LlmConfigurationError, match="DOCWIKI_FOUNDRY_PROJECT_ENDPOINT"):
        settings.require_foundry()
    with pytest.raises(LlmConfigurationError, match="DOCWIKI_LLM_FIXTURES"):
        settings.require_fixtures_dir()


def test_rate_limit_merge_keeps_the_most_restrictive_values() -> None:
    merged = RateLimit(tokens_per_minute=50_000, requests_per_minute=0).merge(
        RateLimit(tokens_per_minute=80_000, requests_per_minute=120)
    )
    assert merged == RateLimit(tokens_per_minute=50_000, requests_per_minute=120)


def test_packaged_price_table_is_marked_unverified() -> None:
    table = PriceTable.packaged()
    assert table.verified is False
    assert table.info.name == "prices.yaml (packaged)"
    assert "placeholder" in table.info.source
    assert len(table.info.sha256) == 64
    assert {"gpt-4.1", "gpt-4.1-mini", "gpt-5-mini"} <= set(table.models)


def test_price_resolution_order_and_prefix_matching() -> None:
    table = PriceTable.from_mapping(
        {
            "format": "docwiki.llm.prices/v1",
            "currency": "USD",
            "unit": "per_1m_tokens",
            "models": {
                "gpt-4.1": {"input": 2.0, "output": 8.0},
                "gpt-4.1-mini": {"input": 0.4, "output": 1.6, "verified": True},
            },
            "deployments": {"docwiki-smart": "gpt-4.1"},
        }
    )
    assert table.model_for_deployment("docwiki-smart") == "gpt-4.1"
    versioned = table.resolve("gpt-4.1-mini-2025-04-14")
    assert versioned is not None and versioned.model_id == "gpt-4.1-mini"
    assert versioned.verified is True
    assert table.resolve(None, "unknown", "GPT-4.1") is not None
    assert table.resolve("gpt-4.10") is None
    assert table.resolve("other-model") is None
    smart = table.resolve("gpt-4.1")
    assert smart is not None and smart.verified is False
    assert smart.cached_input_per_1m == smart.input_per_1m


def test_cost_formula_uses_cached_input_price() -> None:
    table = PriceTable.packaged()
    price = table.resolve("gpt-4.1-mini")
    assert price is not None
    usage = LlmUsage(input_tokens=1_000_000, cached_input_tokens=200_000, output_tokens=500_000)
    expected = (800_000 * 0.40 + 200_000 * 0.10 + 500_000 * 1.60) / 1_000_000
    assert price.cost(usage) == pytest.approx(expected)


def test_custom_price_table_file(tmp_path: Path) -> None:
    path = tmp_path / "prices.custom.yaml"
    path.write_text(
        "format: docwiki.llm.prices/v1\ncurrency: USD\nunit: per_1m_tokens\nverified: true\n"
        "models:\n  my-model:\n    input: 1\n    output: 2\n",
        encoding="utf-8",
    )
    table = PriceTable.load(path)
    assert table.info.name == "prices.custom.yaml"
    assert table.verified is True
    assert table.resolve("my-model") is not None


@pytest.mark.parametrize(
    "content",
    [
        "format: docwiki.llm.prices/v1\ncurrency: EUR\nunit: per_1m_tokens\nmodels: {}\n",
        "format: docwiki.llm.prices/v1\ncurrency: USD\nunit: per_1m_tokens\n"
        "models:\n  m:\n    input: -1\n    output: 1\n",
        "not: [valid",
    ],
)
def test_invalid_price_tables_raise(tmp_path: Path, content: str) -> None:
    path = tmp_path / "prices.yaml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(LlmConfigurationError, match=r"prices\.yaml"):
        PriceTable.load(path)


def test_missing_price_table_raises(tmp_path: Path) -> None:
    with pytest.raises(LlmConfigurationError, match=r"missing\.yaml"):
        PriceTable.load(tmp_path / "missing.yaml")
