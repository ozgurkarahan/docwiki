"""Raw files are downloaded only when a stage needs their bytes."""

from __future__ import annotations

import shutil
from types import SimpleNamespace

from storage_doubles import RemoteStorage

from docwiki.contracts.extracted import Block, ExtractedDoc, ExtractionInfo, Figure
from docwiki.contracts.ids import source_id_for
from docwiki.contracts.locators import DocxParagraphLocator, PdfPageLocator
from docwiki.engine_types import CitedLocator, ExtractResult
from docwiki.orchestration.pipeline import Pipeline


async def test_unchanged_sources_are_not_downloaded_again(harness, corpus):
    remote = RemoteStorage(harness.storage)
    harness.storage = remote
    first = await harness.run()
    assert first.status == "succeeded", first.errors
    # a new job execution starts with an empty scratch folder
    shutil.rmtree(harness.settings.work_dir / ".scratch", ignore_errors=True)
    remote.raw_reads.clear()
    (corpus / "notes" / "extra.txt").write_text("Gearbox oil note for WTG-12.\n", encoding="utf-8")
    second = await harness.run()
    assert second.status == "succeeded", second.errors
    assert set(remote.raw_reads) == {"raw/notes/extra.txt"}


def test_evidence_reads_the_raw_file_only_when_it_needs_it():
    sid = source_id_for("manuals/gearbox.pdf")
    block = Block(
        id="b0001",
        kind="paragraph",
        text="Torque the bolts to 12 Nm.",
        locator=PdfPageLocator(page=1),
        provenance="native-text",
    )
    doc = ExtractedDoc(
        source_id=sid,
        source_path="manuals/gearbox.pdf",
        source_hash="sha256:" + "0" * 64,
        media_type="application/pdf",
        lang="en",
        blocks=[block],
        extraction=ExtractionInfo(adapter="local", adapter_version="1"),
    )
    work = SimpleNamespace(extract=ExtractResult(doc=doc, page_images={1: b"png"}))
    page1 = [CitedLocator(sid, PdfPageLocator(page=1), ("b0001",))]
    page2 = [CitedLocator(sid, PdfPageLocator(page=2), ("b0001",))]
    needs = Pipeline._evidence_needs_raw
    assert needs(work, page1, False) is False, "the extract stage rendered page 1"
    assert needs(work, page1, True) is True, "an original is copied from the raw file"
    assert needs(work, page2, False) is True, "page 2 must be rendered from the raw file"
    figure = Figure(id="f01", locator=DocxParagraphLocator(paragraph=3), image="f01.png")
    work.extract.doc = doc.model_copy(update={"figures": [figure]})
    assert needs(work, page1, False) is True, "DOCX/PPTX pictures are re-read from the file"
