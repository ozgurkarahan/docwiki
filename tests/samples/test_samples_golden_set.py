"""The public golden set (evals/golden/dev.jsonl) is well-formed, sealed and corpus-grounded."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from samples.generators.textdump import locator_text, normalise

from docwiki.contracts import parse_locator_key, slugify_ascii
from docwiki.domain.loader import load_pack

FIELDS = ["id", "split", "category", "question", "lang", "expected_answer", "must_include",
          "required_citations", "forbidden", "abstain", "notes"]
CATEGORIES = {"single-hop", "multi-hop", "numeric", "table", "contradiction", "supersession",
              "multilingual", "ocr", "abstain", "injection", "restricted", "skill"}
LOCATOR_KINDS = {
    "pdf": {"pdf-page"},
    "docx": {"docx-paragraph", "docx-table"},
    "xlsx": {"xlsx-rows"},
    "csv": {"csv-rows"},
    "pptx": {"pptx-slide"},
    "eml": {"eml-part"},
    "vtt": {"vtt-cue"},
    "md": {"text-lines"},
    "txt": {"text-lines"},
}
IMAGE_FORMATS = {"jpg", "png"}
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


@pytest.fixture(scope="module")
def golden_dir(repo_root: Path) -> Path:
    return repo_root / "evals" / "golden"


@pytest.fixture(scope="module")
def records(golden_dir: Path) -> list[dict[str, Any]]:
    raw = (golden_dir / "dev.jsonl").read_bytes()
    assert b"\r" not in raw and raw.endswith(b"\n")
    return [json.loads(line) for line in raw.decode("utf-8").splitlines()]


@pytest.fixture(scope="module")
def entries(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["path"]: entry for entry in manifest["files"]}


def test_seal_matches_dev_set_and_corpus(golden_dir: Path, corpus_root: Path) -> None:
    seal = dict(
        line.rsplit("=", 1) for line in (golden_dir / "SEAL").read_text("utf-8").splitlines()
    )
    dev = (golden_dir / "dev.jsonl").read_bytes()
    assert seal["dev.jsonl sha256"] == hashlib.sha256(dev).hexdigest()
    assert int(seal["questions"]) == len(dev.splitlines())
    date.fromisoformat(seal["sealed"])
    manifest = (corpus_root / "MANIFEST.json").read_bytes()
    assert seal["corpus MANIFEST.json sha256"] == hashlib.sha256(manifest).hexdigest()


def test_schema_and_coverage(records: list[dict[str, Any]]) -> None:
    assert 25 <= len(records) <= 40
    for index, record in enumerate(records, start=1):
        assert list(record) == FIELDS
        assert record["id"] == f"q{index:03d}" and record["split"] == "dev"
        assert record["category"] in CATEGORIES and record["lang"] in {"en", "fr"}
        assert record["question"].strip() and record["expected_answer"].strip()
        assert isinstance(record["abstain"], bool) and isinstance(record["notes"], str)
        for key in ("must_include", "forbidden"):
            assert all(isinstance(item, str) and item.strip() for item in record[key])
        for citation in record["required_citations"]:
            assert set(citation) == {"source_path", "locator_key"}
    assert {record["category"] for record in records} == CATEGORIES
    assert any(record["lang"] == "fr" for record in records)


def test_abstain_injection_and_restricted_rules(
    records: list[dict[str, Any]], bible: dict[str, Any], extracted, documents
) -> None:
    canary = bible["injection"]["canary"]
    assert canary in extracted(bible["injection"]["document"]).text()
    public_text = "\n".join(
        extracted(entry["path"]).text()
        for entry in documents
        if entry["sensitivity"] != "restricted"
    )
    for record in records:
        if record["abstain"]:
            assert record["required_citations"] == [] and record["must_include"] == []
        else:
            assert record["required_citations"], record["id"]
            if record["category"] != "injection":
                assert record["must_include"], record["id"]
        if record["category"] == "abstain":
            assert record["abstain"]
        if record["category"] == "injection":
            assert canary in record["forbidden"] and not record["abstain"]
        if record["category"] == "restricted":
            assert record["abstain"] and record["forbidden"]
            assert not any(value in public_text for value in record["forbidden"]), record["id"]
        else:
            assert record["category"] == "injection" or not record["forbidden"], record["id"]


def test_skill_tasks_cover_the_domain_skills(
    records: list[dict[str, Any]], repo_root: Path
) -> None:
    skills = set(load_pack(repo_root / "domains" / "wind-om").skill_templates)
    tasks = [record["notes"] for record in records if record["category"] == "skill"]
    assert sorted(note.removeprefix("skill=") for note in tasks) == sorted(skills)


def _check_bounds(key: str, entry: dict[str, Any]) -> None:
    fmt, counts = entry["format"], entry["counts"]
    parts = parse_locator_key(key)
    assert parts.kind in LOCATOR_KINDS[fmt], f"{key} on {fmt}"
    if parts.kind == "pdf-page":
        assert parts.page <= counts["pages"]
    elif parts.kind == "docx-paragraph":
        assert parts.paragraph <= counts["paragraphs"]
    elif parts.kind == "docx-table":
        assert parts.table <= len(counts["tables"])
        assert parts.row_end <= counts["tables"][parts.table - 1]
    elif parts.kind == "xlsx-rows":
        sheets = {sheet["slug"]: sheet for sheet in counts["sheets"]}
        assert parts.sheet_slug in sheets
        sheet = sheets[parts.sheet_slug]
        assert slugify_ascii(sheet["name"]) == parts.sheet_slug
        assert parts.row_start >= 2 and parts.row_end <= sheet["rows"]
    elif parts.kind == "csv-rows":
        assert parts.row_start >= 2 and parts.row_end <= counts["rows"]
    elif parts.kind == "pptx-slide":
        assert parts.slide <= counts["slides"]
    elif parts.kind == "eml-part":
        assert parts.part in {"headers", "body"}
        if parts.line_end is not None:
            assert parts.part == "body" and parts.line_end <= counts["body_lines"]
    elif parts.kind == "vtt-cue":
        assert parts.cue_start in counts["cue_starts"]
    else:
        assert parts.line_end <= counts["lines"]


def test_citations_resolve_within_bounds(
    records: list[dict[str, Any]], entries: dict[str, dict[str, Any]], extracted
) -> None:
    for record in records:
        texts: list[str] = []
        ocr_only = False
        for citation in record["required_citations"]:
            path, key = citation["source_path"], citation["locator_key"]
            entry = entries.get(path)
            assert entry is not None, f"{record['id']}: {path} not in MANIFEST"
            assert entry["copy_of"] is None and not entry["held_back"], path
            assert entry["sensitivity"] != "restricted" and path.startswith("full/"), path
            if key == "*":
                assert entry["format"] in IMAGE_FORMATS, f"{record['id']}: {path}"
                ocr_only = True
                continue
            _check_bounds(key, entry)
            text = locator_text(extracted(path), key)
            assert text is not None, f"{record['id']}: {key} in {path}"
            if entry["format"] == "pdf" and entry["stamp"] == "image":
                ocr_only = True
                continue
            texts.append(text)
        if ocr_only or record["abstain"]:
            continue
        haystack = normalise("\n".join(texts))
        for item in record["must_include"]:
            numbers = NUMBER.findall(item)
            assert normalise(item) in haystack or (
                numbers and all(number in haystack for number in numbers)
            ), f"{record['id']}: {item!r} not in the cited evidence"
