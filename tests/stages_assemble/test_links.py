"""Stage ``links``: autolinking, related sections, backlinks, banners, reconciliation, edges."""

from __future__ import annotations

from assemble_helpers import entity_page, pack, source_page, topic_page

from docwiki.contracts.ids import source_id_for
from docwiki.contracts.markdown import BACKLINKS_END, BACKLINKS_START, extract_links
from docwiki.stages.links import (
    apply_links,
    build_edges,
    inline_text,
    md_link,
    plural,
    singular,
    strip_generated_sections,
    type_label,
)

REV_A = "procedures/SOP-GBX-010 rev A.txt"
REV_B = "procedures/SOP-GBX-010 rev B.txt"
NOTE = "notes/supplier-note.txt"

SOURCE_BODY = """# {title}

Short summary mentioning WTG-07 and Litware.

## Key facts

- WTG-07 uses ISO VG 220 at cold sites, WTG-07 again.[^c1]
- Litware supplies the gearbox.[^c1]

## Contents

### Cold sites

`WTG-07` in code is never linked; [WTG-07 already linked](../entities/asset/wtg-07.md) counts.
WTG-07 later in the same section stays plain.

```
WTG-07 inside a fence
```

> Quoted WTG-07 in a blockquote stays plain.

#### WTG-07 heading stays plain

The turbine 7 alias links too.

## Sources

[^c1]: [{title} — line 1](../evidence/{sid}/l0001-l0001.md) · ✓ quote verified
"""


def _pages():
    rev_a_id, rev_b_id, note_id = (source_id_for(p) for p in (REV_A, REV_B, NOTE))
    rev_a = source_page(
        REV_A,
        "SOP-GBX-010 rev A",
        SOURCE_BODY.format(title="SOP-GBX-010 rev A", sid=rev_a_id),
        slug="sop-gbx-010-rev-a",
        entities=["asset:wtg-07", "organisation:litware", "asset:wtg-12"],
        superseded_by=[rev_b_id],
    )
    rev_b = source_page(
        REV_B,
        "SOP-GBX-010 rev B",
        SOURCE_BODY.format(title="SOP-GBX-010 rev B", sid=rev_b_id),
        slug="sop-gbx-010-rev-b",
        entities=["asset:wtg-07"],
        supersedes=[rev_a_id],
    )
    note = source_page(
        NOTE,
        "Supplier [note](http://example.com) <b>",
        "# Supplier note\n\nNothing about entities.\n",
        slug="supplier-note",
        category="correspondence",
    )
    wtg07 = entity_page(
        "asset:wtg-07",
        "WTG-07",
        "# WTG-07\n\nWTG-07 is a turbine; Litware built its gearbox.\n\n## Documents\n\n"
        "- [SOP-GBX-010 rev B](../../sources/sop-gbx-010-rev-b.md)\n",
        sources=[rev_b_id, note_id],
    )
    litware = entity_page(
        "organisation:litware",
        "Litware",
        "# Litware\n\nOEM of the gearboxes.\n\n## Documents\n\n"
        "- [SOP-GBX-010 rev A](../../sources/sop-gbx-010-rev-a.md)\n",
        sources=[rev_a_id],
    )
    topic = topic_page(
        "gearbox-oil",
        "Gearbox oil",
        "# Gearbox oil\n\n## Overview\n\nOil for WTG-07.\n\n## Sources consulted\n\n"
        "- [SOP-GBX-010 rev A](../sources/sop-gbx-010-rev-a.md)\n"
        "- [SOP-GBX-010 rev B](../sources/sop-gbx-010-rev-b.md)\n",
        sources=[rev_a_id, rev_b_id],
    )
    return [rev_a, rev_b, note, wtg07, litware, topic]


def _by_path(pages):
    return {page.path: page for page in pages}


def test_reconcile_superseded_banner_related_and_backlinks():
    result = apply_links(_pages(), pack())
    pages = _by_path(result.pages)
    rev_a = pages["sources/sop-gbx-010-rev-a.md"]
    # dangling entity dropped, topics come from the topic pages
    assert rev_a.frontmatter.entities == ["asset:wtg-07", "organisation:litware"]
    assert rev_a.frontmatter.topics == ["topic:gearbox-oil"]
    intro = rev_a.body.split("## Key facts")[0]
    assert "> **Superseded** by [SOP-GBX-010 rev B](sop-gbx-010-rev-b.md)." in intro
    related = rev_a.body.split("## Related", 1)[1].split(BACKLINKS_START, 1)[0]
    assert "- Asset: [WTG-07](../entities/asset/wtg-07.md)" in related
    assert "- Organisation: [Litware](../entities/organisation/litware.md)" in related
    assert "- Topic: [Gearbox oil](../topics/gearbox-oil.md)" in related
    assert "- Superseded by: [SOP-GBX-010 rev B](sop-gbx-010-rev-b.md)" in related
    order = [rev_a.body.index(marker) for marker in ("## Related", BACKLINKS_START, "## Sources")]
    assert order == sorted(order)
    backlinks = rev_a.body.split(BACKLINKS_START, 1)[1].split(BACKLINKS_END, 1)[0]
    titles = [link.text for link in extract_links(backlinks)]
    assert titles == sorted(titles, key=str.casefold)
    assert set(titles) == {"Gearbox oil", "Litware", "SOP-GBX-010 rev B"}
    rev_b = pages["sources/sop-gbx-010-rev-b.md"]
    assert "- Supersedes: [SOP-GBX-010 rev A](sop-gbx-010-rev-a.md)" in rev_b.body
    assert "**Superseded**" not in rev_b.body
    topic = pages["topics/gearbox-oil.md"]
    assert "- Assets: [WTG-07]" in topic.body or "- Asset: [WTG-07]" in topic.body
    wtg = pages["entities/asset/wtg-07.md"]
    assert "- Topic: [Gearbox oil](../../topics/gearbox-oil.md)" in wtg.body


def test_render_banner_code_spans_become_links_without_a_second_banner():
    pages = _pages()
    rev_a, rev_b_id = pages[0], source_id_for(REV_B)
    lines = rev_a.body.split("\n")
    lines[1:1] = ["", f"> **Superseded** by `{rev_b_id}`. Use the current revision."]
    pages[0] = rev_a.model_copy(update={"body": "\n".join(lines)})
    result = apply_links(pages, pack())
    body = _by_path(result.pages)["sources/sop-gbx-010-rev-a.md"].body
    intro = body.split("## Key facts")[0]
    assert "> **Superseded** by [SOP-GBX-010 rev B](sop-gbx-010-rev-b.md)." in intro
    assert intro.count("**Superseded**") == 1
    assert f"`{rev_b_id}`" not in body
    assert apply_links(result.pages, pack()).pages == result.pages


def test_autolinks_first_mention_per_section_only_in_plain_text():
    result = apply_links(_pages(), pack())
    body = _by_path(result.pages)["sources/sop-gbx-010-rev-b.md"].body
    facts = body.split("## Key facts", 1)[1].split("## Contents", 1)[0]
    assert facts.count("](../entities/asset/wtg-07.md)") == 1
    assert "[Litware](../entities/organisation/litware.md)" in facts
    contents = body.split("### Cold sites", 1)[1].split("## Related", 1)[0]
    assert "`WTG-07` in code" in contents
    assert "[WTG-07 already linked](../entities/asset/wtg-07.md) counts." in contents
    assert "WTG-07 later in the same section stays plain." in contents
    assert "WTG-07 inside a fence" in contents and "[WTG-07](" not in contents.split("```")[1]
    assert "> Quoted WTG-07 in a blockquote stays plain." in contents
    assert "#### WTG-07 heading stays plain" in contents
    alias_section = contents.split("#### WTG-07 heading stays plain", 1)[1]
    assert "[turbine 7](../entities/asset/wtg-07.md)" in alias_section
    footnotes = body.split("## Sources", 1)[1]
    assert "../entities" not in footnotes
    wtg = _by_path(result.pages)["entities/asset/wtg-07.md"].body
    assert "[WTG-07](" not in wtg.split("## Documents")[0], "an entity never links itself"
    assert "[Litware](../organisation/litware.md)" in wtg


def test_links_stage_is_idempotent():
    first = apply_links(_pages(), pack())
    second = apply_links(first.pages, pack())
    assert [page.render() for page in second.pages] == [page.render() for page in first.pages]
    assert second.edges == first.edges
    for page in first.pages:
        assert page.body.count(BACKLINKS_START) <= 1
        assert page.body.count("## Related") <= 1


def test_edges_follow_the_contract():
    result = apply_links(_pages(), pack())
    edges = {(edge.from_, edge.to, edge.kind) for edge in result.edges}
    rev_a, rev_b = source_id_for(REV_A), source_id_for(REV_B)
    assert (rev_b, rev_a, "supersedes") in edges
    assert (rev_a, "organisation:litware", "mentions") in edges
    assert ("topic:gearbox-oil", rev_a, "topic-of") in edges
    assert ("asset:wtg-07", "topic:gearbox-oil", "related") in edges
    assert not any(kind == "related" and a == rev_a and b == "asset:wtg-07" for a, b, kind in edges)
    assert [(e.from_, e.to, e.kind) for e in result.edges] == sorted(edges)
    assert build_edges(result.pages) == result.edges


def test_cites_edges_come_from_footnotes_of_other_pages():
    rev_a_id = source_id_for(REV_A)
    rev_a = source_page(REV_A, "Rev A", "# Rev A\n", slug="rev-a")
    topic = topic_page(
        "gearbox-oil",
        "Gearbox oil",
        "# Gearbox oil\n\nOil.[^c1]\n\n## Sources\n\n"
        f"[^c1]: [Rev A — line 1](../evidence/{rev_a_id}/l0001-l0001.md) · ✓ quote verified\n",
        sources=[rev_a_id],
    )
    edges = {(e.from_, e.to, e.kind) for e in build_edges([rev_a, topic])}
    assert ("topic:gearbox-oil", rev_a_id, "cites") in edges


def test_untrusted_titles_are_escaped_in_generated_links():
    text = inline_text("Supplier [note](http://example.com) <script>alert(1)</script>\nx")
    assert "](http" not in text and "<script>" not in text and "\n" not in text
    link = md_link("A [b] c", "sources/index.md", "sources/a.md")
    assert link == r"[A \[b\] c](a.md)"
    result = apply_links(_pages(), pack())
    note_backlinks = [
        page for page in result.pages if "Supplier" in page.body and "example.com" in page.body
    ]
    assert not note_backlinks or all("](http" not in page.body for page in note_backlinks)


def test_strip_generated_sections_and_plurals():
    body = (
        "# T\n\ntext\n\n## Related\n\n- x\n\n"
        f"{BACKLINKS_START}\n## Referenced by\n\n- y\n\n{BACKLINKS_END}\n\n## Sources\n\n[^c1]: z\n"
    )
    stripped = strip_generated_sections(body)
    assert "## Related" not in stripped and BACKLINKS_START not in stripped
    assert stripped.endswith("## Sources\n\n[^c1]: z\n")
    assert plural("Asset", 2) == "Assets"
    assert plural("Process", 2) == "Processes"
    assert plural("Synthesis", 2) == "Syntheses"
    assert plural("Category", 3) == "Categories"
    assert plural("Topic", 1) == "Topic"


def test_type_labels_keep_plural_pack_titles():
    assert type_label("Spare parts", 2) == "Spare parts"
    assert type_label("Spare parts", 1) == "Spare part"
    assert type_label("Service bulletins", 1) == "Service bulletin"
    assert type_label("Categories", 1) == "Category"
    assert type_label("Processes", 1) == "Process"
    assert singular("Status codes") == "Status code"
    assert singular("Glass") == "Glass"


def test_related_entity_labels_use_the_plural_pack_title_once():
    wtg12 = entity_page(
        "asset:wtg-12", "WTG-12", "# WTG-12\n\nA turbine.\n", sources=[source_id_for(REV_A)]
    )
    pages = _by_path(apply_links([*_pages(), wtg12], pack()).pages)
    related = pages["sources/sop-gbx-010-rev-a.md"].body.split("## Related", 1)[1]
    assert (
        "- Assets: [WTG-07](../entities/asset/wtg-07.md), [WTG-12](../entities/asset/wtg-12.md)"
        in related
    )
    assert "Assetses" not in related
