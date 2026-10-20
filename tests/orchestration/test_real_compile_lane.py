"""Integration with the real lanes behind the engine registry.

``classify_source``, ``compile_source``, ``render_source_page``, ``build_entity_pages`` and
``build_topic_pages`` are the compile lane's modules; ``extract_source`` and ``build_evidence``
are either the stubs or the extract lane's modules (full real engine). The fake LLM answers the
real prompts from the delimited document data they carry, so every citation is checked by the
real verifier.
"""

from __future__ import annotations

import re
from typing import Any

import pytest
from engine_stubs import CANARY, build_evidence, extract_source

from docwiki.contracts.ids import source_id_for
from docwiki.contracts.safety import detect_injection
from docwiki.llm import FakeLlmClient, LlmRequest
from docwiki.orchestration.registry import load_engine, missing_engine_functions
from docwiki.release.reader import ReleaseReader
from docwiki.release.validate import validate_release

pytest.importorskip("docwiki.stages.compile")

_DATA_RE = re.compile(r"BEGIN DOCUMENT DATA ([0-9a-f]{12})\n(.*)\nEND DOCUMENT DATA \1", re.DOTALL)
_UNIT_RE = re.compile(r"^\[([a-z]\d+)\] (\S+)")
_ROW_RE = re.compile(r"^(t\d+:r\d+): (.*)$")
_FACT_RE = re.compile(r"^\[(F\d+)\] (?:S\d+|\([^)]*\)): (.*)$", re.MULTILINE)


def _units(text: str) -> list[dict[str, Any]]:
    match = _DATA_RE.search(text)
    assert match, "the compile prompt carries delimited document data"
    units: list[dict[str, Any]] = []
    for line in match.group(2).split("\n")[1:]:
        head = _UNIT_RE.match(line)
        if head:
            units.append({"id": head.group(1), "kind": head.group(2), "lines": []})
        elif units and line.startswith("  "):
            units[-1]["lines"].append(line[2:])
    return units


def compile_answer(request: LlmRequest) -> dict[str, Any]:
    facts: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []
    for unit in _units(request.text):
        if unit["kind"] == "table":
            for line in unit["lines"]:
                row = _ROW_RE.match(line)
                cells = [c.strip() for c in row.group(2).split(" | ")] if row else []
                cells = [cell for cell in cells if cell]
                if row and len(cells) >= 2:
                    facts.append(
                        {
                            "text": " ".join(cells) + ".",
                            "citations": [{"block_id": row.group(1), "quote": " | ".join(cells)}],
                            "numbers": [],
                        }
                    )
            sections.append(
                {
                    "heading": "Table",
                    "body": f"The table lists the rows of the file.[[cite:{unit['id']}]]",
                    "table_refs": [unit["id"]],
                }
            )
            continue
        body = " ".join(unit["lines"]).strip()
        if not body or body.startswith("FICTIONAL") or detect_injection(body):
            continue
        facts.append(
            {"text": body, "citations": [{"block_id": unit["id"], "quote": body}], "numbers": []}
        )
    if not sections and facts:
        first = facts[0]
        ref = first["citations"][0]["block_id"]
        sections.append(
            {"heading": "Content", "body": f"{first['text']}[[cite:{ref}]]", "table_refs": []}
        )
    return {
        "title": "",
        "summary": "A short fictional document of the engine test corpus.",
        "key_facts": facts,
        "sections": sections,
        "entity_mentions": [],
        "unknown_entities": [],
        "glossary_candidates": [],
        "injection_flags": [],
    }


def _first_fact(request: LlmRequest) -> tuple[str, str] | None:
    match = _FACT_RE.search(request.text)
    return (match.group(1), match.group(2).strip()) if match else None


def entity_answer(request: LlmRequest) -> dict[str, Any]:
    fact = _first_fact(request)
    return {"sentences": [{"text": fact[1], "fact_ids": [fact[0]]}] if fact else []}


def topic_answer(request: LlmRequest) -> dict[str, Any]:
    fact = _first_fact(request)
    return {
        "summary": "Window delivery in the fictional engine test corpus.",
        "overview": [{"text": fact[1], "fact_ids": [fact[0]]}] if fact else [],
        "sections": [],
        "contradictions": [],
        "superseded": [],
    }


def real_lane_llm() -> FakeLlmClient:
    return FakeLlmClient(
        {
            "classify": {
                "doc_type": "note",
                "category": "correspondence",
                "confidence": 0.7,
                "doc_number": None,
                "revision": None,
                "lang": "en",
            },
            "compile": compile_answer,
            "compile_repair": {"facts": []},
            "entity_summary": entity_answer,
            "topic_synthesis": topic_answer,
        }
    )


async def test_real_compile_lane_builds_a_valid_release(make_harness):
    engine = load_engine({"extract_source": extract_source, "build_evidence": build_evidence})
    assert engine.origins["compile_source"] == "docwiki.stages.compile:compile_source"
    assert engine.origins["build_topic_pages"] == "docwiki.stages.topics:build_topic_pages"
    harness = make_harness(engine=engine, llm=real_lane_llm())
    outcome = await harness.run()
    assert outcome.status == "succeeded", outcome.errors
    root = harness.current_release()
    problems = [
        f"{v.gate} {v.severity} {v.code} {v.path}:{v.line} {v.message}"
        for v in validate_release(root, canaries=[CANARY], glossary_seeded=True)
    ]
    assert problems == []

    reader = ReleaseReader.open(harness.settings.work_dir)
    pages = {page.id: page for page in reader.list_pages("source")}
    rev_a = source_id_for("devis/DEV-2026-014 indice A.txt")
    rev_b = source_id_for("devis/DEV-2026-014 indice B.docx")
    old = reader.read_page(rev_a)
    assert old.frontmatter.status == "superseded"
    intro = old.body.split("\n## ", 1)[0]
    newer = pages[rev_b].path.rsplit("/", 1)[-1]
    assert f"]({newer})" in intro and f"`{rev_b}`" not in old.body
    assert {page.id for page in reader.list_pages("entity")} >= {"building-element:baie-f1"}
    topics = reader.list_pages("topic")
    assert [topic.id for topic in topics] == ["topic:schedule-and-window-delivery"]
    for topic in topics:
        for source_id in reader.read_page(topic.id).frontmatter.sources:
            assert topic.id in reader.read_page(source_id).frontmatter.topics
    quality = (root / "wiki" / "_meta" / "quality.md").read_text(encoding="utf-8")
    assert "| G04 | quote-verification | yes | pass |" in quality
    assert CANARY not in quality

    second = await harness.run()
    assert second.status == "no-op"
    calls = len(harness.llm.requests)
    rebuild = await harness.run(kind="rebuild", force=True)
    assert rebuild.status == "succeeded" and rebuild.published, rebuild.errors
    assert len(harness.llm.requests) == calls, "a rebuild reuses every LLM artifact"
    assert validate_release(harness.current_release(), canaries=[CANARY]) == []


@pytest.mark.skipif(bool(missing_engine_functions()), reason="a lane is not merged yet")
async def test_full_real_engine_builds_a_contained_public_release(make_harness):
    engine = load_engine()
    assert engine.origins["extract_source"].startswith("docwiki.extract.")
    assert engine.origins["build_evidence"].startswith("docwiki.evidence.")
    harness = make_harness(engine=engine, llm=real_lane_llm(), audience="public")
    outcome = await harness.run()
    assert outcome.status == "succeeded", outcome.errors
    root = harness.current_release()
    problems = [
        f"{v.gate} {v.severity} {v.code} {v.path}:{v.line} {v.message}"
        for v in validate_release(root, audience="public", canaries=[CANARY], glossary_seeded=True)
    ]
    assert problems == []
    reader = ReleaseReader.open(harness.settings.work_dir)
    titles = {page.id: page.title for page in reader.list_pages("source")}
    note = source_id_for("notes/supplier-note.txt")
    rev_b = source_id_for("devis/DEV-2026-014 indice B.docx")
    assert {note, rev_b} <= set(titles)
    # the fictional public sample publishes originals, except for the flagged note
    assert list((root / "evidence" / rev_b).glob("original.*"))
    assert not list((root / "evidence" / note).glob("original.*"))
    needle = CANARY.encode("utf-8")
    leaks = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and needle in path.read_bytes()
    ]
    assert leaks == []
    assert outcome.report.versions.extractors["extract.adapter_version"]
