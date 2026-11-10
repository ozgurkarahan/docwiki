"""Search arms (``rag-plus``, ``foundry-iq``) offline: fake LLM, fake Azure AI Search transport."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from evals.corpus import CorpusContext
from evals.registry import get_system
from evals.runner import RunOptions
from evals.systems import RAG_PROMPT_VERSION, RAG_SYSTEM_PROMPT, SystemNotConfigured
from evals.systems_search import (
    DECOMPOSE_PROMPT_VERSION,
    ENV_ENDPOINT,
    ENV_INDEX,
    ENV_KB,
    KNOWLEDGE_API_VERSION,
    SEARCH_API_VERSION,
    FoundryIqSystem,
    IndexedChunk,
    RagPlusSystem,
    SearchClient,
    SearchServiceError,
    chunk_metadata,
    definition_sha256,
    index_chunks,
    index_definition,
    knowledge_base_definition,
    rrf_fuse,
)
from evals_testkit import MAIL, QUOTE, STUDY, question

from docwiki.llm import FakeLlmClient, LlmRequest, PriceTable, UsageLedger

ENDPOINT = "https://search.example.test"
ENV = {
    ENV_ENDPOINT: ENDPOINT,
    ENV_INDEX: "test-index",
    ENV_KB: "test-kb",
    "DOCWIKI_FAST_MODEL": "gpt-test",
    "DOCWIKI_SMART_MODEL": "gpt-test",
}
PRICES = PriceTable.from_mapping(
    {
        "format": "docwiki.llm.prices/v1",
        "currency": "USD",
        "unit": "per_1m_tokens",
        "verified": True,
        "models": {"gpt-test": {"input": 2.0, "output": 8.0, "cached_input": 0.5}},
        "deployments": {"fake-smart": "gpt-test", "fake-fast": "gpt-test", "plan": "gpt-test"},
    }
)


def run(coro: Any) -> Any:
    return asyncio.run(coro)


async def _token() -> str:
    return "test-token"


async def _no_sleep(_: float) -> None:
    return None


class FakeSearchService:
    """In-memory Azure AI Search: index definition, documents, hybrid queries, retrieve."""

    def __init__(self, items: list[IndexedChunk]) -> None:
        self.items = items
        self.requests: list[tuple[str, str, dict[str, Any] | None]] = []
        self.hits: Callable[[str], list[dict[str, Any]]] = lambda query: []
        self.retrieve_payload: dict[str, Any] = {"references": [], "activity": []}
        self.status_for: dict[str, list[int]] = {}
        self.kb: dict[str, Any] = knowledge_base_definition(
            "test-kb",
            "test-ks",
            resource_uri="https://models.example.test",
            deployment="plan",
            model="gpt-test",
        )

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def client(self) -> SearchClient:
        return SearchClient(
            ENDPOINT, token_provider=_token, transport=self.transport(), sleep=_no_sleep
        )

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-token"
        body = json.loads(request.content) if request.content else None
        path = request.url.path
        self.requests.append((request.method, path, body))
        forced = self.status_for.get(path)
        if forced:
            status = forced.pop(0)
            if status != 200:
                return httpx.Response(
                    status,
                    headers={"retry-after": "0"},
                    json={"error": {"code": "Throttled", "message": "slow down"}},
                )
        version = request.url.params["api-version"]
        if path == "/indexes/test-index" and request.method == "GET":
            assert version == SEARCH_API_VERSION
            return httpx.Response(200, json=self._definition())
        if path == "/indexes/test-index/docs/search":
            assert body is not None
            if body["search"] == "*":
                docs = [{"id": item.id, "chunk_sha256": item.chunk_sha256} for item in self.items]
                page = docs[body["skip"] : body["skip"] + body["top"]]
                return httpx.Response(200, json={"value": page})
            assert body["queryType"] == "semantic" and body["vectorQueries"][0]["kind"] == "text"
            return httpx.Response(200, json={"value": self.hits(body["search"])})
        if path == "/knowledgebases/test-kb" and request.method == "GET":
            assert version == KNOWLEDGE_API_VERSION
            return httpx.Response(200, json=self.kb)
        if path == "/knowledgebases/test-kb/retrieve":
            assert version == KNOWLEDGE_API_VERSION
            return httpx.Response(200, json=self.retrieve_payload)
        return httpx.Response(404, json={"error": {"code": "NotFound", "message": "no route"}})

    def _definition(self) -> dict[str, Any]:
        definition = index_definition(
            "test-index",
            resource_uri="https://models.example.test",
            embed_deployment="embed",
            embed_model="text-embedding-3-small",
            dimensions=512,
        )
        definition["@odata.etag"] = '"0x1"'
        return definition


def _items(corpus: CorpusContext) -> list[IndexedChunk]:
    return index_chunks(corpus.docs, corpus.manifest.select("full", "public"))


def _by_path(items: list[IndexedChunk], path: str) -> IndexedChunk:
    return next(item for item in items if item.chunk.path == path)


def _hit(item: IndexedChunk, reranker: float, score: float = 0.5) -> dict[str, Any]:
    return {"id": item.id, "@search.score": score, "@search.rerankerScore": reranker}


# --------------------------------------------------------------------------- index content


def test_chunk_metadata_from_paths() -> None:
    assert chunk_metadata(
        "full/chantiers/moreau/1-marche/works-contract/2026-02-10_contrat-de-travaux-signe.docx"
    ) == ("moreau", "works-contract", "2026-02-10")
    assert chunk_metadata("full/entreprise/price-list/2026-01-08_tarif-2026.xlsx") == (
        "entreprise",
        "price-list",
        "2026-01-08",
    )
    assert chunk_metadata(QUOTE) == ("devis", "devis", None)


def test_index_chunks_are_the_baseline_chunks(corpus: CorpusContext) -> None:
    from evals.systems import BaselineRagSystem

    items = _items(corpus)
    baseline = BaselineRagSystem(docs=corpus.docs, files=corpus.manifest.select())
    baseline.build_index()
    assert [item.chunk for item in items] == baseline.chunks
    assert len({item.id for item in items}) == len(items)
    assert STUDY not in {item.chunk.path for item in items}
    quote = _by_path(items, QUOTE)
    assert quote.id.startswith(quote.chunk.sha256[:16]) and quote.id.endswith("-0000")
    doc = quote.document([0.1, 0.2])
    assert doc["locator_keys"] == list(quote.chunk.keys) and doc["vector"] == [0.1, 0.2]
    assert doc["header"].startswith(quote.chunk.title) and "undated" in doc["header"]
    assert "vector" not in quote.document()


def test_index_definition_and_stable_hash() -> None:
    definition = index_definition(
        "a",
        resource_uri="https://x.example.test",
        embed_deployment="e",
        embed_model="m",
        dimensions=8,
    )
    vector = next(field for field in definition["fields"] if field["name"] == "vector")
    assert vector["dimensions"] == 8 and vector["retrievable"] is False
    vectorizer = definition["vectorSearch"]["vectorizers"][0]
    assert (
        vectorizer["kind"] == "azureOpenAI" and "apiKey" not in vectorizer["azureOpenAIParameters"]
    )
    assert definition["semantic"]["configurations"][0]["prioritizedFields"]["titleField"] == {
        "fieldName": "title"
    }
    other = index_definition(
        "b",
        resource_uri="https://y.example.test",
        embed_deployment="e",
        embed_model="m",
        dimensions=8,
    )
    other["@odata.etag"] = "x"
    assert definition_sha256(definition) == definition_sha256(other)  # name, endpoint, etag ignored
    other["fields"][0]["sortable"] = False
    assert definition_sha256(definition) != definition_sha256(other)


def test_knowledge_base_is_extractive_with_pinned_effort() -> None:
    kb = knowledge_base_definition(
        "kb", "ks", resource_uri="https://x.example.test", deployment="fast", model="m"
    )
    assert kb["outputMode"] == "extractiveData"
    assert kb["retrievalReasoningEffort"] == {"kind": "low"}
    assert kb["knowledgeSources"] == [{"name": "ks"}]


# ---------------------------------------------------------------------------------- fusion


def test_rrf_fusion() -> None:
    fused = rrf_fuse([["a", "b", "c"], ["b", "d"], ["b", "a", "a"]], k=60)
    assert [doc_id for doc_id, _ in fused] == ["b", "a", "d", "c"]
    assert fused[0][1] == pytest.approx(1 / 62 + 1 / 61 + 1 / 61)
    assert rrf_fuse([["x"], ["y"]]) == [("x", 1 / 61), ("y", 1 / 61)]  # tie: then the id
    assert rrf_fuse([]) == []


# ------------------------------------------------------------------------------- transport


def test_client_retries_throttling_then_maps_errors() -> None:
    service = FakeSearchService([])
    service.status_for["/indexes/test-index"] = [429, 503, 200]
    client = service.client()
    status, payload = run(client.request("GET", "/indexes/test-index", operation="get index"))
    assert status == 200 and payload["name"] == "test-index" and client.retries == 2
    with pytest.raises(SearchServiceError) as caught:
        run(client.request("GET", "/indexes/missing", operation="get index"))
    assert caught.value.status == 404 and caught.value.code == "NotFound"
    assert ENDPOINT not in str(caught.value)
    service.status_for["/indexes/test-index"] = [429] * 10
    with pytest.raises(SearchServiceError, match="HTTP 429"):
        run(client.request("GET", "/indexes/test-index", operation="get index"))
    run(client.aclose())


# -------------------------------------------------------------------------------- rag-plus


def _rag_plus(
    corpus: CorpusContext,
    service: FakeSearchService,
    answer: Any,
    plan: Any,
    env: dict[str, str] | None = None,
) -> tuple[RagPlusSystem, FakeLlmClient]:
    llm = FakeLlmClient(
        {"eval_rag_plus": answer, "eval_rag_plus_decompose": plan}, ledger=UsageLedger(PRICES)
    )
    system = RagPlusSystem(
        docs=corpus.docs,
        files=corpus.manifest.select(),
        llm=llm,
        env=ENV if env is None else env,
        search=service.client(),
    )
    return system, llm


def test_rag_plus_decomposes_fuses_and_answers_like_baseline_rag(corpus: CorpusContext) -> None:
    items = _items(corpus)
    quote, mail = _by_path(items, QUOTE), _by_path(items, MAIL)
    service = FakeSearchService(items)
    service.hits = lambda query: (
        [_hit(mail, 1.0), _hit(quote, 3.5)] if "devis" in query else [_hit(quote, 2.0)]
    )
    seen: list[LlmRequest] = []

    def answer(request: LlmRequest) -> dict[str, Any]:
        seen.append(request)
        return {
            "answer": "44943,60 € including VAT.",
            "citations": [{"chunk_id": "c1"}, {"chunk_id": "[c1]"}, {"chunk_id": "c9"}],
        }

    plan = {"queries": ["devis DEV-2026-014 indice B", "  devis   DEV-2026-014 indice B ", "", "x"]}
    system, llm = _rag_plus(corpus, service, answer, plan)
    run(system.setup())
    result = run(system.answer(question()))

    assert result.info["queries"] == [question().question, "devis DEV-2026-014 indice B", "x"]
    assert [entry["path"] for entry in result.info["retrieved"]] == [QUOTE, MAIL]
    assert result.info["retrieved"][0]["rrf"] > result.info["retrieved"][1]["rrf"]
    assert "text" not in json.dumps(result.info["retrieved"])
    request = seen[0]
    assert request.tier == "smart" and request.prompt_version == RAG_PROMPT_VERSION
    assert request.system == RAG_SYSTEM_PROMPT
    assert f'<passage id="c1" source="{QUOTE}">' in request.text
    decompose = llm.requests[0]
    assert decompose.tier == "fast" and decompose.prompt_version == DECOMPOSE_PROMPT_VERSION
    units = {citation.unit for citation in result.citations}
    assert units == {"c1", "c9"}
    mapped = [citation for citation in result.citations if citation.unit == "c1"]
    assert [citation.locator_key for citation in mapped] == list(quote.chunk.keys)
    assert all(citation.source_path == QUOTE for citation in mapped)
    assert "Sources:\n[1]" in result.text and not result.abstained
    assert result.usage.calls == 2
    costs = result.info["cost_usd"]
    assert costs["semantic_ranker_estimate"] == pytest.approx(3 / 1000)
    assert result.cost_usd == pytest.approx(
        costs["decompose"] + costs["answer"] + costs["semantic_ranker_estimate"], abs=1e-6
    )
    versions = run(system.versions())
    assert versions["decompose_deployment"] == "fake-fast"
    assert versions["index_schema_sha256"] and versions["search_api_version"] == SEARCH_API_VERSION
    assert "test-index" not in json.dumps(versions)
    assert system.config()["chunks"] == len(items)
    run(system.aclose())


def test_rag_plus_caps_sub_queries_and_handles_no_hit(corpus: CorpusContext) -> None:
    service = FakeSearchService(_items(corpus))
    plan = {"queries": [f"q{n}" for n in range(9)]}
    system, llm = _rag_plus(corpus, service, {"answer": "Not found.", "citations": []}, plan)
    run(system.setup())
    result = run(system.answer(question()))
    assert len(result.info["queries"]) == 5  # the question plus at most 4 sub-queries
    assert result.abstained and result.citations == [] and result.info["retrieved"] == []
    assert "(no passage matched the question)" in llm.requests[-1].text


def test_rag_plus_refuses_a_stale_index(corpus: CorpusContext) -> None:
    items = _items(corpus)
    service = FakeSearchService(items[:-1])
    system, _ = _rag_plus(corpus, service, {}, {})
    with pytest.raises(SystemNotConfigured, match="1 missing, 0 extra, 0 changed"):
        run(system.setup())


def test_missing_configuration_and_access(corpus: CorpusContext) -> None:
    service = FakeSearchService(_items(corpus))
    system, _ = _rag_plus(corpus, service, {}, {}, env={})
    with pytest.raises(SystemNotConfigured, match=f"{ENV_ENDPOINT}, {ENV_INDEX}"):
        run(system.setup())
    service.status_for["/indexes/test-index"] = [403]
    system, _ = _rag_plus(corpus, service, {}, {})
    with pytest.raises(SystemNotConfigured, match="HTTP 403"):
        run(system.setup())
    kb_env = {key: value for key, value in ENV.items() if key != ENV_KB}
    iq = FoundryIqSystem(
        docs=corpus.docs,
        files=corpus.manifest.select(),
        llm=FakeLlmClient({}),
        env=kb_env,
        search=service.client(),
    )
    with pytest.raises(SystemNotConfigured, match=ENV_KB):
        run(iq.setup())


# ------------------------------------------------------------------------------ foundry-iq


def test_foundry_iq_maps_references_to_passages(corpus: CorpusContext) -> None:
    items = _items(corpus)
    quote, mail = _by_path(items, QUOTE), _by_path(items, MAIL)
    service = FakeSearchService(items)
    service.retrieve_payload = {
        "response": [{"content": [{"type": "text", "text": "[]"}]}],
        "activity": [
            {"type": "modelQueryPlanning", "id": 0, "inputTokens": 1000, "outputTokens": 100},
            {"type": "searchIndex", "id": 1, "searchIndexArguments": {"search": "quote total"}},
            {"type": "searchIndex", "id": 2, "searchIndexArguments": {"search": "devis TTC"}},
            {"type": "agenticReasoning", "id": 3, "reasoningTokens": 1_000_000},
        ],
        "references": [
            {"type": "searchIndex", "id": "0", "docKey": mail.id, "rerankerScore": 2.1},
            {"type": "searchIndex", "id": "1", "docKey": quote.id, "rerankerScore": 3.4},
            {"type": "searchIndex", "id": "2", "docKey": "unknown-0000", "rerankerScore": 3.0},
        ],
    }
    llm = FakeLlmClient(
        {"eval_foundry_iq": {"answer": "44943,60 €.", "citations": [{"chunk_id": "c1"}]}},
        ledger=UsageLedger(PRICES),
    )
    system = FoundryIqSystem(
        docs=corpus.docs, files=corpus.manifest.select(), llm=llm, env=ENV, search=service.client()
    )
    run(system.setup())
    result = run(system.answer(question()))
    body = next(body for method, path, body in service.requests if path.endswith("/retrieve"))
    assert body["outputMode"] == "extractiveData" and body["maxOutputDocuments"] == 8
    assert body["retrievalReasoningEffort"] == {"kind": "low"}
    assert body["knowledgeSourceParams"][0]["knowledgeSourceName"] == "test-ks"
    assert [entry["path"] for entry in result.info["retrieved"]] == [QUOTE, MAIL]
    assert result.info["unknown_ids"] == 1 and result.info["search_activities"] == 2
    assert result.info["planned_queries"] == ["quote total", "devis TTC"]
    assert {citation.source_path for citation in result.citations} == {QUOTE}
    costs = result.info["cost_usd"]
    assert costs["agentic_reasoning_estimate"] == pytest.approx(0.022)
    assert costs["query_planning"] == pytest.approx((1000 * 2.0 + 100 * 8.0) / 1_000_000)
    assert result.usage.calls == 2 and result.usage.input_tokens > 1000
    versions = run(system.versions())
    assert versions["reasoning_effort"] == "low" and versions["kb_name_sha256"]
    assert versions["knowledge_api_version"] == KNOWLEDGE_API_VERSION
    assert "test-kb" not in json.dumps(versions)
    run(system.aclose())


# -------------------------------------------------------------------------------- registry


def test_search_arms_are_registered(corpus: CorpusContext) -> None:
    for name, cls in (("rag-plus", RagPlusSystem), ("foundry-iq", FoundryIqSystem)):
        spec = get_system(name)
        assert spec.indexes_documents
        options = RunOptions(system=name, questions=None, env=ENV)  # type: ignore[arg-type]
        system = spec.factory(options, corpus)
        assert isinstance(system, cls) and system.name == name and system.top_k == 8
