"""Registry entities bound to one scope (v1.7, ADR 0011): links, related lists and hubs.

An entry whose attributes name a value for the pack's scope dimension (``chantier: alpha``)
belongs to that scope only: a page of another scope, of the default scope or without scope
neither lists nor autolinks it, even when it shares the entity's names.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from assemble_helpers import DAY, PACK_DIR, STAMP, entity_page, pack, source_page, topic_page

from docwiki.contracts.ids import source_id_for
from docwiki.contracts.markdown import extract_links
from docwiki.contracts.pages import Page, SourceFrontmatter, TopicFrontmatter
from docwiki.domain import load_pack
from docwiki.domain.models import DomainPack
from docwiki.stages.hubs import build_hubs
from docwiki.stages.links import apply_links

SCOPED = Path(__file__).resolve().parents[1] / "orchestration" / "fixtures" / "scoped-pack"
ALPHA = "chantiers/alpha/3-execution/note/2026-03-02 supplier note.txt"
BETA = "chantiers/beta/note/site visit.txt"
COMPANY = "entreprise/note/workshop note.txt"
LOT_ALPHA = "work-package:lot-5-windows"
LOT_BETA = "work-package:lot-2-windows"
MAKER = "organisation:vanarsdel-menuiseries"

SCOPED_ENTITIES = """
  - type: work-package
    key: lot-5-windows
    label: Lot 5 - Windows
    aliases:
      - {text: window delivery, lang: en}
    attributes: {lot: 5, chantier: alpha}
  - type: work-package
    key: lot-2-windows
    label: Lot 2 - Windows of Beta
    aliases:
      - {text: window delivery, lang: en}
    attributes: {lot: 2, chantier: beta}
"""


def scoped_entities_pack(root: Path) -> Path:
    """The scoped test pack plus two work packages, one bound to each chantier, that share an
    alias (as the lots of two quotes share their titles)."""
    target = root / "scoped-pack"
    shutil.copytree(SCOPED, target)
    entities = target / "entities.yaml"
    text = entities.read_text(encoding="utf-8")
    text = text.replace("types:\n", "types:\n  - key: work-package\n    title: Work packages\n", 1)
    entities.write_text(text.rstrip("\n") + "\n" + SCOPED_ENTITIES, encoding="utf-8")
    return target


@pytest.fixture
def scoped(tmp_path: Path) -> DomainPack:
    return load_pack(scoped_entities_pack(tmp_path))


def _topic(slug: str, scope: str | None, title: str, body: str, sources: list[str]) -> Page:
    if scope is None:
        return topic_page(slug, title, body, sources=sources)
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
    )
    return Page(path=f"topics/{scope}/{slug}.md", frontmatter=fm, body=body)


def _pages() -> list[Page]:
    alpha, beta, company = source_id_for(ALPHA), source_id_for(BETA), source_id_for(COMPANY)
    sentence = "The window delivery of VanArsdel Menuiseries is planned.\n"
    return [
        source_page(ALPHA, "Supplier note", f"# Supplier note\n\n{sentence}", slug="alpha-note",
                    entities=[LOT_ALPHA, MAKER]),
        # the compiled mentions name the alpha lot too: its alias is in the text
        source_page(BETA, "Site visit", f"# Site visit\n\n{sentence}", slug="beta-visit",
                    entities=[LOT_ALPHA, LOT_BETA, MAKER]),
        source_page(COMPANY, "Workshop note", f"# Workshop note\n\n{sentence}",
                    slug="workshop-note", entities=[LOT_ALPHA]),
        entity_page(LOT_ALPHA, "Lot 5 - Windows", "# Lot 5 - Windows\n\nSee the window delivery.\n",
                    sources=[alpha, beta]),
        entity_page(LOT_BETA, "Lot 2 - Windows of Beta", "# Lot 2\n\nThe window delivery.\n",
                    sources=[beta]),
        entity_page(MAKER, "VanArsdel Menuiseries", "# VanArsdel Menuiseries\n",
                    sources=[alpha, beta]),
        _topic("windows", "beta", "Windows — Beta", f"# Windows — Beta\n\n{sentence}", [beta]),
        _topic("windows", None, "Windows", f"# Windows\n\n{sentence}", [alpha, beta, company]),
    ]  # fmt: skip


def _by_path(pages: list[Page]) -> dict[str, Page]:
    return {page.path: page for page in pages}


def _hrefs(page: Page, section: str | None = None) -> set[str]:
    """Links of one section, or of the text before the generated sections."""
    body = page.body
    if section is not None:
        body = body.split(f"## {section}", 1)[1].split("\n## ", 1)[0]
    else:
        body = body.split("\n## Related", 1)[0]
    return {link.href for link in extract_links(body)}


def _targets(page: Page, section: str | None = None) -> set[str]:
    return {href.rsplit("/", 1)[-1] for href in _hrefs(page, section)}


def test_a_source_of_another_scope_does_not_mention_a_scoped_entity(scoped: DomainPack) -> None:
    pages = _by_path(apply_links(_pages(), scoped).pages)
    alpha = pages["sources/alpha-note.md"].frontmatter
    beta = pages["sources/beta-visit.md"].frontmatter
    company = pages["sources/workshop-note.md"].frontmatter
    assert isinstance(beta, SourceFrontmatter) and isinstance(company, SourceFrontmatter)
    assert alpha.entities == [MAKER, LOT_ALPHA]
    # the entity page still lists the beta source (an older build): the scope wins
    assert beta.entities == [MAKER, LOT_BETA]
    assert company.entities == []
    # and the catalog edges follow
    edges = apply_links(_pages(), scoped).edges
    assert not any(e.to == LOT_ALPHA and e.from_ == beta.id for e in edges)


def test_the_autolinker_links_the_entity_of_the_pages_scope_only(scoped: DomainPack) -> None:
    pages = _by_path(apply_links(_pages(), scoped).pages)
    # an alias shared by two scoped entities links the one of the page's scope
    assert "lot-5-windows.md" in _targets(pages["sources/alpha-note.md"])
    assert _targets(pages["sources/beta-visit.md"]) >= {"lot-2-windows.md"}
    assert "lot-5-windows.md" not in _targets(pages["sources/beta-visit.md"])
    assert "lot-5-windows.md" not in _targets(pages["topics/beta/windows.md"])
    # the default scope and a company page without scope link neither; company-wide still links
    for path in ("sources/workshop-note.md", "topics/windows.md"):
        targets = _targets(pages[path])
        assert not targets & {"lot-5-windows.md", "lot-2-windows.md"}, path
        assert "vanarsdel-menuiseries.md" in targets, path
    # the entity's own page never links itself; the other scope's lot is not linked from it
    assert not _targets(pages["entities/work-package/lot-5-windows.md"]) & {
        "lot-5-windows.md",
        "lot-2-windows.md",
    }


def test_related_lists_keep_scoped_entities_in_their_scope(scoped: DomainPack) -> None:
    pages = _by_path(apply_links(_pages(), scoped).pages)
    beta_topic = _targets(pages["topics/beta/windows.md"], "Related")
    assert "lot-2-windows.md" in beta_topic and "lot-5-windows.md" not in beta_topic
    # a company topic lists what each of its sources mentions within its own scope
    company_topic = _targets(pages["topics/windows.md"], "Related")
    assert {"lot-5-windows.md", "lot-2-windows.md"} <= company_topic
    beta_source = _targets(pages["sources/beta-visit.md"], "Related")
    assert "lot-5-windows.md" not in beta_source and "lot-2-windows.md" in beta_source
    # the alpha lot's page does not list the beta topic
    lot = _hrefs(pages["entities/work-package/lot-5-windows.md"], "Related")
    assert "../../topics/windows.md" in lot  # the company topic
    assert not any("/beta/" in href for href in lot)


def test_hubs_list_only_the_entities_of_their_scope(scoped: DomainPack) -> None:
    content = apply_links(_pages(), scoped).pages
    hubs = _by_path(build_hubs(content, scoped, stamp=STAMP, updated=DAY).pages)

    def entities(path: str) -> set[str]:
        return _targets(hubs[path], "Entities")

    assert {"lot-5-windows.md", "vanarsdel-menuiseries.md"} <= entities("chantiers/alpha.md")
    beta = entities("chantiers/beta.md")
    # the alpha lot's page still lists the beta source (an older build): never on the beta hub
    assert "lot-2-windows.md" in beta and "lot-5-windows.md" not in beta
    assert not entities("chantiers/entreprise.md") & {"lot-5-windows.md", "lot-2-windows.md"}


def test_a_pack_without_scopes_links_as_before(tmp_path: Path) -> None:
    """Without scopes.yaml a ``chantier`` attribute means nothing: the same pages and links."""
    plain_dir = tmp_path / "test-pack"
    shutil.copytree(PACK_DIR, plain_dir)
    entities = plain_dir / "entities.yaml"
    text = entities.read_text(encoding="utf-8")
    text = text.replace(
        "    label: baie F1\n", "    label: baie F1\n    attributes: {chantier: x}\n"
    )
    entities.write_text(text, encoding="utf-8")
    bound = load_pack(plain_dir)
    assert bound.entity("building-element:baie-f1").attributes == {"chantier": "x"}
    pages = [
        source_page("devis/a.txt", "A", "# A\n\nThe baie coulissante.\n", slug="a",
                    entities=["building-element:baie-f1"]),
        entity_page("building-element:baie-f1", "Baie F1", "# Baie F1\n",
                    sources=[source_id_for("devis/a.txt")]),
        topic_page("windows", "Windows", "# Windows\n\nThe baie coulissante.\n",
                   sources=[source_id_for("devis/a.txt")]),
    ]  # fmt: skip
    before = apply_links(pages, pack()).pages
    after = apply_links(pages, bound).pages
    assert [page.render() for page in after] == [page.render() for page in before]
    linked = _by_path(after)
    assert linked["sources/a.md"].frontmatter.entities == ["building-element:baie-f1"]
    assert "baie-f1.md" in _targets(linked["sources/a.md"])
    assert "baie-f1.md" in _targets(linked["topics/windows.md"])
