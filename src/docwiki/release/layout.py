"""Physical layouts of a release: the published release folder and the portable wiki folder.

* ``release``: ``releases/<id>/{manifest.json, catalog.json, search.db, wiki/, evidence/, tables/,
  site/}`` (architecture §3).
* ``portable``: the content namespace as the folder root (wiki files at the root, ``evidence/``
  mounted at ``evidence/``, exactly like the Quartz ``content/`` folder) plus the machine files in
  ``.docwiki/{manifest.json, current.json, search.db, tables/}``. Relative links resolve with plain
  file paths, so the folder works on GitHub, in Obsidian/VS Code and for agents reading files.

Manifest paths are always release-relative (``wiki/…``, ``evidence/…``, ``tables/…``,
``search.db``, ``catalog.json``); :meth:`ReleaseLayout.file_for` maps them to files.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from docwiki.contracts.layout import EVIDENCE_MOUNT, SKILL_PROJECTIONS, ReleaseFiles

__all__ = [
    "POINTER_FILE",
    "PORTABLE_META_DIR",
    "ReleaseIntegrityError",
    "ReleaseLayout",
    "is_portable",
]

PORTABLE_META_DIR = ".docwiki"
"""Folder of the machine files inside a portable wiki folder."""

POINTER_FILE = "current.json"


class ReleaseIntegrityError(RuntimeError):
    """A release file is missing or does not match the manifest hash."""


def is_portable(path: str | Path) -> bool:
    """True when ``path`` is a portable wiki folder (``.docwiki/manifest.json`` present)."""
    return (Path(path) / PORTABLE_META_DIR / ReleaseFiles.MANIFEST).is_file()


def _walk(directory: Path) -> Iterator[Path]:
    """Files below ``directory`` (sorted, symlinked folders not followed)."""
    for current, dirnames, filenames in os.walk(directory):
        dirnames.sort()
        for name in sorted(filenames):
            yield Path(current) / name


@dataclass(frozen=True)
class ReleaseLayout:
    """Where the parts of one release live on disk."""

    kind: Literal["release", "portable"]
    root: Path

    @classmethod
    def detect(cls, path: str | Path) -> ReleaseLayout | None:
        """The layout rooted exactly at ``path`` (pointers are not followed), else ``None``."""
        root = Path(path)
        if (root / ReleaseFiles.MANIFEST).is_file():
            return cls("release", root)
        if is_portable(root):
            return cls("portable", root)
        return None

    @property
    def portable(self) -> bool:
        return self.kind == "portable"

    @property
    def wiki_root(self) -> Path:
        return self.root if self.portable else self.root / ReleaseFiles.WIKI_DIR

    @property
    def evidence_root(self) -> Path:
        return self.root / EVIDENCE_MOUNT

    @property
    def meta_root(self) -> Path:
        """Folder holding ``manifest.json``, ``search.db`` and ``tables/``."""
        return self.root / PORTABLE_META_DIR if self.portable else self.root

    @property
    def manifest_path(self) -> Path:
        return self.meta_root / ReleaseFiles.MANIFEST

    @property
    def search_db_path(self) -> Path:
        return self.meta_root / ReleaseFiles.SEARCH_DB

    @property
    def tables_root(self) -> Path:
        return self.meta_root / ReleaseFiles.TABLES_DIR

    @property
    def catalog_path(self) -> Path:
        """``catalog.json`` (in a portable folder: the wiki copy at the folder root)."""
        return self.root / ReleaseFiles.CATALOG

    @property
    def pointer_path(self) -> Path | None:
        """The pointer copy of a portable folder (``.docwiki/current.json``), if any."""
        if not self.portable:
            return None
        pointer = self.meta_root / POINTER_FILE
        return pointer if pointer.is_file() else None

    @property
    def site_root(self) -> Path | None:
        return None if self.portable else self.root / ReleaseFiles.SITE_DIR

    def physical(self, release_rel: str) -> str | None:
        """Folder-relative path of a manifest path; ``None`` when the layout omits it
        (``site/`` is not part of a portable folder)."""
        if not self.portable:
            return release_rel
        head, _, rest = release_rel.partition("/")
        if head == ReleaseFiles.WIKI_DIR and rest:
            return rest
        if head == ReleaseFiles.SITE_DIR:
            return None
        if head == EVIDENCE_MOUNT or release_rel == ReleaseFiles.CATALOG:
            return release_rel
        return f"{PORTABLE_META_DIR}/{release_rel}"

    def file_for(self, release_rel: str) -> Path | None:
        """File of a manifest path (``None`` when the layout omits it)."""
        physical = self.physical(release_rel)
        return None if physical is None else self.root.joinpath(*physical.split("/"))

    def display(self, release_rel: str) -> str:
        """Path reported to users (folder-relative)."""
        return self.physical(release_rel) or release_rel

    def wiki_display(self, wiki_rel: str) -> str:
        """Reported path of a wiki-relative path (``""`` is the wiki root itself)."""
        if not wiki_rel:
            return "." if self.portable else ReleaseFiles.WIKI_DIR
        return self.display(f"{ReleaseFiles.WIKI_DIR}/{wiki_rel}")

    def ns_display(self, ns_path: str) -> str:
        """Reported path of a content-namespace path."""
        if ns_path.split("/", 1)[0] == EVIDENCE_MOUNT:
            return ns_path
        return self.wiki_display(ns_path)

    def content_file(self, ns_path: str) -> Path:
        """File of a content-namespace path (wiki pages and ``evidence/…``)."""
        parts = ns_path.split("/")
        if not ns_path or "\\" in ns_path or any(part in ("", ".", "..") for part in parts):
            raise ValueError(f"invalid content path: {ns_path!r}")
        if parts[0] == EVIDENCE_MOUNT:
            return self.root.joinpath(*parts)
        return self.wiki_root.joinpath(*parts)

    def _owned_wiki_dot_dirs(self) -> list[Path]:
        return [self.root.joinpath(*projection.split("/")) for projection in SKILL_PROJECTIONS]

    def wiki_files(self) -> list[tuple[str, Path]]:
        """``(wiki-relative path, file)`` of every wiki file, excluding the evidence mount and,
        in a portable folder, ``.docwiki/`` and dot entries the export does not own."""
        if not self.portable:
            base = self.wiki_root
            if not base.is_dir():
                return []
            return [(path.relative_to(base).as_posix(), path) for path in _walk(base)]
        files: list[Path] = []
        for child in sorted(self.root.iterdir()):
            if child.name.startswith(".") or child.name == EVIDENCE_MOUNT:
                continue
            files.extend(_walk(child) if child.is_dir() else [child])
        for skills in self._owned_wiki_dot_dirs():
            if skills.is_dir():
                files.extend(_walk(skills))
        return sorted(
            ((path.relative_to(self.root).as_posix(), path) for path in files),
            key=lambda item: item[0],
        )

    def owned_files(self) -> list[Path]:
        """Every file this layout manages (``manifest.json`` and the pointer copy included)."""
        if not self.portable:
            return list(_walk(self.root)) if self.root.is_dir() else []
        files = [path for _, path in self.wiki_files()]
        for extra in (self.evidence_root, self.meta_root):
            if extra.is_dir():
                files.extend(_walk(extra))
        return sorted(files)

    def release_rel_of(self, path: Path) -> str | None:
        """Manifest path of an owned file (``None`` for the manifest, the pointer copy and files
        the layout does not own)."""
        try:
            rel = path.relative_to(self.root).as_posix()
        except ValueError:
            return None
        if not self.portable:
            return None if rel == ReleaseFiles.MANIFEST else rel
        head, _, rest = rel.partition("/")
        if head == PORTABLE_META_DIR:
            if rest in (ReleaseFiles.MANIFEST, POINTER_FILE):
                return None
            return rest or None
        if head == EVIDENCE_MOUNT:
            return rel
        if rel == ReleaseFiles.CATALOG:
            return f"{ReleaseFiles.WIKI_DIR}/{ReleaseFiles.CATALOG}"
        if head.startswith(".") and not any(
            rel.startswith(f"{projection}/") for projection in SKILL_PROJECTIONS
        ):
            return None
        return f"{ReleaseFiles.WIKI_DIR}/{rel}"
