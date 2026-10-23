"""The hand-made mock release stays aligned with the ``batiment`` domain pack."""

from __future__ import annotations

import posixpath
from pathlib import Path

import pytest

from docwiki.contracts.pages import (
    EntityFrontmatter,
    Page,
    QueryFrontmatter,
    SourceFrontmatter,
    TopicFrontmatter,
)
from docwiki.domain import load_pack
from docwiki.domain.models import DomainPack
from docwiki.domain.rules import match_doc_type, parse_doc_number, parse_revision
from docwiki.release import ReleaseReader

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "samples" / "fixtures" / "mock-release"


@pytest.fixture(scope="module")
def pack() -> DomainPack:
    return load_pack(REPO_ROOT / "domains" / "batiment")


@pytest.fixture(scope="module")
def reader() -> ReleaseReader:
    return ReleaseReader.open(FIXTURE_ROOT)


@pytest.fixture(scope="module")
def pages(reader: ReleaseReader) -> list[Page]:
    return [reader.read_page(entry.id) for entry in reader.list_pages()]


def test_source_pages_follow_the_taxonomy_and_supersession_rules(
    pack: DomainPack, pages: list[Page]
) -> None:
    sources = [p.frontmatter for p in pages if isinstance(p.frontmatter, SourceFrontmatter)]
    assert len(sources) == 3
    categories = {category.key for category in pack.taxonomy.categories}
    for fm in sources:
        name = posixpath.basename(fm.source_path)
        assert fm.category in categories
        doc_type = next(entry for entry in pack.taxonomy.doc_types if entry.key == fm.doc_type)
        assert (doc_type.category, doc_type.authority) == (fm.category, fm.authority)
        match = match_doc_type(pack, name, "")
        assert match is not None and match.doc_type == fm.doc_type, name
        assert parse_doc_number(pack, name) == fm.doc_number, name
        assert parse_revision(pack, name) == fm.revision, name


def test_entities_topics_and_glossary_come_from_the_pack(
    pack: DomainPack, pages: list[Page], reader: ReleaseReader
) -> None:
    registry = {(entry.type, entry.key): entry for entry in pack.entities.registry}
    topic_slugs = {topic.slug for topic in pack.topics.topics}
    entity_pages = topic_pages = 0
    for page in pages:
        fm = page.frontmatter
        if isinstance(fm, EntityFrontmatter):
            entry = registry[(fm.entity_type, fm.key)]
            assert fm.title == entry.label
            assert [(alias.text, alias.lang) for alias in fm.aliases] == [
                (alias.text, alias.lang) for alias in entry.aliases
            ]
            entity_pages += 1
        elif isinstance(fm, TopicFrontmatter):
            assert fm.topic_slug in topic_slugs
            topic_pages += 1
    assert (entity_pages, topic_pages) == (3, 1)
    terms = {term.term: term for term in pack.glossary.terms}
    assert reader.catalog.glossary
    for entry in reader.catalog.glossary:
        assert entry.synonyms == terms[entry.term].synonyms


def test_content_pages_carry_the_banner_of_the_pack(pack: DomainPack, pages: list[Page]) -> None:
    banner = f"> {pack.info.banner}"
    content = [
        page
        for page in pages
        if isinstance(
            page.frontmatter,
            SourceFrontmatter | EntityFrontmatter | TopicFrontmatter | QueryFrontmatter,
        )
    ]
    assert len(content) == 8
    for page in content:
        assert banner in page.body, page.path


def test_the_single_filed_answer_cites_two_kinds_of_evidence(
    pages: list[Page], reader: ReleaseReader
) -> None:
    [query] = [page for page in pages if isinstance(page.frontmatter, QueryFrontmatter)]
    assert query.path.startswith("queries/") and query.frontmatter.approved_by == "owner"
    cited = [
        reader.resolve_evidence(source_id, locator_key).frontmatter.provenance
        for source_id, locator_key in (
            ("src-59cf9366e50c", "sheet-planning-r0006-r0009"),
            ("src-f0757603684a", "para-0011"),
            ("src-7630d0741377", "p0001"),
        )
    ]
    assert set(cited) == {"deterministic-table", "native-text"}
    section = query.body.split("## How this answer was produced", 1)[1].split("\n## ", 1)[0]
    bullets = [line for line in section.splitlines() if line.startswith("- ")]
    assert bullets == [
        "- search `date de livraison des fenêtres`",
        "- get_evidence `src-59cf9366e50c/sheet-planning-r0006-r0009`",
    ]
