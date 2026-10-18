"""Folder-storage releases with a ``site/`` folder, published like the pipeline does."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from docwiki.contracts.gates import gate_results
from docwiki.contracts.manifest import CurrentPointer
from docwiki.contracts.runs import VersionInfo
from docwiki.contracts.storage import FolderStorage
from docwiki.release import ReleaseWriter, publish_release

CREATED_AT = datetime(2026, 2, 15, 9, 0, tzinfo=UTC)
VERSIONS = VersionInfo(docwiki="0.1.0", domain_pack="portal-test", domain_pack_hash="test")


def site_files(title: str) -> dict[str, bytes]:
    page = f"<!DOCTYPE html><title>{title}</title>".encode()
    return {
        "site/index.html": page + b"<p>home</p>",
        "site/404.html": page + b"<p>Page not found</p>",
        "site/sources/a.html": page + b"<p>source a</p>",
        "site/sources/index.html": page + b"<p>sources</p>",
        "site/postscript.js": b"console.log(1)",
        "site/index.css": b"body{}",
        "site/static/docwiki/icon.svg": b"<svg xmlns='http://www.w3.org/2000/svg'/>",
        "site/evidence/src-0/img/p0001.png": b"\x89PNG",
        "site/llms.txt": b"# Wiki\n",
    }


def publish(
    storage: FolderStorage,
    staging: Path,
    *,
    title: str = "first",
    day: int = 0,
    with_site: bool = True,
) -> CurrentPointer:
    writer = ReleaseWriter(
        staging,
        created_at=CREATED_AT + timedelta(days=day),
        audience="public",
        versions=VERSIONS,
    )
    writer.write_text("wiki/index.md", f"# {title}\n")
    if with_site:
        for path, data in site_files(title).items():
            writer.write_bytes(path, data)
    staged = writer.finalize(gates=gate_results([]))
    return publish_release(storage, staged, now=CREATED_AT + timedelta(days=day))
