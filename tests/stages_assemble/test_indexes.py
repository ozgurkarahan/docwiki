"""Stage ``indexes``: log, glossary, home page, ``llms.txt`` and catalog."""

from __future__ import annotations

from datetime import date

from assemble_helpers import (
    CREATED,
    DAY,
    RELEASE_ID,
    STAMP,
    entity_page,
    pack,
    source_page,
    topic_page,
)

from docwiki.contracts.catalog import Catalog
from docwiki.contracts.ids import source_id_for
from docwiki.contracts.markdown import extract_headings, extract_links, resolve_href
from docwiki.engine_types import TopicSkip
from docwiki.stages.indexes import (
    build_catalog,
    build_indexes,
    changes_since,
    parse_log_entries,
    run_page_path,
)
from docwiki.stages.links import apply_links

RUN_ID = "run-20260215-090000-0a1b2c3d"
REV_A = "procedures/SOP-GBX-010 rev A.txt"
REV_B = "procedures/SOP-GBX-010 rev B.txt"


def _content():
    a, b = source_id_for(REV_A), source_id_for(REV_B)
    pages = [
        source_page(REV_A, "Rev A", "# Rev A\n", slug="rev-a", superseded_by=[b]),
        source_page(REV_B, "Rev B", "# Rev B\n", slug="rev-b", supersedes=[a]),
        entity_page("asset:wtg-07", "WTG-07", "# WTG-07\n", sources=[b]),
        topic_page("gearbox-oil", "Gearbox oil", "# Gearbox oil\n", sources=[a, b]),
    ]
    return apply_links(pages, pack()).pages


def _bundle(content, previous_log=None, entries=(), skips=()):
    return build_indexes(
        content,
        pack(),
        stamp=STAMP,
        updated=DAY,
        sensitivity="public",
        run_id=RUN_ID,
        previous_log=previous_log,
        new_entries=list(entries),
        topic_skips=list(skips),
        extra_paths=["AGENTS.md", "_meta/quality.md", run_page_path(RUN_ID)],
    )


def test_first_release_log_entries_and_recent_changes():
    content = _content()
    entries = changes_since(None, content, day=DAY)
    actions = [(entry.action, entry.title) for entry in entries]
    assert actions == [
        ("ingest", "Rev A"),
        ("ingest", "Rev B"),
        ("supersede", "Rev A"),
        ("topic", "Gearbox oil"),
    ]
    bundle = _bundle(content, entries=entries)
    pages = {page.path: page for page in bundle.pages}
    log = pages["log.md"].body
    assert log.startswith("# Log\n\n## [2026-02-15] ingest | Rev A")
    assert "- [Rev A](sources/rev-a.md) is superseded by [Rev B](sources/rev-b.md)" in log
    home = pages["index.md"].body
    recent = home.split("## Recent changes", 1)[1]
    assert recent.index("topic: [Gearbox oil]") < recent.index("ingest: [Rev A]")
    assert f"[Run receipt](_meta/runs/{RUN_ID}.md)" in home


def test_log_is_append_only_and_dead_links_become_text():
    content = _content()
    first = _bundle(content, entries=changes_since(None, content, day=DAY))
    previous_log = {p.path: p for p in first.pages}["log.md"].render()
    remaining = [p for p in content if p.path != "sources/rev-a.md"]
    remaining = apply_links(remaining, pack()).pages
    catalog = build_catalog(
        [*content, *first.pages],
        [],
        release_id=RELEASE_ID,
        audience="internal",
        generated_at=CREATED,
        glossary=first.glossary,
    )
    later = date(2026, 3, 1)
    entries = changes_since(catalog, remaining, day=later)
    assert (entries[0].action, entries[0].title) == ("withdraw", "Rev A")
    second = _bundle(remaining, previous_log=previous_log, entries=entries)
    log = {p.path: p for p in second.pages}["log.md"].body
    old_part = previous_log.split("# Log", 1)[1]
    assert "## [2026-02-15] ingest | Rev A\n\n- Rev A\n" in log, "dead link turned into text"
    assert "[Rev B](sources/rev-b.md)" in log
    assert log.count("## [2026-02-15]") == old_part.count("## [2026-02-15]")
    assert "## [2026-03-01] withdraw | Rev A" in log
    parsed = parse_log_entries(log)
    withdraw = [entry for entry in parsed if entry.action == "withdraw"]
    assert len(withdraw) == 1 and withdraw[0].link is None
    assert parsed[-1].action == "topic" and parsed[-1].link == "topics/gearbox-oil.md"


def test_glossary_anchors_synonyms_and_see_also():
    content = _content()
    bundle = _bundle(content)
    glossary = {p.path: p for p in bundle.pages}["glossary.md"]
    anchors = {h.anchor for h in extract_headings(glossary.body)}
    assert [entry.page for entry in bundle.glossary] == ["glossary.md#iso-vg", "glossary.md#wtg"]
    assert all(entry.page.split("#")[1] in anchors for entry in bundle.glossary)
    assert bundle.glossary[0].synonyms == {
        "fr": ["grade de viscosité ISO"],
        "de": ["ISO-Viskositätsklasse"],
    }
    assert "- See also: [Gearbox oil](topics/gearbox-oil.md)" in glossary.body
    assert "- See also: [WTG-07](entities/asset/wtg-07.md)" in glossary.body


def test_index_pages_links_resolve_and_llms_txt_format():
    content = _content()
    bundle = _bundle(content, skips=[TopicSkip("blade-inspection", "insufficient_evidence", ())])
    paths = {page.path for page in [*content, *bundle.pages]} | {
        "AGENTS.md",
        "_meta/quality.md",
        run_page_path(RUN_ID),
    }
    for page in bundle.pages:
        for link in extract_links(page.body):
            target = resolve_href(page.path, link.href).path
            assert target in paths, (page.path, link.href)
    llms = bundle.llms_txt.split("\n")
    assert llms[0] == "# Contoso Renewables engine test wiki"
    assert llms[2].startswith("> ")
    for section in ("## Start here", "## Topics", "## Entities", "## Sources"):
        assert section in llms
    assert "- [Rev A](sources/rev-a.md): (superseded) Summary of Rev A." in llms
    topics = {p.path: p for p in bundle.pages}["topics/index.md"].body
    assert "## Not synthesised yet" in topics and "Blade inspection" in topics
    sources = {p.path: p for p in bundle.pages}["sources/index.md"].body
    assert "superseded by [Rev B](rev-b.md) · public" in sources
    types = {p.path for p in bundle.pages}
    assert {"entities/index.md", "entities/asset/index.md", "topics/index.md"} <= types
    by_path = {p.path: p for p in bundle.pages}
    assert by_path["entities/asset/index.md"].frontmatter.title == "Assets"
    assert "- [Assets](asset/index.md): " in by_path["entities/index.md"].body


def test_catalog_matches_the_pages():
    content = _content()
    bundle = _bundle(content)
    pages = [*content, *bundle.pages]
    catalog = build_catalog(
        pages,
        [],
        release_id=RELEASE_ID,
        audience="internal",
        generated_at=CREATED,
        glossary=bundle.glossary,
    )
    assert isinstance(Catalog.from_json(catalog.to_json()), Catalog)
    assert [entry.path for entry in catalog.pages] == sorted(page.path for page in pages)
    assert [source.source_id for source in catalog.sources] == sorted(
        source_id_for(path) for path in (REV_A, REV_B)
    )
