"""Stages ``publish`` and ``site``, the run receipt page and research-answer carry-forward."""

from __future__ import annotations

import shutil
import sys
import types
from datetime import UTC, date, datetime
from pathlib import Path

from assemble_helpers import STAMP, source_page

from docwiki.contracts.extracted import Block, ExtractedDoc, ExtractionInfo
from docwiki.contracts.gates import Violation, gate_results
from docwiki.contracts.ids import source_id_for
from docwiki.contracts.locators import TextLinesLocator
from docwiki.contracts.pages import DocwikiStamp, Page, QueryFrontmatter
from docwiki.contracts.runs import CostReceipt, LlmUsage, RunReport, VersionInfo
from docwiki.contracts.storage import FolderStorage
from docwiki.orchestration.pipeline import carry_queries
from docwiki.release.publish import read_current_pointer
from docwiki.release.writer import ReleaseWriter
from docwiki.stages.publish import finalize_and_publish, run_receipt_page
from docwiki.stages.sitehook import build_site_for_release

MOCK = Path(__file__).resolve().parents[2] / "samples" / "fixtures" / "mock-release"
MOCK_ID = "20260215T090000Z-decd4b59"
VERSIONS = VersionInfo(docwiki="0.1.0", domain_pack="wind-om-mock", domain_pack_hash="h")


def _writer(tmp_path: Path) -> ReleaseWriter:
    """A writer whose staging folder holds a copy of the (valid) mock release content."""
    writer = ReleaseWriter(
        tmp_path / "staging",
        created_at=datetime(2026, 2, 15, 9, 0, tzinfo=UTC),
        audience="public",
        versions=VERSIONS,
    )
    return writer


def test_blocked_gates_never_publish(tmp_path: Path):
    writer = _writer(tmp_path)
    storage = FolderStorage(tmp_path / "store", fsync=False)
    failing = gate_results([Violation(gate="G02", code="link-unresolved", message="broken link")])
    result = finalize_and_publish(writer, gates=failing, counts={}, storage=storage)
    assert result.status == "blocked" and "G02" in (result.reason or "")
    assert (result.staged.root / "manifest.json").is_file()
    assert read_current_pointer(storage) is None


def test_final_validation_blocks_an_invalid_release(tmp_path: Path):
    writer = _writer(tmp_path)
    storage = FolderStorage(tmp_path / "store", fsync=False)
    result = finalize_and_publish(writer, gates=gate_results([]), counts={}, storage=storage)
    assert result.status == "blocked"
    assert "final validation failed" in (result.reason or "")
    assert read_current_pointer(storage) is None


def test_valid_release_is_published_and_dry_runs_are_not(tmp_path: Path):
    source = MOCK / "releases" / MOCK_ID
    for name, dry in (("published", False), ("dry", True)):
        writer = ReleaseWriter(
            tmp_path / name,
            created_at=datetime(2026, 2, 15, 9, 0, tzinfo=UTC),
            audience="public",
            versions=VersionInfo(
                docwiki="0.1.0",
                domain_pack="wind-om-mock",
                domain_pack_hash="mock-pack-v1",
                prompts={"compile": "mock-1"},
                extractors={"local": "mock-1"},
            ),
            run_id="run-20260215-090000-0a1b2c3d",
            inputs=_mock_inputs(source),
        )
        assert writer.release_id == MOCK_ID
        for item in source.rglob("*"):
            rel = item.relative_to(source).as_posix()
            if item.is_file() and rel != "manifest.json":
                target = writer.root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(item, target)
        storage = FolderStorage(tmp_path / f"store-{name}", fsync=False)
        result = finalize_and_publish(
            writer,
            gates=gate_results([], skipped=["G04", "G10", "G15"]),
            counts={"sources": 3},
            storage=None if dry else storage,
        )
        assert result.status == ("dry-run" if dry else "published"), result.reason
        pointer = read_current_pointer(storage)
        assert (pointer is None) is dry
        if pointer is not None:
            assert pointer[0].release_id == MOCK_ID


def _mock_inputs(source: Path):
    from docwiki.contracts.manifest import ReleaseManifest

    return ReleaseManifest.from_json((source / "manifest.json").read_bytes()).inputs


def test_site_hook_skips_builds_and_reports_failures(tmp_path: Path, monkeypatch):
    monkeypatch.delitem(sys.modules, "docwiki.site", raising=False)
    import importlib

    from docwiki.stages import sitehook

    real_import = importlib.import_module

    def no_site(name, *args, **kwargs):
        if name == "docwiki.site":
            raise ImportError("no site lane")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", no_site)
    missing = build_site_for_release(tmp_path)
    assert missing.status == "skipped" and "not installed" in missing.message
    monkeypatch.setattr(importlib, "import_module", real_import)

    calls = []
    module = types.ModuleType("docwiki.site")

    def build_site(release_root, out_dir, *, base_url=None, page_title=None, banner=None):
        calls.append((release_root, out_dir, base_url, page_title, banner))
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    module.build_site = build_site  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "docwiki.site", module)
    built = build_site_for_release(
        tmp_path, base_url="https://docs.example.org", page_title="Wiki", banner="FICTIONAL"
    )
    assert built.status == "built" and built.path == tmp_path / "site"
    assert calls == [(tmp_path, tmp_path / "site", "https://docs.example.org", "Wiki", "FICTIONAL")]

    def no_node(release_root, out_dir, **_):
        raise RuntimeError("node is required to build the site (Node 22+ with npm, and git)")

    module.build_site = no_node  # type: ignore[attr-defined]
    skipped = build_site_for_release(tmp_path)
    assert skipped.status == "skipped" and "node is required" in skipped.message

    def broken(release_root, out_dir, **_):
        raise RuntimeError("quartz failed\n" + "\n".join(f"problem {n}" for n in range(30)))

    module.build_site = broken  # type: ignore[attr-defined]
    failed = build_site_for_release(tmp_path)
    assert failed.status == "failed" and "quartz failed" in failed.message
    assert "more lines" in failed.message and "problem 29" not in failed.message

    # the real site lane needs Node and git on PATH: without them the stage is skipped
    monkeypatch.setattr(sitehook.shutil, "which", lambda name: None)
    assert sitehook.site_unavailable(lambda *a, **k: None) is None

    def lane_build(*args, **kwargs):
        raise AssertionError("not called")

    lane_build.__module__ = "docwiki.site.build"
    assert "node and git not found" in (sitehook.site_unavailable(lane_build) or "")
    skipped_lane = build_site_for_release(tmp_path, builder=lane_build)
    assert skipped_lane.status == "skipped" and "node and git not found" in skipped_lane.message


def test_run_receipt_page_lists_stages_costs_and_versions():
    report = RunReport(
        run_id="run-20260215-090000-0a1b2c3d",
        kind="ingest",
        requested_by="cli",
        status="running",
        started_at=datetime(2026, 2, 15, 9, 0, tzinfo=UTC),
        audience="public",
        versions=VersionInfo(docwiki="0.1.0", domain_pack="test-wind", domain_pack_hash="a" * 64),
        cost=CostReceipt(
            price_table="prices.yaml",
            llm=[
                LlmUsage(
                    role="smart",
                    deployment="smart-dep",
                    model="model-x",
                    calls=2,
                    input_tokens=100,
                    output_tokens=50,
                    cost=0.0012,
                )
            ],
            total_cost=0.0012,
        ),
        errors=["ValueError: something with <b>html</b>"],
    )
    page = run_receipt_page(report, stamp=STAMP, updated=date(2026, 2, 15), sensitivity="public")
    assert page.path == "_meta/runs/run-20260215-090000-0a1b2c3d.md"
    assert page.frontmatter.id == "meta:runs/run-20260215-090000-0a1b2c3d"
    assert "| smart | `smart-dep` | `model-x` | 2 | 100 | 0 | 50 | 0.001200 |" in page.body
    assert "Total estimated cost: 0.001200 USD" in page.body
    assert "<b>" not in page.body and "1 error recorded" in page.body


def test_carried_queries_lose_withdrawn_citations_and_get_a_banner():
    kept_raw, gone_raw = "notes/kept.txt", "notes/gone.txt"
    kept, gone = source_id_for(kept_raw), source_id_for(gone_raw)
    body = (
        "# Which oil?\n\nISO VG 220.[^c1] Older answer.[^c2] Again.[^c1]\n\n## Sources\n\n"
        f"[^c1]: [Kept — line 1](../evidence/{kept}/l0001-l0001.md) · ✓ quote verified\n"
        f"[^c2]: [Gone — line 1](../evidence/{gone}/l0001-l0001.md) · ✓ quote verified\n"
    )
    stamp = DocwikiStamp(release="20260101T000000Z-00000000")
    query = Page(
        path="queries/2026-01-02-which-oil.md",
        frontmatter=QueryFrontmatter(
            id="query:2026-01-02-which-oil",
            title="Which oil?",
            summary="Answer.",
            sensitivity="public",
            updated=date(2026, 1, 2),
            docwiki=stamp,
            question="Which oil?",
            asked_by="researcher",
            sources=sorted([kept, gone]),
            approved_by="librarian",
        ),
        body=body,
    )
    doc = ExtractedDoc(
        source_id=kept,
        source_path=kept_raw,
        source_hash="sha256:" + "1" * 64,
        media_type="text/plain",
        lang="en",
        blocks=[
            Block(
                id="b0001",
                kind="paragraph",
                text="ISO VG 220",
                locator=TextLinesLocator(line_start=1, line_end=1),
                provenance="native-text",
            )
        ],
        extraction=ExtractionInfo(adapter="local", adapter_version="1"),
    )
    pages = {kept: source_page(kept_raw, "Kept", "# Kept\n", slug="kept")}
    carried, cited = carry_queries([query], pages, {kept: doc}, stamp=STAMP, day=date(2026, 2, 15))
    (page,) = carried
    assert page.frontmatter.sources == [kept]
    assert page.frontmatter.docwiki == STAMP
    assert "> **Warning:** this answer cited sources that were withdrawn" in page.body
    assert "[^c2]" not in page.body and page.body.count("[^c1]") == 3
    assert [item.source_id for item in cited] == [kept]
    again, _ = carry_queries([page], pages, {kept: doc}, stamp=STAMP, day=date(2026, 2, 15))
    assert again[0].body.count("**Warning:**") == 1
