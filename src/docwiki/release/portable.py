"""Portable wiki folder: the content namespace as a plain folder plus ``.docwiki/`` machine files.

``export_portable(release, out)`` writes:

* the wiki files at the folder root and the evidence sidecars under ``evidence/`` (the Quartz
  ``content/`` layout), so every relative link (``../evidence/<source_id>/<key>.md``) resolves as a
  plain file path on GitHub, in Obsidian/VS Code and for agents reading files;
* ``.docwiki/manifest.json`` (copied unchanged), ``.docwiki/current.json`` (pointer copy),
  ``.docwiki/search.db`` and ``.docwiki/tables/``.

``site/`` (the Quartz build output) is not part of a portable folder.
"""

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path

from pydantic import ValidationError

from docwiki.contracts._base import sha256_hex
from docwiki.contracts.layout import SKILL_PROJECTIONS, ReleaseFiles
from docwiki.contracts.manifest import CurrentPointer
from docwiki.release.layout import (
    POINTER_FILE,
    PORTABLE_META_DIR,
    ReleaseIntegrityError,
    ReleaseLayout,
    is_portable,
)
from docwiki.release.reader import ReleaseReader

__all__ = ["export_portable", "portable_owned_entries"]


def _remove(path: Path) -> None:
    def make_writable(function, target, _excinfo) -> None:  # type: ignore[no-untyped-def]
        os.chmod(target, stat.S_IWRITE)
        function(target)

    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path, onexc=make_writable)
    else:
        path.unlink()


def portable_owned_entries(folder: str | Path) -> list[Path]:
    """Entries of ``folder`` that an export owns and replaces: every non-dot entry,
    ``.docwiki/`` and the ``skills/`` folders of ``.agents``, ``.claude`` and ``.github``.
    Other dot entries (``.git``, ``.obsidian``, ``.github/workflows``…) are left alone."""
    base = Path(folder)
    if not base.is_dir():
        return []
    owned: list[Path] = []
    for child in sorted(base.iterdir()):
        if child.name == PORTABLE_META_DIR or not child.name.startswith("."):
            owned.append(child)
    for projection in SKILL_PROJECTIONS:
        skills = base.joinpath(*projection.split("/"))
        if skills.exists():
            owned.append(skills)
    return owned


def _clean(out: Path, *, force: bool) -> None:
    if not out.exists():
        out.mkdir(parents=True)
        return
    if not out.is_dir():
        raise NotADirectoryError(f"{out} is not a folder")
    owned = portable_owned_entries(out)
    if owned and not is_portable(out) and not force:
        raise FileExistsError(
            f"{out} is not empty and is not a portable wiki folder; pass force=True to replace "
            "its non-dot entries"
        )
    for entry in owned:
        _remove(entry)
    for projection in SKILL_PROJECTIONS:
        parent = out / projection.split("/", 1)[0]
        if parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()


def _pointer_bytes(reader: ReleaseReader) -> bytes:
    """The pointer copy: the pointer that selected the release when it names this manifest, else
    the parent folder's ``current.json`` when it does, else one derived from the manifest."""
    candidates: list[bytes] = []
    if reader.pointer_bytes is not None:
        candidates.append(reader.pointer_bytes)
    if not reader.portable:
        sibling = reader.root.parent / POINTER_FILE
        if sibling.is_file():
            candidates.append(sibling.read_bytes())
    for data in candidates:
        try:
            pointer = CurrentPointer.from_json(data)
        except ValidationError:
            continue
        if pointer.release_id != reader.release_id:
            continue
        if pointer.manifest_sha256 != reader.manifest_sha256:
            raise ReleaseIntegrityError(
                f"current.json of {reader.release_id} does not match its manifest.json"
            )
        return data
    derived = CurrentPointer(
        release_id=reader.release_id,
        created_at=reader.manifest.created_at,
        audience=reader.manifest.audience,
        manifest_sha256=reader.manifest_sha256,
    )
    return derived.to_json().encode("utf-8")


def export_portable(release_root: str | Path, out_dir: str | Path, *, force: bool = False) -> Path:
    """Write the portable wiki folder of a release into ``out_dir`` and return it.

    ``release_root`` is anything :meth:`ReleaseReader.open` accepts (release folder, ``releases/``
    folder or fixture root with ``current.json``, or a portable folder). Every file is checked
    against the manifest before it is written; the output is deterministic and the export is
    idempotent: owned entries of ``out_dir`` are replaced (see :func:`portable_owned_entries`),
    other dot entries are kept. A non-empty folder that is not already a portable wiki folder is
    only cleaned with ``force=True``.
    """
    reader = ReleaseReader.open(release_root)
    source = reader.layout
    out = Path(out_dir)
    src, dst = source.root.resolve(), out.resolve()
    if dst == src or dst.is_relative_to(src) or src.is_relative_to(dst):
        raise ValueError("out_dir must not be the release folder, inside it or one of its parents")
    pointer = _pointer_bytes(reader)
    _clean(out, force=force)
    target = ReleaseLayout("portable", out)
    written: dict[str, str] = {}
    for rel, entry in sorted(reader.manifest.files.items()):
        physical = target.physical(rel)
        origin = source.file_for(rel)
        if physical is None or origin is None:
            continue
        data = origin.read_bytes()
        if len(data) != entry.size or sha256_hex(data) != entry.sha256:
            raise ReleaseIntegrityError(f"{source.display(rel)} does not match manifest.json")
        if physical in written:
            if written[physical] != entry.sha256:
                raise ReleaseIntegrityError(f"{rel} and another copy of {physical} differ")
            continue
        destination = out.joinpath(*physical.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        written[physical] = entry.sha256
    meta = target.meta_root
    meta.mkdir(parents=True, exist_ok=True)
    (meta / ReleaseFiles.MANIFEST).write_bytes(reader.manifest_bytes)
    (meta / POINTER_FILE).write_bytes(pointer)
    return out
