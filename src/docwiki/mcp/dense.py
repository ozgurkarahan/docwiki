"""Evaluation-only, immutable-release dense vectors and Gate A reciprocal rank fusion.

The NPZ contains JSON scalars ``metadata`` and ``rows``, int64 ``rowids`` and an N x D
float32 ``matrix``. No pickle, document text, credentials or deployment endpoint is stored.
"""

from __future__ import annotations

import asyncio
import io
import json
import threading
from collections import OrderedDict
from collections.abc import Callable, Coroutine, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np

from docwiki.contracts.enums import allowed_for_audience
from docwiki.contracts.layout import ReleaseFiles
from docwiki.llm.embed_input import EMBED_INPUT_VERSION
from docwiki.llm.embeddings import EmbeddingClient
from docwiki.mcp.config import McpConfig
from docwiki.mcp.source import ReleaseSource, Snapshot, StorageReleaseSource
from docwiki.search.index import SearchHit, SearchIndex

ARTIFACT_FORMAT = "docwiki.eval-vectors/v1"
QUERY_INPUT_VERSION = "query-verbatim-v1"
LANE_DEPTH = 50
RRF_K = 60
QUERY_CACHE_SIZE = 256
ROW_KEY_FIELDS = ("kind", "page_id", "path", "anchor", "source_id", "locator_key")


def index_rows(index: SearchIndex) -> list[dict[str, Any]]:
    """Read every docs row in rowid order, under the search index's connection lock."""
    with index._lock:
        cursor = index._conn.execute("SELECT * FROM docs ORDER BY rowid")
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def row_keys(rows: Sequence[dict[str, Any]]) -> list[list[Any]]:
    return [[row.get(key) for key in ROW_KEY_FIELDS] for row in rows]


def hit_key(hit: SearchHit) -> tuple[str, str]:
    if hit.kind == "source-block":
        return f"src:{hit.source_id}", str(hit.locator_key)
    return hit.path, str(hit.anchor or "")


def fuse(lexical: Sequence[SearchHit], dense: Sequence[SearchHit]) -> list[SearchHit]:
    """Gate A RRF: k=60, best-rank, lexical-lane and stable-key tie breaks."""
    table: dict[tuple[str, str], dict[str, Any]] = {}
    for lane, hits in enumerate((lexical, dense)):
        seen: set[tuple[str, str]] = set()
        for rank, hit in enumerate(hits, 1):
            key = hit_key(hit)
            if key in seen:
                continue
            seen.add(key)
            entry = table.setdefault(key, {"hit": hit, "score": 0.0, "best": rank, "lanes": set()})
            entry["score"] += 1.0 / (RRF_K + rank)
            entry["best"] = min(entry["best"], rank)
            entry["lanes"].add(lane)
    ordered = sorted(
        table.items(),
        key=lambda item: (-item[1]["score"], item[1]["best"], min(item[1]["lanes"]), item[0]),
    )
    return [
        entry["hit"].model_copy(update={"score": round(entry["score"], 8)}) for _, entry in ordered
    ]


def _run[T](factory: Callable[[], Coroutine[Any, Any, T]]) -> T:
    """Keep clients on one loop, close them on that loop, and also support async direct callers.

    MCP dense tool bodies run in worker threads. A direct Python caller may instead already
    own an event loop; a short-lived joined worker avoids nested asyncio.run in that case.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(factory())
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(factory())).result()


def _artifact_bytes(source: ReleaseSource, config: McpConfig) -> bytes:
    location = config.vectors
    assert location is not None
    if location.startswith("blob:") or (config.mode == "azure" and location.startswith("work/")):
        key = location.removeprefix("blob:")
        if not key.startswith("work/"):
            raise ValueError("vector blob must be a work/ storage key")
        if isinstance(source, StorageReleaseSource):
            storage = source.storage
        elif config.mode == "azure":
            from docwiki.mcp.blob import AzureBlobStorage

            storage = AzureBlobStorage(
                config.storage_account, containers={"work": config.work_container}
            )
        else:
            raise ValueError("vector blob requires Azure storage mode")
        return storage.read_bytes(key)
    return Path(location).read_bytes()


def query_embedding_client(timeout_s: float) -> EmbeddingClient:
    """Interactive queries fail fast instead of sleeping through a batch-oriented Retry-After."""
    from docwiki.llm.foundry_embeddings import FoundryEmbeddingClient
    from docwiki.llm.retry import RetryPolicy
    from docwiki.llm.settings import LlmSettings

    settings = LlmSettings.from_env().model_copy(update={"timeout_s": timeout_s})
    return FoundryEmbeddingClient(
        settings, retry_policy=RetryPolicy(max_retries=0, max_retry_after_s=0)
    )


class DenseLane:
    """A validated matrix and bounded, thread-safe query cache for one served snapshot."""

    def __init__(
        self,
        snap: Snapshot,
        source: ReleaseSource,
        config: McpConfig,
        client_factory: Callable[[], EmbeddingClient],
    ) -> None:
        self.snap = snap
        self.client_factory = client_factory
        self.timeout_s = config.dense_timeout_s
        self._query_lock = threading.Lock()
        self._queries: OrderedDict[str, np.ndarray] = OrderedDict()
        self._inflight: dict[str, Future[np.ndarray]] = {}
        with np.load(io.BytesIO(_artifact_bytes(source, config)), allow_pickle=False) as artifact:
            self.metadata = json.loads(str(artifact["metadata"].item()))
            keys = json.loads(str(artifact["rows"].item()))
            self.rowids = artifact["rowids"]
            self.matrix = artifact["matrix"]
        rows = index_rows(snap.search)
        expected = {
            "format": ARTIFACT_FORMAT,
            "release_id": snap.release_id,
            "input_version": EMBED_INPUT_VERSION,
            "search_sha256": snap.reader.manifest.files[ReleaseFiles.SEARCH_DB].sha256,
        }
        for field, value in expected.items():
            if self.metadata.get(field) != value:
                raise ValueError(f"vector artifact {field} mismatch")
        dims = self.metadata.get("dimensions")
        if type(dims) is not int or dims < 1:
            raise ValueError("vector artifact dimensions must be a positive integer")
        if not self.metadata.get("model"):
            raise ValueError("vector artifact model is missing")
        if (
            self.rowids.dtype != np.dtype("int64")
            or self.rowids.shape != (len(rows),)
            or self.rowids.tolist() != [row["rowid"] for row in rows]
            or keys != row_keys(rows)
        ):
            raise ValueError("vector artifact row keys or rowids mismatch")
        if self.matrix.dtype != np.dtype("float32") or self.matrix.shape != (len(rows), dims):
            raise ValueError("vector artifact matrix dimensions or dtype mismatch")
        if not np.isfinite(self.matrix).all() or not np.allclose(
            np.linalg.norm(self.matrix, axis=1), 1.0, atol=1e-5
        ):
            raise ValueError("vector artifact matrix must contain finite L2-normalised vectors")
        self.sensitivity = {row["rowid"]: row["sensitivity"] for row in rows}

    async def _embed(self, text: str) -> np.ndarray:
        async with asyncio.timeout(self.timeout_s):
            return await self._embed_with_client(text)

    async def _embed_with_client(self, text: str) -> np.ndarray:
        client = self.client_factory()
        try:
            info = await client.describe()
            if info.model_name != self.metadata["model"]:
                raise ValueError("vector artifact model mismatch with embedding deployment")
            if info.dimensions != self.metadata["dimensions"]:
                raise ValueError("vector artifact dimensions mismatch with embedding deployment")
            if self.metadata.get("model_version") != info.model_version:
                raise ValueError("vector artifact model_version mismatch with embedding deployment")
            result = await client.embed([text], "query", QUERY_INPUT_VERSION)
            if result.model != self.metadata["model"] or result.dimensions != info.dimensions:
                raise ValueError("query embedding model/dimensions mismatch")
            vector = np.asarray(result.vectors, dtype=np.float32)
            if vector.shape != (1, info.dimensions) or not np.isfinite(vector).all():
                raise ValueError("query embedding must be one finite vector")
            norm = float(np.linalg.norm(vector[0]))
            if norm == 0.0:
                raise ValueError("query embedding must not be the zero vector")
            # Same rule as the artifact rows (scripts/build_eval_vectors.py): cosine on unit
            # vectors. Shortened text-embedding-3 vectors are not exactly unit length.
            return vector[0] / norm
        finally:
            # Cancellation of the request must not turn into an unbounded SDK close.
            async with asyncio.timeout(min(self.timeout_s, 1.0)):
                await client.aclose()

    def query(self, text: str) -> np.ndarray:
        with self._query_lock:
            if text in self._queries:
                self._queries.move_to_end(text)
                return self._queries[text]
            pending = self._inflight.get(text)
            owner = pending is None
            if pending is None:
                pending = Future()
                self._inflight[text] = pending
        if not owner:
            return pending.result(timeout=self.timeout_s)
        try:
            vector = _run(lambda: self._embed(text))
        except BaseException as exc:
            with self._query_lock:
                self._inflight.pop(text)
            pending.set_exception(exc)
            raise
        with self._query_lock:
            self._queries[text] = vector
            if len(self._queries) > QUERY_CACHE_SIZE:
                self._queries.popitem(last=False)
            self._inflight.pop(text)
        pending.set_result(vector)
        return vector

    def search(
        self,
        text: str,
        *,
        kinds: Sequence[str] | None = None,
        types: Sequence[str] | None = None,
        entity: str | None = None,
        topic: str | None = None,
        within: str | None = None,
        lang: str | None = None,
        accept: Callable[[SearchHit], bool],
    ) -> list[SearchHit]:
        vector = self.query(text)
        index = self.snap.search
        where, params = index._filters(kinds, types, entity, topic, within, lang)
        with index._lock:
            allowed = {
                rowid
                for (rowid,) in index._conn.execute(
                    f"SELECT d.rowid FROM docs d WHERE 1 = 1{where}", params
                )
                if allowed_for_audience(
                    self.sensitivity[rowid] or "restricted", self.snap.audience or "public"
                )
            }
            _, rows = index._load_corpus()
        positions = np.asarray(
            [i for i, rowid in enumerate(self.rowids) if rowid in allowed], dtype=np.int64
        )
        scores = self.matrix[positions] @ vector
        rowids = self.rowids[positions]
        order = np.lexsort((rowids, -scores))
        out: list[SearchHit] = []
        seen: set[tuple[str, str]] = set()
        for i in order:
            hit = SearchIndex._hit(rows[int(rowids[i])], float(scores[i]), [])
            key = hit_key(hit)
            if key in seen or not accept(hit):
                continue
            seen.add(key)
            out.append(hit)
            if len(out) == LANE_DEPTH:
                break
        return out
