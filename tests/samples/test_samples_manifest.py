"""The committed corpus matches MANIFEST.json, the bible catalog and the spec composition."""

from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

MAX_TOTAL_BYTES = 15_000_000
MAX_FILE_BYTES = 1_000_000


def test_manifest_lists_every_file_with_matching_hash(
    corpus_root: Path, manifest: dict[str, Any]
) -> None:
    listed = {entry["path"]: entry for entry in manifest["files"]}
    on_disk = {
        p.relative_to(corpus_root).as_posix()
        for p in corpus_root.rglob("*")
        if p.is_file() and p.name != "MANIFEST.json"
    }
    assert on_disk == set(listed)
    for path, entry in listed.items():
        data = (corpus_root / path).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"], path
        assert len(data) == entry["bytes"], path


def test_manifest_matches_bible_catalog(
    documents: list[dict[str, Any]], bible: dict[str, Any]
) -> None:
    catalog = {doc["path"]: doc for doc in bible["documents"]}
    assert {entry["path"] for entry in documents} == set(catalog)
    for entry in documents:
        doc = catalog[entry["path"]]
        assert entry["id"] == doc["id"]
        assert entry["doc_number"] == doc.get("doc_number")
        assert entry["revision"] == doc.get("revision")
        assert entry["sensitivity"] == doc["sensitivity"]
        assert entry["quickstart"] == bool(doc.get("quickstart"))
        assert entry["held_back"] == bool(doc.get("held_back"))


def test_quickstart_copies_are_byte_identical(
    corpus_root: Path, manifest: dict[str, Any]
) -> None:
    copies = [entry for entry in manifest["files"] if entry["copy_of"]]
    assert len(copies) == 12
    assert sorted(entry["copy_of"] for entry in copies) == manifest["quickstart"]
    for entry in copies:
        assert entry["path"] == "quickstart/" + entry["copy_of"].removeprefix("full/")
        copy = (corpus_root / entry["path"]).read_bytes()
        assert copy == (corpus_root / entry["copy_of"]).read_bytes(), entry["path"]


def test_corpus_composition(documents: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    wind = [e for e in documents if e["path"].startswith("full/")]
    assert 36 <= len(wind) <= 40
    formats = Counter(e["format"] for e in wind)
    assert set(formats) == {"pdf", "docx", "xlsx", "csv", "pptx", "eml", "jpg", "png", "vtt",
                            "md", "txt"}
    held_back = [e for e in documents if e["held_back"]]
    assert [e["path"].split("/")[0] for e in held_back] == ["held-back"]
    restricted = [e for e in documents if e["sensitivity"] == "restricted"]
    assert restricted and all(e["path"].startswith("full/restricted/") for e in restricted)
    it_docs = [e for e in documents if e["path"].startswith("it-runbooks/")]
    assert len(it_docs) == 5
    assert {e["sensitivity"] for e in it_docs} == {"internal"}
    assert {e["domain"] for e in it_docs} == {"it-runbooks"}
    scada = next(e for e in documents if e["id"] == "scada-log")
    assert 1_000 < scada["counts"]["rows"] <= 3_001
    langs = Counter(e["lang"] for e in wind)
    assert langs["fr"] >= 2 and langs["de"] >= 1
    assert manifest["totals"]["bytes"] < MAX_TOTAL_BYTES
    assert all(e["bytes"] < MAX_FILE_BYTES for e in manifest["files"])


def test_image_only_scan_has_no_text_layer(documents: list[dict[str, Any]], extracted) -> None:
    scan = next(e for e in documents if e["id"] == "lift-plan-scan")
    pages = extracted(scan["path"]).units
    assert len(pages) == scan["counts"]["pages"] >= 2
    assert all(not text.strip() for _, text in pages)


def test_manifest_counts_and_text_hashes_match_files(manifest: dict[str, Any], extracted) -> None:
    from samples.generators.manifest import text_digest

    for entry in manifest["files"]:
        content = extracted(entry["path"])
        assert content.counts == entry["counts"], entry["path"]
        assert text_digest(content) == entry["text_sha256"], entry["path"]
