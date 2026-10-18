"""Classify stage: domain-pack rules first, fast LLM fallback with pack enums."""

from __future__ import annotations

import pytest
from compile_testkit import (
    LAB,
    block,
    lab_doc,
    make_doc,
    plan_doc,
    sop_a_doc,
    sop_b_doc,
)

from docwiki.domain import DomainPack
from docwiki.llm import FakeLlmClient, LlmInvalidOutput, LlmRequest
from docwiki.stages.classify import classification_output_model, classify_source


async def test_rule_by_file_name_with_doc_number_and_revision(pack: DomainPack) -> None:
    llm = FakeLlmClient()  # no handler: any model call would fail
    result = await classify_source(sop_b_doc(), pack, llm)
    assert (result.method, result.rule_id, result.doc_type, result.category) == (
        "rule",
        "sop#0",
        "sop",
        "procedures",
    )
    assert (result.authority, result.confidence, result.lang) == (7, 1.0, "en")
    assert (result.doc_number, result.revision) == ("SOP-GBX-010", "B")
    assert llm.requests == []
    older = await classify_source(sop_a_doc(), pack, llm)
    assert older.revision == "A"


async def test_rule_by_text_and_by_xlsx_name(pack: DomainPack) -> None:
    bulletin = make_doc(
        "oem/bulletin-oil.pdf",
        [block("b0001", "Litware service bulletin SB-12: gearbox oil grade change.")],
    )
    result = await classify_source(bulletin, pack, FakeLlmClient())
    assert (result.doc_type, result.rule_id, result.authority) == (
        "service-bulletin",
        "service-bulletin#0",
        9,
    )
    plan = await classify_source(plan_doc(), pack, FakeLlmClient())
    assert (plan.doc_type, plan.category, plan.doc_number, plan.revision) == (
        "maintenance-plan",
        "records",
        None,
        None,
    )


async def test_revision_outside_the_pack_order_is_dropped(pack: DomainPack) -> None:
    doc = make_doc("procedures/SOP-GBX-010 rev Z.pdf", [block("b0001", "Gearbox oil change")])
    result = await classify_source(doc, pack, FakeLlmClient())
    assert (result.doc_number, result.revision) == ("SOP-GBX-010", None)


async def test_llm_fallback_uses_pack_enums(pack: DomainPack) -> None:
    def handler(request: LlmRequest) -> dict:
        return {
            "doc_type": "lab-report",
            "category": "records",
            "confidence": 0.82,
            "doc_number": None,
            "revision": None,
            "lang": "en",
        }

    llm = FakeLlmClient({"classify": handler})
    result = await classify_source(lab_doc(), pack, llm)
    assert (result.method, result.rule_id, result.doc_type, result.category) == (
        "llm",
        None,
        "lab-report",
        "records",
    )
    assert (result.authority, result.confidence) == (6, 0.82)
    [request] = llm.requests
    assert request.tier == "fast" and request.schema_name == "classify"
    assert request.prompt_version == "classify-v1"
    assert request.metadata["source_id"] == LAB
    properties = request.json_schema["properties"]
    assert properties["doc_type"]["enum"] == [
        "sop",
        "service-bulletin",
        "maintenance-plan",
        "lab-report",
    ]
    assert properties["category"]["enum"] == ["procedures", "oem-documentation", "records"]
    assert "BEGIN DOCUMENT DATA" in request.text and "Trey Research" in request.text
    assert "- lab-report: Lab report (category records" in request.text


async def test_llm_category_mismatch_and_numbers_are_checked(pack: DomainPack) -> None:
    def handler(request: LlmRequest) -> dict:
        return {
            "doc_type": "sop",
            "category": "records",
            "confidence": 0.9,
            "doc_number": "SOP-ABC-999",
            "revision": "rev c",
            "lang": "fr",
        }

    doc = make_doc(
        "lab/notes.txt",
        [block("b0001", "Procédure de vidange, révision C.")],
        media_type="text/plain",
        lang="und",
    )
    result = await classify_source(doc, pack, FakeLlmClient({"classify": handler}))
    assert (result.doc_type, result.category) == ("sop", "procedures")
    assert result.confidence == 0.5, "a category that contradicts the taxonomy lowers confidence"
    assert result.doc_number is None, "a document number absent from the text is rejected"
    assert result.revision == "C"
    assert result.lang == "fr"


async def test_llm_output_outside_the_enums_is_invalid(pack: DomainPack) -> None:
    llm = FakeLlmClient(
        {
            "classify": {
                "doc_type": "memo",
                "category": "records",
                "confidence": 0.5,
                "doc_number": None,
                "revision": None,
                "lang": "en",
            }
        }
    )
    with pytest.raises(LlmInvalidOutput):
        await classify_source(lab_doc(), pack, llm)


def test_output_model_is_cached_per_enum_set() -> None:
    first = classification_output_model(("a", "b"), ("x",))
    assert classification_output_model(("a", "b"), ("x",)) is first
    with pytest.raises(ValueError):
        classification_output_model((), ("x",))
