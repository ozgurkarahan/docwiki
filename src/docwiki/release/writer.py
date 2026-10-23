"""ReleaseWriter: stage a release folder, hash every file into the manifest, finalize."""

from __future__ import annotations

import shutil
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from docwiki.contracts._base import sha256_hex
from docwiki.contracts.catalog import Catalog
from docwiki.contracts.extracted import Table
from docwiki.contracts.gates import GateResult
from docwiki.contracts.layout import EVIDENCE_MOUNT, ReleaseFiles
from docwiki.contracts.manifest import FileEntry, ReleaseInputs, ReleaseManifest
from docwiki.contracts.pages import DocwikiStamp, EvidencePage, Page
from docwiki.contracts.runs import VersionInfo
from docwiki.release.tables import SourceTablesIndex, write_source_tables
from docwiki.search.index import SearchBlock, SearchDbInfo, build_search_db

__all__ = ["ReleaseWriter", "StagedRelease", "hash_release_files"]

_TOP_LEVEL = frozenset(
    {
        ReleaseFiles.WIKI_DIR,
        ReleaseFiles.EVIDENCE_DIR,
        ReleaseFiles.TABLES_DIR,
        ReleaseFiles.SITE_DIR,
        ReleaseFiles.CATALOG,
        ReleaseFiles.SEARCH_DB,
    }
)


@dataclass(frozen=True)
class StagedRelease:
    """A finalized release folder ready to publish."""

    root: Path
    manifest: ReleaseManifest
    manifest_sha256: str

    @property
    def release_id(self) -> str:
        return self.manifest.release_id


def hash_release_files(root: Path) -> dict[str, FileEntry]:
    """``{relative path: {sha256, size}}`` for every file except ``manifest.json``, sorted."""
    files: dict[str, FileEntry] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if rel == ReleaseFiles.MANIFEST:
            continue
        data = path.read_bytes()
        files[rel] = FileEntry(sha256=sha256_hex(data), size=len(data))
    return dict(sorted(files.items()))


class ReleaseWriter:
    """Builds ``releases/<release_id>/`` in a local staging folder.

    The release id is computed up front from the manifest identity, so pages can embed it via
    :attr:`stamp`. Call :meth:`finalize` last: it hashes every file and writes ``manifest.json``.
    """

    def __init__(
        self,
        staging_dir: str | Path,
        *,
        created_at: datetime,
        audience: str,
        versions: VersionInfo,
        inputs: ReleaseInputs | None = None,
        run_id: str | None = None,
        wiki_languages: Sequence[str] = ("en",),
    ) -> None:
        if created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        self.created_at = created_at.astimezone(UTC).replace(microsecond=0)
        self.audience = audience
        self.versions = versions
        self.inputs = inputs or ReleaseInputs()
        self.run_id = run_id
        self.wiki_languages = list(wiki_languages) or ["en"]
        """The wiki languages, canonical first (v1.7, ADR 0012)."""
        self.release_id = ReleaseManifest.compute_release_id(
            created_at=self.created_at,
            audience=audience,
            run_id=run_id,
            inputs=self.inputs,
            versions=versions,
        )
        self.root = Path(staging_dir)
        if self.root.exists() and any(self.root.iterdir()):
            raise FileExistsError(f"staging folder is not empty: {self.root}")
        self.root.mkdir(parents=True, exist_ok=True)
        self._finalized = False

    @property
    def stamp(self) -> DocwikiStamp:
        """The ``docwiki`` frontmatter value for pages of this release."""
        return DocwikiStamp(release=self.release_id)

    def _target(self, rel_path: str) -> Path:
        if self._finalized:
            raise RuntimeError("release already finalized")
        parts = rel_path.split("/")
        if (
            not rel_path
            or rel_path.startswith("/")
            or "\\" in rel_path
            or any(p in ("", ".", "..") for p in parts)
        ):
            raise ValueError(f"invalid release path: {rel_path!r}")
        if parts[0] not in _TOP_LEVEL:
            raise ValueError(f"{rel_path!r} is outside the release layout")
        if parts[0] == ReleaseFiles.WIKI_DIR and len(parts) > 1 and parts[1] == EVIDENCE_MOUNT:
            raise ValueError("'wiki/evidence' is reserved (evidence lives at the release root)")
        target = self.root.joinpath(*parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def write_bytes(self, rel_path: str, data: bytes) -> str:
        self._target(rel_path).write_bytes(data)
        return rel_path

    def write_text(self, rel_path: str, text: str) -> str:
        """UTF-8 text with LF line endings (CR characters are rejected)."""
        if "\r" in text:
            raise ValueError(f"{rel_path}: CR characters are not allowed")
        return self.write_bytes(rel_path, text.encode("utf-8"))

    def copy_file(self, rel_path: str, source: str | Path) -> str:
        shutil.copyfile(source, self._target(rel_path))
        return rel_path

    def write_page(self, page: Page) -> str:
        """Write a wiki page to ``wiki/<page.path>`` (its stamp must carry this release id)."""
        if page.frontmatter.docwiki.release != self.release_id:
            raise ValueError(f"{page.path}: docwiki.release must be {self.release_id}")
        return self.write_text(f"{ReleaseFiles.WIKI_DIR}/{page.path}", page.render())

    def write_wiki_file(self, path: str, text: str) -> str:
        """Write a non-page wiki file (``llms.txt``, skill projections…)."""
        return self.write_text(f"{ReleaseFiles.WIKI_DIR}/{path}", text)

    def write_evidence(self, page: EvidencePage) -> str:
        """Write a sidecar; ``page.path`` is ``evidence/<source_id>/<locator_key>.md``."""
        if not page.path.startswith(f"{EVIDENCE_MOUNT}/"):
            raise ValueError("evidence pages live under 'evidence/'")
        return self.write_text(page.path, page.render())

    def write_catalog(self, catalog: Catalog) -> None:
        """``catalog.json`` at the release root and an identical copy in ``wiki/``."""
        if catalog.release_id != self.release_id or catalog.audience != self.audience:
            raise ValueError("catalog release_id/audience must match the release")
        if catalog.wiki_languages != self.wiki_languages:
            raise ValueError("catalog wiki_languages must match the release")
        text = catalog.to_json()
        self.write_text(ReleaseFiles.CATALOG, text)
        self.write_text(f"{ReleaseFiles.WIKI_DIR}/{ReleaseFiles.CATALOG}", text)

    def write_tables(
        self, source_id: str, tables: list[Table], sensitivity: str
    ) -> SourceTablesIndex:
        self._target(f"{ReleaseFiles.TABLES_DIR}/{source_id}/index.json")
        return write_source_tables(self.root, source_id, tables, sensitivity)

    def write_search_db(
        self,
        pages: Iterable[Page],
        blocks: Iterable[SearchBlock],
        synonyms: Iterable[tuple[str, str, str]],
        *,
        use_fts5: bool | None = None,
    ) -> SearchDbInfo:
        return build_search_db(
            pages,
            blocks,
            synonyms,
            self._target(ReleaseFiles.SEARCH_DB),
            release_id=self.release_id,
            audience=self.audience,
            use_fts5=use_fts5,
            languages=self.wiki_languages,
        )

    def finalize(
        self, *, gates: Iterable[GateResult] = (), counts: dict[str, int] | None = None
    ) -> StagedRelease:
        """Hash all files, write ``manifest.json`` and close the writer."""
        if self._finalized:
            raise RuntimeError("release already finalized")
        manifest = ReleaseManifest(
            release_id=self.release_id,
            created_at=self.created_at,
            audience=self.audience,  # type: ignore[arg-type]
            run_id=self.run_id,
            inputs=self.inputs,
            versions=self.versions,
            counts=dict(sorted((counts or {}).items())),
            gates=list(gates),
            files=hash_release_files(self.root),
            wiki_languages=self.wiki_languages,
        )
        data = manifest.to_json().encode("utf-8")
        (self.root / ReleaseFiles.MANIFEST).write_bytes(data)
        self._finalized = True
        return StagedRelease(self.root, manifest, sha256_hex(data))
