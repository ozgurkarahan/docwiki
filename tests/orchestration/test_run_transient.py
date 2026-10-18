"""Transient failures: Content Understanding outages fail the run, transient quarantines retry."""

from __future__ import annotations

import pytest
from engine_stubs import extract_source, stub_engine

from docwiki.contracts.ids import source_id_for
from docwiki.contracts.layout import source_state_key
from docwiki.contracts.state import RETRY_ATTEMPTS, SourceState
from docwiki.engine_types import ExtractionError
from docwiki.extract.cu import ContentUnderstandingError
from docwiki.release.publish import read_current_pointer
from docwiki.release.reader import ReleaseReader

NOTE = "notes/supplier-note.txt"


def _shard(harness) -> SourceState:
    return SourceState.from_json(harness.storage.read_bytes(source_state_key(source_id_for(NOTE))))


def _titles(harness) -> set[str]:
    reader = ReleaseReader.open(harness.settings.work_dir)
    return {page.title for page in reader.list_pages("source")}


def _failing_extract(error):
    """``extract_source`` stub that raises ``error(source_id)`` for the supplier note."""

    async def extract(raw_file, *, rel_path, settings, llm=None):
        if rel_path == NOTE:
            raise error(source_id_for(rel_path))
        return await extract_source(raw_file, rel_path=rel_path, settings=settings, llm=llm)

    return extract


@pytest.mark.parametrize(
    "error",
    [
        lambda sid: ContentUnderstandingError(
            sid, "HTTP 503 ServiceUnavailable", status_code=503, retryable=True
        ),
        lambda sid: ContentUnderstandingError(
            sid, "network error calling Content Understanding", retryable=True
        ),
        lambda sid: ContentUnderstandingError(sid, "HTTP 403 AuthorizationFailed", status_code=403),
        lambda sid: ContentUnderstandingError(sid, "HTTP 401 Unauthorized", status_code=401),
        lambda sid: ContentUnderstandingError(sid, "cannot get an Entra ID token", auth=True),
    ],
    ids=["503", "network", "403", "401", "token"],
)
async def test_content_understanding_outages_fail_the_run_instead_of_quarantining(
    make_harness, error
):
    harness = make_harness(engine=stub_engine(extract_source=_failing_extract(error)))
    outcome = await harness.run()
    assert outcome.status == "failed"
    assert any("ContentUnderstandingError" in message for message in outcome.errors)
    assert read_current_pointer(harness.storage) is None
    assert not _shard(harness).quarantined
    harness.engine = stub_engine()
    healed = await harness.run()
    assert healed.status == "succeeded", healed.errors
    assert healed.report.counts.quarantined == 0
    assert "Supplier note" in _titles(harness)


async def test_document_errors_of_content_understanding_are_final_quarantines(make_harness):
    error = _failing_extract(
        lambda sid: ContentUnderstandingError(sid, "HTTP 400 InvalidContent", status_code=400)
    )
    harness = make_harness(engine=stub_engine(extract_source=error))
    outcome = await harness.run()
    assert outcome.status == "succeeded", outcome.errors
    stage = _shard(harness).stages["extract"]
    assert stage.status == "quarantined" and not stage.retryable and stage.attempts == 1
    assert (await harness.run()).status == "no-op", "a final quarantine is not retried"


class GlitchError(ExtractionError):
    retryable = True


async def test_transient_quarantines_are_retried_by_the_next_run(make_harness):
    harness = make_harness(
        engine=stub_engine(extract_source=_failing_extract(lambda sid: GlitchError(sid, "glitch")))
    )
    first = await harness.run()
    assert first.status == "succeeded", first.errors
    assert _shard(harness).retry_pending
    harness.engine = stub_engine()
    second = await harness.run()
    assert second.status == "succeeded", second.errors
    shard = _shard(harness)
    assert not shard.quarantined and shard.last_error is None
    assert "Supplier note" in _titles(harness)


async def test_transient_quarantines_are_retried_a_bounded_number_of_times(make_harness):
    calls: list[str] = []

    def glitch(sid: str) -> GlitchError:
        calls.append(sid)
        return GlitchError(sid, "glitch")

    harness = make_harness(engine=stub_engine(extract_source=_failing_extract(glitch)))
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        outcome = await harness.run()
        assert outcome.status == "succeeded", outcome.errors
        stage = _shard(harness).stages["extract"]
        assert stage.status == "quarantined" and stage.retryable and stage.attempts == attempt
    assert len(calls) == RETRY_ATTEMPTS
    assert not _shard(harness).retry_pending
    assert (await harness.run()).status == "no-op"
    assert len(calls) == RETRY_ATTEMPTS
