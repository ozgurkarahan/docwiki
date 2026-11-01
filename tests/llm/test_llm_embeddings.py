"""Embedding client tests: length rule, fake, record/replay, Foundry path, ledger, settings."""

from __future__ import annotations

import json
import logging
import math
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import httpx2
import pytest
from llm_testkit import TEST_ENDPOINT, FakeTime, Script, StaticCredential, status_error

from docwiki.contracts.runs import LlmUsage as ContractLlmUsage
from docwiki.llm import (
    EMBED_INPUT_MAX_CHARS,
    EMBED_INPUT_VERSION,
    EmbeddingClient,
    EmbedRequest,
    FakeEmbeddingClient,
    FoundryEmbeddingClient,
    LlmAuthError,
    LlmConfigurationError,
    LlmRateLimited,
    LlmReplayMissing,
    LlmServiceError,
    LlmSettings,
    PriceTable,
    RecordingEmbeddingClient,
    ReplayEmbeddingClient,
    RetryPolicy,
    UsageLedger,
    build_embed_input,
    create_embedding_client,
    fake_vector,
)
from docwiki.llm.embeddings import embed_fixture_path

SECRET_TEXT = "Kestrel turbine torque note"


def _norm(vector: tuple[float, ...]) -> float:
    return math.sqrt(sum(value * value for value in vector))


# ---------------------------------------------------------------------- embed-input-v1


def test_embed_input_joins_title_section_and_normalised_body() -> None:
    shaped = build_embed_input(" Title\t one ", "Section\ntwo", "a  \t b\r\n\r\n\r\n\r\nc\rd")
    assert shaped.text == "Title one\nSection two\n\na b\n\nc\nd"
    assert shaped.truncated is False
    assert shaped.version == EMBED_INPUT_VERSION == "embed-input-v1"


def test_embed_input_skips_missing_parts_and_refuses_empty_rows() -> None:
    assert build_embed_input(None, None, "body").text == "body"
    assert build_embed_input("Title", None, None).text == "Title"
    with pytest.raises(ValueError, match="non-empty"):
        build_embed_input(" ", None, "\n\n")


def test_embed_input_cuts_deterministically_on_a_word_boundary() -> None:
    body = " ".join(f"word{index:05d}" for index in range(2_000))
    first = build_embed_input("Title", "Section", body)
    second = build_embed_input("Title", "Section", body)
    assert first == second
    assert first.truncated is True
    assert first.original_chars > EMBED_INPUT_MAX_CHARS
    assert len(first.text) <= EMBED_INPUT_MAX_CHARS
    assert first.text.split()[-1].startswith("word") and len(first.text.split()[-1]) == 9


def test_embed_input_hard_cuts_text_without_whitespace() -> None:
    shaped = build_embed_input(None, None, "x" * 9_000)
    assert shaped.truncated is True
    assert shaped.text == "x" * EMBED_INPUT_MAX_CHARS


# ---------------------------------------------------------------------- request and validation


def test_request_hash_covers_purpose_version_dimensions_and_normalises_newlines() -> None:
    def digest(text: str, purpose: Any, version: str, dimensions: int) -> str:
        return EmbedRequest.build([text], purpose, version, dimensions).request_hash

    base = EmbedRequest.build(["a\nb"], "document", "embed-input-v1", 512)
    assert base.request_hash == digest("a\r\nb", "document", "embed-input-v1", 512)
    assert base.request_hash != digest("a\nb", "query", "embed-input-v1", 512)
    assert base.request_hash != digest("a\nb", "document", "embed-input-v2", 512)
    assert base.request_hash != digest("a\nb", "document", "embed-input-v1", 256)
    assert base.schema_name == "embed-document"


@pytest.mark.parametrize(
    ("texts", "purpose", "version", "error"),
    [
        ([], "document", "embed-input-v1", ValueError),
        (["ok", " "], "document", "embed-input-v1", ValueError),
        (["x" * (EMBED_INPUT_MAX_CHARS + 1)], "document", "embed-input-v1", ValueError),
        (["ok"], "summary", "embed-input-v1", ValueError),
        (["ok"], "query", "bad version!", ValueError),
        ("ok", "query", "embed-input-v1", TypeError),
        ([1], "query", "embed-input-v1", TypeError),
    ],
)
async def test_embed_rejects_bad_input_before_any_call(
    texts: Any, purpose: Any, version: str, error: type[Exception]
) -> None:
    client = FakeEmbeddingClient()
    with pytest.raises(error):
        await client.embed(texts, purpose, version)
    assert client.requests == []
    assert client.ledger.receipt().totals.calls == 0


# ---------------------------------------------------------------------- fake client


async def test_fake_client_is_deterministic_unit_length_and_batched() -> None:
    ledger = UsageLedger(PriceTable.load(None))
    client = FakeEmbeddingClient(batch_size=2, ledger=ledger)
    assert isinstance(client, EmbeddingClient)
    texts = ["alpha", "beta", "gamma", "alpha"]
    result = await client.embed(texts, "document", "embed-input-v1", {"stage": "vectors"})

    assert result.calls == 2 and len(result.request_hashes) == 2
    assert len(result.vectors) == 4 and result.dimensions == 512
    assert all(len(vector) == 512 for vector in result.vectors)
    assert all(abs(_norm(vector) - 1.0) < 1e-9 for vector in result.vectors)
    assert result.vectors[0] == result.vectors[3] == fake_vector("alpha", 512)
    assert result.vectors[0] != result.vectors[1]
    assert result.origin == "fake" and result.purpose == "document"

    receipt = ledger.receipt()
    assert [(line.tier, line.calls) for line in receipt.lines] == [("embed", 2)]
    assert receipt.stages["vectors"].calls == 2
    assert [(p.schema_name, p.prompt_version, p.tier) for p in receipt.prompts] == [
        ("embed-document", "embed-input-v1", "embed")
    ]
    assert receipt.totals.output_tokens == 0


async def test_fake_client_dimensions_follow_the_settings() -> None:
    client = FakeEmbeddingClient(dimensions=8)
    result = await client.embed(["one"], "query", "embed-input-v1")
    assert len(result.vectors[0]) == 8
    info = await client.describe()
    assert info.dimensions == 8 and info.source == "fake"


async def test_logs_and_spans_never_carry_the_embedded_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG, logger="docwiki.llm")
    client = FakeEmbeddingClient()
    await client.embed([SECRET_TEXT], "query", "embed-input-v1")
    assert caplog.records, "the call must be logged"
    for record in caplog.records:
        assert SECRET_TEXT not in record.getMessage()
        assert SECRET_TEXT not in json.dumps(getattr(record, "docwiki_llm", {}), default=str)


# ---------------------------------------------------------------------- record / replay


async def test_record_then_replay_round_trip(tmp_path: Path) -> None:
    recorder = RecordingEmbeddingClient(FakeEmbeddingClient(batch_size=2), tmp_path)
    recorded = await recorder.embed(["a", "b", "c"], "document", "embed-input-v1")
    assert len(recorder.recorded) == 2
    assert all(path.parent.name == "embed-document" for path in recorder.recorded)

    replay = ReplayEmbeddingClient(tmp_path, batch_size=2)
    replayed = await replay.embed(["a", "b", "c"], "document", "embed-input-v1")
    assert replayed.vectors == recorded.vectors
    assert replayed.origin == "replay"
    assert replayed.request_hashes == recorded.request_hashes
    assert replay.ledger.receipt().lines[0].origins == {"replay": 2}


async def test_replay_missing_batch_explains_the_batch_size(tmp_path: Path) -> None:
    recorder = RecordingEmbeddingClient(FakeEmbeddingClient(batch_size=2), tmp_path)
    await recorder.embed(["a", "b", "c"], "document", "embed-input-v1")
    replay = ReplayEmbeddingClient(tmp_path, batch_size=3)
    with pytest.raises(LlmReplayMissing, match="batch size 3") as caught:
        await replay.embed(["a", "b", "c"], "document", "embed-input-v1")
    assert caught.value.tier == "embed"
    assert replay.ledger.receipt().totals.failed_calls == 1


async def test_replay_refuses_an_edited_fixture(tmp_path: Path) -> None:
    recorder = RecordingEmbeddingClient(FakeEmbeddingClient(), tmp_path)
    await recorder.embed(["a"], "query", "embed-input-v1")
    path = recorder.recorded[0]
    data = json.loads(path.read_text(encoding="utf-8"))
    data["request"]["texts"] = ["tampered"]
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LlmConfigurationError, match="request hash"):
        await ReplayEmbeddingClient(tmp_path).embed(["a"], "query", "embed-input-v1")


async def test_replay_checks_recorded_vector_sizes(tmp_path: Path) -> None:
    request = EmbedRequest.build(["a"], "query", "embed-input-v1", 4)
    recorder = RecordingEmbeddingClient(FakeEmbeddingClient(dimensions=4), tmp_path)
    await recorder.embed(["a"], "query", "embed-input-v1")
    path = embed_fixture_path(tmp_path, request)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["vectors"] = [[0.5, 0.5]]
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LlmServiceError, match="2 dimensions"):
        await ReplayEmbeddingClient(tmp_path, dimensions=4).embed(["a"], "query", "embed-input-v1")


# ---------------------------------------------------------------------- Foundry client


def embeddings_body(
    count: int,
    dimensions: int,
    *,
    order: list[int] | None = None,
    model: str = "text-embedding-3-small",
    prompt_tokens: int = 12,
) -> dict[str, Any]:
    indexes = order if order is not None else list(range(count))
    return {
        "object": "list",
        "data": [
            {"object": "embedding", "index": index, "embedding": [float(index + 1)] * dimensions}
            for index in indexes
        ],
        "model": model,
        "usage": {"prompt_tokens": prompt_tokens, "total_tokens": prompt_tokens},
    }


def embed_ok(count: int, dimensions: int = 4, **kwargs: Any) -> httpx2.Response:
    return httpx2.Response(200, json=embeddings_body(count, dimensions, **kwargs))


@pytest.fixture
def embed_settings() -> LlmSettings:
    return LlmSettings(
        project_endpoint=TEST_ENDPOINT,
        embed_deployment="embed-deployment",
        embed_dimensions=4,
        embed_batch_size=2,
    )


@pytest.fixture
async def make_embedder(
    embed_settings: LlmSettings, credential: StaticCredential, fake_time: FakeTime
) -> AsyncIterator[Callable[..., FoundryEmbeddingClient]]:
    clients: list[FoundryEmbeddingClient] = []

    def factory(script: Script, **overrides: Any) -> FoundryEmbeddingClient:
        options: dict[str, Any] = {
            "credential": credential,
            "http_client": httpx2.AsyncClient(transport=httpx2.MockTransport(script)),
            "clock": fake_time.clock,
            "sleep": fake_time.sleep,
            "retry_policy": RetryPolicy(),
            "ledger": UsageLedger(PriceTable.load(None)),
        }
        options.update(overrides)
        client = FoundryEmbeddingClient(options.pop("settings", embed_settings), **options)
        clients.append(client)
        return client

    yield factory
    for client in clients:
        await client.aclose()


async def test_foundry_embeds_in_batches_and_prices_the_input_tokens(
    make_embedder: Callable[..., FoundryEmbeddingClient],
) -> None:
    script = Script(
        embed_ok(2, order=[1, 0], prompt_tokens=400_000), embed_ok(1, prompt_tokens=100_000)
    )
    client = make_embedder(script)
    result = await client.embed(["one", "two", "three"], "document", "embed-input-v1")

    assert [request.url.path for request in script.requests] == [
        "/api/projects/demo/openai/v1/embeddings"
    ] * 2
    first = script.bodies[0]
    assert first == {
        "model": "embed-deployment",
        "input": ["one", "two"],
        "dimensions": 4,
        "encoding_format": "float",
    }
    assert result.vectors[0] == (1.0,) * 4 and result.vectors[1] == (2.0,) * 4
    assert result.usage.input_tokens == 500_000
    assert result.model == "text-embedding-3-small"
    assert result.calls == 2 and result.origin == "foundry"

    line = client.ledger.receipt().lines[0]
    assert line.tier == "embed" and line.deployment == "embed-deployment"
    assert line.input_tokens == 500_000 and line.output_tokens == 0
    assert line.priced_as == ["text-embedding-3-small"]
    assert line.estimated_cost_usd == pytest.approx(0.01)


async def test_foundry_retries_rate_limits_then_succeeds(
    make_embedder: Callable[..., FoundryEmbeddingClient],
) -> None:
    script = Script(status_error(429, headers={"retry-after": "2"}), embed_ok(1))
    client = make_embedder(script)
    result = await client.embed(["one"], "query", "embed-input-v1")
    assert result.retries == 1
    assert len(script.requests) == 2


async def test_foundry_rate_limit_exhaustion_surfaces(
    make_embedder: Callable[..., FoundryEmbeddingClient],
) -> None:
    client = make_embedder(Script(status_error(429)), retry_policy=RetryPolicy(max_retries=1))
    with pytest.raises(LlmRateLimited, match="DOCWIKI_EMBED"):
        await client.embed(["one"], "query", "embed-input-v1")
    totals = client.ledger.receipt().totals
    assert totals.failed_calls == 1


async def test_foundry_auth_failure_is_not_retried(
    make_embedder: Callable[..., FoundryEmbeddingClient],
) -> None:
    script = Script(status_error(401))
    client = make_embedder(script)
    with pytest.raises(LlmAuthError) as caught:
        await client.embed(["one"], "query", "embed-input-v1")
    assert len(script.requests) == 1
    assert caught.value.tier == "embed"
    assert caught.value.deployment == "embed-deployment"


async def test_foundry_missing_deployment_names_the_setting(
    make_embedder: Callable[..., FoundryEmbeddingClient],
) -> None:
    client = make_embedder(Script(status_error(404)))
    with pytest.raises(LlmServiceError, match="DOCWIKI_EMBED_DEPLOYMENT"):
        await client.embed(["one"], "query", "embed-input-v1")


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (embeddings_body(1, 4), "indexes"),
        (embeddings_body(2, 4, order=[0, 0]), "indexes"),
        (embeddings_body(2, 3), "3 dimensions"),
    ],
)
async def test_foundry_wrong_vectors_are_service_errors(
    make_embedder: Callable[..., FoundryEmbeddingClient], body: dict[str, Any], message: str
) -> None:
    client = make_embedder(Script(httpx2.Response(200, json=body)))
    with pytest.raises(LlmServiceError, match=message):
        await client.embed(["one", "two"], "document", "embed-input-v1")
    assert client.ledger.receipt().totals.failed_calls == 1


def test_foundry_client_requires_an_embedding_deployment() -> None:
    with pytest.raises(LlmConfigurationError, match="DOCWIKI_EMBED_DEPLOYMENT"):
        FoundryEmbeddingClient(LlmSettings(project_endpoint=TEST_ENDPOINT))


# ---------------------------------------------------------------------- settings and factory


def test_settings_read_the_embedding_environment() -> None:
    settings = LlmSettings.from_env(
        {
            "DOCWIKI_FOUNDRY_PROJECT_ENDPOINT": TEST_ENDPOINT,
            "DOCWIKI_EMBED_DEPLOYMENT": " embed ",
            "DOCWIKI_EMBED_MODEL": "text-embedding-3-small",
            "DOCWIKI_EMBED_DIMENSIONS": "256",
            "DOCWIKI_EMBED_BATCH_SIZE": "16",
            "DOCWIKI_EMBED_TPM": "50_000",
            "DOCWIKI_EMBED_RPM": "60",
        }
    )
    assert settings.embedding_deployment() == "embed"
    assert settings.embed_model == "text-embedding-3-small"
    assert settings.embed_dimensions == 256 and settings.embed_batch_size == 16
    assert settings.embed_rate_limit.tokens_per_minute == 50_000
    assert settings.embed_rate_limit.requests_per_minute == 60


def test_settings_defaults_and_bounds() -> None:
    settings = LlmSettings.from_env({})
    assert settings.embed_dimensions == 512 and settings.embed_batch_size == 64
    with pytest.raises(LlmConfigurationError):
        settings.require_embedding()
    for name, value in (("DOCWIKI_EMBED_DIMENSIONS", "0"), ("DOCWIKI_EMBED_BATCH_SIZE", "5000")):
        with pytest.raises((LlmConfigurationError, ValueError)):
            LlmSettings.from_env({name: value})


def test_factory_builds_replay_and_record_embedding_clients(tmp_path: Path) -> None:
    replay = create_embedding_client(
        LlmSettings(mode="replay", fixtures_dir=tmp_path, embed_batch_size=8)
    )
    assert isinstance(replay, ReplayEmbeddingClient) and replay.batch_size == 8
    record = create_embedding_client(
        LlmSettings(
            mode="record",
            fixtures_dir=tmp_path,
            project_endpoint=TEST_ENDPOINT,
            embed_deployment="embed-deployment",
        )
    )
    assert isinstance(record, RecordingEmbeddingClient)
    with pytest.raises(LlmConfigurationError):
        create_embedding_client(LlmSettings(project_endpoint=TEST_ENDPOINT))


def test_run_report_contract_accepts_the_embed_role() -> None:
    usage = ContractLlmUsage(
        role="embed", deployment="embed-deployment", model="text-embedding-3-small", calls=2
    )
    assert usage.role == "embed" and usage.output_tokens == 0
