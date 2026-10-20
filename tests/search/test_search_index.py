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
SRC_QUOTE = "src-00000000000a"
SRC_MINUTES = "src-00000000000b"
TOPIC = "topic:quotes-contract-and-amendment"
BAIE = "building-element:baie-f1"


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
        doc_type="quote",
        category="contract-documents",
        status="current",
        original_lang="fr",
        authority=8,
        extraction={"adapter": "local", "version": "1"},
        body=body,
        **extra,
    )


PAGES = [
    source(
        "sources/quote-dev-2026-014-indice-b.md",
        SRC_QUOTE,
        "Quote DEV-2026-014 indice B",
        "# Quote DEV-2026-014 indice B\n\nQuote of the extension, referred to by the works "
        "contract.\n\n## Key facts\n\n"
        "- The sliding aluminium bay window F1 measures 3,00 x 2,15 m.[^c1]\n\n"
        "## Prices\n\nAll amounts are given excluding VAT.\n\n## Sources\n\n"
        "[^c1]: [Quote DEV-2026-014 indice B — p. 2](../evidence/src-00000000000a/p0002.md) · "
        "✓ quote verified\n",
        entities=[BAIE],
        topics=[TOPIC],
    ),
    source(
        "sources/2026-03-24-compte-rendu-de-chantier-n3.md",
        SRC_MINUTES,
        "Site meeting minutes n°3",
        "# Site meeting minutes n°3\n\nMinutes with the decisions on the amendment n°1.\n\n"
        "## Decisions\n\n"
        "The roof window of the amendment is installed with the roofing.\n\n## Réception\n\n"
        "La réception des travaux est maintenue au 15/05/2026.\n",
        entities=["commercial-document:pln-2026-003"],
    ),
    page(
        "entities/building-element/baie-f1.md",
        id=BAIE,
        type="entity",
        title="Baie F1",
        entity_type="building-element",
        key="baie-f1",
        sources=[SRC_QUOTE],
        body=(
            "# Baie F1\n\nBay window F1 of the extension of the Moreau house.\n\n"
            "## Facts\n\n- Delivery postponed by the window maker.\n"
        ),
    ),
    page(
        "topics/quotes-contract-and-amendment.md",
        id=TOPIC,
        type="topic",
        title="Quotes, contract and amendment",
        topic_slug="quotes-contract-and-amendment",
        sources=[SRC_QUOTE, SRC_MINUTES],
        confidence="high",
        body=(
            "# Quotes, contract and amendment\n\n## Overview\n\n"
            "The quote revision widened the window.\n"
        ),
    ),
    page("index.md", id="index:home", type="index", title="Home", body="# Home\n\nStart here.\n"),
]
BLOCKS = [
    SearchBlock(
        source_id=SRC_QUOTE,
        page_id=SRC_QUOTE,
        path="sources/quote-dev-2026-014-indice-b.md",
        title="Quote DEV-2026-014 indice B",
        locator_key="p0007",
        section="p. 7",
        text="Pose de la baie F1 : largeur 3,00 m, hauteur 2,15 m. "
        "Vérifier le joint d'étanchéité de la baie.",
        sensitivity="public",
        status="current",
        lang="fr",
    ),
]
SYNONYMS = [("HT", "excluding VAT", "en"), ("HT", "hors taxes", "fr")]


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
    hits = index.search("contract amendment")
    assert hits and hits[0].page_id == TOPIC
    assert {hit.page_id for hit in hits} >= {TOPIC, SRC_QUOTE, SRC_MINUTES}


def test_source_blocks_are_searchable_with_locators(index: SearchIndex) -> None:
    hits = index.search("largeur hauteur")
    assert hits[0].kind == "source-block"
    assert (hits[0].source_id, hits[0].locator_key, hits[0].section) == (
        SRC_QUOTE,
        "p0007",
        "p. 7",
    )
    assert "3,00 m" in hits[0].snippet


def test_page_sections_carry_anchors(index: SearchIndex) -> None:
    hit = index.search("sliding aluminium")[0]
    assert (hit.page_id, hit.section, hit.anchor) == (SRC_QUOTE, "Key facts", "key-facts")
    assert "[^c1]" not in hit.snippet and "evidence" not in hit.snippet


def test_synonym_expansion(index: SearchIndex) -> None:
    hits = index.search("HT")
    assert hits and hits[0].page_id == SRC_QUOTE and hits[0].section == "Prices"
    assert index.expand("ht quote") == [
        ("excluding", "vat"),
        ("hors", "taxes"),
        ("ht",),
        ("quote",),
    ]


def test_diacritics_and_case_are_folded(index: SearchIndex) -> None:
    assert index.search("RECEPTION maintenue")[0].section == "Réception"


def test_filters(index: SearchIndex) -> None:
    assert {hit.kind for hit in index.search("baie", kinds=["source-block"])} == {"source-block"}
    assert {hit.page_id for hit in index.search("window", types=["entity"])} == {BAIE}
    entity_hits = {hit.page_id for hit in index.search("window", entity=BAIE)}
    assert entity_hits == {BAIE, SRC_QUOTE}
    topic_hits = {hit.page_id for hit in index.search("window", topic=TOPIC)}
    assert topic_hits == {TOPIC, SRC_QUOTE}
    assert index.search("window", limit=1) and len(index.search("window", limit=1)) == 1
    assert (
        index.search("", limit=5) == []
        and index.search("!!!") == []
        and index.search("window", limit=0) == []
    )
    assert index.search("nonexistentword") == []


def test_fts5_and_fallback_agree_on_top_hits(tmp_path: Path) -> None:
    if not fts5_available():
        pytest.skip("SQLite without FTS5")
    path = tmp_path / "search.db"
    build_search_db(PAGES, BLOCKS, SYNONYMS, path, use_fts5=True)
    with SearchIndex.open(path) as fts, SearchIndex.open(path, force_fallback=True) as fallback:
        assert (fts.backend, fallback.backend) == ("fts5", "bm25")
        for query in ("contract amendment", "largeur hauteur", "HT", "reception", "F1 bay window"):
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
        assert index.search("joint étanchéité")[0].locator_key == "p0007"


def test_build_is_deterministic_and_replaces_existing(tmp_path: Path) -> None:
    first, second = tmp_path / "a.db", tmp_path / "b.db"
    build_search_db(PAGES, BLOCKS, SYNONYMS, first, release_id=RELEASE)
    build_search_db(list(reversed(PAGES)), BLOCKS, SYNONYMS, second, release_id=RELEASE)
    assert first.read_bytes() == second.read_bytes()
    build_search_db(PAGES[:1], [], [], first)
    with SearchIndex.open(first) as index:
        assert {hit.page_id for hit in index.search("window")} == {SRC_QUOTE}


def test_tokenize_and_snippets() -> None:
    assert tokenize("Élévation-des-murs, BC_2026 009; Réception") == [
        "elevation",
        "des",
        "murs",
        "bc",
        "2026",
        "009",
        "reception",
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
