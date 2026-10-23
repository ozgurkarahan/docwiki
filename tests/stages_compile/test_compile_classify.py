"""Classify stage: domain-pack rules first, fast LLM fallback with pack enums."""

from __future__ import annotations

import pytest
from compile_testkit import (
    INVOICE,
    block,
    invoice_doc,
    make_doc,
    plan_doc,
    quote_a_doc,
    quote_b_doc,
)

from docwiki.domain import DomainPack
from docwiki.llm import FakeLlmClient, LlmInvalidOutput, LlmRequest
from docwiki.stages.classify import classification_output_model, classify_source


async def test_rule_by_file_name_with_doc_number_and_revision(pack: DomainPack) -> None:
    llm = FakeLlmClient()  # no handler: any model call would fail
    result = await classify_source(quote_b_doc(), pack, llm)
    assert (result.method, result.rule_id, result.doc_type, result.category) == (
        "rule",
        "quote#0",
        "quote",
        "contract-documents",
    )
    assert (result.authority, result.confidence, result.lang) == (8, 1.0, "fr")
    assert (result.doc_number, result.revision) == ("DEV-2026-014", "B")
    assert llm.requests == []
    older = await classify_source(quote_a_doc(), pack, llm)
    assert older.revision == "A"


async def test_rule_by_text_and_by_xlsx_name(pack: DomainPack) -> None:
    amendment = make_doc(
        "contrat/modification-fenetre-de-toit.pdf",
        [block("b0001", "Avenant n°1 au contrat de travaux : fenêtre de toit FT1.")],
    )
    result = await classify_source(amendment, pack, FakeLlmClient())
    assert (result.doc_type, result.rule_id, result.authority) == (
        "contract-amendment",
        "contract-amendment#0",
        10,
    )
    plan = await classify_source(plan_doc(), pack, FakeLlmClient())
    assert (plan.doc_type, plan.category, plan.doc_number, plan.revision) == (
        "schedule",
        "schedule-and-purchases",
        None,
        None,
    )


async def test_revision_outside_the_pack_order_is_dropped(pack: DomainPack) -> None:
    doc = make_doc("devis/DEV-2026-014 indice Z.pdf", [block("b0001", "Devis de l'extension")])
    result = await classify_source(doc, pack, FakeLlmClient())
    assert (result.doc_number, result.revision) == ("DEV-2026-014", None)


async def test_llm_fallback_uses_pack_enums(pack: DomainPack) -> None:
    def handler(request: LlmRequest) -> dict:
        return {
            "doc_type": "supplier-invoice",
            "category": "purchasing",
            "confidence": 0.82,
            "doc_number": None,
            "revision": None,
            "lang": "fr",
        }

    llm = FakeLlmClient({"classify": handler})
    result = await classify_source(invoice_doc(), pack, llm)
    assert (result.method, result.rule_id, result.doc_type, result.category) == (
        "llm",
        None,
        "supplier-invoice",
        "purchasing",
    )
    assert (result.authority, result.confidence) == (5, 0.82)
    [request] = llm.requests
    assert request.tier == "fast" and request.schema_name == "classify"
    assert request.prompt_version == "classify-v1"
    assert request.metadata["source_id"] == INVOICE
    properties = request.json_schema["properties"]
    assert properties["doc_type"]["enum"] == [
        "quote",
        "contract-amendment",
        "schedule",
        "supplier-invoice",
        "price-study",
    ]
    assert properties["category"]["enum"] == [
        "contract-documents",
        "schedule-and-purchases",
        "purchasing",
        "internal-costing",
    ]
    assert "BEGIN DOCUMENT DATA" in request.text and "Zava Matériaux" in request.text
    assert "- supplier-invoice: Supplier invoice (facture) (category purchasing" in request.text


async def test_llm_category_mismatch_and_numbers_are_checked(pack: DomainPack) -> None:
    def handler(request: LlmRequest) -> dict:
        return {
            "doc_type": "quote",
            "category": "purchasing",
            "confidence": 0.9,
            "doc_number": "DEV-2099-999",
            "revision": "indice c",
            "lang": "fr",
        }

    doc = make_doc(
        "devis/notes.txt",
        [block("b0001", "Devis de l'extension, révision C.")],
        media_type="text/plain",
        lang="und",
    )
    result = await classify_source(doc, pack, FakeLlmClient({"classify": handler}))
    assert (result.doc_type, result.category) == ("quote", "contract-documents")
    assert result.confidence == 0.5, "a category that contradicts the taxonomy lowers confidence"
    assert result.doc_number is None, "a document number absent from the text is rejected"
    assert result.revision == "C"
    assert result.lang == "fr"


async def test_llm_output_outside_the_enums_is_invalid(pack: DomainPack) -> None:
    llm = FakeLlmClient(
        {
            "classify": {
                "doc_type": "memo",
                "category": "purchasing",
                "confidence": 0.5,
                "doc_number": None,
                "revision": None,
                "lang": "fr",
            }
        }
    )
    with pytest.raises(LlmInvalidOutput):
        await classify_source(invoice_doc(), pack, llm)


def test_output_model_is_cached_per_enum_set() -> None:
    first = classification_output_model(("a", "b"), ("x",))
    assert classification_output_model(("a", "b"), ("x",)) is first
    with pytest.raises(ValueError):
        classification_output_model((), ("x",))


async def test_the_path_gives_the_scope_the_axes_and_a_named_type(pack: DomainPack) -> None:
    """v1.7, ADR 0011: with scopes, the raw path decides scope, phase, lot and, when a segment
    names a type of the pack, the type itself (before the rules and the model)."""
    from docwiki.domain.models import ScopesFile

    scoped = pack.model_copy(
        update={
            "scopes": ScopesFile.model_validate(
                {
                    "name": "chantier",
                    "title": "Chantier",
                    "plural": "chantiers",
                    "default": {"key": "entreprise", "title": "Entreprise"},
                    "paths": [
                        {
                            "regex": r"^chantiers/(?P<scope>[a-z0-9-]+)/(?P<phase>[0-5])[^/]*/"
                            r"(?P<type>[a-z0-9-]+)/"
                        }
                    ],
                    "lot_regex": r"(?i)lot[-_ ]?(?P<lot>\d{1,2})",
                }
            )
        }
    )
    llm = FakeLlmClient()  # no handler: any model call would fail
    doc = make_doc(
        "chantiers/ecole/1-marche/schedule/planning lot 2.pdf",
        [block("b0001", "Avenant n°1 au contrat de travaux : fenêtre de toit FT1.")],
    )
    result = await classify_source(doc, scoped, llm)
    assert (result.method, result.doc_type, result.category) == (
        "path",
        "schedule",
        "schedule-and-purchases",
    )
    assert (result.scope, result.phase, result.lot) == ("ecole", "1", "2")
    outside = await classify_source(quote_b_doc(), scoped, llm)
    assert (outside.method, outside.scope, outside.phase) == ("rule", "entreprise", None)
    assert (await classify_source(quote_b_doc(), pack, llm)).scope is None
    assert llm.requests == []
