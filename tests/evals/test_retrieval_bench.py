"""Offline retrieval bench on the committed mock release (no network, no model)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from evals.records import ToolCallRecord, tool_hits
from evals.retrieval_bench import Bench, load_bench_questions, main, release_stats, run

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
