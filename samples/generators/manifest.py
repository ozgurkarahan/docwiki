"""Corpus manifest: hashes, formats, counts, extracted-text hashes, held-back flag, sensitivity."""

from __future__ import annotations

import hashlib
import platform
import sys
import unicodedata
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

from .fonts import font_hashes
from .textdump import MEDIA_TYPES, Extracted, extract
from .world import BIBLE_PATH, World

MANIFEST_NAME = "MANIFEST.json"
LIBRARIES = (
    "fpdf2",
    "fonttools",
    "matplotlib",
    "numpy",
    "openpyxl",
    "pillow",
    "pypdfium2",
    "python-docx",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def environment() -> dict[str, Any]:
    """Interpreter, platform, library versions and embedded fonts.

    Byte-identical regeneration of binary formats needs a match (zlib, libjpeg, fpdf2 and the
    font files shape the bytes); the extracted-text hashes must match everywhere.
    """
    return {
        "python": ".".join(str(v) for v in sys.version_info[:3]),
        "platform": f"{sys.platform}-{platform.machine().lower()}",
        "libraries": {name: importlib_metadata.version(name) for name in LIBRARIES},
        "fonts": font_hashes(),
    }


def text_digest(extracted: Extracted) -> str | None:
    """sha256 of the extracted text (NFC), or None for files without text units (images)."""
    if not extracted.units:
        return None
    text = unicodedata.normalize("NFC", extracted.text())
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def text_sha256(path: Path) -> str | None:
    return text_digest(extract(path))


def build_manifest(out_root: Path, world: World) -> dict[str, Any]:
    docs = {str(doc["path"]): doc for doc in world.documents}
    entries: list[dict[str, Any]] = []
    files = sorted(
        (p for p in out_root.rglob("*") if p.is_file() and p.name != MANIFEST_NAME),
        key=lambda p: p.relative_to(out_root).as_posix(),
    )
    for file in files:
        rel = file.relative_to(out_root).as_posix()
        if rel not in docs:
            raise ValueError(f"file not described in the bible document catalog: {rel}")
        doc = docs[rel]
        fmt = file.suffix.lower().lstrip(".")
        extracted = extract(file)
        entries.append(
            {
                "path": rel,
                "id": doc["id"],
                "sha256": sha256_file(file),
                "bytes": file.stat().st_size,
                "format": fmt,
                "media_type": MEDIA_TYPES[fmt],
                "kind": doc["kind"],
                "title": doc["title"],
                "lang": doc["lang"],
                "date": doc["date"],
                "doc_number": doc.get("doc_number"),
                "revision": doc.get("revision"),
                "held_back": bool(doc.get("held_back")),
                "sensitivity": doc["sensitivity"],
                "procedure_like": bool(doc["procedure_like"]),
                "stamp": doc["stamp"],
                "counts": extracted.counts,
                "text_sha256": text_digest(extracted),
            }
        )
    by_format: dict[str, int] = {}
    for entry in entries:
        by_format[entry["format"]] = by_format.get(entry["format"], 0) + 1
    return {
        "schema": 1,
        "description": (
            "Fictional DocWiki sample corpus (closed world: samples/fiction/bible.yaml). "
            "Paths are relative to samples/corpus. CC BY 4.0."
        ),
        "generator": {
            "name": "DocWiki sample generator",
            "command": "uv run python samples/generators/build.py --out samples/corpus",
            "seed": world.seed,
            "environment": environment(),
        },
        "bible_sha256": sha256_file(BIBLE_PATH),
        "totals": {
            "files": len(entries),
            "documents": sum(1 for e in entries if not e["held_back"]),
            "held_back": sum(1 for e in entries if e["held_back"]),
            "bytes": sum(e["bytes"] for e in entries),
            "by_format": dict(sorted(by_format.items())),
        },
        "files": entries,
    }
