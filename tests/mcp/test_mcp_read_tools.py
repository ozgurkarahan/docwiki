"""Read tools on the committed mock release: happy paths and agent-correctable errors."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from typing import Any

import pytest
from mcp_testkit import MINUTES, PLAN_A, PLAN_B, RELEASE_ID, TOPIC_ID

from docwiki.mcp.tools_read import ReadTools, ToolInputError

Json = Callable[[str], dict[str, Any]]
LOT_5 = "work-package:lot-5-menuiseries-exterieures"


def test_search_ranks_wiki_and_source_hits_with_locators(reads: ReadTools, as_json: Json) -> None:
    data = as_json(reads.search("annoncé report livraison menuiseries", limit=10))
    assert data["release_id"] == RELEASE_ID
    assert data["hits"], data
    top = data["hits"][0]
    assert {"page_id", "path", "title", "section", "anchor", "snippet", "score"} <= set(top)
    blocks = [hit for hit in data["hits"] if hit["kind"] == "source-block"]
    assert blocks, "source blocks must be searchable"
    cited = next(hit for hit in blocks if hit["source_id"] == MINUTES)
    assert cited["origin"] == "source"
    assert cited["locator_key"] == "para-0011"
    assert cited["locator_label"] == "¶ 11"
    assert cited["evidence_path"] == f"evidence/{MINUTES}/para-0011.md"
    assert cited["provenance"] == "native-text"
    superseded = [hit for hit in data["hits"] if hit.get("source_id") == PLAN_A]
    assert all(hit["status"] == "superseded" for hit in superseded)


def test_search_expands_multilingual_synonyms(reads: ReadTools, as_json: Json) -> None:
    data = as_json(reads.search("menuiseries extérieures"))
    assert "exterior joinery" in data["expanded_terms"]
    assert "windows and external doors" in data["expanded_terms"]
    assert any(hit["page_id"] == LOT_5 for hit in data["hits"])


def test_search_filters_and_paging(reads: ReadTools, as_json: Json) -> None:
    topics = as_json(reads.search("window", types=["topic"]))
    assert {hit["page_id"] for hit in topics["hits"]} == {TOPIC_ID}
    by_topic = as_json(
        reads.search("window", topic="planning", kinds=["page-section"])
    )
    assert by_topic["hits"] and all(hit["kind"] == "page-section" for hit in by_topic["hits"])
    entity = as_json(reads.search("window", entity="work-package:lot-3-gros-oeuvre", limit=50))
    assert {hit["page_id"] for hit in entity["hits"]} <= {
        "work-package:lot-3-gros-oeuvre",
        PLAN_A,
        PLAN_B,
        MINUTES,
    }
    first = as_json(reads.search("menuiseries", limit=2))
    second = as_json(reads.search("menuiseries", limit=2, offset=2))
    assert first["next_offset"] == 2 and second["offset"] == 2
    keys = {(h["page_id"], h["section"], h["kind"]) for h in first["hits"]}
    assert not keys & {(h["page_id"], h["section"], h["kind"]) for h in second["hits"]}
    with pytest.raises(ToolInputError, match="unknown entity"):
        reads.search("window", entity="work-package:lot-99-nope")
    empty = as_json(reads.search("zzzxqv"))
    assert empty["hits"] == [] and "hint" in empty


def test_read_page_returns_frontmatter_markdown_citations_and_links(
    reads: ReadTools, as_json: Json
) -> None:
    data = as_json(reads.read_page(TOPIC_ID))
    assert data["page_id"] == TOPIC_ID and data["type"] == "topic"
    assert data["frontmatter"]["contradictions"] == 1
    assert "## Contradictions" in data["markdown"]
    assert "docwiki:backlinks" not in data["markdown"] and "Referenced by" not in data["markdown"]
    assert "[^c1]:" not in data["markdown"], "footnote definitions become structured citations"
    labels = {item["label"]: item for item in data["citations"]}
    assert set(labels) == {"c1", "c2", "c3", "c4", "c5"}
    assert labels["c1"] == {
        "label": "c1",
        "source_title": "Planning and purchase tracking, indice B",
        "locator_label": 'sheet "Planning", rows 6–9',
        "source_id": PLAN_B,
        "locator_key": "sheet-planning-r0006-r0009",
        "evidence_path": f"evidence/{PLAN_B}/sheet-planning-r0006-r0009.md",
        "badge": "table",
        "provenance": "deterministic-table",
    }
    assert {link["page_id"] for link in data["links"]} >= {PLAN_B, LOT_5}
    assert data["truncated"] is False and data["next_offset"] is None
    assert "Contradictions" in data["sections"]


def test_read_page_resolves_paths_sections_and_anchors(reads: ReadTools, as_json: Json) -> None:
    page = "sources/pln-2026-003-indice-b-planning-et-suivi-des-achats.md"
    by_path = as_json(reads.read_page(f"../{page}"))
    assert by_path["page_id"] == PLAN_B and by_path["status"] == "current"
    section = as_json(reads.read_page(f"{page}#contents"))
    assert section["section"] == "Contents"
    assert '### Sheet "Planning"' in section["markdown"], "subsections belong to their section"
    assert "## Key facts" not in section["markdown"]
    assert [c["label"] for c in section["citations"]] == ["c2", "c1"]
    named = as_json(reads.read_page(PLAN_B, section="Key facts"))
    assert named["markdown"].startswith("## Key facts")
    superseded = as_json(
        reads.read_page("sources/pln-2026-003-indice-a-planning-et-suivi-des-achats")
    )
    assert superseded["status"] == "superseded"
    assert superseded["frontmatter"]["superseded_by"] == [PLAN_B]


def test_read_page_errors_help_the_agent(reads: ReadTools) -> None:
    with pytest.raises(ToolInputError, match="Did you mean") as unknown:
        reads.read_page("topic:plannin")
    assert unknown.value.code == "not_found"
    assert TOPIC_ID in unknown.value.details["suggestions"]
    with pytest.raises(ToolInputError, match="get_evidence") as wrong_tool:
        reads.read_page(f"evidence/{MINUTES}/para-0011.md")
    assert wrong_tool.value.code == "invalid_argument"
    with pytest.raises(ToolInputError, match="sections of this page") as section:
        reads.read_page(TOPIC_ID, section="Nope")
    assert section.value.code == "not_found" and "Overview" in section.value.details["sections"]


def test_get_index_scopes(reads: ReadTools, as_json: Json) -> None:
    home = as_json(reads.get_index())
    assert home["page_id"] == "index:home" and "## How to navigate" in home["markdown"]
    packages = as_json(reads.get_index("entities/work-package"))
    assert packages["path"] == "entities/work-package/index.md"
    assert "entities/work-package" in packages["scopes"] and "glossary" in packages["scopes"]
    assert as_json(reads.get_index("log"))["page_id"] == "log"
    with pytest.raises(ToolInputError, match="valid scopes"):
        reads.get_index("everything")


def test_get_links_merges_edge_kinds(reads: ReadTools, as_json: Json) -> None:
    data = as_json(reads.get_links(TOPIC_ID))
    outgoing = {item["page_id"]: item for item in data["outgoing"]}
    assert outgoing[PLAN_A]["kinds"] == ["cites", "topic-of"]
    assert outgoing[PLAN_A]["status"] == "superseded"
    backlinks = {item["page_id"] for item in data["backlinks"]}
    assert "query:2026-03-31-window-delivery-date" in backlinks
    plan_b = as_json(reads.get_links(PLAN_B))
    assert any(i["page_id"] == PLAN_A and "supersedes" in i["kinds"] for i in plan_b["outgoing"])


def test_glossary_matches_terms_and_synonyms(reads: ReadTools, as_json: Json) -> None:
    joinery = as_json(reads.glossary("exterior joinery"))
    assert [m["term"] for m in joinery["matches"]] == ["windows and external doors"]
    assert joinery["matches"][0]["definition"].startswith("The windows, glazed doors")
    assert joinery["matches"][0]["see_also"][0]["page_id"] == LOT_5
    french = as_json(reads.glossary("menuiseries exterieures"))
    assert french["matches"][0]["term"] == "windows and external doors"
    assert as_json(reads.glossary())["total"] == 3
    missing = as_json(reads.glossary("cement mixer"))
    assert missing["matches"] == [] and "hint" in missing


def test_get_evidence_returns_verbatim_content_with_provenance(
    reads: ReadTools, as_json: Json
) -> None:
    data = as_json(reads.get_evidence(PLAN_B, "sheet-planning-r0006-r0009"))
    assert data["provenance"] == "deterministic-table" and data["badge"] == "table"
    assert data["locator_label"] == 'sheet "Planning", rows 6–9'
    assert data["locator"]["kind"] == "xlsx-rows"
    assert data["evidence_path"] == f"evidence/{PLAN_B}/sheet-planning-r0006-r0009.md"
    assert "| T07 | Livraison des menuiseries | 5 | VanArsdel Menuiseries |" in data["content"]
    assert data["source"]["source_path"] == (
        "chantiers/moreau/3-execution/schedule/PLN-2026-003_indice-B_planning-et-suivi-des-achats.xlsx"
    )
    assert data["tables_available"] is True
    pdf = as_json(reads.get_evidence(PLAN_A, "p0001.md"))
    assert pdf["provenance"] == "native-text" and pdf["source"]["status"] == "superseded"
    assert "T07 Livraison des menuiseries 5 VanArsdel Menuiseries 2026-03-30" in pdf["content"]


def test_get_evidence_errors(reads: ReadTools) -> None:
    with pytest.raises(ToolInputError, match="invalid source_id"):
        reads.get_evidence("SRC-1", "p0001")
    with pytest.raises(ToolInputError, match="invalid locator_key"):
        reads.get_evidence(PLAN_A, "page one")
    with pytest.raises(ToolInputError, match=r"Available for .*p0001"):
        reads.get_evidence(PLAN_A, "p0002")
    with pytest.raises(ToolInputError, match="unknown source"):
        reads.get_evidence("src-000000000000", "p0001")


def test_query_table_select_with_row_ids(reads: ReadTools, as_json: Json) -> None:
    data = as_json(
        reads.query_table(
            PLAN_B,
            "SELECT row_id, n_commande, facture_ht FROM t02 "
            "WHERE n_commande LIKE 'BC-%' AND facture_ht > 900 ORDER BY 1",
        )
    )
    assert data["columns"] == ["row_id", "n_commande", "facture_ht"]
    assert data["rows"] == [
        ["r0003", "BC-2026-009", 996.0],
        ["r0004", "BC-2026-010", 4386.5],
        ["r0005", "BC-2026-012", 1484.8],
    ]
    assert data["truncated"] is False and data["row_limit"] == 200
    assert [table["table"] for table in data["tables"]] == ["t01", "t02"]
    achats = data["tables"][1]
    assert ["commande_ht", "Commandé HT", "DOUBLE"] in achats["columns"]
    assert achats["locator_label"] == 'sheet "Achats", rows 1–9'
    total = as_json(
        reads.query_table(
            PLAN_B,
            "SELECT round(sum(commande_ht), 2) AS total FROM t02 WHERE n_commande LIKE 'BC-%'",
        )
    )
    assert total["rows"] == [[15157.3]] and "note" in total
    cte = as_json(
        reads.query_table(
            PLAN_B,
            "-- orders per supplier\nWITH o AS (SELECT fournisseur FROM t02 "
            "WHERE n_commande LIKE 'BC-%') "
            "SELECT fournisseur, count(*) AS orders FROM o GROUP BY fournisseur "
            "ORDER BY fournisseur",
        )
    )
    assert cte["rows"] == [
        ["Adatum Électricité", 1],
        ["VanArsdel Menuiseries", 1],
        ["Zava Matériaux", 4],
    ]


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
        reads.query_table(PLAN_B, sql)
    assert rejected.value.code == "invalid_argument"


def test_query_table_other_errors(reads: ReadTools) -> None:
    with pytest.raises(ToolInputError, match="has no tables"):
        reads.query_table(MINUTES, "SELECT 1")
    with pytest.raises(ToolInputError, match=r"t01\(tache"):
        reads.query_table(PLAN_B, "SELECT nope FROM t01")


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
    assert [p["page_id"] for p in supersede["pages"]] == [PLAN_A, PLAN_B]
    assert "is superseded by" in supersede["details"]
    assert data["entries"][1]["details"] is None, "details only when they add information"
    assert as_json(reads.recent_changes(since=date(2026, 4, 2)))["entries"] == []


def test_every_read_result_is_compact_json(reads: ReadTools) -> None:
    text = reads.read_page("index:home")
    assert "\n  " not in text and json.loads(text)["page_id"] == "index:home"
