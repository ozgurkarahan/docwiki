"""Evaluation switches are isolated from the production server and the raw ablation."""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import threading
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from mcp_testkit import (
    FIXTURE_ROOT,
    MINUTES,
    NOW,
    PLAN_A,
    PLAN_B,
    RELEASE_ID,
    TOPIC_ID,
    copy_fixture,
    load_builder,
    stage_release,
    tool_payload,
)

from docwiki.contracts.catalog import catalog_page_for
from docwiki.contracts.storage import FolderStorage
from docwiki.llm.embed_input import EMBED_INPUT_VERSION, build_embed_input
from docwiki.llm.embeddings import FakeEmbeddingClient
from docwiki.mcp.config import McpConfig
from docwiki.mcp.dense import (
    QUERY_INPUT_VERSION,
    DenseLane,
    fuse,
    hit_key,
    index_rows,
)
from docwiki.mcp.server import build_server, make_source
from docwiki.mcp.source import FolderReleaseSource, ReleaseUnavailableError, StorageReleaseSource
from docwiki.mcp.tools_read import ReadTools, ToolInputError
from docwiki.release import ReleaseWriter, publish_release
from mcp import Client

_spec = importlib.util.spec_from_file_location(
    "build_eval_vectors", Path(__file__).resolve().parents[2] / "scripts" / "build_eval_vectors.py"
)
assert _spec and _spec.loader
_builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_builder)
build_vectors = _builder.build_vectors


@pytest.mark.parametrize(
    ("tool", "digest"),
    [
        ("answer_context", "155fe332bb12d5eb61848752a0a1ac68b5acb0e0ad3631d3e2e967bba7eb67c3"),
        ("search", "f5b3eb5280f739929757dedc9ac43bd3ffda84c0d57f12b644623744f7687ef6"),
    ],
)
@pytest.mark.parametrize("explicit_off", [False, True])
def test_off_is_byte_identical_to_pre_change_baseline(
    tool: str,
    digest: str,
    explicit_off: bool,
) -> None:
    # Digests captured from the unmodified public/main implementation on this fixture.
    env = {"DOCWIKI_MCP_VECTORS": "not-opened.npz"}
    if explicit_off:
        env.update(DOCWIKI_MCP_DENSE="off", DOCWIKI_MCP_SUPERSESSION_COMPANIONS="off")
    config = McpConfig.from_env(env)

    def forbidden() -> Any:
        pytest.fail("off must not construct an embedding client")

    reads = ReadTools(FolderReleaseSource(FIXTURE_ROOT), config, embedding_factory=forbidden)
    assert hashlib.sha256(getattr(reads, tool)("menuiseries").encode()).hexdigest() == digest


def test_config_validation() -> None:
    config = McpConfig.from_env(
        {
            "DOCWIKI_MCP_PIN_RELEASE": RELEASE_ID,
            "DOCWIKI_MCP_DENSE": "on",
            "DOCWIKI_MCP_VECTORS": "vectors.npz",
            "DOCWIKI_MCP_SUPERSESSION_COMPANIONS": "on",
        }
    )
    assert config.pin_release == RELEASE_ID and config.dense and config.supersession_companions
    for env in (
        {"DOCWIKI_MCP_PIN_RELEASE": "../current.json"},
        {"DOCWIKI_MCP_DENSE": "on"},
        {"DOCWIKI_MCP_DENSE": "yes"},
        {"DOCWIKI_MCP_SUPERSESSION_COMPANIONS": "yes"},
    ):
        with pytest.raises(ValueError):
            McpConfig.from_env(env)


@pytest.mark.parametrize("storage_mode", [False, True])
def test_pin_ignores_pointer_and_works_without_one(tmp_path: Path, storage_mode: bool) -> None:
    root = copy_fixture(tmp_path / "releases-root")
    remote = FolderStorage(root, fsync=False)
    staged = stage_release(tmp_path / "staged", created_at=NOW + timedelta(days=1))
    publish_release(remote, staged)
    (root / "releases" / "current.json").unlink()
    if storage_mode:
        source = StorageReleaseSource(remote, tmp_path / "cache", pin_release=RELEASE_ID, ttl_s=0)
    else:
        source = make_source(root, McpConfig(pin_release=RELEASE_ID, pointer_ttl_s=0))
    assert source.current().release_id == RELEASE_ID
    (root / "releases" / "current.json").write_text("broken pointer", encoding="utf-8")
    source.invalidate()
    reads = ReadTools(source, McpConfig())
    assert json.loads(reads.search("menuiseries"))["release_id"] == RELEASE_ID
    assert source.last_error is None


def test_pin_direct_folder_and_missing_release(tmp_path: Path) -> None:
    direct = FIXTURE_ROOT / "releases" / RELEASE_ID
    assert make_source(direct, McpConfig(pin_release=RELEASE_ID)).current().release_id == RELEASE_ID
    missing = "20990101T000000Z-00000000"
    for source in (
        FolderReleaseSource(direct, pin_release=missing),
        FolderReleaseSource(FIXTURE_ROOT, pin_release=missing),
        StorageReleaseSource(FolderStorage(FIXTURE_ROOT), tmp_path / "cache", pin_release=missing),
    ):
        with pytest.raises(ReleaseUnavailableError, match="pinned release"):
            source.current()


@pytest.fixture
def vectors(tmp_path: Path) -> Path:
    out = tmp_path / "vectors.npz"
    asyncio.run(build_vectors(FIXTURE_ROOT, out, FakeEmbeddingClient(dimensions=4)))
    return out


def hybrid(source: Any, vectors: Path, **changes: Any) -> ReadTools:
    return ReadTools(
        source,
        McpConfig(dense=True, vectors=str(vectors), **changes),
        embedding_factory=lambda: FakeEmbeddingClient(dimensions=4),
    )


def rewrite_artifact(path: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    with np.load(path, allow_pickle=False) as artifact:
        parts = {key: artifact[key] for key in artifact.files}
    mutate(parts)
    with path.open("wb") as stream:
        np.savez(stream, **parts)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("format", "unknown"),
        ("release_id", "20990101T000000Z-00000000"),
        ("input_version", "embed-input-v0"),
        ("search_sha256", "0" * 64),
        ("dimensions", 5),
        ("model", ""),
    ],
)
def test_artifact_metadata_mismatch_is_loud(
    source: FolderReleaseSource,
    vectors: Path,
    field: str,
    value: Any,
) -> None:
    def mutate(parts: dict[str, Any]) -> None:
        metadata = json.loads(str(parts["metadata"].item()))
        metadata[field] = value
        parts["metadata"] = np.asarray(json.dumps(metadata))

    rewrite_artifact(vectors, mutate)
    reads = hybrid(source, vectors)
    with pytest.raises(ToolInputError) as raised:
        reads.search("menuiseries")
    assert raised.value.code == "unavailable"
    assert isinstance(raised.value.__cause__, ValueError)
    assert field in str(raised.value.__cause__)


@pytest.mark.parametrize("field", ["rows", "rowids", "matrix", "dtype", "norm", "finite"])
def test_artifact_rows_and_vectors_are_validated(
    source: FolderReleaseSource,
    vectors: Path,
    field: str,
) -> None:
    def mutate(parts: dict[str, Any]) -> None:
        if field == "rows":
            keys = json.loads(str(parts["rows"].item()))
            keys[0][2] = "incorrect.md"
            parts["rows"] = np.asarray(json.dumps(keys))
        elif field == "rowids":
            parts["rowids"][0] += 1000
        elif field == "matrix":
            parts["matrix"] = parts["matrix"][:-1]
        elif field == "dtype":
            parts["matrix"] = parts["matrix"].astype(np.float64)
        else:
            parts["matrix"][0, :] = 0 if field == "norm" else np.nan

    rewrite_artifact(vectors, mutate)
    with pytest.raises(ValueError, match="vector artifact"):
        DenseLane(source.current(), source, McpConfig(vectors=str(vectors)), FakeEmbeddingClient)


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (lambda: FakeEmbeddingClient(dimensions=4, model="other-model"), "model mismatch"),
        (lambda: FakeEmbeddingClient(dimensions=5), "dimensions mismatch"),
    ],
)
def test_live_embedding_identity_must_match(
    source: FolderReleaseSource,
    vectors: Path,
    factory: Callable[..., Any],
    message: str,
) -> None:
    reads = ReadTools(
        source, McpConfig(dense=True, vectors=str(vectors)), embedding_factory=factory
    )
    with pytest.raises(ToolInputError) as raised:
        reads.answer_context("menuiseries")
    assert raised.value.code == "unavailable"
    assert message in str(raised.value.__cause__)


def test_hybrid_uses_gate_a_fusion_and_recovers_nonlexical_hits(
    source: FolderReleaseSource,
    vectors: Path,
) -> None:
    reads = hybrid(source, vectors, max_chars=100000)
    snap = source.current()
    query = "zzzxqvvv"
    assert not snap.search.search(query)
    result = json.loads(reads.search(query, limit=50))
    assert result["hits"] and result["release_id"] == RELEASE_ID
    assert result["retrieval"] == {"mode": "hybrid", "rrf_k": 60, "lane_depth": 50}
    context = json.loads(reads.answer_context(query))
    assert context["hits"] and context["retrieval"]["mode"] == "hybrid"

    query = "menuiseries"
    lane = DenseLane(
        snap, source, McpConfig(vectors=str(vectors)), lambda: FakeEmbeddingClient(dimensions=4)
    )
    lexical = snap.search.search(query, limit=50)
    dense = lane.search(query, accept=lambda _: True)
    expected = fuse(lexical, dense)
    actual = json.loads(reads.search(query, limit=50))["hits"]
    assert [(h["path"], h["anchor"], h.get("locator_key"), h["score"]) for h in actual] == [
        (h.path, h.anchor, h.locator_key, h.score) for h in expected[:50]
    ]
    assert len({hit_key(h) for h in expected}) == len(expected)
    # A row ranked second in both lanes beats either lane's unique first row.
    a, b, c = lexical[:3]
    assert hit_key(fuse([a, b], [c, b])[0]) == hit_key(b)


@pytest.mark.parametrize("raw", [False, True])
def test_dense_respects_scope_kinds_and_audience(tmp_path: Path, raw: bool) -> None:
    root = copy_fixture(tmp_path / "mock")
    staged = stage_release(
        tmp_path / "staged",
        created_at=NOW,
        scopes={PLAN_A: "moreau", PLAN_B: "moreau", MINUTES: "entreprise"},
    )
    publish_release(FolderStorage(root, fsync=False), staged)
    out = tmp_path / "vectors.npz"
    asyncio.run(build_vectors(root, out, FakeEmbeddingClient(dimensions=4)))
    source = FolderReleaseSource(root)
    reads = hybrid(source, out, wiki_ablation="raw" if raw else "off", supersession_companions=True)
    result = json.loads(reads.search("zzzxqvvv", within="moreau", limit=50))
    assert result["hits"] and {h["source_id"] for h in result["hits"]} <= {PLAN_A, PLAN_B}
    if raw:
        assert all(h["kind"] == "source-block" for h in result["hits"])
        assert all("status" not in h and "revisions" not in h for h in result["hits"])
    else:
        pages = json.loads(
            reads.search("zzzxqvvv", kinds=["page-section"], types=["source"], within="moreau")
        )["hits"]
        assert pages and all(h["kind"] == "page-section" for h in pages)
    # Catalog defence in depth, independently of the indexed row's sensitivity.
    snap = source.current()
    for mapping in (reads._by_id(snap), reads._by_path(snap)):
        for key, entry in list(mapping.items()):
            if entry.id == PLAN_A:
                mapping[key] = entry.model_copy(update={"sensitivity": "restricted"})
    assert all(
        h.get("source_id") != PLAN_A
        for h in json.loads(reads.search("zzzxqvvv", within="moreau", limit=50))["hits"]
    )
    context = json.loads(reads.answer_context("zzzxqvvv", within="moreau"))["hits"]
    assert context and all(h.get("source_id") == PLAN_B for h in context)
    # The dense row-level audience check is independent of catalog metadata.
    lane = DenseLane(
        snap, source, McpConfig(vectors=str(out)), lambda: FakeEmbeddingClient(dimensions=4)
    )
    lane.sensitivity = {rowid: "restricted" for rowid in lane.sensitivity}
    assert not lane.search("zzzxqvvv", accept=lambda _: True)


def test_dense_uses_all_search_index_filters(source: FolderReleaseSource, vectors: Path) -> None:
    reads = hybrid(source, vectors)
    snap = source.current()
    for filters in (
        {"kinds": ["source-block"]},
        {"types": ["source"]},
        {"topic": TOPIC_ID},
        {"entity": ""},
    ):
        if "entity" in filters:
            filters["entity"] = next(p.id for p in snap.catalog.pages if p.type == "entity")
        where, params = snap.search._filters(
            filters.get("kinds"),
            filters.get("types"),
            filters.get("entity"),
            filters.get("topic"),
        )
        eligible = {
            (path, anchor, key)
            for path, anchor, key in snap.search._conn.execute(
                f"SELECT d.path, d.anchor, d.locator_key FROM docs d WHERE 1=1{where}", params
            )
        }
        hits = json.loads(reads.search("zzzxqvvv", limit=50, **filters))["hits"]
        assert hits
        assert {(h["path"], h["anchor"], h.get("locator_key")) for h in hits} <= eligible


@pytest.mark.parametrize("tool", ["search", "answer_context"])
def test_companions_on_off_and_raw(source: FolderReleaseSource, tool: str) -> None:
    for raw, enabled in ((False, False), (False, True), (True, True)):
        reads = ReadTools(
            source,
            McpConfig(supersession_companions=enabled, wiki_ablation="raw" if raw else "off"),
        )
        hits = json.loads(getattr(reads, tool)("indice", limit=10))["hits"]
        if not enabled or raw:
            assert all("revisions" not in hit for hit in hits)
            if raw:
                assert all("status" not in hit for hit in hits)
        else:
            revisions = [r for h in hits for r in h.get("revisions", [])]
            assert any(
                r["source_id"] == PLAN_A and r["relation"] == "supersedes" for r in revisions
            )
            assert any(
                r["source_id"] == PLAN_B and r["relation"] == "superseded_by" for r in revisions
            )
            assert all(
                set(r) == {"source_id", "title", "status", "path", "relation"} for r in revisions
            )


def test_companions_audience_filtered(source: FolderReleaseSource) -> None:
    reads = ReadTools(source, McpConfig(supersession_companions=True))
    snap = source.current()
    by_id = reads._by_id(snap)
    by_id[PLAN_A] = by_id[PLAN_A].model_copy(update={"sensitivity": "restricted"})
    assert reads._revisions(snap, PLAN_B) == []


@pytest.mark.parametrize("failure_method", ["describe", "embed"])
async def test_embedding_failure_is_unavailable_through_mcp(
    source: FolderReleaseSource,
    vectors: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_method: str,
) -> None:
    from docwiki.llm.foundry_embeddings import FoundryEmbeddingClient

    async def fail(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("embedding service failed")

    async def describe(self: Any) -> Any:
        return await FakeEmbeddingClient(dimensions=4).describe()

    monkeypatch.setattr(FoundryEmbeddingClient, "describe", describe)
    monkeypatch.setattr(FoundryEmbeddingClient, failure_method, fail)
    # Avoid live client construction; this still exercises the server's real tool wrappers.
    monkeypatch.setattr(FoundryEmbeddingClient, "__init__", lambda self, *args, **kwargs: None)
    monkeypatch.setattr(FoundryEmbeddingClient, "aclose", FakeEmbeddingClient.aclose)
    server = build_server(source, config=McpConfig(dense=True, vectors=str(vectors)))
    async with Client(server) as client:
        for name, argument in (("search", "query"), ("answer_context", "question")):
            data = tool_payload(await client.call_tool(name, {argument: "menuiseries"}))
            assert data["ok"] is False and data["error"]["code"] == "unavailable"


async def test_dense_async_direct_calls_cache_and_threaded_mcp(
    source: FolderReleaseSource,
    vectors: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from docwiki.llm import foundry_embeddings

    made: list[FakeEmbeddingClient] = []
    threads: list[int] = []

    def factory(*args: Any, **kwargs: Any) -> FakeEmbeddingClient:
        threads.append(threading.get_ident())
        client = FakeEmbeddingClient(dimensions=4)
        made.append(client)
        return client

    reads = ReadTools(
        source, McpConfig(dense=True, vectors=str(vectors)), embedding_factory=factory
    )
    # Direct sync APIs also work when their caller owns an asyncio loop.
    reads.search("menuiseries")
    reads.answer_context("menuiseries")
    assert len(made) == 1 and made[0].requests[0].input_version == QUERY_INPUT_VERSION
    assert threads[0] != threading.get_ident()
    monkeypatch.setattr(foundry_embeddings, "FoundryEmbeddingClient", factory)
    server = build_server(source, config=McpConfig(dense=True, vectors=str(vectors)))
    async with Client(server) as client:
        tools = (await client.list_tools()).tools
        assert any(t.name == "search" and "query" in t.input_schema["properties"] for t in tools)
        for name, arg in (("search", "query"), ("answer_context", "question")):
            data = tool_payload(await client.call_tool(name, {arg: "menuiseries"}))
            assert data["ok"] is True and data["retrieval"]["mode"] == "hybrid"


async def test_builder_uses_gate_a_inputs_and_reports_counts(
    source: FolderReleaseSource, tmp_path: Path
) -> None:
    client = FakeEmbeddingClient(dimensions=4, batch_size=3)
    out = tmp_path / "vectors-without-extension"
    report = await build_vectors(FIXTURE_ROOT, out, client, batch_size=3)
    rows = index_rows(source.current().search)
    assert report["rows"] == len(rows) and report["tokens"] > 0
    assert report["calls"] == (len(rows) + 2) // 3
    assert report["estimated_cost_usd"] == 0 and not report["prices_verified"]
    assert [t for request in client.requests for t in request.texts] == [
        build_embed_input(row["title"], row["section"], row["text"]).text for row in rows
    ]
    assert all(
        r.purpose == "document" and r.input_version == EMBED_INPUT_VERSION for r in client.requests
    )
    with np.load(out, allow_pickle=False) as artifact:
        assert artifact["rowids"].tolist() == [r["rowid"] for r in rows]
        assert artifact["matrix"].dtype == np.float32
        assert np.allclose(np.linalg.norm(artifact["matrix"], axis=1), 1)


async def test_builder_never_writes_inside_release(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path / "mock") / "releases" / RELEASE_ID
    with pytest.raises(ValueError, match="immutable release"):
        await build_vectors(root, root / "search.db", FakeEmbeddingClient(dimensions=4))
    assert FolderReleaseSource(root).current().release_id == RELEASE_ID


def test_missing_artifact_fails_instead_of_falling_back(
    source: FolderReleaseSource,
    tmp_path: Path,
) -> None:
    reads = hybrid(source, tmp_path / "missing.npz")
    with pytest.raises(ToolInputError) as raised:
        reads.answer_context("menuiseries")
    assert raised.value.code == "unavailable"
    assert isinstance(raised.value.__cause__, FileNotFoundError)


def test_artifact_is_revalidated_after_release_swap(
    tmp_path: Path,
    vectors: Path,
) -> None:
    root = copy_fixture(tmp_path / "mock")
    source = FolderReleaseSource(root, ttl_s=0)
    reads = hybrid(source, vectors)
    assert json.loads(reads.search("menuiseries"))["release_id"] == RELEASE_ID
    staged = stage_release(tmp_path / "staged", created_at=NOW)
    publish_release(FolderStorage(root, fsync=False), staged)
    with pytest.raises(ToolInputError) as raised:
        reads.search("menuiseries")
    assert raised.value.code == "unavailable"
    assert "release_id mismatch" in str(raised.value.__cause__)


def test_query_embedding_cache_is_bounded_and_lru(
    source: FolderReleaseSource,
    vectors: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from docwiki.mcp import dense

    monkeypatch.setattr(dense, "QUERY_CACHE_SIZE", 2)
    clients: list[FakeEmbeddingClient] = []

    def factory() -> FakeEmbeddingClient:
        client = FakeEmbeddingClient(dimensions=4)
        clients.append(client)
        return client

    lane = DenseLane(source.current(), source, McpConfig(vectors=str(vectors)), factory)
    for text in ("one", "two", "one", "three", "two"):
        lane.query(text)
    assert len(clients) == 4 and len(lane._queries) == 2
    assert list(lane._queries) == ["three", "two"]


def test_vector_blob_and_azure_pin_use_existing_storage(
    tmp_path: Path,
    vectors: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from docwiki.mcp import blob

    root = copy_fixture(tmp_path / "remote")
    storage = FolderStorage(root, fsync=False)
    storage.write_bytes("work/evals/vectors.npz", vectors.read_bytes())
    calls: list[dict[str, Any]] = []

    def make_blob(account: Any, **kwargs: Any) -> FolderStorage:
        calls.append(kwargs)
        return storage

    monkeypatch.setattr(blob, "AzureBlobStorage", make_blob)
    config = McpConfig(
        mode="azure",
        pin_release=RELEASE_ID,
        dense=True,
        vectors="work/evals/vectors.npz",
        work_container="work-eval",
    )
    source = make_source(None, config, cache_dir=tmp_path / "cache")
    assert isinstance(source, StorageReleaseSource)
    reads = ReadTools(source, config, embedding_factory=lambda: FakeEmbeddingClient(dimensions=4))
    assert json.loads(reads.search("zzzxqvvv"))["hits"]
    assert len(calls) == 1 and calls[0]["containers"]["work"] == "work-eval"
    prefixed = ReadTools(
        source,
        config.with_overrides(vectors="blob:work/evals/vectors.npz"),
        embedding_factory=lambda: FakeEmbeddingClient(dimensions=4),
    )
    assert json.loads(prefixed.answer_context("zzzxqvvv"))["release_id"] == RELEASE_ID


async def test_dense_language_tree_mirrors_fallback_and_raw_blocks(
    source: FolderReleaseSource,
    tmp_path: Path,
) -> None:
    original = source.current()
    writer = ReleaseWriter(
        tmp_path / "multilingual",
        created_at=NOW,
        audience="public",
        versions=original.reader.manifest.versions,
        wiki_languages=["en", "fr"],
    )
    pages = []
    for entry in original.catalog.pages:
        page = original.reader.read_page(entry.path)
        page = page.model_copy(
            update={"frontmatter": page.frontmatter.model_copy(update={"docwiki": writer.stamp})}
        )
        pages.append(page)
        writer.write_page(page)
    canonical = next(p for p in pages if p.frontmatter.id == PLAN_B)
    mirror = canonical.model_copy(
        update={
            "path": f"fr/{canonical.path}",
            "frontmatter": canonical.frontmatter.model_copy(
                update={
                    "lang": "fr",
                    "translation_of": PLAN_B,
                }
            ),
        }
    )
    pages.append(mirror)
    writer.write_page(mirror)
    writer.write_catalog(
        original.catalog.model_copy(
            update={
                "release_id": writer.release_id,
                "wiki_languages": ["en", "fr"],
                "pages": [catalog_page_for(p.frontmatter, p.path) for p in pages],
            }
        )
    )
    titles = {
        p.frontmatter.id: (p.frontmatter.title, p.path)
        for p in pages
        if p.frontmatter.type == "source" and p.frontmatter.translation_of is None
    }
    writer.write_search_db(pages, load_builder()._blocks(titles), [])
    for key in original.reader.manifest.files:
        if key.startswith("evidence/"):
            writer.copy_file(key, original.reader.root / key)
    writer.finalize()
    out = tmp_path / "multilingual.npz"
    await build_vectors(writer.root, out, FakeEmbeddingClient(dimensions=4))
    reads = hybrid(FolderReleaseSource(writer.root), out)
    en = json.loads(reads.search("zzzxqvvv", lang="en", limit=50))["hits"]
    fr = json.loads(reads.search("zzzxqvvv", lang="fr", limit=50))["hits"]
    assert en and fr
    assert all(not h["path"].startswith("fr/") for h in en)
    assert any(h["page_id"] == PLAN_B and h["path"].startswith("fr/") for h in fr)
    assert all(
        h["path"].startswith("fr/")
        for h in fr
        if h["page_id"] == PLAN_B and h["kind"] == "page-section"
    )
    assert any(h["page_id"] == PLAN_A and h["kind"] == "page-section" for h in fr)
    assert any(h["kind"] == "source-block" for h in fr)
