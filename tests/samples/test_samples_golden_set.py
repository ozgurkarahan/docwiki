"""The public golden set (evals/golden/dev.jsonl) is well-formed, sealed and corpus-grounded."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from datetime import date
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from evals.textnorm import UNITS, contains_item, extract_values, normalize_text
from samples.generators.textdump import locator_text

from docwiki.contracts import parse_locator_key, slugify_ascii
from docwiki.domain.loader import load_pack

FIELDS = ["id", "split", "category", "question", "lang", "expected_answer", "must_include",
          "required_citations", "forbidden", "abstain", "notes"]
CATEGORIES = {"single-hop", "multi-hop", "numeric", "table", "contradiction", "supersession",
              "multilingual", "ocr", "abstain", "injection", "restricted", "skill"}
DEV_SIZE = (12, 20)  # docs/spec/domain-and-corpus.md §5 (v1.2)
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
TABLE_KINDS = {"docx-table", "xlsx-rows", "csv-rows"}
IMAGE_FORMATS = {"jpg", "png"}
NOT_FOUND = "Not found in the wiki."
SKILL_NOTE = re.compile(r"^skill=([a-z0-9-]+)")


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


@pytest.fixture(scope="module")
def author(golden_dir: Path) -> ModuleType:
    """The authoring script, imported as a module (it is not a package)."""
    spec = importlib.util.spec_from_file_location("golden_author", golden_dir / "author.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_seal_matches_dev_set_and_corpus(golden_dir: Path, corpus_root: Path) -> None:
    lines = (golden_dir / "SEAL").read_text("utf-8").splitlines()
    seal = dict(line.rsplit("=", 1) for line in lines)
    assert list(seal) == ["dev.jsonl sha256", "questions", "sealed", "corpus MANIFEST.json sha256"]
    dev = (golden_dir / "dev.jsonl").read_bytes()
    assert seal["dev.jsonl sha256"] == hashlib.sha256(dev).hexdigest()
    assert int(seal["questions"]) == len(dev.splitlines())
    date.fromisoformat(seal["sealed"])
    manifest = (corpus_root / "MANIFEST.json").read_bytes()
    assert seal["corpus MANIFEST.json sha256"] == hashlib.sha256(manifest).hexdigest()


def test_authoring_source_matches_the_sealed_set(author: ModuleType) -> None:
    """author.py --check: every rule holds and dev.jsonl and SEAL are what it writes."""
    assert author.main(["--check"]) == 0


def test_schema_and_coverage(records: list[dict[str, Any]]) -> None:
    assert DEV_SIZE[0] <= len(records) <= DEV_SIZE[1]
    for index, record in enumerate(records, start=1):
        assert list(record) == FIELDS
        assert record["id"] == f"q{index:03d}" and record["split"] == "dev"
        assert record["category"] in CATEGORIES and record["lang"] in {"en", "fr"}
        assert record["question"].strip() and record["expected_answer"].strip()
        assert "\n" not in record["question"], record["id"]
        assert isinstance(record["abstain"], bool) and isinstance(record["notes"], str)
        for key in ("must_include", "forbidden"):
            assert all(isinstance(item, str) and item.strip() for item in record[key])
        for citation in record["required_citations"]:
            assert set(citation) == {"source_path", "locator_key"}
    assert {record["category"] for record in records} == CATEGORIES
    assert any(record["lang"] == "fr" for record in records)


def _bible_names(bible: dict[str, Any]) -> list[str]:
    names: set[str] = set()
    for organisation in bible["organisations"]:
        names.update(filter(None, (organisation["name"], organisation.get("short"))))
    for person in bible["people"]:
        for full in filter(None, (person["name"], person.get("ascii_name"))):
            names.update({full, full.split()[-1]})
    for place in bible["places"]:
        names.update(filter(None, (place["name"], place.get("short"))))
    return sorted({normalize_text(name) for name in names}, key=len, reverse=True)


def _alphabetic_rest(item: str, names: list[str]) -> list[str]:
    """Words of a normalised item that are neither part of a number, date or code, nor a
    unit, nor a bible name."""
    text = f" {normalize_text(item)} "
    for name in names:
        text = re.sub(rf"(?<!\w){re.escape(name)}(?!\w)", " ", text)
    words = [token.strip(".,;:!?()[]{}\"'") for token in text.split()]
    return [
        word
        for word in words
        if not any(char.isdigit() for char in word)
        and any(char.isalpha() for char in word)
        and word not in UNITS | {"x"}
    ]


def test_english_questions_use_language_neutral_items(
    records: list[dict[str, Any]], bible: dict[str, Any]
) -> None:
    """Numbers with units, dates, document numbers, codes and bible names only: a correct
    English answer never needs a French word (spec §5). French words only for lang fr."""
    names = _bible_names(bible)
    for record in records:
        if record["lang"] != "en":
            continue
        for item in record["must_include"]:
            assert not _alphabetic_rest(item, names), (record["id"], item)
    assert _alphabetic_rest("avenant", names) == ["avenant"]
    assert _alphabetic_rest("47271,60 € TTC", names) == ["ttc"]
    assert not _alphabetic_rest("20 avril 2026", names)
    assert not _alphabetic_rest("VanArsdel Menuiseries", names)


def test_abstain_injection_and_restricted_rules(
    records: list[dict[str, Any]], bible: dict[str, Any], extracted, documents
) -> None:
    injection = bible["injection"]
    canary = injection["canary"]
    assert canary in extracted(injection["document"]).text()
    restricted_only = bible["facts"]["etude_de_prix"]["restricted_only_values"]
    public_text = "\n".join(
        extracted(entry["path"]).text()
        for entry in documents
        if entry["sensitivity"] != "restricted"
    )
    public_norm = normalize_text(public_text)
    for record in records:
        answer = normalize_text(record["expected_answer"])
        if record["abstain"]:
            assert record["required_citations"] == [] and record["must_include"] == []
            assert record["expected_answer"] == NOT_FOUND, record["id"]
        else:
            assert record["required_citations"], record["id"]
            assert record["must_include"], record["id"]
        if record["category"] == "abstain":
            assert record["abstain"] and not record["forbidden"]
        if record["category"] == "injection":
            assert not record["abstain"]
            assert set(injection["forbidden_in_outputs"]) <= set(record["forbidden"])
            assert record["required_citations"][0]["source_path"] == injection["document"]
        elif record["category"] == "restricted":
            assert record["abstain"]
            wanted = [*restricted_only["long"], *restricted_only["short"]]
            assert set(wanted) <= set(record["forbidden"])
            for value in record["forbidden"]:
                assert value not in public_text, (record["id"], value)
                assert not contains_item(value, public_norm), (record["id"], value)
        else:
            assert not record["forbidden"], record["id"]
        for value in record["forbidden"]:
            assert not contains_item(value, answer), (record["id"], value)


def test_skill_tasks_cover_the_domain_skills(
    records: list[dict[str, Any]], repo_root: Path
) -> None:
    skills = set(load_pack(repo_root / "domains" / "batiment").skill_templates)
    tasks = []
    for record in records:
        if record["category"] == "skill":
            match = SKILL_NOTE.match(record["notes"])
            assert match, record["id"]
            tasks.append(match.group(1))
    assert sorted(tasks) == sorted(skills)


def test_no_answer_depends_on_a_photo(
    records: list[dict[str, Any]], entries: dict[str, dict[str, Any]]
) -> None:
    photos = {path for path, entry in entries.items() if entry["format"] in IMAGE_FORMATS}
    assert photos
    for record in records:
        for citation in record["required_citations"]:
            assert citation["source_path"] not in photos, record["id"]
            assert citation["locator_key"] != "*", record["id"]


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


def _in_evidence(item: str, texts: list[str], table_texts: list[str]) -> bool:
    """``item`` in the cited text as evals/textnorm.py matches answers, or its numbers as
    bare values of cited table cells (``6867,30 €`` and a cell ``6867.3``)."""
    haystack = normalize_text("\n".join(texts))
    values = extract_values(haystack)
    if contains_item(item, haystack, values):
        return True
    term = normalize_text(item)
    wanted = extract_values(term)
    words = [token for token in term.split() if any(char.isalpha() for char in token)]
    if not wanted.quantities or any(word not in UNITS for word in words):
        return False
    cells = extract_values(normalize_text("\n".join(table_texts)))
    return wanted.dates <= values.dates and all(
        any(found.value == quantity.value for found in cells.quantities)
        for quantity in wanted.quantities
    )


def test_citations_resolve_within_bounds(
    records: list[dict[str, Any]], entries: dict[str, dict[str, Any]], extracted
) -> None:
    ocr_only: list[tuple[str, str]] = []
    for record in records:
        texts: list[str] = []
        table_texts: list[str] = []
        scanned = False
        for citation in record["required_citations"]:
            path, key = citation["source_path"], citation["locator_key"]
            entry = entries.get(path)
            assert entry is not None, f"{record['id']}: {path} not in MANIFEST"
            assert path.startswith("full/") and not entry.get("copy_of"), path
            assert entry["sensitivity"] != "restricted" and not entry["held_back"], path
            _check_bounds(key, entry)
            text = locator_text(extracted(path), key)
            assert text is not None, f"{record['id']}: {key} in {path}"
            if entry["format"] == "pdf" and entry["stamp"] == "image":
                scanned = True  # image-only scan: only OCR reads it, the locator is checked
                continue
            texts.append(text)
            if parse_locator_key(key).kind in TABLE_KINDS:
                table_texts.append(text)
        if record["abstain"]:
            continue
        for item in record["must_include"]:
            if not _in_evidence(item, texts, table_texts):
                assert scanned, f"{record['id']}: {item!r} not in the cited evidence"
                ocr_only.append((record["id"], item))
    # Items that only the handwriting of the scanned delivery note shows are bare counts.
    assert ocr_only and all(re.fullmatch(r"\d+", item) for _, item in ocr_only), ocr_only


def test_file_check_reports_ids_and_error_codes_only(
    author: ModuleType, records: list[dict[str, Any]]
) -> None:
    """--check --file verifies a private set and never prints its content."""
    base = next(record for record in records if record["category"] == "table")
    secrets = ["secret wording of the question", "secret wording of the answer", "facture"]

    def variant(qid: str, **changes: Any) -> dict[str, Any]:
        return {**base, "id": qid, "split": "holdout", **changes}

    restricted = "full/restricted/2026-02-02_etude-de-prix-interne.xlsx"
    private = [
        variant("h001"),
        variant("h002", question=secrets[0], expected_answer=secrets[1], must_include=["facture"]),
        variant("h003", required_citations=[
            {"source_path": restricted, "locator_key": "sheet-etude-de-prix-r0010-r0010"}]),
        variant("h004", category="injection", forbidden=["no canary"]),
        {"id": "h005", "question": secrets[0]},
    ]
    raw = "\n".join(json.dumps(record, ensure_ascii=False) for record in private) + "\n"
    code, report = author.check_file(raw.encode("utf-8"))
    output = "\n".join(report)
    assert code == 1
    assert report[0] == "5 questions checked: 1 passed, 4 failed"
    assert "h001:" not in output
    assert "h002: item-not-neutral" in output
    assert "h003: source-restricted" in output
    assert "h004: injection-rules" in output
    assert "h005: schema" in output
    for text in [*secrets, restricted, base["question"], base["expected_answer"]]:
        assert text not in output
    assert all(item not in output for item in base["must_include"])
    assert author.check_file(raw.splitlines(keepends=True)[0].encode("utf-8"))[0] == 0
