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

QUOTE_A = "devis/DEV-2026-014 indice A.txt"
QUOTE_B = "devis/DEV-2026-014 indice B.txt"
NOTE = "notes/supplier-note.txt"
PAGE_A = "sources/dev-2026-014-indice-a.md"
PAGE_B = "sources/dev-2026-014-indice-b.md"
BAIE = "entities/building-element/baie-f1.md"
TOPIC = "topic:quotes-contract-and-amendment"
TOPIC_PAGE = "topics/quotes-contract-and-amendment.md"

SOURCE_BODY = """# {title}

Short summary mentioning baie F1 and VanArsdel Menuiseries.

## Key facts

- baie F1 measures 3,00 x 2,15 m in indice B, baie F1 again.[^c1]
- VanArsdel Menuiseries supplies the windows.[^c1]

## Contents

### Dimensions

`baie F1` in code is never linked; [baie F1 linked](../entities/building-element/baie-f1.md) counts.
baie F1 later in the same section stays plain.

```
baie F1 inside a fence
```

> Quoted baie F1 in a blockquote stays plain.

#### baie F1 heading stays plain

The bay window F1 alias links too.

## Sources

[^c1]: [{title} — line 1](../evidence/{sid}/l0001-l0001.md) · ✓ quote verified
"""


def _pages():
    rev_a_id, rev_b_id, note_id = (source_id_for(p) for p in (QUOTE_A, QUOTE_B, NOTE))
    rev_a = source_page(
        QUOTE_A,
        "DEV-2026-014 indice A",
        SOURCE_BODY.format(title="DEV-2026-014 indice A", sid=rev_a_id),
        slug="dev-2026-014-indice-a",
        entities=[
            "building-element:baie-f1",
            "organisation:vanarsdel-menuiseries",
            "building-element:baie-de-liaison",
        ],
        superseded_by=[rev_b_id],
    )
    rev_b = source_page(
        QUOTE_B,
        "DEV-2026-014 indice B",
        SOURCE_BODY.format(title="DEV-2026-014 indice B", sid=rev_b_id),
        slug="dev-2026-014-indice-b",
        entities=["building-element:baie-f1"],
        supersedes=[rev_a_id],
    )
    note = source_page(
        NOTE,
        "Supplier [note](http://example.com) <b>",
        "# Supplier note\n\nNothing about entities.\n",
        slug="supplier-note",
        category="correspondence",
    )
    baie = entity_page(
        "building-element:baie-f1",
        "baie F1",
        "# baie F1\n\nbaie F1 is a bay window; VanArsdel Menuiseries made it.\n\n## Documents\n\n"
        "- [DEV-2026-014 indice B](../../sources/dev-2026-014-indice-b.md)\n",
        sources=[rev_b_id, note_id],
    )
    vanarsdel = entity_page(
        "organisation:vanarsdel-menuiseries",
        "VanArsdel Menuiseries",
        "# VanArsdel Menuiseries\n\nWindow maker of the extension.\n\n## Documents\n\n"
        "- [DEV-2026-014 indice A](../../sources/dev-2026-014-indice-a.md)\n",
        sources=[rev_a_id],
    )
    topic = topic_page(
        "quotes-contract-and-amendment",
        "Quotes, contract and amendment",
        "# Quotes, contract and amendment\n\n## Overview\n\nQuote for baie F1.\n\n"
        "## Sources consulted\n\n"
        "- [DEV-2026-014 indice A](../sources/dev-2026-014-indice-a.md)\n"
        "- [DEV-2026-014 indice B](../sources/dev-2026-014-indice-b.md)\n",
        sources=[rev_a_id, rev_b_id],
    )
    return [rev_a, rev_b, note, baie, vanarsdel, topic]


def _by_path(pages):
    return {page.path: page for page in pages}


def test_reconcile_superseded_banner_related_and_backlinks():
    result = apply_links(_pages(), pack())
    pages = _by_path(result.pages)
    rev_a = pages[PAGE_A]
    # dangling entity dropped, topics come from the topic pages
    assert rev_a.frontmatter.entities == [
        "building-element:baie-f1",
        "organisation:vanarsdel-menuiseries",
    ]
    assert rev_a.frontmatter.topics == [TOPIC]
    intro = rev_a.body.split("## Key facts")[0]
    assert "> **Superseded** by [DEV-2026-014 indice B](dev-2026-014-indice-b.md)." in intro
    related = rev_a.body.split("## Related", 1)[1].split(BACKLINKS_START, 1)[0]
    assert "- Building element: [baie F1](../entities/building-element/baie-f1.md)" in related
    assert (
        "- Organisation: [VanArsdel Menuiseries]"
        "(../entities/organisation/vanarsdel-menuiseries.md)" in related
    )
    assert (
        "- Topic: [Quotes, contract and amendment](../topics/quotes-contract-and-amendment.md)"
        in related
    )
    assert "- Superseded by: [DEV-2026-014 indice B](dev-2026-014-indice-b.md)" in related
    order = [rev_a.body.index(marker) for marker in ("## Related", BACKLINKS_START, "## Sources")]
    assert order == sorted(order)
    backlinks = rev_a.body.split(BACKLINKS_START, 1)[1].split(BACKLINKS_END, 1)[0]
    titles = [link.text for link in extract_links(backlinks)]
    assert titles == sorted(titles, key=str.casefold)
    assert set(titles) == {
        "Quotes, contract and amendment",
        "VanArsdel Menuiseries",
        "DEV-2026-014 indice B",
    }
    rev_b = pages[PAGE_B]
    assert "- Supersedes: [DEV-2026-014 indice A](dev-2026-014-indice-a.md)" in rev_b.body
    assert "**Superseded**" not in rev_b.body
    topic = pages[TOPIC_PAGE]
    assert "- Building elements: [baie F1]" in topic.body or "- Building element: [baie F1]" in (
        topic.body
    )
    baie = pages[BAIE]
    assert (
        "- Topic: [Quotes, contract and amendment](../../topics/quotes-contract-and-amendment.md)"
        in baie.body
    )


def test_render_banner_code_spans_become_links_without_a_second_banner():
    pages = _pages()
    rev_a, rev_b_id = pages[0], source_id_for(QUOTE_B)
    lines = rev_a.body.split("\n")
    lines[1:1] = ["", f"> **Superseded** by `{rev_b_id}`. Use the current revision."]
    pages[0] = rev_a.model_copy(update={"body": "\n".join(lines)})
    result = apply_links(pages, pack())
    body = _by_path(result.pages)[PAGE_A].body
    intro = body.split("## Key facts")[0]
    assert "> **Superseded** by [DEV-2026-014 indice B](dev-2026-014-indice-b.md)." in intro
    assert intro.count("**Superseded**") == 1
    assert f"`{rev_b_id}`" not in body
    assert apply_links(result.pages, pack()).pages == result.pages


def test_autolinks_first_mention_per_section_only_in_plain_text():
    result = apply_links(_pages(), pack())
    body = _by_path(result.pages)[PAGE_B].body
    facts = body.split("## Key facts", 1)[1].split("## Contents", 1)[0]
    assert facts.count("](../entities/building-element/baie-f1.md)") == 1
    assert "[VanArsdel Menuiseries](../entities/organisation/vanarsdel-menuiseries.md)" in facts
    contents = body.split("### Dimensions", 1)[1].split("## Related", 1)[0]
    assert "`baie F1` in code" in contents
    assert "[baie F1 linked](../entities/building-element/baie-f1.md) counts." in contents
    assert "baie F1 later in the same section stays plain." in contents
    assert "baie F1 inside a fence" in contents and "[baie F1](" not in contents.split("```")[1]
    assert "> Quoted baie F1 in a blockquote stays plain." in contents
    assert "#### baie F1 heading stays plain" in contents
    alias_section = contents.split("#### baie F1 heading stays plain", 1)[1]
    assert "[bay window F1](../entities/building-element/baie-f1.md)" in alias_section
    footnotes = body.split("## Sources", 1)[1]
    assert "../entities" not in footnotes
    baie = _by_path(result.pages)[BAIE].body
    assert "[baie F1](" not in baie.split("## Documents")[0], "an entity never links itself"
    assert "[VanArsdel Menuiseries](../organisation/vanarsdel-menuiseries.md)" in baie


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
    rev_a, rev_b = source_id_for(QUOTE_A), source_id_for(QUOTE_B)
    assert (rev_b, rev_a, "supersedes") in edges
    assert (rev_a, "organisation:vanarsdel-menuiseries", "mentions") in edges
    assert (TOPIC, rev_a, "topic-of") in edges
    assert ("building-element:baie-f1", TOPIC, "related") in edges
    assert not any(
        kind == "related" and a == rev_a and b == "building-element:baie-f1"
        for a, b, kind in edges
    )
    assert [(e.from_, e.to, e.kind) for e in result.edges] == sorted(edges)
    assert build_edges(result.pages) == result.edges


def test_cites_edges_come_from_footnotes_of_other_pages():
    rev_a_id = source_id_for(QUOTE_A)
    rev_a = source_page(QUOTE_A, "Indice A", "# Indice A\n", slug="indice-a")
    topic = topic_page(
        "quotes-contract-and-amendment",
        "Quotes, contract and amendment",
        "# Quotes, contract and amendment\n\nWidth 3,00 m.[^c1]\n\n## Sources\n\n"
        f"[^c1]: [Indice A — line 1](../evidence/{rev_a_id}/l0001-l0001.md) · ✓ quote verified\n",
        sources=[rev_a_id],
    )
    edges = {(e.from_, e.to, e.kind) for e in build_edges([rev_a, topic])}
    assert (TOPIC, rev_a_id, "cites") in edges


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
    assert plural("Quote", 2) == "Quotes"
    assert plural("Process", 2) == "Processes"
    assert plural("Synthesis", 2) == "Syntheses"
    assert plural("Category", 3) == "Categories"
    assert plural("Topic", 1) == "Topic"


def test_type_labels_keep_plural_pack_titles():
    assert type_label("Work packages", 2) == "Work packages"
    assert type_label("Work packages", 1) == "Work package"
    assert type_label("Delivery notes", 1) == "Delivery note"
    assert type_label("Categories", 1) == "Category"
    assert type_label("Processes", 1) == "Process"
    assert singular("Building elements") == "Building element"
    assert singular("Glass") == "Glass"


def test_related_entity_labels_use_the_plural_pack_title_once():
    liaison = entity_page(
        "building-element:baie-de-liaison",
        "baie de liaison",
        "# baie de liaison\n\nAn opening.\n",
        sources=[source_id_for(QUOTE_A)],
    )
    pages = _by_path(apply_links([*_pages(), liaison], pack()).pages)
    related = pages[PAGE_A].body.split("## Related", 1)[1]
    assert (
        "- Building elements: [baie de liaison](../entities/building-element/baie-de-liaison.md), "
        "[baie F1](../entities/building-element/baie-f1.md)" in related
    )
    assert "Building elementses" not in related
