"""Regenerating the corpus reproduces the committed files.

Extracted text must be identical everywhere. Bytes must be identical for plain-text formats, and
for every format when the interpreter, platform, library versions and embedded font files match
the ones recorded in MANIFEST.json (binary encoders such as zlib, libjpeg, fpdf2 font subsetting
and the DejaVu font files shape the bytes elsewhere).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

TEXT_FORMATS = {"eml"}


def test_regeneration_reproduces_text_and_bytes(tmp_path: Path, manifest: dict[str, Any]) -> None:
    from samples.generators.corpus import build_corpus
    from samples.generators.manifest import environment, text_sha256

    build_corpus(tmp_path, write_manifest=False)
    same_environment = environment() == manifest["generator"]["environment"]
    generated = {
        p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file()
    }
    assert generated == {entry["path"] for entry in manifest["files"]}
    text_mismatch: list[str] = []
    byte_mismatch: list[str] = []
    for entry in manifest["files"]:
        new_file = tmp_path / entry["path"]
        if text_sha256(new_file) != entry["text_sha256"]:
            text_mismatch.append(entry["path"])
        compare_bytes = entry["format"] in TEXT_FORMATS or same_environment
        digest = hashlib.sha256(new_file.read_bytes()).hexdigest()
        if compare_bytes and digest != entry["sha256"]:
            byte_mismatch.append(entry["path"])
    assert not text_mismatch, f"extracted text differs: {text_mismatch}"
    assert not byte_mismatch, f"bytes differ: {byte_mismatch}"
