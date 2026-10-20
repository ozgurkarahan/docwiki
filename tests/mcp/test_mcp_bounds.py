"""Output bounds: every result fits the character budget and pages losslessly."""

from __future__ import annotations

import json
from typing import Any

import pytest
from mcp_testkit import PLAN_B, TOPIC_ID

from docwiki.mcp.bounds import ResultTooLargeError, clip, fit_items, fit_text, result_json
from docwiki.mcp.config import MIN_MAX_CHARS, McpConfig
from docwiki.mcp.source import FolderReleaseSource
from docwiki.mcp.tools_ops import OpsTools
from docwiki.mcp.tools_read import ReadTools


def test_fit_text_pages_losslessly_and_prefers_line_breaks() -> None:
    text = "".join(f'line {n:03d} with some words, quotes " and accents é\n' for n in range(200))

    def build(window: str, next_offset: int | None) -> dict[str, Any]:
        return {"text": window, "next_offset": next_offset, "truncated": next_offset is not None}

    pieces: list[str] = []
    offset: int | None = 0
    calls = 0
    while offset is not None:
        out = fit_text(text, offset, build, 1500)
        assert len(out) <= 1500
        data = json.loads(out)
        pieces.append(data["text"])
        assert data["text"].endswith("\n"), "windows end at a line break when possible"
        offset = data["next_offset"]
        calls += 1
    assert "".join(pieces) == text and calls > 5


def test_fit_items_keeps_the_longest_prefix() -> None:
    items = [{"n": n, "pad": "x" * 50} for n in range(100)]

    def build(chunk: Any, truncated: bool) -> dict[str, Any]:
        return {"items": list(chunk), "truncated": truncated}

    out, count = fit_items(items, build, 1000)
    data = json.loads(out)
    assert len(out) <= 1000 and data["truncated"] is True
    assert count == len(data["items"]) and 0 < count < 100
    assert len(result_json(build(items[: count + 1], True))) > 1000
    assert data["ok"] is True and out.startswith('{"ok":true,')
    full, total = fit_items(items[:3], build, 1000)
    assert total == 3 and json.loads(full)["truncated"] is False
    with pytest.raises(ResultTooLargeError):
        fit_items(items, lambda chunk, _: {"items": list(chunk), "pad": "y" * 2000}, 1000)
    with pytest.raises(ResultTooLargeError):
        fit_text("abc", 0, lambda window, _: {"pad": "y" * 2000, "t": window}, 1000)


def test_clip() -> None:
    assert clip(None, 3) is None and clip("abc", 3) == "abc"
    assert clip("abcdef", 4) == "abc…"


@pytest.fixture
def tight() -> ReadTools:
    config = McpConfig(max_chars=MIN_MAX_CHARS)
    from mcp_testkit import FIXTURE_ROOT

    return ReadTools(FolderReleaseSource(FIXTURE_ROOT), config)


def test_read_page_pages_under_a_tight_budget(tight: ReadTools) -> None:
    full = json.loads(ReadTools(tight.source, McpConfig()).read_page(TOPIC_ID))
    pieces: list[str] = []
    offset: int | None = 0
    labels: set[str] = set()
    while offset is not None:
        out = tight.read_page(TOPIC_ID, offset=offset)
        assert len(out) <= MIN_MAX_CHARS
        data = json.loads(out)
        pieces.append(data["markdown"])
        labels |= {citation["label"] for citation in data["citations"]}
        if data["next_offset"] is not None:
            assert data["truncated"] is True and "hint" in data
        offset = data["next_offset"]
    assert "".join(pieces) == full["markdown"]
    assert labels == {"c1", "c2", "c3", "c4", "c5"}, "each window carries its citations"


CROSS_JOIN = (
    "SELECT a.row_id, a.n_commande, b.row_id AS other, b.n_commande AS other_order "
    "FROM t02 AS a, t02 AS b"
)


@pytest.mark.parametrize(
    ("name", "kwargs"),
    [
        ("search", {"query": "livraison des menuiseries du planning", "limit": 50}),
        ("read_page", {"page": "index:home"}),
        ("read_page", {"page": PLAN_B}),
        ("get_index", {"scope": "home"}),
        ("get_links", {"page": TOPIC_ID}),
        ("glossary", {}),
        ("get_evidence", {"source_id": PLAN_B, "locator_key": "sheet-planning-r0006-r0009"}),
        ("query_table", {"source_id": PLAN_B, "sql": f"{CROSS_JOIN}, t02 AS c"}),
        ("get_skill", {"name": "deep-research"}),
        ("list_skills", {}),
        ("recent_changes", {"limit": 100}),
    ],
)
def test_every_read_tool_respects_the_budget(
    tight: ReadTools, name: str, kwargs: dict[str, Any]
) -> None:
    out = getattr(tight, name)(**kwargs)
    assert len(out) <= MIN_MAX_CHARS
    data = json.loads(out)
    assert "truncated" in data
    if data["truncated"]:
        assert data.get("next_offset") is not None or name == "query_table"


def test_query_table_char_budget_drops_rows(tight: ReadTools) -> None:
    data = json.loads(tight.query_table(PLAN_B, CROSS_JOIN))
    assert data["truncated"] is True and 0 < data["row_count"] < 64 and "hint" in data


def test_ops_results_respect_the_budget(
    work_storage: Any, seeded: dict[str, Any], tight: ReadTools
) -> None:
    from mcp_testkit import NOW

    from docwiki.mcp.ingest_queue import FolderQueue
    from docwiki.mcp.workstore import WorkStore

    ops = OpsTools(
        tight.source,
        tight.config,
        store_factory=lambda: WorkStore(work_storage),
        queue_factory=lambda: FolderQueue(work_storage),
        clock=lambda: NOW,
    )
    for out in (
        ops.run_status(),
        ops.list_sources(limit=200),
        ops.quality_report(),
        ops.explain_source(seeded["broken_id"]),
        ops.list_proposals(limit=100),
    ):
        assert len(out) <= MIN_MAX_CHARS
        json.loads(out)


def test_config_rejects_tiny_budgets() -> None:
    with pytest.raises(ValueError, match="DOCWIKI_MCP_MAX_CHARS"):
        McpConfig(max_chars=100)
