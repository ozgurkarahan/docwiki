import hashlib
import unicodedata
from datetime import UTC, date, datetime

import pytest

from docwiki.contracts.ids import (
    assign_source_slugs,
    assign_unique_slugs,
    cache_key,
    check_wiki_path,
    entity_page_path,
    format_entity_id,
    format_query_id,
    format_release_id,
    format_topic_id,
    index_page_path,
    new_run_id,
    normalize_tags,
    parse_entity_id,
    parse_query_id,
    parse_release_id,
    parse_topic_id,
    proposal_id_for,
    query_page_path,
    slugify_ascii,
    source_id_for,
    topic_page_path,
)


def test_source_id_matches_spec_formula() -> None:
    path = "devis/Devis Extension.pdf"
    expected = "src-" + hashlib.sha256(path.lower().encode("utf-8")).hexdigest()[:12]
    assert source_id_for(path) == expected


def test_source_id_is_case_and_normalisation_insensitive() -> None:
    nfc = "réunions/Compte rendu n3.docx"
    nfd = unicodedata.normalize("NFD", nfc)
    assert nfc != nfd
    assert source_id_for(nfc) == source_id_for(nfd) == source_id_for(nfc.upper())
    assert source_id_for("./a/b.pdf") == source_id_for("a/b.pdf")
    assert source_id_for("a/b.pdf") != source_id_for("a/c.pdf")


@pytest.mark.parametrize(
    "bad", ["", "/abs/x.pdf", "a\\b.pdf", "a/../b.pdf", "a//b.pdf", "C:/x.pdf", "a/\x01.pdf"]
)
def test_source_id_rejects_non_posix_relative_paths(bad: str) -> None:
    with pytest.raises(ValueError):
        source_id_for(bad)


@pytest.mark.parametrize(
    ("text", "slug"),
    [
        ("Devis Extension", "devis-extension"),
        ("Réception des travaux — Indice B", "reception-des-travaux-indice-b"),
        ("  DEV_2026__014 (final)  ", "dev-2026-014-final"),
        ("Straße Œuvre Ærø", "strasse-oeuvre-aero"),
        ("Façade-Élévation", "facade-elevation"),
        ("---", ""),
        ("日本語", ""),
        ("Ａｂｃ　１２３", "abc-123"),
    ],
)
def test_slugify_ascii(text: str, slug: str) -> None:
    assert slugify_ascii(text) == slug


def test_slugify_truncates_without_trailing_dash() -> None:
    slug = slugify_ascii("word " * 30, max_len=12)
    assert slug == "word-word-wo"
    assert slugify_ascii("abcde fghij", max_len=6) == "abcde"
    assert len(slugify_ascii("x" * 100)) == 60


def test_assign_source_slugs_suffixes_every_collision_order_independently() -> None:
    a, b, c = (
        source_id_for("a/Report.pdf"),
        source_id_for("b/report.docx"),
        source_id_for("c/other.pdf"),
    )
    stems = {a: "Report", b: "report", c: "Other"}
    first = assign_source_slugs(stems)
    second = assign_source_slugs(dict(reversed(list(stems.items()))))
    assert first == second
    assert first[c] == "other"
    assert first[a] == f"report-{a[4:8]}"
    assert first[b] == f"report-{b[4:8]}"
    assert len(set(first.values())) == 3


def test_assign_source_slugs_keeps_existing_assignments() -> None:
    a, b = source_id_for("a/Report.pdf"), source_id_for("b/report.docx")
    first = assign_source_slugs({a: "Report"})
    assert first == {a: "report"}
    second = assign_source_slugs({a: "Report", b: "report"}, existing=first)
    assert second[a] == "report"
    assert second[b] == f"report-{b[4:8]}"


def test_assign_source_slugs_handles_suffix_clash_long_names_and_empty_stems() -> None:
    a = source_id_for("x/a.pdf")
    b = source_id_for("y/a.pdf")
    clash = f"a-{a[4:8]}"
    c = source_id_for("z/c.pdf")
    slugs = assign_source_slugs({a: "a", b: "a", c: clash})
    assert slugs[c] != slugs[a] and len(set(slugs.values())) == 3
    long_a, long_b = source_id_for("1.pdf"), source_id_for("2.pdf")
    long_slugs = assign_source_slugs({long_a: "z" * 80, long_b: "z" * 80})
    assert all(len(slug) <= 60 for slug in long_slugs.values())
    empty = source_id_for("only-cjk/日本.pdf")
    assert assign_source_slugs({empty: "日本"})[empty] == empty


def test_assign_unique_slugs_for_sheets() -> None:
    assert assign_unique_slugs(["Planning", "planning", "Planning!", "計画"], fallback="sheet") == [
        "planning",
        "planning-2",
        "planning-3",
        "sheet",
    ]


def test_entity_topic_and_query_ids() -> None:
    assert format_entity_id("building-element", "baie-f1") == "building-element:baie-f1"
    assert parse_entity_id("commercial-document:dev-2026-014") == (
        "commercial-document",
        "dev-2026-014",
    )
    bad_ids = (
        "building-element",
        "building-element:BAIE-F1",
        "topic:x",
        "building-element:",
        "Building-element:x",
        "building-element:a--b",
    )
    for bad in bad_ids:
        with pytest.raises(ValueError):
            parse_entity_id(bad)
    assert format_topic_id("site-progress") == "topic:site-progress"
    assert parse_topic_id("topic:site-progress") == "site-progress"
    with pytest.raises(ValueError):
        parse_topic_id("topics:site-progress")
    query_id = format_query_id(date(2026, 3, 31), "window-delivery-date")
    assert query_id == "query:2026-03-31-window-delivery-date"
    assert parse_query_id(query_id) == (date(2026, 3, 31), "window-delivery-date")
    with pytest.raises(ValueError):
        parse_query_id("query:2026-3-4-x")


def test_page_paths() -> None:
    assert entity_page_path("building-element:baie-f1") == "entities/building-element/baie-f1.md"
    assert topic_page_path("topic:site-progress") == "topics/site-progress.md"
    assert query_page_path("query:2026-03-31-window-delivery-date") == (
        "queries/2026-03-31-window-delivery-date.md"
    )
    assert index_page_path("home") == "index.md"
    assert index_page_path("entities/building-element") == "entities/building-element/index.md"
    with pytest.raises(ValueError):
        index_page_path("glossary")


@pytest.mark.parametrize(
    "path",
    [
        "index.md",
        "AGENTS.md",
        "llms.txt",
        "sources/devis-extension.md",
        "entities/building-element/baie-f1.md",
        "_meta/quality.md",
        "_meta/runs/run-20260101-120000-0a1b2c3d.md",
        ".agents/skills/wiki-navigator/SKILL.md",
        ".github/skills/cite-sources/SKILL.md",
        "evidence/src-0123456789ab/img/p0003.png",
    ],
)
def test_check_wiki_path_accepts_contract_paths(path: str) -> None:
    assert check_wiki_path(path) is None


@pytest.mark.parametrize(
    "path",
    [
        "Sources/x.md",
        "sources/X.md",
        "sources.v2/x.md",
        "entities/none/x.md",
        "entities/PageType.SOURCE/x.md",
        "-bad.md",
        "a//b.md",
        ".agents/skills/Bad/SKILL.md",
        ".agents/skills/x/skill.md2",
        "sources/x y.md",
    ],
)
def test_check_wiki_path_rejects_bad_paths(path: str) -> None:
    assert check_wiki_path(path) is not None


def test_normalize_tags() -> None:
    assert normalize_tags(["Planning", "windows", "planning ", ""]) == ["planning", "windows"]


def test_cache_key_is_deterministic_and_sensitive_to_every_element() -> None:
    base = dict(
        stage_version="1",
        prompt_version="p1",
        model_id="m",
        model_version="v",
        domain_pack_hash="h",
    )
    key = cache_key("compile", ["b", "a"], **base)
    assert key == cache_key("compile", ["a", "b"], **base)
    assert len(key) == 64
    variants = {
        cache_key("extract", ["a", "b"], **base),
        cache_key("compile", ["a", "c"], **base),
        cache_key("compile", ["a", "b"], **{**base, "stage_version": "2"}),
        cache_key("compile", ["a", "b"], **{**base, "prompt_version": "p2"}),
        cache_key("compile", ["a", "b"], **{**base, "model_id": "m2"}),
        cache_key("compile", ["a", "b"], **{**base, "model_version": "v2"}),
        cache_key("compile", ["a", "b"], **{**base, "domain_pack_hash": "h2"}),
        cache_key("compile", ["a", "b"], **base, schema_version=2),
    }
    assert key not in variants and len(variants) == 8


def test_release_and_run_ids() -> None:
    created = datetime(2026, 1, 31, 8, 5, 9, tzinfo=UTC)
    release_id = format_release_id(created, "0123456789abcdef")
    assert release_id == "20260131T080509Z-01234567"
    assert parse_release_id(release_id) == (created, "01234567")
    with pytest.raises(ValueError):
        parse_release_id("20260131T080509Z-0123456")
    with pytest.raises(ValueError):
        format_release_id(datetime(2026, 1, 1), "0123456789")
    run_id = new_run_id(created, "0a1b2c3d")
    assert run_id == "run-20260131-080509-0a1b2c3d"
    assert check_wiki_path(f"_meta/runs/{run_id}.md") is None
    assert new_run_id().startswith("run-")


def test_proposal_id_is_deterministic() -> None:
    first = proposal_id_for("entity", {"type": "building-element", "key": "fenetre-f2"})
    assert first == proposal_id_for("entity", {"key": "fenetre-f2", "type": "building-element"})
    assert first != proposal_id_for("glossary", {"type": "building-element", "key": "fenetre-f2"})
    assert first.startswith("prop-") and len(first) == 17
