"""Run semantics: idempotency, deletions, quarantine, recompiles, overlay and audiences."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from engine_stubs import BROKEN_MARKER, CANARY

from docwiki.contracts.layout import StorageKeys, source_state_key
from docwiki.contracts.proposals import GlossaryProposalPayload, new_proposal
from docwiki.contracts.state import SourceState
from docwiki.release.publish import list_release_ids, read_current_pointer
from docwiki.release.reader import ReleaseReader
from docwiki.release.validate import validate_release


def _valid(root: Path) -> list[str]:
    return [
        f"{v.gate} {v.code} {v.path}:{v.line} {v.message}"
        for v in validate_release(root, canaries=[CANARY], glossary_seeded=True)
    ]


def _shard(harness, raw_path: str) -> SourceState:
    from docwiki.contracts.ids import source_id_for

    data = harness.storage.read_bytes(source_state_key(source_id_for(raw_path)))
    return SourceState.from_json(data)


async def test_second_run_is_a_no_op_and_rebuild_reuses_every_artifact(harness):
    first = await harness.run()
    assert first.status == "succeeded", first.errors
    calls = len(harness.llm.requests)
    assert calls > 0
    artifacts = set(harness.storage.list("work/artifacts/"))

    second = await harness.run()
    assert second.status == "no-op"
    assert len(harness.llm.requests) == calls
    assert read_current_pointer(harness.storage)[0].release_id == first.release_id

    third = await harness.run(kind="rebuild", force=True)
    assert third.status == "succeeded", third.errors
    assert third.release_id != first.release_id
    assert len(harness.llm.requests) == calls, "a rebuild must not call the model again"
    assert set(harness.storage.list("work/artifacts/")) == artifacts
    hits = {stage.stage: stage.cache_hits for stage in third.report.stages}
    assert hits["extract"] == hits["classify"] == hits["compile"] == 4
    assert hits["entities"] == hits["topics"] == 1
    assert _valid(harness.current_release()) == []
    # unchanged content keeps its "updated" date and the log only grows
    first_root = harness.settings.work_dir / "releases" / first.release_id
    old_log = (first_root / "wiki" / "log.md").read_text(encoding="utf-8")
    new_log = (harness.current_release() / "wiki" / "log.md").read_text(encoding="utf-8")
    assert old_log.split("# Log", 1)[1].strip() in new_log


async def test_unchanged_quarantined_sources_are_not_retried(harness, corpus):
    (corpus / "notes" / "broken.txt").write_text(f"{BROKEN_MARKER}\n", encoding="utf-8")
    first = await harness.run()
    assert first.status == "succeeded", first.errors
    assert first.report.counts.quarantined == 1
    shard = _shard(harness, "notes/broken.txt")
    assert shard.quarantined
    assert shard.last_error and "unreadable test document" in shard.last_error
    gates = {gate.gate: gate for gate in first.gates}
    assert gates["G15"].status == "warn"
    assert gates["G16"].status == "skipped"  # the test pack locks no terms
    assert _valid(harness.current_release()) == []
    quality = (harness.current_release() / "wiki" / "_meta" / "quality.md").read_text("utf-8")
    assert "## Quarantined sources" in quality

    (corpus / "notes" / "extra.txt").write_text("Note about window F2.\n", encoding="utf-8")
    second = await harness.run()
    assert second.status == "succeeded", second.errors
    assert second.report.counts.quarantined == 1
    extract = next(stage for stage in second.report.stages if stage.stage == "extract")
    assert extract.failures == 0, "the quarantined source must not be extracted again"


async def test_deleted_raw_file_becomes_a_tombstone_and_a_withdraw_entry(harness, corpus):
    first = await harness.run()
    assert first.status == "succeeded", first.errors
    calls = len(harness.llm.requests)
    (corpus / "notes" / "supplier-note.txt").unlink()

    second = await harness.run()
    assert second.status == "succeeded", second.errors
    assert second.report.counts.deleted == 1
    shard = _shard(harness, "notes/supplier-note.txt")
    assert shard.deleted and shard.deleted_at is not None
    root = harness.current_release()
    assert _valid(root) == []
    reader = ReleaseReader.open(harness.settings.work_dir)
    assert "Supplier note" not in {page.title for page in reader.list_pages("source")}
    log = (root / "wiki" / "log.md").read_text(encoding="utf-8")
    assert "] withdraw | Supplier note" in log
    # the log is append-only: earlier entries stay, their dead links become plain text
    assert "] ingest | Supplier note" in log
    assert "(sources/supplier-note.md)" not in log
    # dependent pages were rebuilt: the topic no longer lists the withdrawn source
    from docwiki.contracts.ids import source_id_for

    topic = reader.read_page("topic:schedule-and-window-delivery")
    assert source_id_for("notes/supplier-note.txt") not in topic.frontmatter.sources
    assert len(topic.frontmatter.sources) == 3
    assert len(harness.llm.requests) > calls, "entity and topic pages are rebuilt"


async def test_recompile_with_operator_hints_forces_one_source(harness):
    first = await harness.run()
    assert first.status == "succeeded", first.errors
    from docwiki.contracts.ids import source_id_for

    target = source_id_for("records/purchase-plan.csv")
    calls = len(harness.llm.requests)
    second = await harness.run(kind="recompile", recompile={target: "Use the row headers."})
    assert second.status == "succeeded", second.errors
    compiled = [r for r in harness.llm.requests[calls:] if r.schema_name == "compile"]
    assert len(compiled) == 1
    assert "Use the row headers." in compiled[0].text
    hints = json.loads(harness.storage.read_bytes(f"work/state/hints/{target}.json"))
    assert hints["hints"] == "Use the row headers."
    third = await harness.run(kind="rebuild", force=True)
    assert third.status == "succeeded", third.errors
    assert not [
        r for r in harness.llm.requests[calls + len(compiled) :] if r.schema_name == "compile"
    ], "the hinted compilation is reused"


async def test_accepted_glossary_proposal_flows_into_the_overlay(harness):
    first = await harness.run()
    assert first.status == "succeeded", first.errors
    proposal = new_proposal(
        "glossary",
        GlossaryProposalPayload(
            term="HT",
            definition="Price excluding VAT.",
            synonyms={"fr": ["hors taxes"]},
        ),
        created_at=datetime(2026, 2, 1, tzinfo=UTC),
    )
    accepted = proposal.model_copy(
        update={
            "status": "accepted",
            "decided_by": "librarian",
            "decided_at": datetime(2026, 2, 2, tzinfo=UTC),
        }
    )
    harness.storage.write_bytes(
        f"{StorageKeys.PROPOSALS_DIR}/{proposal.id}.json", accepted.to_json().encode("utf-8")
    )
    second = await harness.run()
    assert second.status == "succeeded", second.errors
    assert harness.storage.exists(StorageKeys.OVERLAY)
    glossary = (harness.current_release() / "wiki" / "glossary.md").read_text(encoding="utf-8")
    assert "## HT" in glossary and "hors taxes" in glossary
    assert _valid(harness.current_release()) == []
    third = await harness.run()
    assert third.status == "no-op"


async def test_public_build_excludes_internal_and_restricted_sources(make_harness):
    harness = make_harness(audience="public")
    outcome = await harness.run()
    assert outcome.status == "succeeded", outcome.errors
    root = harness.current_release()
    assert [
        f"{v.gate} {v.code} {v.path} {v.message}"
        for v in validate_release(root, audience="public", canaries=[CANARY])
    ] == []
    reader = ReleaseReader.open(harness.settings.work_dir)
    titles = {page.title for page in reader.list_pages("source")}
    assert "Purchase plan" not in titles  # internal purchase plan
    assert all(page.sensitivity == "public" for page in reader.catalog.pages)
    assert not (root / "tables").exists()
    classify_targets = {
        r.metadata.get("source_id") for r in harness.llm.requests if r.schema_name == "classify"
    }
    from docwiki.contracts.ids import source_id_for

    assert source_id_for("restricted/price-study.txt") not in classify_targets


async def test_doc_type_rules_below_the_default_tier_keep_sources_in_public_builds(
    make_harness, pack_dir: Path, tmp_path: Path
):
    pack = tmp_path / "pack"
    shutil.copytree(pack_dir, pack)
    (pack / "sensitivity.yaml").write_text(
        "default: internal\n"
        "rules:\n"
        "  - tier: public\n    doc_type: quote\n"
        "  - tier: public\n    doc_type: note\n"
        '  - tier: restricted\n    path_glob: "**/restricted/**"\n',
        encoding="utf-8",
    )
    harness = make_harness(audience="public", pack=pack)
    outcome = await harness.run()
    assert outcome.status == "succeeded", outcome.errors
    reader = ReleaseReader.open(harness.settings.work_dir)
    titles = {page.title for page in reader.list_pages("source")}
    assert {"DEV-2026-014 indice A", "DEV-2026-014 indice B", "Supplier note"} <= titles
    assert not titles & {"Purchase plan", "Price study"}, "plan: default tier; study: restricted"
    assert all(page.sensitivity == "public" for page in reader.catalog.pages)


async def test_gate_failure_blocks_publish_and_keeps_the_current_release(make_harness):
    from engine_stubs import render_source_page, stub_engine

    harness = make_harness()
    first = await harness.run()
    assert first.status == "succeeded", first.errors

    def leaky_render(*args, **kwargs):
        page, cited = render_source_page(*args, **kwargs)
        body = page.body.replace("## Figures", f"Leaked: {CANARY}\n\n## Figures", 1)
        return page.model_copy(update={"body": body}), cited

    harness.engine = stub_engine(render_source_page=leaky_render)
    second = await harness.run(kind="rebuild", force=True)
    assert second.status == "failed"
    assert not second.published
    assert {gate.gate for gate in second.gates if gate.blocks_publish} == {"G08"}
    assert read_current_pointer(harness.storage)[0].release_id == first.release_id
    assert list_release_ids(harness.storage) == [first.release_id]
    assert second.staged_root is not None and (second.staged_root / "manifest.json").is_file()
    report = json.loads(
        harness.storage.read_bytes(f"{StorageKeys.RUNS_DIR}/{second.run_id}/report.json")
    )
    assert report["status"] == "failed"
    assert report["release_id"] is None


async def test_systemic_errors_fail_the_run_without_publishing(make_harness):
    from engine_stubs import stub_engine

    from docwiki.llm import LlmRateLimited

    async def throttled(*args, **kwargs):
        raise LlmRateLimited("still throttled after retries")

    harness = make_harness(engine=stub_engine(compile_source=throttled))
    outcome = await harness.run()
    assert outcome.status == "failed"
    assert any("LlmRateLimited" in error for error in outcome.errors)
    assert read_current_pointer(harness.storage) is None
    shard = _shard(harness, "records/purchase-plan.csv")
    assert not shard.quarantined


async def test_quarantine_on_compile_failure_keeps_the_run_going(make_harness):
    from engine_stubs import compile_source, stub_engine

    async def picky(doc, classification, pack, llm, *, hints=None):
        if doc.source_path.endswith(".csv"):
            raise ValueError("model output did not validate")
        return await compile_source(doc, classification, pack, llm, hints=hints)

    harness = make_harness(engine=stub_engine(compile_source=picky))
    outcome = await harness.run()
    assert outcome.status == "succeeded", outcome.errors
    shard = _shard(harness, "records/purchase-plan.csv")
    assert shard.stages["compile"].status == "quarantined"
    assert _valid(harness.current_release()) == []
