"""ReleaseReader: open a release folder, a portable wiki folder or a ``current.json`` pointer."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any

from docwiki.contracts._base import sha256_hex
from docwiki.contracts.catalog import Catalog, CatalogEdge, CatalogPage
from docwiki.contracts.ids import SOURCE_ID_RE
from docwiki.contracts.layout import EVIDENCE_MOUNT, SKILL_PROJECTIONS
from docwiki.contracts.locators import parse_locator_key
from docwiki.contracts.manifest import CurrentPointer, ReleaseManifest
from docwiki.contracts.markdown import split_sections
from docwiki.contracts.pages import EvidenceFrontmatter, EvidencePage, Page, SkillFile
from docwiki.release.layout import PORTABLE_META_DIR, ReleaseIntegrityError, ReleaseLayout
from docwiki.release.tables import (
    SourceTablesIndex,
    TableQueryResult,
    connect_tables_at,
    query_tables_at,
    read_tables_index_at,
)

__all__ = ["EvidenceRecord", "ReleaseNotFoundError", "ReleaseReader", "SkillInfo"]


class ReleaseNotFoundError(FileNotFoundError):
    """No release folder or ``current.json`` at the given location."""


@dataclass(frozen=True)
class EvidenceRecord:
    """A resolved evidence sidecar."""

    source_id: str
    locator_key: str
    path: str
    """Content-namespace path (``evidence/<source_id>/<locator_key>.md``)."""
    frontmatter: EvidenceFrontmatter
    body: str
    original: str | None
    """Content-namespace path of the published original, when present."""


@dataclass(frozen=True)
class SkillInfo:
    name: str
    description: str
    path: str


class ReleaseReader:
    """Read-only view of one release, in the release layout (``manifest.json``, ``wiki/``,
    ``evidence/``, ``tables/``) or the portable layout (wiki at the root, ``evidence/``,
    machine files in ``.docwiki/``); see :class:`~docwiki.release.layout.ReleaseLayout`."""

    def __init__(
        self,
        root: str | Path,
        *,
        pointer: CurrentPointer | None = None,
        pointer_bytes: bytes | None = None,
    ) -> None:
        layout = ReleaseLayout.detect(root)
        if layout is None:
            raise ReleaseNotFoundError(
                f"no manifest.json or {PORTABLE_META_DIR}/manifest.json in {Path(root)}"
            )
        self.layout = layout
        self.root = layout.root
        self.pointer = pointer
        self.pointer_bytes = pointer_bytes

    @classmethod
    def open(cls, path: str | Path, *, verify: bool = False) -> ReleaseReader:
        """Open a release dir, a portable wiki folder (``.docwiki/manifest.json``), a
        ``releases/`` folder with ``current.json``, or a folder that contains
        ``releases/current.json`` (such as the mock release fixture).

        ``verify=True`` checks every manifest hash first (:meth:`verify_files`) and raises
        :class:`~docwiki.release.layout.ReleaseIntegrityError` on any mismatch.
        """
        base = Path(path)
        reader: ReleaseReader | None = None
        layout = ReleaseLayout.detect(base)
        if layout is not None and layout.pointer_path is not None:
            data = layout.pointer_path.read_bytes()
            reader = cls(base, pointer=CurrentPointer.from_json(data), pointer_bytes=data)
        elif layout is not None:
            reader = cls(base)
        else:
            for releases in (base, base / "releases"):
                pointer_file = releases / "current.json"
                if pointer_file.is_file():
                    data = pointer_file.read_bytes()
                    pointer = CurrentPointer.from_json(data)
                    reader = cls(releases / pointer.release_id, pointer=pointer, pointer_bytes=data)
                    break
        if reader is None:
            raise ReleaseNotFoundError(f"no release or current.json found at {base}")
        if verify:
            problems = reader.verify_files()
            if problems:
                raise ReleaseIntegrityError("; ".join(problems[:5]))
        return reader

    @property
    def portable(self) -> bool:
        return self.layout.portable

    @cached_property
    def manifest_bytes(self) -> bytes:
        return self.layout.manifest_path.read_bytes()

    @cached_property
    def manifest(self) -> ReleaseManifest:
        return ReleaseManifest.from_json(self.manifest_bytes)

    @property
    def manifest_sha256(self) -> str:
        return sha256_hex(self.manifest_bytes)

    @property
    def release_id(self) -> str:
        return self.manifest.release_id

    @property
    def audience(self) -> str:
        return self.manifest.audience

    @cached_property
    def catalog(self) -> Catalog:
        return Catalog.from_json(self.layout.catalog_path.read_bytes())

    @property
    def wiki_root(self) -> Path:
        return self.layout.wiki_root

    @property
    def evidence_root(self) -> Path:
        return self.layout.evidence_root

    @property
    def tables_root(self) -> Path:
        return self.layout.tables_root

    def file_for(self, release_rel: str) -> Path | None:
        """File of a manifest path (``wiki/…``, ``evidence/…``, ``tables/…``, ``search.db``)."""
        return self.layout.file_for(release_rel)

    def verify_files(self) -> list[str]:
        """Problems found when checking every manifest entry (path mapping applied); ``[]`` when
        all files exist with the recorded size and SHA-256."""
        problems: list[str] = []
        for rel, entry in self.manifest.files.items():
            file = self.layout.file_for(rel)
            if file is None:
                continue
            if not file.is_file():
                problems.append(f"{self.layout.display(rel)}: missing")
                continue
            data = file.read_bytes()
            if len(data) != entry.size or sha256_hex(data) != entry.sha256:
                problems.append(f"{self.layout.display(rel)}: does not match manifest.json")
        return problems

    def content_file(self, ns_path: str) -> Path:
        """File of a content-namespace path (``evidence/…`` maps to the evidence folder)."""
        return self.layout.content_file(ns_path)

    def list_pages(self, page_type: str | None = None) -> list[CatalogPage]:
        return [page for page in self.catalog.pages if page_type is None or page.type == page_type]

    def page_entry(self, page: str) -> CatalogPage:
        """Catalog entry by page id or wiki path."""
        entry = self.catalog.page_by_id().get(page) or self.catalog.page_by_path().get(page)
        if entry is None:
            raise KeyError(f"unknown page: {page!r}")
        return entry

    def read_page_text(self, page: str) -> str:
        return self.content_file(self.page_entry(page).path).read_text(encoding="utf-8")

    def read_page(self, page: str) -> Page:
        entry = self.page_entry(page)
        return Page.parse(self.read_page_text(page), entry.path)

    def read_section(self, page: str, section: str) -> str:
        """Markdown of one section, matched by heading text (case-insensitive) or anchor."""
        wanted = section.strip().lstrip("#").strip()
        for item in split_sections(self.read_page(page).body):
            if item.heading is None:
                continue
            if item.anchor == wanted or item.heading.casefold() == wanted.casefold():
                return f"{'#' * item.level} {item.heading}\n{item.markdown}".rstrip() + "\n"
        raise KeyError(f"section {section!r} not found in {page!r}")

    def links(self, page: str) -> dict[str, list[CatalogEdge]]:
        """``{"outgoing": [...], "backlinks": [...]}`` from the catalog edges."""
        page_id = self.page_entry(page).id
        return {
            "outgoing": [edge for edge in self.catalog.edges if edge.from_ == page_id],
            "backlinks": [edge for edge in self.catalog.edges if edge.to == page_id],
        }

    def evidence_path(self, source_id: str, locator_key: str) -> str:
        if not SOURCE_ID_RE.match(source_id):
            raise ValueError(f"invalid source_id: {source_id!r}")
        parse_locator_key(locator_key)
        return f"{EVIDENCE_MOUNT}/{source_id}/{locator_key}.md"

    def resolve_evidence(self, source_id: str, locator_key: str) -> EvidenceRecord:
        ns_path = self.evidence_path(source_id, locator_key)
        file = self.content_file(ns_path)
        if not file.is_file():
            raise KeyError(f"no evidence sidecar {ns_path}")
        page = EvidencePage.parse(file.read_text(encoding="utf-8"), ns_path)
        if not isinstance(page.frontmatter, EvidenceFrontmatter):
            raise KeyError(f"{ns_path} is not an evidence sidecar")
        originals = sorted(
            p.name for p in (self.evidence_root / source_id).glob("original.*") if p.is_file()
        )
        original = f"{EVIDENCE_MOUNT}/{source_id}/{originals[0]}" if originals else None
        return EvidenceRecord(
            source_id, locator_key, ns_path, page.frontmatter, page.body, original
        )

    def list_evidence(self, source_id: str | None = None) -> list[str]:
        base = self.evidence_root
        pattern = f"{source_id}/*.md" if source_id else "*/*.md"
        return sorted(
            f"{EVIDENCE_MOUNT}/{p.relative_to(base).as_posix()}"
            for p in base.glob(pattern)
            if p.name != "index.md"
        )

    @property
    def search_db_path(self) -> Path:
        return self.layout.search_db_path

    def open_search(self, *, force_fallback: bool = False) -> Any:
        from docwiki.search.index import SearchIndex

        return SearchIndex.open(self.search_db_path, force_fallback=force_fallback)

    def tables(self, source_id: str) -> SourceTablesIndex:
        return read_tables_index_at(self.tables_root, source_id)

    def sources_with_tables(self) -> list[str]:
        """Source ids that have an ``index.json`` in the tables folder."""
        if not self.tables_root.is_dir():
            return []
        return sorted(
            folder.name
            for folder in self.tables_root.iterdir()
            if folder.is_dir() and (folder / "index.json").is_file()
        )

    def table_file(self, source_id: str, table_id: str) -> Path:
        entry = self.tables(source_id).entry(table_id)
        return self.tables_root / source_id / entry.file

    def connect_tables(self, source_id: str) -> Any:
        """Locked-down in-memory DuckDB connection with tables ``t01``… of a source."""
        return connect_tables_at(self.tables_root, source_id)

    def query_table(self, source_id: str, sql: str, *, max_rows: int = 200) -> TableQueryResult:
        return query_tables_at(self.tables_root, source_id, sql, max_rows=max_rows)

    def list_skills(self) -> list[SkillInfo]:
        base = self.wiki_root / SKILL_PROJECTIONS[0]
        skills: list[SkillInfo] = []
        if not base.is_dir():
            return skills
        for folder in sorted(p for p in base.iterdir() if p.is_dir()):
            skill = SkillFile.parse((folder / "SKILL.md").read_text(encoding="utf-8"), folder.name)
            skills.append(
                SkillInfo(
                    skill.name,
                    skill.frontmatter.description,
                    f"{SKILL_PROJECTIONS[0]}/{folder.name}/SKILL.md",
                )
            )
        return skills

    def read_skill(self, name: str) -> str:
        for skill in self.list_skills():
            if skill.name == name:
                return self.content_file(skill.path).read_text(encoding="utf-8")
        raise KeyError(f"unknown skill: {name!r}")
