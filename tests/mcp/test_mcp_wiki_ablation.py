"""``DOCWIKI_MCP_WIKI_ABLATION=raw``: an evaluation server that hides the compiled wiki and serves
only the documents' extracted blocks (the "agent without the wiki" arm of an ablation)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pytest
from mcp_testkit import FIXTURE_ROOT, MINUTES, TOPIC_ID

from docwiki.mcp.config import McpConfig
from docwiki.mcp.source import FolderReleaseSource
from docwiki.mcp.tools_read import RAW_KIND, RAW_ONLY_HINT, ReadTools, ToolInputError

Json = Callable[[str], dict[str, Any]]
QUESTION = "date de livraison des fenêtres"


@pytest.fixture
def raw_reads() -> ReadTools:
    config = McpConfig(wiki_ablation="raw")
    return ReadTools(FolderReleaseSource(FIXTURE_ROOT, ttl_s=config.pointer_ttl_s), config)


def test_config_reads_the_flag_and_rejects_unknown_values() -> None:
    assert McpConfig.from_env({}).wiki_ablation == "off"
    assert McpConfig.from_env({"DOCWIKI_MCP_WIKI_ABLATION": "RAW"}).wiki_ablation == "raw"
    with pytest.raises(ValueError, match="DOCWIKI_MCP_WIKI_ABLATION"):
        McpConfig.from_env({"DOCWIKI_MCP_WIKI_ABLATION": "pages"})


def test_answer_context_serves_only_extracted_blocks(raw_reads: ReadTools, as_json: Json) -> None:
    data = as_json(raw_reads.answer_context(QUESTION))
    hits = data["hits"]
    assert hits and all(hit["kind"] == RAW_KIND and hit["origin"] == "source" for hit in hits)
    assert all("status" not in hit for hit in hits), "revision status is a compiled fact"
    assert {"home_index", "hub", "views"}.isdisjoint(data)
    assert data["hint"] == RAW_ONLY_HINT
    minutes = next(hit for hit in hits if hit.get("locator_key") == "para-0011")
    assert minutes["source_id"] == MINUTES and minutes["citations"]


def test_search_serves_only_extracted_blocks(raw_reads: ReadTools, as_json: Json) -> None:
    data = as_json(raw_reads.search(QUESTION))
    assert data["hits"] and {hit["kind"] for hit in data["hits"]} == {RAW_KIND}
    with pytest.raises(ToolInputError, match="switched off"):
        raw_reads.search(QUESTION, types=["topic"])
    with pytest.raises(ToolInputError, match="switched off"):
        raw_reads.search(QUESTION, kinds=["section"])


@pytest.mark.parametrize(
    ("tool", "call"),
    [
        ("read_page", lambda r: r.read_page("index")),
        ("get_index", lambda r: r.get_index()),
        ("get_links", lambda r: r.get_links("index")),
        ("glossary", lambda r: r.glossary()),
        ("get_skill", lambda r: r.get_skill("wiki-navigator")),
        ("list_skills", lambda r: r.list_skills()),
        ("recent_changes", lambda r: r.recent_changes()),
    ],
)
def test_wiki_tools_are_switched_off(
    raw_reads: ReadTools, tool: str, call: Callable[[ReadTools], str]
) -> None:
    with pytest.raises(ToolInputError, match=f"^{tool} is switched off") as caught:
        call(raw_reads)
    assert caught.value.code == "not_found"
    assert caught.value.details == {"wiki_ablation": "raw"}


def test_not_found_recovery_distinguishes_raw_tools_from_bad_arguments(
    reads: ReadTools, raw_reads: ReadTools
) -> None:
    with pytest.raises(ToolInputError) as unknown:
        reads.read_page("topic:plannin")
    assert unknown.value.code == "not_found"
    assert TOPIC_ID in unknown.value.details["suggestions"]
    assert "wiki_ablation" not in unknown.value.details
    # Recovery on the same tool remains valid for a corrected page argument.
    assert reads.read_page(TOPIC_ID)
    with pytest.raises(ToolInputError) as unavailable:
        raw_reads.read_page(TOPIC_ID)
    assert unavailable.value.code == "not_found"
    assert unavailable.value.details == {"wiki_ablation": "raw"}


def test_evidence_and_tables_stay_available(raw_reads: ReadTools, as_json: Json) -> None:
    data = as_json(raw_reads.get_evidence(MINUTES, "para-0011"))
    assert "20/04/2026" in json.dumps(data, ensure_ascii=False)


def test_default_server_is_unchanged(reads: ReadTools, as_json: Json) -> None:
    data = as_json(reads.answer_context(QUESTION))
    assert "home_index" in data
    assert as_json(reads.get_index())["ok"] is True
