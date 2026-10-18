"""Run report warnings: problems that did not fail the run."""

from __future__ import annotations

from dataclasses import replace

from docwiki.contracts.layout import run_report_key
from docwiki.contracts.runs import RunReport
from docwiki.orchestration.pipeline import RunRequest
from docwiki.orchestration.workflow import execute_run


async def test_problems_noticed_outside_the_pipeline_are_run_warnings(harness):
    async with harness.context(lambda: True) as ctx:
        noticed = replace(ctx, notices=lambda: ["queue: renewals refused"])
        outcome = await execute_run(noticed, RunRequest())
    assert outcome.status == "succeeded", outcome.errors
    assert outcome.report.warnings == ["queue: renewals refused"]
    assert outcome.errors == []
    stored = RunReport.from_json(harness.storage.read_bytes(run_report_key(outcome.run_id)))
    assert stored.warnings == ["queue: renewals refused"]
    receipt = harness.current_release() / "wiki" / "_meta" / "runs" / f"{outcome.run_id}.md"
    text = receipt.read_text(encoding="utf-8")
    assert "## Warnings" in text and "1 warning recorded" in text
