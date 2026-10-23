"""Following a run (v1.7, slice C): the documents it processes, the stage at work while it runs,
and the pages its release added, changed or removed."""

from __future__ import annotations

import json

from docwiki.contracts.layout import run_report_key
from docwiki.contracts.runs import RunReport


async def test_a_run_reports_its_documents_and_the_pages_it_changed(harness, corpus):
    progress: list[RunReport] = []
    storage = harness.storage
    write_bytes = storage.write_bytes

    def spy(key: str, data: bytes, **kwargs):  # every report written while the run is at work
        result = write_bytes(key, data, **kwargs)
        if key.startswith("work/runs/") and key.endswith("/report.json"):
            report = RunReport.from_json(data)
            if report.status == "running":
                progress.append(report)
        return result

    storage.write_bytes = spy  # type: ignore[method-assign]
    first = await harness.run()
    assert first.status == "succeeded", first.errors
    report = first.report
    assert {document.change for document in report.documents} == {"new"}
    assert len(report.documents) == report.counts.new
    added = {change.path for change in report.page_changes if change.change == "added"}
    assert any(path.startswith("sources/") for path in added)
    assert all(change.change == "added" for change in report.page_changes)
    # while it ran, the report named the stage at work and never called it done
    stages = [item.current_stage for item in progress if item.current_stage]
    assert "discover" in stages and "compile" in stages and "publish" in stages
    for item in progress:
        if item.current_stage:
            assert item.current_stage not in {stage.stage for stage in item.stages}
    assert progress[-1].documents  # the documents are known once discover has run

    # a rebuild with no new document changes no page and processes no document
    storage.write_bytes = write_bytes  # type: ignore[method-assign]
    rebuilt = await harness.run(kind="rebuild", force=True)
    assert rebuilt.status == "succeeded", rebuilt.errors
    assert rebuilt.report.documents == [] or all(
        document.change == "recompiled" for document in rebuilt.report.documents
    )
    assert rebuilt.report.page_changes == []  # the home page's recent changes do not count

    # the final report on storage is the finished one, with its changes
    stored = RunReport.from_json(storage.read_bytes(run_report_key(first.run_id)))
    assert stored.status == "succeeded" and stored.current_stage is None
    assert json.loads(stored.to_json())["page_changes"]
