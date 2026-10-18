from datetime import date
from pathlib import Path

import pytest

import docwiki.search.index as search_index
from docwiki.contracts.pages import Page, parse_frontmatter
from docwiki.search import (
    SearchBlock,
    SearchIndex,
    build_search_db,
    fts5_available,
    make_snippet,
    tokenize,
)

RELEASE = "20260131T080509Z-01234567"
SRC_MANUAL = "src-00000000000a"
SRC_SOP = "src-00000000000b"


def page(path: str, **fields: object) -> Page:
    data: dict[str, object] = {
        "summary": "Fictional sample.",
        "sensitivity": "public",
        "updated": date(2026, 1, 31),
        "docwiki": {"schema": 1, "release": RELEASE},
    }
    data.update(fields)
    body = str(data.pop("body"))
    return Page(path=path, frontmatter=parse_frontmatter(data), body=body)


def source(path: str, source_id: str, title: str, body: str, **extra: object) -> Page:
    return page(
        path,
        id=source_id,
        type="source",
        title=title,
        source_id=source_id,
        source_path=f"raw/{source_id}.pdf",
        source_hash="sha256:" + "a" * 64,
        media_type="application/pdf",
        doc_type="manual",
        category="oem",
        status="current",
        original_lang="en",
        authority=5,
        extraction={"adapter": "local", "version": "1"},
        body=body,
        **extra,
    )


PAGES = [
    source(
        "sources/gearbox-manual.md",
        SRC_MANUAL,
        "Litware gearbox manual",
        "# Litware gearbox manual\n\nOEM manual excerpt.\n\n## Key facts\n\n"
        "- The gearbox oil grade is ISO VG 320.[^c1]\n\n## Sources\n\n"
        "[^c1]: [Litware gearbox manual — p. 3](../evidence/src-00000000000a/p0003.md) · "
        "✓ quote verified\n",
        entities=["asset:wtg-07"],
        topics=["topic:gearbox-oil"],
    ),
    source(
        "sources/sop-gbx-010-rev-b.md",
        SRC_SOP,
        "Gearbox oil change SOP rev B",
        "# Gearbox oil change SOP rev B\n\nProcedure summary.\n\n## Safety\n\n"
        "Apply lockout/tagout before opening the nacelle.\n\n## Température\n\n"
        "La température minimale est de -20 °C.\n",
        entities=["procedure:sop-gbx-010"],
    ),
    page(
        "entities/asset/wtg-07.md",
        id="asset:wtg-07",
        type="entity",
        title="WTG-07",
        entity_type="asset",
        key="wtg-07",
        sources=[SRC_MANUAL],
        body=(
            "# WTG-07\n\nTurbine seven of the Contoso Renewables fleet.\n\n"
            "## Facts\n\n- Gearbox over-temperature alarms.\n"
        ),
    ),
    page(
        "topics/gearbox-oil.md",
        id="topic:gearbox-oil",
        type="topic",
        title="Gearbox oil",
        topic_slug="gearbox-oil",
        sources=[SRC_MANUAL, SRC_SOP],
        confidence="high",
        body="# Gearbox oil\n\n## Overview\n\nThe oil grade changed for cold sites.\n",
    ),
    page("index.md", id="index:home", type="index", title="Home", body="# Home\n\nStart here.\n"),
]
BLOCKS = [
    SearchBlock(
        source_id=SRC_MANUAL,
        page_id=SRC_MANUAL,
        path="sources/gearbox-manual.md",
        title="Litware gearbox manual",
        locator_key="p0007",
        section="p. 7",
        text="Torque the drain plug to 45 Nm after the oil change. Check the breather filter.",
        sensitivity="public",
        status="current",
        lang="en",
    ),
]
SYNONYMS = [("LOTO", "lockout/tagout", "en"), ("LOTO", "consignation", "fr")]


@pytest.fixture(params=["fts5", "bm25"])
def index(request: pytest.FixtureRequest, tmp_path: Path) -> SearchIndex:
    use_fts = request.param == "fts5"
    if use_fts and not fts5_available():
        pytest.skip("SQLite without FTS5")
    path = tmp_path / "search.db"
    info = build_search_db(
        PAGES, BLOCKS, SYNONYMS, path, release_id=RELEASE, audience="public", use_fts5=use_fts
    )
    assert info.fts5 is use_fts
    opened = SearchIndex.open(path)
    assert opened.backend == request.param
    yield opened
    opened.close()


def test_meta_and_rows(index: SearchIndex) -> None:
    assert index.meta["schema"] == "1"
    assert index.meta["release_id"] == RELEASE
    assert index.meta["audience"] == "public"
    assert index.meta["tokenizer"] == "unicode61 remove_diacritics 2"


def test_ranking_prefers_title_matches(index: SearchIndex) -> None:
    hits = index.search("gearbox oil")
    assert hits and hits[0].page_id == "topic:gearbox-oil"
    assert {hit.page_id for hit in hits} >= {"topic:gearbox-oil", SRC_MANUAL, SRC_SOP}


def test_source_blocks_are_searchable_with_locators(index: SearchIndex) -> None:
    hits = index.search("drain plug torque")
    assert hits[0].kind == "source-block"
    assert (hits[0].source_id, hits[0].locator_key, hits[0].section) == (
        SRC_MANUAL,
        "p0007",
        "p. 7",
    )
    assert "45 Nm" in hits[0].snippet


def test_page_sections_carry_anchors(index: SearchIndex) -> None:
    hit = index.search("ISO VG 320")[0]
    assert (hit.page_id, hit.section, hit.anchor) == (SRC_MANUAL, "Key facts", "key-facts")
    assert "[^c1]" not in hit.snippet and "evidence" not in hit.snippet


def test_synonym_expansion(index: SearchIndex) -> None:
    hits = index.search("LOTO")
    assert hits and hits[0].page_id == SRC_SOP and hits[0].section == "Safety"
    assert index.expand("loto procedure") == [
        ("consignation",),
        ("lockout", "tagout"),
        ("loto",),
        ("procedure",),
    ]


def test_diacritics_and_case_are_folded(index: SearchIndex) -> None:
    assert index.search("TEMPERATURE minimale")[0].section == "Température"


def test_filters(index: SearchIndex) -> None:
    assert {hit.kind for hit in index.search("oil", kinds=["source-block"])} == {"source-block"}
    assert {hit.page_id for hit in index.search("gearbox", types=["entity"])} == {"asset:wtg-07"}
    entity_hits = {hit.page_id for hit in index.search("gearbox", entity="asset:wtg-07")}
    assert entity_hits == {"asset:wtg-07", SRC_MANUAL}
    topic_hits = {hit.page_id for hit in index.search("oil", topic="topic:gearbox-oil")}
    assert topic_hits == {"topic:gearbox-oil", SRC_MANUAL}
    assert index.search("gearbox", limit=1) and len(index.search("gearbox", limit=1)) == 1
    assert (
        index.search("", limit=5) == []
        and index.search("!!!") == []
        and index.search("oil", limit=0) == []
    )
    assert index.search("nonexistentword") == []


def test_fts5_and_fallback_agree_on_top_hits(tmp_path: Path) -> None:
    if not fts5_available():
        pytest.skip("SQLite without FTS5")
    path = tmp_path / "search.db"
    build_search_db(PAGES, BLOCKS, SYNONYMS, path, use_fts5=True)
    with SearchIndex.open(path) as fts, SearchIndex.open(path, force_fallback=True) as fallback:
        assert (fts.backend, fallback.backend) == ("fts5", "bm25")
        for query in ("gearbox oil", "drain plug", "LOTO", "temperature", "WTG-07 alarms"):
            assert fts.search(query)[0].page_id == fallback.search(query)[0].page_id, query


def test_automatic_fallback_when_fts5_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(search_index, "fts5_available", lambda conn=None: False)
    path = tmp_path / "search.db"
    info = build_search_db(PAGES, BLOCKS, SYNONYMS, path)
    assert not info.fts5
    with SearchIndex.open(path) as index:
        assert index.backend == "bm25"
        assert index.meta["fts5"] == "0"
        assert index.search("breather filter")[0].locator_key == "p0007"


def test_build_is_deterministic_and_replaces_existing(tmp_path: Path) -> None:
    first, second = tmp_path / "a.db", tmp_path / "b.db"
    build_search_db(PAGES, BLOCKS, SYNONYMS, first, release_id=RELEASE)
    build_search_db(list(reversed(PAGES)), BLOCKS, SYNONYMS, second, release_id=RELEASE)
    assert first.read_bytes() == second.read_bytes()
    build_search_db(PAGES[:1], [], [], first)
    with SearchIndex.open(first) as index:
        assert {hit.page_id for hit in index.search("oil")} == {SRC_MANUAL}


def test_tokenize_and_snippets() -> None:
    assert tokenize("Getriebeöl-Wechsel, ISO_VG 320; Température") == [
        "getriebeol",
        "wechsel",
        "iso",
        "vg",
        "320",
        "temperature",
    ]
    text = (
        " ".join(f"w{i}" for i in range(60))
        + " target phrase here "
        + " ".join(f"z{i}" for i in range(60))
    )
    snippet = make_snippet(text, [("target", "phrase")])
    assert snippet.startswith("…") and snippet.endswith("…") and "target phrase" in snippet
    assert make_snippet("short text", [("missing",)]) == "short text"
    assert len(make_snippet("x " * 500, [("x",)])) <= 241
