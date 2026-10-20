"""The committed corpus matches MANIFEST.json, the bible catalog and the spec composition."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from pathlib import Path
from typing import Any

MAX_TOTAL_BYTES = 5_000_000
MAX_FILE_BYTES = 1_000_000
# Spec domain-and-corpus.md section 3.1: 12 public documents, 1 restricted, 1 held back.
PUBLIC_FORMATS = {"pdf": 4, "docx": 3, "xlsx": 1, "eml": 2, "jpg": 2}


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
    documents: list[dict[str, Any]], bible: dict[str, Any], repo_root: Path,
    manifest: dict[str, Any],
) -> None:
    catalog = {doc["path"]: doc for doc in bible["documents"]}
    assert [entry["path"] for entry in documents] == sorted(catalog)
    for entry in documents:
        doc = catalog[entry["path"]]
        for key in ("id", "kind", "title", "lang", "date", "format", "sensitivity", "stamp"):
            assert entry[key] == doc[key], (entry["path"], key)
        assert entry["doc_number"] == doc.get("doc_number")
        assert entry["revision"] == doc.get("revision")
        assert entry["held_back"] == bool(doc.get("held_back"))
        assert entry["procedure_like"] == bool(doc["procedure_like"])
        assert {"copy_of", "quickstart", "domain"}.isdisjoint(entry)
    bible_bytes = (repo_root / "samples/fiction/bible.yaml").read_bytes()
    assert manifest["bible_sha256"] == hashlib.sha256(bible_bytes).hexdigest()
    assert "quickstart" not in manifest


def test_corpus_composition(
    documents: list[dict[str, Any]], manifest: dict[str, Any], corpus_root: Path
) -> None:
    assert sorted(p.name for p in corpus_root.iterdir() if p.is_dir()) == ["full", "held-back"]
    full = [e for e in documents if e["path"].startswith("full/")]
    public = [e for e in full if e["sensitivity"] == "public"]
    restricted = [e for e in documents if e["sensitivity"] == "restricted"]
    held_back = [e for e in documents if e["held_back"]]
    assert len(public) == 12 and len(full) == 13 and len(documents) == 14
    assert Counter(e["format"] for e in public) == PUBLIC_FORMATS
    assert [e["path"].split("/")[:2] for e in restricted] == [["full", "restricted"]]
    assert [e["format"] for e in restricted] == ["xlsx"]
    assert [e["path"].split("/")[0] for e in held_back] == ["held-back"]
    assert [e["format"] for e in held_back] == ["xlsx"]
    assert not any(e["path"].startswith("full/restricted/") for e in public)
    assert {e["lang"] for e in documents} == {"fr"}
    assert manifest["totals"] == {
        "files": 14,
        "documents": 13,
        "held_back": 1,
        "bytes": sum(e["bytes"] for e in documents),
        "by_format": dict(sorted(Counter(e["format"] for e in documents).items())),
    }
    assert manifest["totals"]["bytes"] < MAX_TOTAL_BYTES
    assert all(e["bytes"] < MAX_FILE_BYTES for e in documents)


def test_planning_workbooks_have_the_two_sheets(
    documents: list[dict[str, Any]], bible: dict[str, Any]
) -> None:
    names = list(bible["facts"]["planning"]["sheets"])
    plannings = [e for e in documents if e["kind"] == "planning"]
    assert len(plannings) == 2
    for entry in plannings:
        assert [sheet["name"] for sheet in entry["counts"]["sheets"]] == names


def test_photo_assets_match_their_provenance_record(
    repo_root: Path, bible: dict[str, Any], documents: list[dict[str, Any]]
) -> None:
    folder = repo_root / "samples" / "generators" / "assets" / "photos"
    record = (folder / "PROVENANCE.md").read_text(encoding="utf-8")
    hashes = dict(re.findall(r"^\| `([^`]+\.jpg)` \|.*\| `([0-9a-f]{64})` \|$", record,
                             flags=re.MULTILINE))
    entries = {key: value for key, value in bible["facts"]["photos"].items()
               if isinstance(value, dict) and "asset" in value}
    assert set(hashes) == {Path(e["asset"]).name for e in entries.values()}
    assert set(hashes) == {file.name for file in folder.glob("*.jpg")}
    for name, digest in hashes.items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest, name
    photos = [entry for entry in documents if entry["format"] == "jpg"]
    assert sorted(entry["id"] for entry in photos) == sorted(f"photo-{key}" for key in entries)


def test_image_only_scan_has_no_text_layer(
    documents: list[dict[str, Any]], extracted, bible: dict[str, Any]
) -> None:
    scans = [e for e in documents if e["format"] == "pdf" and e["stamp"] == "image"]
    assert [e["id"] for e in scans] == ["bl-scan"]
    scan = scans[0]
    pages = extracted(scan["path"]).units
    assert len(pages) == scan["counts"]["pages"] == bible["facts"]["zava_delivery"]["pages"] == 1
    assert all(not text.strip() for _, text in pages)


def test_text_pdfs_have_a_text_layer(documents: list[dict[str, Any]], extracted) -> None:
    pdfs = [e for e in documents if e["format"] == "pdf" and e["stamp"] != "image"]
    assert len(pdfs) == 3
    for entry in pdfs:
        assert all(text.strip() for _, text in extracted(entry["path"]).units), entry["path"]


def test_manifest_counts_and_text_hashes_match_files(manifest: dict[str, Any], extracted) -> None:
    from samples.generators.manifest import text_digest

    for entry in manifest["files"]:
        content = extracted(entry["path"])
        assert content.counts == entry["counts"], entry["path"]
        assert text_digest(content) == entry["text_sha256"], entry["path"]
