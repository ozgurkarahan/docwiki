"""Offline retrieval bench: what ``answer_context`` finds and what it actually serves.

Run on a release folder, without any model or Azure call::

    uv run python evals/retrieval_bench.py --release <release folder> \
        --questions evals/golden/dev.jsonl --out evals/results/<date>-retrieval-lexical-dev.json

Two measures per question with ``required_citations`` (docs/spec/evals.md §8):

* **candidate recall** ``@k`` and MRR - the raw ranking of ``answer_context`` (one row per
  section or source locator, audience-filtered), before any text budget. A source block counts
  through its own locator; a wiki section counts through the footnote citations of its whole
  text (flagged ``proxy``: the section cites the evidence, it is not the evidence);
* **served recall** ``@5`` / ``@10`` - the citations that remain in the serialized output of
  ``answer_context(question, limit=k)`` after the 12 K-character budget.

A required citation may list ``alternatives`` (other ``{source_path, locator_key}`` pairs that
carry the same fact); any of them counts. A probe (``evals/golden/probes.py``) runs with its own
``within`` and ``lang``; its candidates are also checked for scope, language-tree and audience
violations, and its results are aggregated per probe kind. Per-question rows are written for the
``dev`` and ``retrieval-tune`` splits only, never the question text; other splits (the blind
decision set, the holdout) get aggregates only.

``--misses-from`` replays the read-tool calls of a result file on the same release and classifies
the required citations each failed answer did not cite: ``absent`` (not in the candidates),
``candidate_cut`` (a candidate the served window dropped) or ``served_unused`` (returned by a tool
call, not cited by the answer).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import inspect
import json
import sqlite3
import statistics
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docwiki.llm.embed_input import EMBED_INPUT_VERSION, build_embed_input
from docwiki.llm.embeddings import EmbeddingClient
from docwiki.mcp.config import McpConfig
from docwiki.mcp.source import FolderReleaseSource, Snapshot
from docwiki.mcp.tools_read import _CONTEXT_SKIPPED_TYPES, ReadTools
from docwiki.search.index import SearchIndex
from evals.corpus import CorpusManifest, ReleaseCatalog, SourceResolver
from evals.locators import keys_match
from evals.questions import GoldenQuestion, QuestionSetError
from evals.records import tool_hits

__all__ = [
    "BENCH_FORMAT",
    "Bench",
    "SemanticLane",
    "Target",
    "load_bench_questions",
    "main",
    "release_stats",
]

BENCH_FORMAT = "docwiki.evals.retrieval/v1"
CANDIDATE_DEPTH = 50
"""Candidates ranked per question (``answer_context`` caps its raw search at 100 rows)."""
KS = (5, 10, 20, 50)
SERVED_LIMITS = (5, 10)
DETAIL_SPLITS = frozenset({"dev", "retrieval-tune"})
"""Splits whose per-question rows are written; the others (``retrieval-blind``, the holdout)
get aggregates only."""
QUESTION_K = 10
"""A question is found at ``QUESTION_K`` when its required citations rank in the first
``QUESTION_K`` candidates (``hit_all``: every one; ``hit_any``: at least one)."""
EMBED_DIMENSIONS = 512
EMBED_TOKEN_LIMIT = 8191
"""Input limit of text-embedding-3-small, in tokens."""
CHARS_PER_TOKEN = 4.0
"""Rough estimate used before a tokenizer is wired in (S2); French text runs a little denser."""
DEFAULT_EMBED_PRICE = 0.02
"""Indicative USD per million input tokens, to be verified on the official pricing page."""
REPLAYED_TOOLS = frozenset({"answer_context", "search", "read_page", "get_evidence"})
RRF_K = 60
"""Reciprocal rank fusion constant of the hybrid mode (Gate A pilot)."""
LANE_DEPTH = 50
"""Candidates each lane (lexical, semantic) brings to the fusion."""


# ------------------------------------------------------------------------------ questions


@dataclass(frozen=True)
class Target:
    """One required citation and its accepted alternatives, as ``(source_path, locator_key)``."""

    options: tuple[tuple[str, str], ...]

    @property
    def source_path(self) -> str:
        return self.options[0][0]

    @property
    def locator_key(self) -> str:
        return self.options[0][1]

    def matches(self, path: str | None, key: str | None) -> bool:
        if not path or not key:
            return False
        return any(path == p and keys_match(k, key) for p, k in self.options)


@dataclass(frozen=True)
class BenchQuestion:
    question: GoldenQuestion
    targets: tuple[Target, ...]
    probe: str | None = None
    """The probe kind (``evals/golden/probes.py``); ``None`` for a golden question."""
    within: str | None = None

    @property
    def arguments(self) -> dict[str, str | None]:
        """The ``answer_context`` filters: a probe's ``within`` and ``lang``; none for a golden
        question (the Researcher's usual first call)."""
        if self.probe is None:
            return {"within": None, "lang": None}
        return {"within": self.within, "lang": self.question.lang}


def _targets(raw: Mapping[str, Any]) -> tuple[Target, ...]:
    out: list[Target] = []
    for required in raw.get("required_citations") or []:
        options = [(str(required["source_path"]), str(required["locator_key"]))]
        for alternative in required.get("alternatives") or []:
            pair = (str(alternative["source_path"]), str(alternative["locator_key"]))
            if pair not in options:
                options.append(pair)
        out.append(Target(tuple(options)))
    return tuple(out)


def load_bench_questions(path: Path) -> tuple[list[BenchQuestion], str]:
    """The questions of a JSONL golden set with their targets, and the file's SHA-256."""
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise QuestionSetError(f"cannot read {Path(path).name}: {exc.strerror}") from None
    questions: list[BenchQuestion] = []
    for number, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            probe, within = data.get("probe"), data.get("within")
            if not (probe is None or isinstance(probe, str)) or not (
                within is None or isinstance(within, str)
            ):
                raise TypeError("probe and within are strings or null")
            questions.append(
                BenchQuestion(
                    GoldenQuestion.model_validate(data),
                    _targets(data),
                    probe=probe,
                    within=within if probe is not None else None,
                )
            )
        except (ValueError, KeyError, TypeError) as exc:
            # never chain: messages could quote the (possibly private) input
            raise QuestionSetError(
                f"line {number} of {Path(path).name} is invalid ({type(exc).__name__})"
            ) from None
    if not questions:
        raise QuestionSetError(f"{Path(path).name} has no questions")
    return questions, hashlib.sha256(raw).hexdigest()


# ------------------------------------------------------------------------------- release


def _release_dir(path: Path) -> Path:
    for root in (path, path / "releases"):
        if (root / "search.db").is_file() and (root / "manifest.json").is_file():
            return root
        pointer = root / "current.json"
        if pointer.is_file():
            release_id = json.loads(pointer.read_text(encoding="utf-8"))["release_id"]
            return root / release_id
    raise FileNotFoundError("no release folder (manifest.json + search.db) found")


def _quantile(values: Sequence[int], q: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * (len(ordered) - 1) + 0.5))]


def release_stats(
    search_db: Path,
    *,
    dimensions: int = EMBED_DIMENSIONS,
    price_per_million: float = DEFAULT_EMBED_PRICE,
) -> dict[str, Any]:
    """Indexed rows and text lengths of a release: the inputs of the embedding estimate.

    Each row would be embedded as ``title + section + text`` (the S2 length rule); tokens are
    estimated at ``CHARS_PER_TOKEN`` characters per token until a tokenizer measures them.
    """
    conn = sqlite3.connect(f"file:{search_db.as_posix()}?mode=ro", uri=True)
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(docs)")}
        tree = "COALESCE(tree, '')" if "tree" in columns else "''"  # schema 1 has no mirrors
        rows = conn.execute(
            f"SELECT kind, {tree}, COALESCE(title, ''), COALESCE(section, ''), "
            "COALESCE(text, '') FROM docs"
        ).fetchall()
    finally:
        conn.close()
    by_kind: Counter[str] = Counter()
    by_tree: Counter[str] = Counter()
    lengths: list[int] = []
    for kind, tree, title, section, text in rows:
        by_kind[kind] += 1
        by_tree[tree or "canonical"] += 1
        lengths.append(len(f"{title}\n{section}\n{text}"))
    tokens = [int(length / CHARS_PER_TOKEN + 0.999) for length in lengths]
    total_tokens = sum(tokens)
    return {
        "rows": len(rows),
        "rows_by_kind": dict(sorted(by_kind.items())),
        "rows_by_tree": dict(sorted(by_tree.items())),
        "input_chars": {
            "total": sum(lengths),
            "p50": _quantile(lengths, 0.5),
            "p95": _quantile(lengths, 0.95),
            "max": max(lengths, default=0),
        },
        "estimated_tokens": {
            "method": f"chars/{CHARS_PER_TOKEN:g}",
            "total": total_tokens,
            "p50": _quantile(tokens, 0.5),
            "p95": _quantile(tokens, 0.95),
            "max": max(tokens, default=0),
            "rows_over_model_limit": sum(1 for t in tokens if t > EMBED_TOKEN_LIMIT),
            "model_limit": EMBED_TOKEN_LIMIT,
        },
        "vectors": {
            "dimensions": dimensions,
            "float32_bytes": len(rows) * dimensions * 4,
        },
        "embedding_cost_usd": {
            "price_per_million_tokens": price_per_million,
            "price_verified": False,
            "one_full_build": round(total_tokens / 1_000_000 * price_per_million, 6),
        },
    }


# --------------------------------------------------------------------------------- bench


def _pairs(value: Any) -> list[tuple[str, str]]:
    """Every ``(source_id, locator_key)`` pair found anywhere in a JSON value."""
    found: list[tuple[str, str]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            source_id, key = node.get("source_id"), node.get("locator_key")
            if isinstance(source_id, str) and isinstance(key, str) and source_id and key:
                found.append((source_id, key))
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    return list(dict.fromkeys(found))


class SemanticLane:
    """Brute-force cosine search over the embedded rows of one ``search.db`` (Gate A pilot).

    Every row is embedded with ``embed-input-v1``; the questions are embedded verbatim, all
    before the bench runs (one event loop). Vectors are cached under ``cache_dir`` by the SHA-256
    of the database, the model and the dimensions; question vectors by the SHA-256 of the
    question, never its text.
    """

    def __init__(
        self,
        rowids: np.ndarray,
        matrix: np.ndarray,
        queries: Mapping[str, np.ndarray],
        *,
        model: str,
        dimensions: int,
        usage: Mapping[str, Any],
    ) -> None:
        self.rowids = rowids
        self.matrix = matrix
        self.position = {int(rowid): index for index, rowid in enumerate(rowids)}
        self._queries = dict(queries)
        self.model = model
        self.dimensions = dimensions
        self.usage = dict(usage)

    def query(self, text: str) -> np.ndarray:
        return self._queries[_text_key(text)]

    @classmethod
    def build(
        cls,
        db: Path,
        questions: Sequence[str],
        client: EmbeddingClient,
        cache_dir: Path,
        *,
        price_per_million: float = DEFAULT_EMBED_PRICE,
    ) -> SemanticLane:
        return asyncio.run(
            cls._build(db, questions, client, cache_dir, price_per_million=price_per_million)
        )

    @classmethod
    async def _build(
        cls,
        db: Path,
        questions: Sequence[str],
        client: EmbeddingClient,
        cache_dir: Path,
        *,
        price_per_million: float,
    ) -> SemanticLane:
        try:
            info = await client.describe()
            model = info.model_name or info.deployment
            dims = info.dimensions
            cache_dir.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256(db.read_bytes()).hexdigest()[:16]
            rows_file = cache_dir / f"rows-{digest}-{model}-{dims}-{EMBED_INPUT_VERSION}.npz"
            billed = {"rows": 0, "questions": 0}
            if rows_file.is_file():
                cached = np.load(rows_file)
                rowids, matrix = cached["rowids"], cached["matrix"]
                rows_tokens = int(cached["tokens"])
            else:
                ids, texts = _row_inputs(db)
                result = await client.embed(texts, "document", EMBED_INPUT_VERSION)
                rowids = np.asarray(ids, dtype=np.int64)
                matrix = np.asarray(result.vectors, dtype=np.float32)
                rows_tokens = billed["rows"] = result.usage.input_tokens
                tmp = rows_file.with_suffix(".tmp.npz")
                np.savez(tmp, rowids=rowids, matrix=matrix, tokens=np.int64(rows_tokens))
                tmp.replace(rows_file)
            queries_file = cache_dir / f"queries-{model}-{dims}.json"
            stored: dict[str, list[float]] = (
                json.loads(queries_file.read_text(encoding="utf-8"))
                if queries_file.is_file()
                else {}
            )
            missing = list(dict.fromkeys(q for q in questions if _text_key(q) not in stored))
            if missing:
                result = await client.embed(missing, "query", "query-verbatim-v1")
                billed["questions"] = result.usage.input_tokens
                for text, vector in zip(missing, result.vectors, strict=True):
                    stored[_text_key(text)] = [float(x) for x in vector]
                queries_file.write_text(json.dumps(stored), encoding="utf-8", newline="\n")
        finally:
            await client.aclose()
        queries = {key: np.asarray(vec, dtype=np.float32) for key, vec in stored.items()}
        tokens = billed["rows"] + billed["questions"]
        usage = {
            "rows_embedded": len(rowids),
            "rows_tokens": rows_tokens,
            "billed_tokens": billed,
            "billed_usd": round(tokens * price_per_million / 1_000_000, 6),
        }
        return cls(rowids, matrix, queries, model=model, dimensions=dims, usage=usage)


def _text_key(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def _row_inputs(db: Path) -> tuple[list[int], list[str]]:
    conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    try:
        records = conn.execute("SELECT rowid, title, section, text FROM docs ORDER BY rowid")
        ids: list[int] = []
        texts: list[str] = []
        for rowid, title, section, text in records:
            try:
                shaped = build_embed_input(title, section, text)
            except ValueError:
                continue
            ids.append(int(rowid))
            texts.append(shaped.text)
    finally:
        conn.close()
    return ids, texts


def _hit_key(hit: Any) -> tuple[str, str]:
    if hit.kind == "source-block":
        return (f"src:{hit.source_id}", str(hit.locator_key))
    return (hit.path, str(hit.anchor or ""))


@dataclass(frozen=True)
class Candidate:
    rank: int
    kind: str
    cited: tuple[tuple[str, str], ...]
    path: str = ""
    anchor: str | None = None
    locator_key: str | None = None
    lanes: str = "lexical"
    """The lanes that ranked the row: ``lexical``, ``semantic`` or ``both`` (hybrid mode)."""

    @property
    def proxy(self) -> bool:
        return self.kind != "source-block"


@dataclass(frozen=True)
class RowFacts:
    """What the index records about a candidate's row: its scope, tree and sensitivity."""

    scope: str | None
    tree: str | None
    sensitivity: str | None


class Bench:
    """The retrieval measures of one release."""

    def __init__(
        self,
        release: Path,
        corpus: Path,
        *,
        semantic: SemanticLane | None = None,
        rrf_k: int = RRF_K,
        lane_depth: int = LANE_DEPTH,
    ) -> None:
        self.release_dir = _release_dir(Path(release))
        self.reads = ReadTools(FolderReleaseSource(self.release_dir), McpConfig())
        self.snap: Snapshot = self.reads.snapshot()
        catalog = ReleaseCatalog.load(self.release_dir / "catalog.json")
        self.resolver = SourceResolver(CorpusManifest.load(Path(corpus)), catalog)
        self._facts: dict[tuple[str, str, str | None, str | None], list[RowFacts]] = {}
        self.semantic = semantic
        self.rrf_k = rrf_k
        self.lane_depth = lane_depth
        self._eligible: dict[tuple[str | None, str | None], np.ndarray] = {}

    @property
    def mode(self) -> str:
        return "lexical" if self.semantic is None else "hybrid"

    @property
    def served_limits(self) -> tuple[int, ...]:
        """Served recall runs the deployed ``answer_context``: lexical mode only."""
        return SERVED_LIMITS if self.semantic is None else ()

    def path_of(self, source_id: str) -> str | None:
        return self.resolver.path_for_id(source_id)

    def _dedupe(self, hits: Iterable[Any], limit: int) -> list[Any]:
        """The ``answer_context`` candidate rules: one row per section or source locator, nothing
        above the release's audience, no index, log or meta page."""
        reads, snap = self.reads, self.snap
        by_path, by_id = reads._by_path(snap), reads._by_id(snap)
        seen: set[tuple[str, str]] = set()
        out: list[Any] = []
        for hit in hits:
            key = _hit_key(hit)
            if key in seen:
                continue
            entry = by_path.get(hit.path) or by_id.get(hit.page_id)
            if entry is None or not reads._allowed(snap, entry.sensitivity):
                continue
            if entry.type in _CONTEXT_SKIPPED_TYPES:
                continue
            seen.add(key)
            out.append(hit)
            if len(out) >= limit:
                break
        return out

    def _semantic_hits(
        self, question: str, scope: str | None, language: str | None, limit: int
    ) -> list[Any]:
        """Rows by cosine similarity, under the same filters as the lexical search."""
        lane = self.semantic
        assert lane is not None
        index = self.snap.search
        eligible = self._eligible.get((scope, language))
        if eligible is None:
            where, params = index._filters(None, None, None, None, scope, language)
            sql = f"SELECT d.rowid FROM docs d WHERE 1 = 1{where}"
            allowed = {rowid for (rowid,) in index._conn.execute(sql, params)}
            eligible = np.asarray(
                sorted(lane.position[r] for r in allowed if r in lane.position), dtype=np.int64
            )
            self._eligible[(scope, language)] = eligible
        if not len(eligible):
            return []
        scores = lane.matrix[eligible] @ lane.query(question)
        rowids = lane.rowids[eligible]
        order = np.lexsort((rowids, -scores))
        _, rows = index._load_corpus()
        hits = (SearchIndex._hit(rows[int(rowids[i])], float(scores[i]), []) for i in order)
        return self._dedupe(hits, limit)

    def _ranked(
        self,
        question: str,
        scope: str | None,
        language: str | None,
        depth: int,
        lexical_only: bool = False,
    ) -> list[tuple[Any, str]]:
        """The ranked hits and the lanes behind each: lexical alone, or the RRF fusion."""
        reads, snap = self.reads, self.snap
        if self.semantic is None or lexical_only:
            lexical = reads._context_candidates(snap, question, scope, language, depth)[:depth]
            return [(hit, "lexical") for hit in lexical]
        lanes = (
            reads._context_candidates(snap, question, scope, language, self.lane_depth)[
                : self.lane_depth
            ],
            self._semantic_hits(question, scope, language, self.lane_depth),
        )
        table: dict[tuple[str, str], dict[str, Any]] = {}
        for lane, hits in enumerate(lanes):
            for rank, hit in enumerate(hits, 1):
                entry = table.setdefault(
                    _hit_key(hit), {"hit": hit, "score": 0.0, "best": rank, "lanes": set()}
                )
                entry["score"] += 1.0 / (self.rrf_k + rank)
                entry["best"] = min(entry["best"], rank)
                entry["lanes"].add(lane)
        ordered = sorted(
            table.items(),
            key=lambda item: (-item[1]["score"], item[1]["best"], min(item[1]["lanes"]), item[0]),
        )
        names = {frozenset({0}): "lexical", frozenset({1}): "semantic"}
        return [
            (entry["hit"], names.get(frozenset(entry["lanes"]), "both"))
            for _, entry in ordered[:depth]
        ]

    def candidates(
        self,
        question: str,
        *,
        within: str | None = None,
        lang: str | None = None,
        depth: int = CANDIDATE_DEPTH,
        lexical_only: bool = False,
    ) -> list[Candidate]:
        """The raw ``answer_context`` ranking with the citations each row would carry."""
        reads, snap = self.reads, self.snap
        scope = reads._within(snap, within)
        language = reads._lang(snap, lang)
        out: list[Candidate] = []
        ranked = self._ranked(question, scope, language, depth, lexical_only)
        for rank, (hit, lanes) in enumerate(ranked, 1):
            where = {
                "path": hit.path,
                "anchor": hit.anchor,
                "locator_key": hit.locator_key,
                "lanes": lanes,
            }
            if hit.kind == "source-block":
                cited = ((hit.source_id, hit.locator_key),) if hit.locator_key else ()
                out.append(Candidate(rank, hit.kind, cited, **where))
                continue
            part = reads._context_hit(snap, hit)
            if part is None:
                continue
            pairs = _pairs(part.fixed) + _pairs(
                [part.by_label[x] for x in reads._refs_in(part.text) if x in part.by_label]
            )
            out.append(Candidate(rank, hit.kind, tuple(dict.fromkeys(pairs)), **where))
        return out

    def facts(self, candidate: Candidate) -> list[RowFacts]:
        """The index rows behind a candidate (one per chunk; they share their facts)."""
        key = (candidate.kind, candidate.path, candidate.anchor, candidate.locator_key)
        cached = self._facts.get(key)
        if cached is not None:
            return cached
        db = self.release_dir / "search.db"
        conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
        try:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(docs)")}
            scope = "scope" if "scope" in columns else "NULL"
            tree = "tree" if "tree" in columns else "NULL"
            if candidate.kind == "source-block":
                clause, value = "COALESCE(locator_key, '') = ?", candidate.locator_key or ""
            else:
                clause, value = "COALESCE(anchor, '') = ?", candidate.anchor or ""
            rows = conn.execute(
                f"SELECT DISTINCT {scope}, {tree}, sensitivity FROM docs "
                f"WHERE kind = ? AND path = ? AND {clause}",
                (candidate.kind, candidate.path, value),
            ).fetchall()
        finally:
            conn.close()
        found = [RowFacts(*row) for row in rows]
        self._facts[key] = found
        return found

    def violations(
        self,
        candidates: Sequence[Candidate],
        *,
        within: str | None,
        lang: str | None,
    ) -> dict[str, int]:
        """Candidates that break the call's filters: another scope than ``within``, a tree other
        than the requested language's or the canonical one, or content above ``public``."""
        languages = list(self.snap.catalog.wiki_languages)
        canonical = languages[0] if languages else None
        wanted = self.reads._lang(self.snap, lang) or canonical
        counts = {"scope": 0, "lang": 0, "audience": 0, "unknown_row": 0}
        for candidate in candidates:
            rows = self.facts(candidate)
            if not rows:
                counts["unknown_row"] += 1
                continue
            if within is not None and any(row.scope != within for row in rows):
                counts["scope"] += 1
            if any(row.tree not in (None, wanted, canonical) for row in rows):
                counts["lang"] += 1
            if any(row.sensitivity != "public" for row in rows):
                counts["audience"] += 1
        return counts

    def served(self, question: str, limit: int, **arguments: Any) -> list[tuple[str, str]]:
        """The citation pairs left in the serialized ``answer_context`` output."""
        output = self.reads.answer_context(question, limit=limit, **arguments)
        pairs: list[tuple[str, str]] = []
        for hit in tool_hits("answer_context", output) or []:
            pairs.extend(hit.cited)
            if hit.kind == "source-block" and hit.source_id and hit.locator_key:
                pairs.append((hit.source_id, hit.locator_key))
        return list(dict.fromkeys(pairs))

    def _matched(self, target: Target, pairs: Iterable[tuple[str, str]]) -> bool:
        return any(target.matches(self.path_of(sid), key) for sid, key in pairs)

    def first_rank(self, target: Target, candidates: Sequence[Candidate]) -> Candidate | None:
        for candidate in candidates:
            if self._matched(target, candidate.cited):
                return candidate
        return None

    def measure(self, item: BenchQuestion) -> dict[str, Any]:
        question = item.question
        arguments = item.arguments
        candidates = self.candidates(question.question, **arguments)
        served = {k: self.served(question.question, k, **arguments) for k in self.served_limits}
        rows: list[dict[str, Any]] = []
        for target in item.targets:
            first = self.first_rank(target, candidates)
            row: dict[str, Any] = {
                "source_path": target.source_path,
                "locator_key": target.locator_key,
                "alternatives": len(target.options) - 1,
                "rank": first.rank if first else None,
                "proxy": first.proxy if first else None,
                **{f"served@{k}": self._matched(target, served[k]) for k in self.served_limits},
            }
            if self.semantic is not None:
                row["lanes"] = first.lanes if first else None
            rows.append(row)
        ranks = [row["rank"] for row in rows if row["rank"] is not None]
        total = len(rows)
        top = [row["rank"] is not None and row["rank"] <= QUESTION_K for row in rows]
        return {
            "id": question.id,
            "split": question.split,
            "category": question.category,
            "lang": question.lang,
            "probe": item.probe,
            "within": arguments["within"],
            "targets": rows,
            "candidates": len(candidates),
            **{f"candidate_recall@{k}": sum(1 for r in ranks if r <= k) / total for k in KS},
            "mrr": 1.0 / min(ranks) if ranks else 0.0,
            **{
                f"served_recall@{k}": sum(1 for row in rows if row[f"served@{k}"]) / total
                for k in self.served_limits
            },
            f"hit_all@{QUESTION_K}": all(top),
            f"hit_any@{QUESTION_K}": any(top),
            "violations": self.violations(candidates, **arguments),
            **self._paired(item),
        }

    def _paired(self, item: BenchQuestion) -> dict[str, Any]:
        """In hybrid mode, the same question ranked by the lexical lane alone, so a run can
        count the questions the fusion gains and loses without writing any question out."""
        if self.semantic is None:
            return {}
        lexical = self.candidates(item.question.question, **item.arguments, lexical_only=True)
        found = []
        for target in item.targets:
            first = self.first_rank(target, lexical)
            found.append(first is not None and first.rank <= QUESTION_K)
        return {f"lexical_hit_all@{QUESTION_K}": all(found)}

    # ------------------------------------------------------------------------------ misses

    def _replay(self, call: Mapping[str, Any]) -> list[tuple[str, str]] | None:
        name = call.get("name")
        if name not in REPLAYED_TOOLS or call.get("status") not in (None, "completed"):
            return []
        arguments = dict(call.get("arguments") or {})
        if name == "get_evidence":
            source_id, key = arguments.get("source_id"), arguments.get("locator_key")
            return [(source_id, key)] if source_id and key else []
        method = getattr(self.reads, str(name))
        accepted = set(inspect.signature(method).parameters)
        try:
            output = method(**{k: v for k, v in arguments.items() if k in accepted})
        except Exception:
            return None
        return _pairs(json.loads(output))

    def classify_misses(
        self, result: Mapping[str, Any], questions: Mapping[str, BenchQuestion]
    ) -> dict[str, Any]:
        """Why each failed answer of a result file missed its required citations."""
        rows: list[dict[str, Any]] = []
        for record in result.get("questions") or []:
            item = questions.get(str(record.get("id")))
            accuracy = (record.get("metrics") or {}).get("answer_accuracy")
            if item is None or accuracy is None or accuracy >= 1.0:
                continue
            cited_ok = [
                bool(entry.get("matched"))
                for entry in (record.get("details") or {}).get("required_citations") or []
            ]
            served: list[tuple[str, str]] = []
            replay_errors = 0
            searches: list[Mapping[str, Any]] = []
            for call in record.get("tool_calls") or []:
                pairs = self._replay(call)
                if pairs is None:
                    replay_errors += 1
                    continue
                served.extend(pairs)
                if call.get("name") in ("answer_context", "search"):
                    searches.append(call.get("arguments") or {})
            pools = [self.candidates(item.question.question)]
            for arguments in searches:
                query = arguments.get("question") or arguments.get("query")
                if not isinstance(query, str) or not query.strip():
                    continue
                try:
                    pools.append(
                        self.candidates(
                            query, within=arguments.get("within"), lang=arguments.get("lang")
                        )
                    )
                except Exception:
                    replay_errors += 1
            reasons: Counter[str] = Counter()
            for index, target in enumerate(item.targets):
                if index < len(cited_ok) and cited_ok[index]:
                    continue
                if self._matched(target, served):
                    reasons["served_unused"] += 1
                elif any(self.first_rank(target, pool) for pool in pools):
                    reasons["candidate_cut"] += 1
                else:
                    reasons["absent"] += 1
            label = next(
                (name for name in ("absent", "candidate_cut", "served_unused") if reasons[name]),
                "all_cited",
            )
            rows.append(
                {
                    "id": item.question.id,
                    "category": item.question.category,
                    "label": label,
                    "missing_citations": dict(sorted(reasons.items())),
                    "tool_calls_replayed": len(record.get("tool_calls") or []),
                    "replay_errors": replay_errors,
                }
            )
        return {
            "result_file": {
                "system": result.get("system"),
                "split": result.get("split"),
                "release_id": (result.get("versions") or {}).get("release_id"),
            },
            "replayed_on": self.snap.release_id,
            "labels": dict(sorted(Counter(row["label"] for row in rows).items())),
            "questions": rows,
        }


def _mean(values: Iterable[float]) -> float | None:
    data = list(values)
    return round(statistics.fmean(data), 4) if data else None


def aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    targets = [target for row in rows for target in row["targets"]]
    found = [target for target in targets if target["rank"] is not None]
    keys = [f"candidate_recall@{k}" for k in KS] + ["mrr"]
    keys += [
        f"served_recall@{k}" for k in SERVED_LIMITS if rows and f"served_recall@{k}" in rows[0]
    ]
    violations: Counter[str] = Counter()
    for row in rows:
        violations.update(row.get("violations") or {})
    lanes = Counter(target.get("lanes") for target in found if target.get("lanes"))
    return {
        "questions": len(rows),
        "required_citations": len(targets),
        **{key: _mean(row[key] for row in rows) for key in keys},
        **{
            f"questions_{name}@{QUESTION_K}": sum(
                1 for row in rows if row.get(f"{name}@{QUESTION_K}")
            )
            for name in ("hit_all", "hit_any")
        },
        "found_via_proxy": sum(1 for target in found if target["proxy"]),
        "found_direct": sum(1 for target in found if not target["proxy"]),
        "violations": {
            name: violations[name] for name in ("scope", "lang", "audience", "unknown_row")
        },
        **({"found_by_lanes": dict(sorted(lanes.items()))} if lanes else {}),
        **_paired_counts(rows),
    }


def _paired_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    key = f"lexical_hit_all@{QUESTION_K}"
    if not rows or key not in rows[0]:
        return {}
    pairs = [(bool(row[key]), bool(row[f"hit_all@{QUESTION_K}"])) for row in rows]
    return {
        f"paired_vs_lexical_hit_all@{QUESTION_K}": {
            "lexical": sum(1 for lex, _ in pairs if lex),
            "gained": sum(1 for lex, hyb in pairs if hyb and not lex),
            "lost": sum(1 for lex, hyb in pairs if lex and not hyb),
        }
    }


def run(
    bench: Bench,
    questions: Sequence[BenchQuestion],
    *,
    questions_name: str,
    questions_sha256: str,
    date: str,
    price_per_million: float = DEFAULT_EMBED_PRICE,
    misses_from: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    measured = [bench.measure(item) for item in questions if item.targets]
    by_split: dict[str, list[dict[str, Any]]] = {}
    for row in measured:
        by_split.setdefault(row["split"], []).append(row)
    snap = bench.snap
    out: dict[str, Any] = {
        "format": BENCH_FORMAT,
        "mode": bench.mode,
        "date": date,
        "release": {
            "release_id": snap.release_id,
            "audience": snap.audience,
            "manifest_sha256": snap.manifest_sha256,
        },
        "questions_file": {
            "name": questions_name,
            "sha256": questions_sha256,
            "questions": len(questions),
            "with_required_citations": len(measured),
        },
        "settings": {
            "candidate_depth": CANDIDATE_DEPTH,
            "ks": list(KS),
            "served_limits": list(bench.served_limits),
            "query": "the question verbatim; no within and no lang for a golden question (the "
            "Researcher's usual first call), the probe's within and lang for a probe",
            "question_k": QUESTION_K,
            "violations": "candidates outside within, in a tree other than the requested "
            "language's or the canonical one, or not public",
            "section_counting": "proxy: a wiki section counts through the footnotes of its text",
        },
        "release_stats": release_stats(
            bench.release_dir / "search.db", price_per_million=price_per_million
        ),
        "splits": {split: aggregate(rows) for split, rows in sorted(by_split.items())},
        "questions": [
            {key: value for key, value in row.items() if key != "split"}
            for row in measured
            if row["split"] in DETAIL_SPLITS
        ],
    }
    by_probe: dict[str, list[dict[str, Any]]] = {}
    lane = bench.semantic
    if lane is not None:
        out["settings"]["hybrid"] = {
            "embed_model": lane.model,
            "dimensions": lane.dimensions,
            "row_input": EMBED_INPUT_VERSION,
            "question_input": "the question verbatim",
            "search": "brute-force cosine over the rows passing the lexical filters, then the "
            "answer_context candidate rules",
            "fusion": "reciprocal rank fusion",
            "rrf_k": bench.rrf_k,
            "lane_depth": bench.lane_depth,
        }
        out["embedding_usage"] = lane.usage
    for row in measured:
        if row["probe"] is not None:
            by_probe.setdefault(f"{row['split']}/{row['probe']}", []).append(row)
    if by_probe:
        out["probes"] = {name: aggregate(rows) for name, rows in sorted(by_probe.items())}
    if misses_from is not None:
        by_id = {item.question.id: item for item in questions}
        out["misses"] = bench.classify_misses(misses_from, by_id)
    return out


# ----------------------------------------------------------------------------------- CLI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--release", type=Path, required=True, help="release folder")
    parser.add_argument("--questions", type=Path, default=Path("evals/golden/dev.jsonl"))
    parser.add_argument("--corpus", type=Path, default=Path("samples/corpus"))
    parser.add_argument("--out", type=Path, help="output JSON (default: standard output)")
    parser.add_argument("--misses-from", type=Path, help="result file whose failures to classify")
    parser.add_argument("--date", help="date written in the output (default: today, UTC)")
    parser.add_argument("--price-per-million", type=float, default=DEFAULT_EMBED_PRICE)
    parser.add_argument(
        "--mode",
        choices=("lexical", "hybrid"),
        default="lexical",
        help="hybrid: fuse a semantic lane (needs the DOCWIKI_EMBED_* and Foundry settings)",
    )
    parser.add_argument("--rrf-k", type=int, default=RRF_K)
    parser.add_argument("--lane-depth", type=int, default=LANE_DEPTH)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(".local/retrieval-bench"),
        help="vector cache of the hybrid mode (keep it out of git)",
    )
    parser.add_argument(
        "--note", action="append", default=[], help="a note written in the output (repeatable)"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    questions, sha256 = load_bench_questions(args.questions)
    semantic = None
    if args.mode == "hybrid":
        from docwiki.llm.factory import create_embedding_client

        db = _release_dir(args.release) / "search.db"
        semantic = SemanticLane.build(
            db,
            [item.question.question for item in questions if item.targets],
            create_embedding_client(),
            args.cache_dir,
            price_per_million=args.price_per_million,
        )
    bench = Bench(
        args.release, args.corpus, semantic=semantic, rrf_k=args.rrf_k, lane_depth=args.lane_depth
    )
    misses = json.loads(args.misses_from.read_text(encoding="utf-8")) if args.misses_from else None
    report = run(
        bench,
        questions,
        questions_name=args.questions.name,
        questions_sha256=sha256,
        date=args.date or datetime.now(UTC).date().isoformat(),
        price_per_million=args.price_per_million,
        misses_from=misses,
    )
    if args.note:
        report["notes"] = list(args.note)
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
