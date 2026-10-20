"""Figure descriptions: fast tier, image part, model-description provenance, failures."""

from __future__ import annotations

from extract_fixtures import Corpus

from docwiki.engine_types import ExtractSettings
from docwiki.extract import FIGURE_PROMPT_VERSION, FIGURE_SCHEMA_NAME
from docwiki.extract.figures import FIGURE_SYSTEM_PROMPT
from docwiki.llm import FakeLlmClient, LlmRequest, LlmServiceError

DESCRIPTION = "Blue rectangle crossed by a white diagonal line; no labels or values are visible."


def describer() -> FakeLlmClient:
    return FakeLlmClient({FIGURE_SCHEMA_NAME: {"description": f"  {DESCRIPTION}\n"}})


async def test_pdf_figure_description(corpus: Corpus) -> None:
    llm = describer()
    result = await corpus.extract("docs/devis-indice-a.pdf", llm=llm)
    doc = result.doc
    (figure,) = doc.figures
    assert figure.description == DESCRIPTION
    assert figure.description_provenance == "model-description"
    ref = next(block for block in doc.blocks if block.kind == "figure-ref")
    assert (ref.text, ref.provenance, ref.locator) == (
        DESCRIPTION,
        "model-description",
        figure.locator,
    )
    # reading order: after the list items above the figure, ids stay sequential
    assert [b.kind for b in doc.blocks[-3:]] == ["figure-ref", "heading", "paragraph"]
    assert [b.id for b in doc.blocks] == [f"b{i:04d}" for i in range(1, len(doc.blocks) + 1)]
    assert doc.extraction.model == "fake-model"

    (request,) = llm.requests
    assert isinstance(request, LlmRequest)
    assert request.tier == "fast"
    assert request.prompt_version == FIGURE_PROMPT_VERSION
    assert len(request.images) == 1 and request.images[0].media_type == "image/png"
    assert "untrusted" in request.system and request.system == FIGURE_SYSTEM_PROMPT
    assert request.metadata["source_id"] == doc.source_id
    assert request.text == "Describe this figure."  # no document text in the prompt


async def test_image_and_office_figures_are_described(corpus: Corpus) -> None:
    for rel in (
        "photos/photo-palettes.png",
        "docs/avenant-n1.docx",
        "slides/support-reunion-chantier.pptx",
    ):
        doc = (await corpus.extract(rel, llm=describer())).doc
        assert [figure.description for figure in doc.figures] == [DESCRIPTION]
        assert sum(block.kind == "figure-ref" for block in doc.blocks) == 1


async def test_no_description_without_llm_or_when_disabled(corpus: Corpus) -> None:
    llm = describer()
    disabled = await corpus.extract(
        "docs/devis-indice-a.pdf", ExtractSettings(describe_figures=False), llm=llm
    )
    assert llm.requests == []
    assert disabled.doc.figures[0].description is None
    assert all(block.kind != "figure-ref" for block in disabled.doc.blocks)
    without = await corpus.extract("docs/devis-indice-a.pdf")
    assert without.doc.to_json() == disabled.doc.to_json()


async def test_failures_and_empty_answers_become_warnings(corpus: Corpus) -> None:
    def fail(request: LlmRequest) -> dict[str, str]:
        raise LlmServiceError("service unavailable")

    failing = FakeLlmClient({FIGURE_SCHEMA_NAME: fail})
    result = await corpus.extract("docs/devis-indice-a.pdf", llm=failing)
    assert result.doc.figures[0].description is None
    assert "figure-description-failed: f01: LlmServiceError" in result.warnings

    empty = FakeLlmClient({FIGURE_SCHEMA_NAME: {"description": "N/A"}})
    result = await corpus.extract("docs/devis-indice-a.pdf", llm=empty)
    assert result.doc.figures[0].description is None
    assert result.doc.extraction.model is None
