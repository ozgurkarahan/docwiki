"""Builders of small, valid pages for the assemble-stage unit tests (fictional content)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from docwiki.contracts.ids import source_id_for
from docwiki.contracts.manifest import ReleaseInputs, ReleaseManifest
from docwiki.contracts.pages import (
    DocwikiStamp,
    EntityFrontmatter,
    ExtractionSummary,
    Page,
    SourceFrontmatter,
    TopicFrontmatter,
)
from docwiki.contracts.runs import VersionInfo
from docwiki.domain import load_pack
from docwiki.domain.models import DomainPack

PACK_DIR = Path(__file__).resolve().parent / "fixtures" / "test-pack"
CREATED = datetime(2026, 4, 1, 9, 0, 0, tzinfo=UTC)
DAY = date(2026, 4, 1)
VERSIONS = VersionInfo(docwiki="0.1.0", domain_pack="test-batiment", domain_pack_hash="h")
RELEASE_ID = ReleaseManifest.compute_release_id(
    created_at=CREATED,
    audience="internal",
    run_id=None,
    inputs=ReleaseInputs(),
    versions=VERSIONS,
)
STAMP = DocwikiStamp(release=RELEASE_ID)


def pack() -> DomainPack:
    return load_pack(PACK_DIR)


def source_page(
    raw_path: str,
    title: str,
    body: str,
    *,
    slug: str,
    entities: list[str] | None = None,
    supersedes: list[str] | None = None,
    superseded_by: list[str] | None = None,
    sensitivity: str = "public",
    category: str = "contract-documents",
) -> Page:
    source_id = source_id_for(raw_path)
    fm = SourceFrontmatter(
        id=source_id,
        title=title,
        summary=f"Summary of {title}.",
        sensitivity=sensitivity,  # type: ignore[arg-type]
        updated=DAY,
        docwiki=STAMP,
        source_id=source_id,
        source_path=raw_path,
        source_hash="sha256:" + "0" * 64,
        media_type="text/plain",
        doc_type="quote",
        category=category,
        status="superseded" if superseded_by else "current",
        supersedes=sorted(supersedes or []),
        superseded_by=sorted(superseded_by or []),
        original_lang="fr",
        entities=sorted(entities or []),
        authority=8,
        extraction=ExtractionSummary(adapter="local", version="1"),
    )
    return Page(path=f"sources/{slug}.md", frontmatter=fm, body=body)


def entity_page(entity_id: str, title: str, body: str, *, sources: list[str]) -> Page:
    entity_type, key = entity_id.split(":")
    fm = EntityFrontmatter(
        id=entity_id,
        title=title,
        summary=f"{title} of the registry.",
        sensitivity="public",
        updated=DAY,
        docwiki=STAMP,
        entity_type=entity_type,
        key=key,
        sources=sorted(sources),
    )
    return Page(path=f"entities/{entity_type}/{key}.md", frontmatter=fm, body=body)


def topic_page(slug: str, title: str, body: str, *, sources: list[str]) -> Page:
    fm = TopicFrontmatter(
        id=f"topic:{slug}",
        title=title,
        summary=f"Synthesis about {title.lower()}.",
        sensitivity="public",
        updated=DAY,
        docwiki=STAMP,
        topic_slug=slug,
        sources=sorted(sources),
        confidence="medium",
    )
    return Page(path=f"topics/{slug}.md", frontmatter=fm, body=body)
