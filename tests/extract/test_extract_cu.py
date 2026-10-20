"""Content Understanding adapter: REST flow, record/replay, mapping and parity with local."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import httpx
import pytest
from extract_fixtures import Corpus, fake_cu_response, source

from docwiki.contracts.locators import ImageRegionLocator
from docwiki.engine_types import ExtractSettings
from docwiki.extract import ContentUnderstandingError, cu
from docwiki.extract.cu import (
    ContentUnderstandingClient,
    cu_request,
    parse_source,
    recording_path,
    save_recording,
)

ENDPOINT = "https://docwiki-cu.example"
PDF = "docs/devis-indice-a.pdf"


class FakeTokens:
    def __init__(self) -> None:
        self.calls = 0

    async def get_token(self) -> str:
        self.calls += 1
        return "unit-test-bearer"


class FakeService:
    """In-memory Content Understanding: analyzeBinary → 202, then Running → Succeeded."""

    def __init__(self, response: dict[str, Any], *, running_polls: int = 1) -> None:
        self.response = response
        self.running_polls = running_polls
        self.requests: list[httpx.Request] = []
        self.post_status = 202
        self.post_failures: list[int] = []
        self.location = (
            f"{ENDPOINT}/contentunderstanding/analyzerResults/op-0001?api-version=2025-11-01"
        )

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.method == "POST":
            if self.post_failures:
                return httpx.Response(
                    self.post_failures.pop(0),
                    headers={"retry-after": "0"},
                    json={"error": {"code": "TooManyRequests", "message": "slow down"}},
                )
            if self.post_status != 202:
                return httpx.Response(
                    self.post_status,
                    json={"error": {"code": "PermissionDenied", "message": "no role"}},
                )
            return httpx.Response(
                202,
                headers={"Operation-Location": self.location},
                json={"id": "op-0001", "status": "NotStarted"},
            )
        if self.running_polls > 0:
            self.running_polls -= 1
            return httpx.Response(
                200, headers={"retry-after": "0"}, json={"id": "op-0001", "status": "Running"}
            )
        return httpx.Response(200, json={"id": "op-0001", **self.response})


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch, corpus: Corpus) -> FakeService:
    fake = FakeService(fake_cu_response(corpus.pdf_layout))
    sleeps: list[float] = []

    async def no_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    def factory(settings: ExtractSettings) -> ContentUnderstandingClient:
        return ContentUnderstandingClient(
            settings.cu_endpoint or "",
            tokens=FakeTokens(),
            transport=httpx.MockTransport(fake.handler),
            sleep=no_sleep,
        )

    monkeypatch.setattr(cu, "client_factory", factory)
    fake.sleeps = sleeps  # type: ignore[attr-defined]
    return fake


def azure(mode: str, recordings: Path | None, **kwargs: Any) -> ExtractSettings:
    return ExtractSettings(
        mode="azure",
        cu_endpoint=ENDPOINT,
        cu_mode=mode,
        recordings_dir=recordings,
        **kwargs,  # type: ignore[arg-type]
    )


def test_parse_source_formats() -> None:
    assert parse_source("D(2,1,2,5,2,5,4,1,4)") == [(2, (1.0, 2.0, 5.0, 4.0))]
    assert parse_source("D(1,0.5,1,2,3)") == [(1, (0.5, 1.0, 2.5, 4.0))]
    assert parse_source("D(1,1,1,2,1,2,2,1,2);D(2,0,0,1,0,1,1,0,1)")[1][0] == 2
    assert parse_source(None) == []


async def test_record_then_replay(corpus: Corpus, service: FakeService, tmp_path: Path) -> None:
    recorded = await corpus.extract(PDF, azure("record", tmp_path))
    post, *polls = service.requests
    assert post.method == "POST"
    assert post.url.path == "/contentunderstanding/analyzers/prebuilt-layout:analyzeBinary"
    assert post.url.params["api-version"] == "2025-11-01"
    assert post.url.params["stringEncoding"] == "codePoint"
    assert "range" not in post.url.params
    assert post.headers["Authorization"] == "Bearer unit-test-bearer"
    assert post.headers["Content-Type"] == "application/octet-stream"
    assert post.content == corpus.path(PDF).read_bytes()
    assert [p.url.path for p in polls] == ["/contentunderstanding/analyzerResults/op-0001"] * 2
    assert all(p.headers["Authorization"] == "Bearer unit-test-bearer" for p in polls)

    (recording,) = tmp_path.glob("*.json")
    request = cu_request(
        analyzer="prebuilt-layout", data=corpus.path(PDF).read_bytes(), content_range=None
    )
    assert recording == recording_path(tmp_path, request)
    text = recording.read_text(encoding="utf-8")
    assert "docwiki-cu.example" not in text and "op-0001" not in text
    assert json.loads(text)["request"] == request

    service.requests.clear()
    replayed = await corpus.extract(PDF, azure("replay", tmp_path))
    assert service.requests == []
    assert replayed.doc.to_json() == recorded.doc.to_json()
    doc = replayed.doc
    assert doc.extraction.adapter == "content-understanding"
    assert doc.extraction.analyzer == "prebuilt-layout"
    assert doc.extraction.adapter_version.endswith("+cu.2025-11-01")
    assert doc.blocks[0].kind == "heading" and doc.blocks[0].level == 1
    assert {block.provenance for block in doc.blocks} == {"native-text"}
    assert sorted(replayed.page_images) == [1, 2]


async def test_replay_without_recording_fails_offline(corpus: Corpus, tmp_path: Path) -> None:
    with pytest.raises(ContentUnderstandingError, match="cu_mode=record") as error:
        await corpus.extract(PDF, azure("replay", tmp_path))
    assert error.value.retryable is False


async def test_replay_rejects_tampered_request(corpus: Corpus, tmp_path: Path) -> None:
    data = corpus.path(PDF).read_bytes()
    request = cu_request(analyzer="prebuilt-layout", data=data, content_range=None)
    path = recording_path(tmp_path, request)
    save_recording(path, {**request, "analyzer": "other"}, fake_cu_response(corpus.pdf_layout))
    with pytest.raises(ContentUnderstandingError, match="does not match"):
        await corpus.extract(PDF, azure("replay", tmp_path))


async def test_parity_with_local_adapter(corpus: Corpus, tmp_path: Path) -> None:
    data = corpus.path(PDF).read_bytes()
    request = cu_request(analyzer="prebuilt-layout", data=data, content_range=None)
    save_recording(recording_path(tmp_path, request), request, fake_cu_response(corpus.pdf_layout))
    local = (await corpus.extract(PDF)).doc
    cloud = (await corpus.extract(PDF, azure("replay", tmp_path))).doc

    assert cloud.metadata.page_count == local.metadata.page_count == 2

    def per_page(doc: Any) -> dict[int, str]:
        pages: dict[int, str] = {}
        for block in doc.blocks:
            if block.kind != "figure-ref":
                pages[block.locator.page] = pages.get(block.locator.page, "") + block.text
        return {page: re.sub(r"\s+", "", text) for page, text in pages.items()}

    assert per_page(cloud) == per_page(local)
    assert [len([b for b in d.blocks if b.locator.page == 1]) for d in (local, cloud)] == [6, 6]
    for local_block, cloud_block in zip(local.blocks, cloud.blocks, strict=True):
        assert local_block.locator_key == cloud_block.locator_key
        assert local_block.kind == cloud_block.kind
        assert cloud_block.locator.bbox[1] == pytest.approx(local_block.locator.bbox[1], abs=0.03)
        assert cloud_block.locator.bbox[0] == pytest.approx(local_block.locator.bbox[0], abs=0.03)


async def test_tables_figures_and_reading_order(corpus: Corpus, tmp_path: Path) -> None:
    layout = corpus.pdf_layout
    response = fake_cu_response(layout)
    content = response["result"]["contents"][0]
    paragraphs = content["paragraphs"]
    markdown_end = len(content["markdown"])
    cell_paragraphs = [
        {
            "content": text,
            "source": source(2, [x, 3, x + 1, 3, x + 1, 3.2, x, 3.2]),
            "span": {"offset": markdown_end + i * 10, "length": len(text)},
        }
        for i, (text, x) in enumerate(
            (("Tâche", 1.0), ("Date", 3.0), ("T07", 1.0), ("2026-03-30", 3.0))
        )
    ]
    first_cell = len(paragraphs)
    paragraphs += cell_paragraphs
    cells = []
    for i, (row, column) in enumerate(((0, 0), (0, 1), (1, 0), (1, 1))):
        y = 3.0 + row * 0.3
        cells.append(
            {
                "kind": "columnHeader" if row == 0 else "content",
                "rowIndex": row,
                "columnIndex": column,
                "content": cell_paragraphs[i]["content"],
                "source": source(
                    2,
                    [
                        1.0 + 2 * column,
                        y,
                        2.5 + 2 * column,
                        y,
                        2.5 + 2 * column,
                        y + 0.2,
                        1.0 + 2 * column,
                        y + 0.2,
                    ],
                ),
                "elements": [f"/paragraphs/{first_cell + i}"],
            }
        )
    content["tables"] = [
        {
            "rowCount": 2,
            "columnCount": 2,
            "cells": cells,
            "source": source(2, [1, 3, 5, 3, 5, 3.5, 1, 3.5]),
            "span": {"offset": markdown_end, "length": 40},
        }
    ]
    content["figures"] = [
        {
            "id": "1.1",
            "source": source(1, [0.7874, 5.9055, 3.5433, 5.9055, 3.5433, 7.6280, 0.7874, 7.6280]),
            "span": {"offset": paragraphs[5]["span"]["offset"] + 5, "length": 3},
            "caption": {"content": "Figure 1: plan de la baie F1"},
        }
    ]
    data = corpus.path(PDF).read_bytes()
    request = cu_request(analyzer="prebuilt-layout", data=data, content_range=None)
    save_recording(recording_path(tmp_path, request), request, response)
    result = await corpus.extract(PDF, azure("replay", tmp_path))
    doc = result.doc

    (table,) = doc.tables
    assert table.columns == ["Tâche", "Date"]
    assert [(row.row_id, row.cells) for row in table.rows] == [("r0002", ["T07", "2026-03-30"])]
    assert table.provenance == "native-text" and table.locator.page == 2
    row_block = doc.blocks[-1]
    assert (row_block.kind, row_block.text) == ("table-ref", "Tâche: T07; Date: 2026-03-30")
    assert row_block.locator.page == 2 and row_block.locator.bbox is not None
    assert all(block.text not in ("Tâche", "Date", "T07") for block in doc.blocks)

    (figure,) = doc.figures
    assert figure.caption == "Figure 1: plan de la baie F1"
    assert figure.locator.page == 1
    assert figure.bbox == pytest.approx([0.0952, 0.5051, 0.4286, 0.6524], abs=0.002)
    assert result.figures["f01"].startswith(b"\x89PNG")


async def test_scanned_pdf_gets_ocr_provenance_and_confidence(
    corpus: Corpus, tmp_path: Path
) -> None:
    from extract_fixtures import PdfItem, PdfLayout

    rel = "docs/bon-de-livraison-scan.pdf"
    layout = PdfLayout([PdfItem(1, "Bon de livraison BL-2026-0391", (20, 20, 80, 30))], pages=1)
    response = fake_cu_response(layout, words=True)
    data = corpus.path(rel).read_bytes()
    request = cu_request(analyzer="prebuilt-layout", data=data, content_range=None)
    save_recording(recording_path(tmp_path, request), request, response)
    result = await corpus.extract(rel, azure("replay", tmp_path))
    (block,) = result.doc.blocks
    assert (block.text, block.provenance, block.confidence) == (
        "Bon de livraison BL-2026-0391",
        "ocr",
        0.9,
    )
    assert not any(w.startswith("needs-ocr") for w in result.warnings)


async def test_image_regions_follow_ocr_order(corpus: Corpus, tmp_path: Path) -> None:
    rel = "photos/photo-palettes.png"
    response = {
        "status": "Succeeded",
        "result": {
            "contents": [
                {
                    "kind": "document",
                    "unit": "pixel",
                    "markdown": "Palettes reçues\n\n8 palettes",
                    "pages": [
                        {
                            "pageNumber": 1,
                            "width": 320,
                            "height": 200,
                            "words": [
                                {
                                    "content": "8",
                                    "span": {"offset": 17, "length": 1},
                                    "confidence": 0.5,
                                }
                            ],
                        }
                    ],
                    "paragraphs": [
                        {
                            "content": "Palettes reçues",
                            "source": "D(1,32,20,160,20,160,40,32,40)",
                            "span": {"offset": 0, "length": 15},
                        },
                        {
                            "content": "8 palettes",
                            "source": "D(1,32,100,96,40)",
                            "span": {"offset": 17, "length": 10},
                        },
                    ],
                }
            ]
        },
    }
    data = corpus.path(rel).read_bytes()
    request = cu_request(analyzer="prebuilt-layout", data=data, content_range=None)
    save_recording(recording_path(tmp_path, request), request, response)
    result = await corpus.extract(rel, azure("replay", tmp_path))
    first, second = result.doc.blocks
    assert first.locator == ImageRegionLocator(region=1, bbox=[0.1, 0.1, 0.5, 0.2])
    assert second.locator == ImageRegionLocator(region=2, bbox=[0.1, 0.5, 0.4, 0.7])
    assert (first.provenance, second.confidence) == ("ocr", 0.5)
    assert [b.locator_key for b in result.doc.blocks] == ["img-b01", "img-b02"]
    (figure,) = result.doc.figures
    assert figure.locator == ImageRegionLocator(region=3, bbox=[0.0, 0.0, 1.0, 1.0])


async def test_max_pages_sends_a_page_range(
    corpus: Corpus, service: FakeService, tmp_path: Path
) -> None:
    await corpus.extract(PDF, azure("live", None, max_pages=1))
    assert service.requests[0].url.params["range"] == "1-1"


async def test_azure_mode_keeps_local_adapters_for_other_formats(
    corpus: Corpus, tmp_path: Path
) -> None:
    result = await corpus.extract("plans/commandes.csv", azure("replay", tmp_path))
    assert result.doc.extraction.adapter == "local"
    assert list(tmp_path.iterdir()) == []


async def test_throttling_is_retried(corpus: Corpus, service: FakeService) -> None:
    service.post_failures = [429, 503]
    result = await corpus.extract(PDF, azure("live", None))
    assert len(result.doc.blocks) > 0
    assert [r.method for r in service.requests][:3] == ["POST", "POST", "POST"]


async def test_auth_errors_are_not_retried(corpus: Corpus, service: FakeService) -> None:
    service.post_status = 403
    with pytest.raises(ContentUnderstandingError) as error:
        await corpus.extract(PDF, azure("live", None))
    assert error.value.status_code == 403 and not error.value.retryable
    assert "Cognitive Services User" in error.value.reason
    assert len(service.requests) == 1
    assert error.value.auth and error.value.systemic, "the orchestrator aborts the run"


async def test_outages_and_auth_failures_are_systemic(corpus: Corpus, service: FakeService) -> None:
    service.post_failures = [503] * 5
    with pytest.raises(ContentUnderstandingError) as outage:
        await corpus.extract(PDF, azure("live", None))
    assert outage.value.status_code == 503 and outage.value.retryable
    assert outage.value.systemic

    class NoToken:
        def get_token(self, *scopes: str) -> Any:
            raise RuntimeError("no credential available")

    tokens = cu.AzureTokenProvider(credential=NoToken())
    with pytest.raises(cu.CuServiceError, match="Entra ID token") as missing:
        await tokens.get_token()
    assert missing.value.auth
    wrapped = ContentUnderstandingError("src-0123456789ab", str(missing.value), auth=True)
    assert wrapped.systemic and not wrapped.retryable


async def test_document_errors_are_not_systemic(corpus: Corpus, service: FakeService) -> None:
    service.response = {"status": "Failed", "error": {"code": "InvalidContent", "message": "bad"}}
    with pytest.raises(ContentUnderstandingError) as error:
        await corpus.extract(PDF, azure("live", None))
    assert not error.value.systemic, "quarantined: the document cannot be analysed"
    service.post_status = 400
    with pytest.raises(ContentUnderstandingError) as bad:
        await corpus.extract(PDF, azure("live", None))
    assert bad.value.status_code == 400 and not bad.value.systemic


async def test_failed_operation(corpus: Corpus, service: FakeService) -> None:
    service.response = {"status": "Failed", "error": {"code": "InvalidContent", "message": "bad"}}
    with pytest.raises(ContentUnderstandingError, match="analysis failed: InvalidContent: bad"):
        await corpus.extract(PDF, azure("live", None))


async def test_operation_location_on_another_host_is_refused(
    corpus: Corpus, service: FakeService
) -> None:
    service.location = "https://elsewhere.example/contentunderstanding/analyzerResults/op-0001"
    with pytest.raises(ContentUnderstandingError, match="another host"):
        await corpus.extract(PDF, azure("live", None))
    assert len(service.requests) == 1


async def test_unexpected_result_shape(corpus: Corpus, service: FakeService) -> None:
    service.response = {"status": "Succeeded", "result": {"contents": []}}
    with pytest.raises(ContentUnderstandingError, match="no document content"):
        await corpus.extract(PDF, azure("live", None))


def test_endpoint_validation() -> None:
    assert cu.normalize_endpoint(f"{ENDPOINT}/contentunderstanding/") == ENDPOINT
    # The pipeline is configured with the Foundry project endpoint; CU is account-level.
    assert cu.normalize_endpoint(f"{ENDPOINT}/api/projects/docwiki") == ENDPOINT
    assert cu.normalize_endpoint(f"{ENDPOINT}/API/Projects/docwiki/") == ENDPOINT
    with pytest.raises(ValueError):
        cu.normalize_endpoint("http://insecure.example")
    with pytest.raises(ValueError, match="account endpoint"):
        cu.normalize_endpoint(f"{ENDPOINT}/openai/deployments/x")


@pytest.mark.parametrize(
    ("host", "endpoint", "trusted"),
    [
        ("docwiki-cu.example", ENDPOINT, True),
        (
            "example-resource.cognitiveservices.azure.com",
            "https://example-resource.services.ai.azure.com",
            True,
        ),
        (
            "other-resource.cognitiveservices.azure.com",
            "https://example-resource.cognitiveservices.azure.com",
            False,
        ),
        (
            "example-resource.cognitiveservices.azure.com.attacker.example",
            "https://example-resource.cognitiveservices.azure.com",
            False,
        ),
        ("attacker.example", ENDPOINT, False),
    ],
)
def test_operation_location_host_rules(host: str, endpoint: str, trusted: bool) -> None:
    assert cu._same_resource(host, endpoint) is trusted
