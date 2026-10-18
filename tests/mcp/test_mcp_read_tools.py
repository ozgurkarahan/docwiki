"""Read tools on the committed mock release: happy paths and agent-correctable errors."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from typing import Any

import pytest
from mcp_testkit import PLAN, RELEASE_ID, SOP_A, SOP_B

from docwiki.mcp.tools_read import ReadTools, ToolInputError

Json = Callable[[str], dict[str, Any]]


def test_search_ranks_wiki_and_source_hits_with_locators(reads: ReadTools, as_json: Json) -> None:
    data = as_json(reads.search("cold sites ISO VG 220", limit=10))
    assert data["release_id"] == RELEASE_ID
    assert data["hits"], data
    top = data["hits"][0]
    assert {"page_id", "path", "title", "section", "anchor", "snippet", "score"} <= set(top)
    blocks = [hit for hit in data["hits"] if hit["kind"] == "source-block"]
    assert blocks, "source blocks must be searchable"
    cited = next(hit for hit in blocks if hit["source_id"] == SOP_B)
    assert cited["origin"] == "source"
    assert cited["locator_key"] == "para-0004"
    assert cited["locator_label"] == "¶ 4"
    assert cited["evidence_path"] == f"evidence/{SOP_B}/para-0004.md"
    assert cited["provenance"] == "native-text"
    superseded = [hit for hit in data["hits"] if hit.get("source_id") == SOP_A]
    assert all(hit["status"] == "superseded" for hit in superseded)


def test_search_expands_multilingual_synonyms(reads: ReadTools, as_json: Json) -> None:
    data = as_json(reads.search("éolienne"))
    assert "wtg" in data["expanded_terms"]
    assert "wind turbine generator" in data["expanded_terms"]
    assert any(hit["page_id"].startswith("asset:wtg") for hit in data["hits"])


def test_search_filters_and_paging(reads: ReadTools, as_json: Json) -> None:
    topics = as_json(reads.search("oil", types=["topic"]))
    assert {hit["page_id"] for hit in topics["hits"]} == {"topic:gearbox-oil"}
    by_topic = as_json(reads.search("oil", topic="gearbox-oil", kinds=["page-section"]))
    assert by_topic["hits"] and all(hit["kind"] == "page-section" for hit in by_topic["hits"])
    entity = as_json(reads.search("oil", entity="asset:wtg-12", limit=50))
    assert {hit["page_id"] for hit in entity["hits"]} <= {"asset:wtg-12", PLAN}
    first = as_json(reads.search("gearbox", limit=2))
    second = as_json(reads.search("gearbox", limit=2, offset=2))
    assert first["next_offset"] == 2 and second["offset"] == 2
    keys = {(h["page_id"], h["section"], h["kind"]) for h in first["hits"]}
    assert not keys & {(h["page_id"], h["section"], h["kind"]) for h in second["hits"]}
    with pytest.raises(ToolInputError, match="unknown entity"):
        reads.search("oil", entity="asset:nope")
    empty = as_json(reads.search("zzzxqv"))
    assert empty["hits"] == [] and "hint" in empty


def test_read_page_returns_frontmatter_markdown_citations_and_links(
    reads: ReadTools, as_json: Json
) -> None:
    data = as_json(reads.read_page("topic:gearbox-oil"))
    assert data["page_id"] == "topic:gearbox-oil" and data["type"] == "topic"
    assert data["frontmatter"]["contradictions"] == 1
    assert "## Contradictions" in data["markdown"]
    assert "docwiki:backlinks" not in data["markdown"] and "Referenced by" not in data["markdown"]
    assert "[^c1]:" not in data["markdown"], "footnote definitions become structured citations"
    labels = {item["label"]: item for item in data["citations"]}
    assert set(labels) == {"c1", "c2", "c3"}
    assert labels["c2"] == {
        "label": "c2",
        "source_title": "Maintenance plan 2026",
        "locator_label": 'sheet "Plan", rows 2–4',
        "source_id": PLAN,
        "locator_key": "sheet-plan-r0002-r0004",
        "evidence_path": f"evidence/{PLAN}/sheet-plan-r0002-r0004.md",
        "badge": "table",
        "provenance": "deterministic-table",
    }
    assert {link["page_id"] for link in data["links"]} >= {SOP_B, "asset:wtg-07"}
    assert data["truncated"] is False and data["next_offset"] is None
    assert "Contradictions" in data["sections"]


def test_read_page_resolves_paths_sections_and_anchors(reads: ReadTools, as_json: Json) -> None:
    by_path = as_json(reads.read_page("../sources/sop-gbx-010-rev-b.md"))
    assert by_path["page_id"] == SOP_B and by_path["status"] == "current"
    section = as_json(reads.read_page("sources/sop-gbx-010-rev-b.md#contents"))
    assert section["section"] == "Contents"
    assert "### Cold sites" in section["markdown"], "subsections belong to their section"
    assert "## Key facts" not in section["markdown"]
    assert [c["label"] for c in section["citations"]] == ["c1", "c2"]
    named = as_json(reads.read_page(SOP_B, section="Key facts"))
    assert named["markdown"].startswith("## Key facts")
    superseded = as_json(reads.read_page("sources/sop-gbx-010-rev-a"))
    assert superseded["status"] == "superseded"
    assert superseded["frontmatter"]["superseded_by"] == [SOP_B]


def test_read_page_errors_help_the_agent(reads: ReadTools) -> None:
    with pytest.raises(ToolInputError, match="Did you mean") as unknown:
        reads.read_page("topic:gearbox-oils")
    assert unknown.value.code == "not_found"
    assert "topic:gearbox-oil" in unknown.value.details["suggestions"]
    with pytest.raises(ToolInputError, match="get_evidence") as wrong_tool:
        reads.read_page(f"evidence/{SOP_B}/para-0004.md")
    assert wrong_tool.value.code == "invalid_argument"
    with pytest.raises(ToolInputError, match="sections of this page") as section:
        reads.read_page("topic:gearbox-oil", section="Nope")
    assert section.value.code == "not_found" and "Overview" in section.value.details["sections"]


def test_get_index_scopes(reads: ReadTools, as_json: Json) -> None:
    home = as_json(reads.get_index())
    assert home["page_id"] == "index:home" and "## How to navigate" in home["markdown"]
    assets = as_json(reads.get_index("entities/asset"))
    assert assets["path"] == "entities/asset/index.md"
    assert "entities/asset" in assets["scopes"] and "glossary" in assets["scopes"]
    assert as_json(reads.get_index("log"))["page_id"] == "log"
    with pytest.raises(ToolInputError, match="valid scopes"):
        reads.get_index("everything")


def test_get_links_merges_edge_kinds(reads: ReadTools, as_json: Json) -> None:
    data = as_json(reads.get_links("topic:gearbox-oil"))
    outgoing = {item["page_id"]: item for item in data["outgoing"]}
    assert outgoing[SOP_A]["kinds"] == ["cites", "topic-of"]
    assert outgoing[SOP_A]["status"] == "superseded"
    backlinks = {item["page_id"] for item in data["backlinks"]}
    assert "query:2026-02-12-cold-site-gearbox-oil" in backlinks
    rev_b = as_json(reads.get_links(SOP_B))
    assert any(i["page_id"] == SOP_A and "supersedes" in i["kinds"] for i in rev_b["outgoing"])


def test_glossary_matches_terms_and_synonyms(reads: ReadTools, as_json: Json) -> None:
    wtg = as_json(reads.glossary("wtg"))
    assert [m["term"] for m in wtg["matches"]] == ["WTG"]
    assert wtg["matches"][0]["definition"].startswith("Wind turbine generator")
    assert wtg["matches"][0]["see_also"][0]["page_id"] == "asset:wtg-07"
    french = as_json(reads.glossary("grade de viscosite iso"))
    assert french["matches"][0]["term"] == "ISO VG"
    assert as_json(reads.glossary())["total"] == 3
    missing = as_json(reads.glossary("blade pitch"))
    assert missing["matches"] == [] and "hint" in missing


def test_get_evidence_returns_verbatim_content_with_provenance(
    reads: ReadTools, as_json: Json
) -> None:
    data = as_json(reads.get_evidence(PLAN, "sheet-plan-r0002-r0004"))
    assert data["provenance"] == "deterministic-table" and data["badge"] == "table"
    assert data["locator_label"] == 'sheet "Plan", rows 2–4'
    assert data["locator"]["kind"] == "xlsx-rows"
    assert data["evidence_path"] == f"evidence/{PLAN}/sheet-plan-r0002-r0004.md"
    assert "| WTG-12 | Gearbox oil change | ISO VG 220 | 2026-05 | 6 |" in data["content"]
    assert data["source"]["source_path"] == "records/maintenance-plan-2026.xlsx"
    assert data["tables_available"] is True
    pdf = as_json(reads.get_evidence(SOP_A, "p0001.md"))
    assert pdf["provenance"] == "native-text" and pdf["source"]["status"] == "superseded"
    assert "Use ISO VG 320 gearbox oil for all turbines." in pdf["content"]


def test_get_evidence_errors(reads: ReadTools) -> None:
    with pytest.raises(ToolInputError, match="invalid source_id"):
        reads.get_evidence("SRC-1", "p0001")
    with pytest.raises(ToolInputError, match="invalid locator_key"):
        reads.get_evidence(SOP_A, "page one")
    with pytest.raises(ToolInputError, match=r"Available for .*p0001"):
        reads.get_evidence(SOP_A, "p0002")
    with pytest.raises(ToolInputError, match="unknown source"):
        reads.get_evidence("src-000000000000", "p0001")


def test_query_table_select_with_row_ids(reads: ReadTools, as_json: Json) -> None:
    data = as_json(
        reads.query_table(PLAN, "SELECT row_id, asset, hours FROM t01 WHERE hours > 5 ORDER BY 1")
    )
    assert data["columns"] == ["row_id", "asset", "hours"]
    assert data["rows"] == [["r0002", "WTG-07", 6], ["r0004", "WTG-12", 6]]
    assert data["truncated"] is False and data["row_limit"] == 200
    assert data["tables"][0]["table"] == "t01"
    assert ["oil_grade", "Oil grade", "VARCHAR"] in data["tables"][0]["columns"]
    assert data["tables"][0]["locator_label"] == 'sheet "Plan", rows 1–4'
    total = as_json(reads.query_table(PLAN, "SELECT sum(hours) AS total FROM t01"))
    assert total["rows"] == [[14]] and "note" in total
    cte = as_json(
        reads.query_table(
            PLAN,
            "-- hours per asset\nWITH h AS (SELECT asset, hours FROM t01) "
            "SELECT asset, sum(hours) AS hours FROM h GROUP BY asset ORDER BY asset",
        )
    )
    assert cte["rows"] == [["WTG-07", 8], ["WTG-12", 6]]


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM t01",
        "DROP TABLE t01",
        "SELECT 1; SELECT 2",
        "SELECT * FROM t01; DROP TABLE t01",
        "COPY t01 TO 'out.csv'",
        "ATTACH 'other.db'",
        "SELECT * FROM read_csv('secret.csv')",
        "PRAGMA database_list",
        "DESCRIBE t01",
        "SHOW TABLES",
        "/* comment */ INSERT INTO t01 VALUES ('r9999', 'x', 'y', 'z', 'w', 1)",
    ],
)
def test_query_table_rejects_non_select_and_multiple_statements(reads: ReadTools, sql: str) -> None:
    with pytest.raises(ToolInputError, match="query rejected") as rejected:
        reads.query_table(PLAN, sql)
    assert rejected.value.code == "invalid_argument"


def test_query_table_other_errors(reads: ReadTools) -> None:
    with pytest.raises(ToolInputError, match="has no tables"):
        reads.query_table(SOP_B, "SELECT 1")
    with pytest.raises(ToolInputError, match=r"t01\(asset"):
        reads.query_table(PLAN, "SELECT nope FROM t01")


def test_skills(reads: ReadTools, as_json: Json) -> None:
    listing = as_json(reads.list_skills())
    names = [skill["name"] for skill in listing["skills"]]
    assert names == ["cite-sources", "deep-research", "wiki-maintainer", "wiki-navigator"]
    assert listing["projections"] == [".agents/skills", ".claude/skills", ".github/skills"]
    skill = as_json(reads.get_skill("wiki-navigator"))
    assert skill["content"].startswith("---\nname: wiki-navigator")
    assert skill["path"] == ".agents/skills/wiki-navigator/SKILL.md"
    with pytest.raises(ToolInputError, match="available skills"):
        reads.get_skill("make-coffee")


def test_recent_changes_newest_first(reads: ReadTools, as_json: Json) -> None:
    data = as_json(reads.recent_changes(limit=2))
    assert [entry["action"] for entry in data["entries"]] == ["query", "topic"]
    assert data["total"] == 6 and data["next_offset"] == 2
    supersede = as_json(reads.recent_changes(limit=1, offset=2))["entries"][0]
    assert supersede["action"] == "supersede"
    assert [p["page_id"] for p in supersede["pages"]] == [SOP_A, SOP_B]
    assert "is superseded by" in supersede["details"]
    assert data["entries"][1]["details"] is None, "details only when they add information"
    assert as_json(reads.recent_changes(since=date(2026, 3, 1)))["entries"] == []


def test_every_read_result_is_compact_json(reads: ReadTools) -> None:
    text = reads.read_page("index:home")
    assert "\n  " not in text and json.loads(text)["page_id"] == "index:home"
