"""Hub pages and the company dashboard (v1.7, ADR 0011), built by code from the pages."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from assemble_helpers import DAY, STAMP, pack, source_page, topic_page

from docwiki.contracts.ids import source_id_for
from docwiki.contracts.pages import ContradictionPair, Page, TopicFrontmatter
from docwiki.domain import load_pack
from docwiki.stages.hubs import HubBundle, build_hubs, dashboard_lines
from docwiki.stages.indexes import build_indexes
from docwiki.stages.links import apply_links

SCOPED = Path(__file__).resolve().parents[1] / "orchestration" / "fixtures" / "scoped-pack"
ALPHA_A = "chantiers/alpha/1-marche/quote/DEV-2026-014 indice A.txt"
ALPHA_B = "chantiers/alpha/3-execution/quote/DEV-2026-014 indice B.txt"
BETA = "chantiers/beta/1-marche/quote/DEV-2026-020 indice A.txt"
COMPANY = "entreprise/note/2026-02-11 workshop note.txt"


def _scoped_topic(slug: str, scope: str, title: str, sources: list[str], contradictions: int):
    fm = TopicFrontmatter(
        id=f"topic:{scope}/{slug}",
        title=title,
        summary=f"Synthesis about {title.lower()}.",
        sensitivity="public",
        updated=DAY,
        docwiki=STAMP,
        topic_slug=slug,
        scope=scope,
        sources=sorted(sources),
        confidence="medium",
        contradictions=contradictions,
    )
    return Page(path=f"topics/{scope}/{slug}.md", frontmatter=fm, body=f"# {title}\n")


def _content():
    a, b = source_id_for(ALPHA_A), source_id_for(ALPHA_B)
    beta = source_id_for(BETA)
    pages = [
        source_page(ALPHA_A, "Indice A", "# Indice A\n", slug="indice-a", superseded_by=[b]),
        source_page(ALPHA_B, "Indice B", "# Indice B\n", slug="indice-b", supersedes=[a]),
        source_page(BETA, "Beta quote", "# Beta quote\n", slug="beta-quote"),
        source_page(COMPANY, "Workshop note", "# Workshop note\n", slug="workshop-note"),
        _scoped_topic("schedule-and-window-delivery", "alpha", "Windows — Alpha", [a, b], 2),
        topic_page("kitchen-renovation", "Kitchen renovation", "# Kitchen\n", sources=[beta]),
    ]
    return apply_links(pages, load_pack(SCOPED)).pages


def test_a_pack_without_scopes_has_no_hubs_and_the_same_home():
    content = apply_links(
        [source_page(ALPHA_A, "Indice A", "# Indice A\n", slug="indice-a")], pack()
    ).pages
    empty = build_hubs(content, pack(), stamp=STAMP, updated=DAY)
    assert empty.pages == [] and empty.summaries == []
    assert dashboard_lines(empty, pack(), "index.md") == []

    def bundle(hubs: HubBundle | None):
        return build_indexes(
            content,
            pack(),
            stamp=STAMP,
            updated=DAY,
            sensitivity="public",
            run_id="run-20260401-090000-0a1b2c3d",
            previous_log=None,
            new_entries=[],
            hubs=hubs,
        )

    assert [p.render() for p in bundle(None).pages] == [p.render() for p in bundle(empty).pages]


def test_hubs_documents_topics_and_open_contradictions():
    scoped = load_pack(SCOPED)
    content = _content()
    dates = {source_id_for(ALPHA_A): date(2026, 1, 5)}
    hubs = build_hubs(content, scoped, stamp=STAMP, updated=DAY, dates=dates)
    by_path = {page.path: page for page in hubs.pages}
    assert sorted(by_path) == [
        "chantiers/alpha.md",
        "chantiers/beta.md",
        "chantiers/entreprise.md",
        "chantiers/index.md",
    ]
    alpha = by_path["chantiers/alpha.md"]
    assert alpha.frontmatter.sources == sorted([source_id_for(ALPHA_A), source_id_for(ALPHA_B)])
    body = alpha.body
    assert "- [Indice A](../sources/indice-a.md): superseded by [Indice B]" in body
    assert body.index("### Phase 1 marché") < body.index("### Phase 3 exécution")
    contradictions = body.split("## Open contradictions", 1)[1].split("##", 1)[0]
    assert (
        "[Windows — Alpha](../topics/alpha/schedule-and-window-delivery.md): 2 contradictions"
        in (contradictions)
    )
    # a company topic shows on the hubs whose sources it synthesises, never as theirs
    beta = by_path["chantiers/beta.md"].body
    assert "[Kitchen renovation](../topics/kitchen-renovation.md)" in beta
    assert "Kitchen renovation" not in body
    assert "No open contradictions" in beta
    # the document's own date wins; otherwise a date in the file name; otherwise ``updated``
    assert "(2026-01-05)" in body.split("## Last document received", 1)[1]
    company = by_path["chantiers/entreprise.md"].body
    assert "[Workshop note](../sources/workshop-note.md) (2026-02-11)" in company

    rows = dashboard_lines(hubs, scoped, "index.md")
    assert rows[0] == "## Chantiers"
    alpha_row = next(line for line in rows if "[Chantier Alpha]" in line)
    assert alpha_row.startswith("| [Chantier Alpha](chantiers/alpha.md) | 3 exécution |")
    assert alpha_row.endswith("| 2 |")


def test_a_scope_named_index_is_refused():
    scoped = load_pack(SCOPED)
    content = apply_links(
        [source_page("chantiers/index/x.txt", "X", "# X\n", slug="x")], scoped
    ).pages
    with pytest.raises(ValueError, match="scope value 'index'"):
        build_hubs(content, scoped, stamp=STAMP, updated=DAY)


def test_a_title_that_shows_its_date_does_not_repeat_it():
    from datetime import date

    from docwiki.stages.hubs import _date_suffix

    assert _date_suffix("Compte rendu n°3 (2026-03-24)", date(2026, 3, 24)) == ""
    assert _date_suffix("Compte rendu n°3", date(2026, 3, 24)) == " (2026-03-24)"


def test_open_contradictions_are_counted_once_per_pair_of_sources():
    """The same disagreement stated by several topics of a scope counts once (v1.7); a topic
    written before v1.7 has no pairs and counts with its number."""
    scoped = load_pack(SCOPED)
    note_path = "chantiers/alpha/3-execution/note/2026-03-02 supplier note.txt"
    a, b, note = source_id_for(ALPHA_A), source_id_for(ALPHA_B), source_id_for(note_path)

    def stating(slug: str, title: str, pairs: list[tuple[list[str], str]]) -> Page:
        page = _scoped_topic(slug, "alpha", title, [a, b, note], len(pairs))
        data = page.frontmatter.model_dump()
        data["contradiction_pairs"] = [
            ContradictionPair(sources=sorted(ids), subject=subject) for ids, subject in pairs
        ]
        return Page(path=page.path, frontmatter=TopicFrontmatter(**data), body=page.body)

    pages = [
        source_page(ALPHA_A, "Indice A", "# Indice A\n", slug="indice-a"),
        source_page(ALPHA_B, "Indice B", "# Indice B\n", slug="indice-b"),
        source_page(note_path, "Supplier note", "# Supplier note\n", slug="supplier-note"),
        stating("windows", "Windows — Alpha", [([a, b], "Width of F1"), ([b, note], "Delivery")]),
        stating("schedule", "Schedule — Alpha", [([b, a], "width of F1"), ([a, b], "F1 width")]),
        stating("costs", "Costs — Alpha", [([a, b], "Price"), ([a, b], "Total")]),
        _scoped_topic("old", "alpha", "Old — Alpha", [a, b], 2),
    ]
    content = apply_links(pages, load_pack(SCOPED)).pages
    hubs = build_hubs(content, scoped, stamp=STAMP, updated=DAY)
    summary = next(item for item in hubs.summaries if item.scope == "alpha")
    # the pairs {a, b} and {b, note}, plus the 2 contradictions of the topic without pairs
    assert summary.open_count == 4
    alpha = next(page for page in hubs.pages if page.path == "chantiers/alpha.md").body
    section = alpha.split("## Open contradictions\n\n", 1)[1].split("\n\n", 1)[0]
    assert section.splitlines() == [
        "- [Indice A](../sources/indice-a.md) and [Indice B](../sources/indice-b.md): Price; "
        "Total; width of F1; and 1 more (in [Costs — Alpha](../topics/alpha/costs.md), "
        "[Schedule — Alpha](../topics/alpha/schedule.md), "
        "[Windows — Alpha](../topics/alpha/windows.md)).",
        "- [Indice B](../sources/indice-b.md) and [Supplier note](../sources/supplier-note.md): "
        "Delivery (in [Windows — Alpha](../topics/alpha/windows.md)).",
        "- [Old — Alpha](../topics/alpha/old.md): 2 contradictions",
    ]
    rows = dashboard_lines(hubs, scoped, "index.md")
    assert next(line for line in rows if "[Chantier Alpha]" in line).endswith("| 4 |")
