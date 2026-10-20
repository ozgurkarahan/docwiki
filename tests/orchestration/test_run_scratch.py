"""Remote raw files: scratch copies are keyed and verified by content hash."""

from __future__ import annotations

import pytest
from storage_doubles import RemoteStorage

from docwiki.contracts.ids import source_id_for
from docwiki.contracts.layout import source_state_key
from docwiki.contracts.state import SourceState
from docwiki.orchestration.pipeline import Pipeline, RunRequest
from docwiki.release.reader import ReleaseReader

NOTE = "notes/supplier-note.txt"
NOTE_ID = source_id_for(NOTE)


def _shard(harness) -> SourceState:
    return SourceState.from_json(harness.storage.read_bytes(source_state_key(NOTE_ID)))


async def test_overwritten_raw_file_is_extracted_from_its_new_bytes(harness, corpus):
    harness.storage = RemoteStorage(harness.storage)
    first = await harness.run()
    assert first.status == "succeeded", first.errors
    (corpus / "notes" / "supplier-note.txt").write_text(
        "Note from VanArsdel Menuiseries: the bay window F1 is delivered with its hardware.\n",
        encoding="utf-8",
    )
    second = await harness.run()
    assert second.status == "succeeded", second.errors
    assert second.report.counts.changed == 1
    assert second.report.counts.quarantined == 0
    shard = _shard(harness)
    assert not shard.quarantined, shard.last_error


async def test_scratch_copies_are_verified_before_reuse(harness, corpus):
    remote = RemoteStorage(harness.storage)
    harness.storage = remote
    expected = (corpus / "notes" / "supplier-note.txt").read_bytes()
    async with harness.context(lambda: True) as ctx:
        pipeline = Pipeline(ctx, RunRequest())
        await pipeline.prepare()
        item = pipeline.work[NOTE_ID].item
        remote.raw_reads.clear()
        path = pipeline.materialize(item)
        assert path.read_bytes() == expected
        assert pipeline.materialize(item) == path and remote.raw_reads == [item.key]
        path.write_bytes(b"stale bytes of an older version")
        assert pipeline.materialize(item).read_bytes() == expected
        assert remote.raw_reads == [item.key, item.key]


@pytest.mark.parametrize("remote", [False, True], ids=["local", "remote"])
async def test_raw_file_replaced_during_a_run_is_retried(harness, corpus, remote):
    if remote:
        harness.storage = RemoteStorage(harness.storage)
    note = corpus / "notes" / "supplier-note.txt"
    original = note.read_bytes()
    async with harness.context(lambda: True) as ctx:
        pipeline = Pipeline(ctx, RunRequest())
        await pipeline.prepare()
        note.write_bytes(b"Replaced while the run was going on.\n")
        await pipeline.extract_one(NOTE_ID)
    assert pipeline.work[NOTE_ID].status == "quarantined"
    stage = _shard(harness).stages["extract"]
    assert stage.status == "quarantined" and stage.retryable and stage.attempts == 1
    # the upload was rolled back: discover sees the recorded content again ("unchanged")
    note.write_bytes(original)
    outcome = await harness.run()
    assert outcome.status == "succeeded", outcome.errors
    assert outcome.report.counts.quarantined == 0
    assert not _shard(harness).quarantined
    reader = ReleaseReader.open(harness.settings.work_dir)
    assert "Supplier note" in {page.title for page in reader.list_pages("source")}
