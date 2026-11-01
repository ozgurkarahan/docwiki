"""Offline retrieval bench on the committed mock release (no network, no model)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from evals.records import ToolCallRecord, tool_hits
from evals.retrieval_bench import (
    Bench,
    SemanticLane,
    _row_inputs,
    _text_key,
    load_bench_questions,
    main,
    release_stats,
    run,
)

from docwiki.llm.embeddings import FakeEmbeddingClient

MINUTES = (
    "full/chantiers/moreau/3-execution/site-meeting-minutes/"
    "2026-03-24_compte-rendu-de-chantier-n3.docx"
)
WALLS = "Élévation des murs 70 %"
WINDOWS = "fenêtres livraison 20 avril"


def _question(qid: str, text: str, citations: list[dict[str, Any]], split: str = "dev") -> str:
    return json.dumps(
        {
            "id": qid,
            "split": split,
            "category": "fact",
            "question": text,
            "lang": "fr",
            "required_citations": citations,
        },
        ensure_ascii=False,
    )


@pytest.fixture(scope="module")
def bench(repo_root: Path) -> Bench:
    return Bench(repo_root / "samples/fixtures/mock-release", repo_root / "samples/corpus")


@pytest.fixture
def golden(tmp_path: Path) -> Path:
    lines = [
        _question("b001", WALLS, [{"source_path": MINUTES, "locator_key": "para-0007"}]),
        _question("b002", WINDOWS, [{"source_path": MINUTES, "locator_key": "para-0011"}]),
        _question(
            "b003",
            WALLS,
            [
                {
                    "source_path": MINUTES,
                    "locator_key": "para-0099",
                    "alternatives": [{"source_path": MINUTES, "locator_key": "para-0007"}],
                }
            ],
        ),
        _question("b004", WALLS, [{"source_path": MINUTES, "locator_key": "para-0099"}]),
        _question("b005", "Question sans citation requise", []),
        _question(
            "h001",
            "Secret holdout phrasing about walls",
            [{"source_path": MINUTES, "locator_key": "para-0007"}],
            split="holdout",
        ),
    ]
    path = tmp_path / "bench.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _report(bench: Bench, golden: Path, **kwargs: Any) -> dict[str, Any]:
    questions, sha256 = load_bench_questions(golden)
    return run(
        bench,
        questions,
        questions_name=golden.name,
        questions_sha256=sha256,
        date="2026-10-28",
        **kwargs,
    )


def _row(report: dict[str, Any], qid: str) -> dict[str, Any]:
    return next(row for row in report["questions"] if row["id"] == qid)


def test_source_block_counts_directly_at_its_rank(bench: Bench, golden: Path) -> None:
    row = _row(_report(bench, golden), "b001")
    (target,) = row["targets"]
    assert target["rank"] == 1
    assert target["proxy"] is False
    assert row["candidate_recall@5"] == 1.0
    assert row["mrr"] == 1.0


def test_wiki_section_counts_through_its_citations_as_a_proxy(bench: Bench, golden: Path) -> None:
    row = _row(_report(bench, golden), "b002")
    (target,) = row["targets"]
    candidates = bench.candidates(WINDOWS)
    assert candidates[0].kind == "page-section" and not candidates[0].cited
    assert target["rank"] == 2
    assert target["proxy"] is True
    assert row["mrr"] == 0.5


def test_alternatives_are_accepted(bench: Bench, golden: Path) -> None:
    report = _report(bench, golden)
    with_alternative, without = _row(report, "b003"), _row(report, "b004")
    assert with_alternative["targets"][0]["alternatives"] == 1
    assert with_alternative["targets"][0]["rank"] == 1
    assert without["targets"][0]["rank"] is None
    assert without["candidate_recall@50"] == 0.0
    assert without["mrr"] == 0.0
    assert without["served_recall@10"] == 0.0


def test_served_recall_reads_the_serialized_output(bench: Bench, golden: Path) -> None:
    row = _row(_report(bench, golden), "b001")
    assert row["served_recall@5"] == 1.0
    served = bench.served(WALLS, 1)
    assert served and all(isinstance(pair, tuple) and len(pair) == 2 for pair in served)


def test_output_is_deterministic(bench: Bench, golden: Path) -> None:
    first = json.dumps(_report(bench, golden), sort_keys=True)
    second = json.dumps(_report(bench, golden), sort_keys=True)
    assert first == second


def test_no_question_text_and_no_rows_for_non_dev_splits(bench: Bench, golden: Path) -> None:
    report = _report(bench, golden)
    text = json.dumps(report, ensure_ascii=False)
    assert "Secret holdout phrasing" not in text
    assert WALLS not in text and WINDOWS not in text
    assert {row["id"] for row in report["questions"]} == {"b001", "b002", "b003", "b004"}
    assert report["splits"]["holdout"]["questions"] == 1
    assert report["splits"]["holdout"]["candidate_recall@5"] == 1.0
    assert report["questions_file"]["with_required_citations"] == 5


def test_release_stats_of_the_mock_release(repo_root: Path) -> None:
    db = repo_root / "samples/fixtures/mock-release/releases/20260401T090000Z-8a41b109/search.db"
    stats = release_stats(db, dimensions=512, price_per_million=0.02)
    assert stats["rows"] == 84
    assert stats["rows_by_kind"] == {"page-section": 76, "source-block": 8}
    assert stats["vectors"]["float32_bytes"] == 84 * 512 * 4
    assert stats["estimated_tokens"]["rows_over_model_limit"] == 0
    assert stats["embedding_cost_usd"]["price_verified"] is False
    assert 0 < stats["embedding_cost_usd"]["one_full_build"] < 0.001


def test_misses_are_classified(bench: Bench, golden: Path) -> None:
    def failed(qid: str, calls: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "id": qid,
            "metrics": {"answer_accuracy": 0.0},
            "details": {"required_citations": [{"matched": False}]},
            "tool_calls": calls,
        }

    served_call = {
        "name": "answer_context",
        "status": "completed",
        "arguments": {"question": WALLS, "limit": 5},
    }
    result = {
        "system": "docwiki-researcher",
        "split": "dev",
        "questions": [
            failed("b001", [served_call]),
            failed("b002", []),
            failed("b004", [served_call]),
            {"id": "b003", "metrics": {"answer_accuracy": 1.0}},
            failed("unknown", []),
        ],
    }
    misses = _report(bench, golden, misses_from=result)["misses"]
    labels = {row["id"]: row["label"] for row in misses["questions"]}
    assert labels == {"b001": "served_unused", "b002": "candidate_cut", "b004": "absent"}
    assert misses["labels"] == {"absent": 1, "candidate_cut": 1, "served_unused": 1}
    assert misses["replayed_on"] == bench.snap.release_id


def test_tool_hits_keep_ids_only(bench: Bench) -> None:
    output = bench.reads.answer_context(WALLS, limit=3)
    hits = tool_hits("answer_context", output)
    assert hits is not None and [hit.rank for hit in hits] == [1, 2, 3]
    assert hits[0].kind == "source-block"
    assert hits[0].source_id == "src-f0757603684a" and hits[0].locator_key == "para-0007"
    assert ("src-f0757603684a", "para-0007") in hits[0].cited
    dumped = json.dumps([hit.model_dump() for hit in hits], ensure_ascii=False)
    assert "70 %" not in dumped and "text" not in dumped
    mcp_content = [{"type": "text", "text": output}]
    assert tool_hits("search", mcp_content) == hits
    assert tool_hits("read_page", output) is None
    assert tool_hits("answer_context", "not json") is None


def test_old_tool_call_records_are_unchanged() -> None:
    record = ToolCallRecord(name="read_page", status="completed", arguments={"page": "x"})
    assert "hits" not in record.model_dump(exclude_none=True)


def _probe(qid: str, split: str, probe: str, within: str | None, lang: str = "fr") -> str:
    record = json.loads(
        _question(qid, WALLS, [{"source_path": MINUTES, "locator_key": "para-0007"}], split)
    )
    record.update({"lang": lang, "probe": probe, "within": within, "audience": "public"})
    return json.dumps(record, ensure_ascii=False)


@pytest.fixture
def probes(tmp_path: Path) -> Path:
    lines = [
        _probe("t001", "retrieval-tune", "paraphrase-fr", "moreau"),
        _probe("t002", "retrieval-tune", "en-to-fr", None, lang="en"),
        _probe("x001", "retrieval-blind", "lexical-control", None),
        _question("b001", WALLS, [{"source_path": MINUTES, "locator_key": "para-0007"}]),
    ]
    path = tmp_path / "probes.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_probes_run_with_their_within_and_lang(
    bench: Bench, probes: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    original = Bench.candidates

    def candidates(self: Bench, question: str, **kwargs: Any) -> list[Any]:
        calls.append(("candidates", kwargs))
        return original(self, question)

    def served(self: Bench, question: str, limit: int, **kwargs: Any) -> list[tuple[str, str]]:
        calls.append(("served", kwargs))
        return []

    monkeypatch.setattr(Bench, "candidates", candidates)
    monkeypatch.setattr(Bench, "served", served)
    monkeypatch.setattr(Bench, "violations", lambda self, candidates, **kwargs: {})
    report = _report(bench, probes)
    filters = [kwargs for _, kwargs in calls]
    assert {"within": "moreau", "lang": "fr"} in filters
    assert {"within": None, "lang": "en"} in filters
    assert {"within": None, "lang": None} in filters  # the golden question
    assert {(name, json.dumps(kwargs)) for name, kwargs in calls} >= {
        ("served", json.dumps({"within": "moreau", "lang": "fr"}))
    }
    assert _row(report, "t001")["within"] == "moreau"
    assert _row(report, "b001")["probe"] is None


def test_probe_report_details_tune_and_aggregates_blind(
    bench: Bench, probes: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = Bench.candidates
    monkeypatch.setattr(
        Bench, "candidates", lambda self, question, **kwargs: original(self, question)
    )
    monkeypatch.setattr(Bench, "served", lambda self, question, limit, **kwargs: [])
    zero = {"scope": 0, "lang": 0, "audience": 0, "unknown_row": 0}
    monkeypatch.setattr(Bench, "violations", lambda self, candidates, **kwargs: dict(zero))
    report = _report(bench, probes)
    assert {row["id"] for row in report["questions"]} == {"t001", "t002", "b001"}
    assert set(report["probes"]) == {
        "retrieval-blind/lexical-control",
        "retrieval-tune/en-to-fr",
        "retrieval-tune/paraphrase-fr",
    }
    blind = report["probes"]["retrieval-blind/lexical-control"]
    assert blind["questions"] == 1
    assert blind["questions_hit_all@10"] == 1 and blind["questions_hit_any@10"] == 1
    assert blind["violations"] == {"scope": 0, "lang": 0, "audience": 0, "unknown_row": 0}
    assert "x001" not in json.dumps(report)
    assert WALLS not in json.dumps(report, ensure_ascii=False)


def test_row_facts_come_from_the_index(bench: Bench) -> None:
    candidates = bench.candidates(WALLS)
    assert candidates and all(candidate.path for candidate in candidates)
    for candidate in candidates[:5]:
        facts = bench.facts(candidate)
        assert facts and all(row.sensitivity == "public" for row in facts)
    assert bench.violations(candidates, within=None, lang=None) == {
        "scope": 0,
        "lang": 0,
        "audience": 0,
        "unknown_row": 0,
    }


def test_violations_count_scope_tree_and_audience(
    bench: Bench, monkeypatch: pytest.MonkeyPatch
) -> None:
    from evals.retrieval_bench import Candidate, RowFacts

    canonical = next(iter(bench.snap.catalog.wiki_languages), None)
    rows = {
        "a": [RowFacts("moreau", canonical, "public")],
        "b": [RowFacts("nacrines", canonical, "public")],
        "c": [RowFacts("moreau", "xx", "public")],
        "d": [RowFacts("moreau", None, "internal")],
        "e": [],
    }
    monkeypatch.setattr(Bench, "facts", lambda self, candidate: rows[candidate.path])
    candidates = [Candidate(i, "page-section", (), path=name) for i, name in enumerate(rows, 1)]
    assert bench.violations(candidates, within="moreau", lang=None) == {
        "scope": 1,
        "lang": 1,
        "audience": 1,
        "unknown_row": 1,
    }
    assert bench.violations(candidates, within=None, lang=None)["scope"] == 0


def test_cli_writes_the_report(repo_root: Path, golden: Path, tmp_path: Path) -> None:
    out = tmp_path / "bench.json"
    code = main(
        [
            "--release",
            str(repo_root / "samples/fixtures/mock-release"),
            "--questions",
            str(golden),
            "--corpus",
            str(repo_root / "samples/corpus"),
            "--out",
            str(out),
            "--date",
            "2026-10-28",
        ]
    )
    assert code == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["format"] == "docwiki.evals.retrieval/v1"
    assert report["release"]["release_id"] == "20260401T090000Z-8a41b109"


# ------------------------------------------------------------------------------ hybrid


def _mock_db(repo_root: Path) -> Path:
    root = repo_root / "samples/fixtures/mock-release/releases"
    release_id = json.loads((root / "current.json").read_text(encoding="utf-8"))["release_id"]
    return root / release_id / "search.db"


def _lane_towards(
    repo_root: Path, question: str, locator_key: str, others: tuple[str, ...] = ()
) -> SemanticLane:
    """A lane whose question vector points exactly at the source block ``locator_key``."""
    db = _mock_db(repo_root)
    ids, _ = _row_inputs(db)
    rng = np.random.default_rng(7)
    matrix = rng.normal(size=(len(ids), 16)).astype(np.float32)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    try:
        (target,) = conn.execute(
            "SELECT rowid FROM docs WHERE kind = 'source-block' AND locator_key = ?",
            (locator_key,),
        ).fetchone()
    finally:
        conn.close()
    rowids = np.asarray(ids, dtype=np.int64)
    queries = {_text_key(text): matrix[0].copy() for text in others}
    queries[_text_key(question)] = matrix[ids.index(target)].copy()
    return SemanticLane(rowids, matrix, queries, model="test", dimensions=16, usage={})


def test_hybrid_brings_back_a_row_the_lexical_search_misses(repo_root: Path) -> None:
    question = "zzqx qqvv wwkk"
    lexical = Bench(repo_root / "samples/fixtures/mock-release", repo_root / "samples/corpus")
    assert lexical.candidates(question) == []
    hybrid = Bench(
        repo_root / "samples/fixtures/mock-release",
        repo_root / "samples/corpus",
        semantic=_lane_towards(repo_root, question, "para-0007"),
    )
    found = hybrid.candidates(question)
    assert found[0].kind == "source-block"
    assert found[0].locator_key == "para-0007"
    assert found[0].lanes == "semantic"
    assert len(found) <= hybrid.lane_depth
    assert hybrid.candidates(question) == found


def test_hybrid_fusion_keeps_lexical_hits_and_marks_both_lanes(repo_root: Path) -> None:
    lexical = Bench(repo_root / "samples/fixtures/mock-release", repo_root / "samples/corpus")
    hybrid = Bench(
        repo_root / "samples/fixtures/mock-release",
        repo_root / "samples/corpus",
        semantic=_lane_towards(repo_root, WALLS, "para-0007"),
    )
    plain = {(c.kind, c.path, c.anchor, c.locator_key) for c in lexical.candidates(WALLS)}
    fused = hybrid.candidates(WALLS)
    assert plain <= {(c.kind, c.path, c.anchor, c.locator_key) for c in fused}
    top = next(c for c in fused if c.locator_key == "para-0007")
    assert top.lanes == "both"
    assert top.rank == 1


def test_hybrid_semantic_lane_uses_the_lexical_filters(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    question = "zzqx qqvv wwkk"
    hybrid = Bench(
        repo_root / "samples/fixtures/mock-release",
        repo_root / "samples/corpus",
        semantic=_lane_towards(repo_root, question, "para-0007"),
    )
    calls: list[tuple[Any, ...]] = []

    def no_target(*args: Any) -> tuple[str, list[object]]:
        calls.append(args)
        return " AND d.locator_key IS NOT 'para-0007'", []

    monkeypatch.setattr(hybrid.snap.search, "_filters", no_target)
    found = hybrid.candidates(question)
    assert calls and calls[0][4:] == (None, None)
    assert found and all(c.locator_key != "para-0007" for c in found)


def test_hybrid_report_has_no_served_recall_and_records_lanes(
    repo_root: Path, golden: Path
) -> None:
    hybrid = Bench(
        repo_root / "samples/fixtures/mock-release",
        repo_root / "samples/corpus",
        semantic=_lane_towards(
            repo_root, WALLS, "para-0007", (WINDOWS, "Secret holdout phrasing about walls")
        ),
    )
    report = _report(hybrid, golden)
    assert report["mode"] == "hybrid"
    assert report["settings"]["served_limits"] == []
    assert report["settings"]["hybrid"]["rrf_k"] == 60
    assert report["settings"]["hybrid"]["lane_depth"] == 50
    dev = report["splits"]["dev"]
    assert "served_recall@5" not in dev
    assert dev["found_by_lanes"]["both"] >= 1
    first = report["questions"][0]["targets"][0]
    assert first["lanes"] == "both"
    paired = dev["paired_vs_lexical_hit_all@10"]
    lexical = _report(
        Bench(repo_root / "samples/fixtures/mock-release", repo_root / "samples/corpus"), golden
    )
    assert "paired_vs_lexical_hit_all@10" not in lexical["splits"]["dev"]
    assert paired["lexical"] == lexical["splits"]["dev"]["questions_hit_all@10"]
    assert paired["lexical"] + paired["gained"] - paired["lost"] == dev["questions_hit_all@10"]


def test_semantic_lane_build_caches_vectors_without_question_text(
    repo_root: Path, tmp_path: Path
) -> None:
    db = _mock_db(repo_root)
    question = "Quand les fenêtres sont-elles livrées ?"
    first = SemanticLane.build(db, [question], FakeEmbeddingClient(dimensions=32), tmp_path)
    assert first.usage["rows_embedded"] == first.matrix.shape[0] > 0
    assert first.usage["billed_tokens"]["rows"] > 0
    assert first.usage["billed_tokens"]["questions"] > 0
    assert np.allclose(np.linalg.norm(first.matrix, axis=1), 1.0, atol=1e-5)
    again = SemanticLane.build(db, [question], FakeEmbeddingClient(dimensions=32), tmp_path)
    assert again.usage["billed_tokens"] == {"rows": 0, "questions": 0}
    assert np.array_equal(again.matrix, first.matrix)
    assert np.array_equal(again.query(question), first.query(question))
    for file in tmp_path.iterdir():
        if file.suffix == ".json":
            assert "fenêtres" not in file.read_text(encoding="utf-8")
