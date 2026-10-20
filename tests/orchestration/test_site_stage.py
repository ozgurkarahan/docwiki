"""Stage ``site`` inside a run: built into the release before finalize, skipped, failed, scanned."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from engine_stubs import CANARY

from docwiki.contracts.gates import GateResult
from docwiki.contracts.manifest import ReleaseManifest
from docwiki.release.publish import read_current_pointer
from docwiki.release.validate import validate_release
from docwiki.stages import sitehook


def manifest_gates(root: Path) -> list[GateResult]:
    return ReleaseManifest.from_json((root / "manifest.json").read_bytes()).gates


def _fake_lane(monkeypatch: pytest.MonkeyPatch, html: str = "<p>wiki</p>") -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def build_site(release_root: Path, out_dir: Path, **options: Any) -> Path:
        calls.append({"root": Path(release_root), "out": Path(out_dir), **options})
        assert (Path(release_root) / "catalog.json").is_file()
        assert not (Path(release_root) / "manifest.json").exists(), "built before finalize"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(html, encoding="utf-8")
        return out_dir

    monkeypatch.setattr(sitehook, "site_builder", lambda: build_site)
    return calls


async def test_site_is_built_into_the_release_before_it_is_finalized(make_harness, monkeypatch):
    calls = _fake_lane(monkeypatch)
    harness = make_harness(build_site=True, site_base_url="https://docs.example.org")
    outcome = await harness.run()
    assert outcome.status == "succeeded" and outcome.published, outcome.errors
    root = harness.current_release()
    assert (root / "site" / "index.html").is_file()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert "site/index.html" in manifest["files"]
    assert calls[0]["out"] == calls[0]["root"] / "site"
    assert calls[0]["page_title"] == "Chantier Moreau engine test wiki"
    assert calls[0]["banner"] == "FICTIONAL - NOT FOR OPERATIONAL USE"
    assert calls[0]["base_url"] == "https://docs.example.org"
    # the staged release has no manifest yet: the run passes its gates and id for the home page
    assert calls[0]["run_id"] == outcome.report.run_id
    assert [gate.gate for gate in calls[0]["gates"]] == [gate.gate for gate in manifest_gates(root)]
    assert validate_release(root, canaries=[CANARY]) == []
    quality = (root / "wiki" / "_meta" / "quality.md").read_text(encoding="utf-8")
    assert "## Site" in quality and "Built from this release" in quality


async def test_missing_node_skips_the_site_with_a_warning_and_still_publishes(
    make_harness, monkeypatch
):
    def lane_build(*args: Any, **kwargs: Any) -> Path:
        raise AssertionError("not called without Node")

    lane_build.__module__ = "docwiki.site.build"
    monkeypatch.setattr(sitehook, "site_builder", lambda: lane_build)
    monkeypatch.setattr(sitehook.shutil, "which", lambda name: None)
    harness = make_harness()
    outcome = await harness.run(site=True)
    assert outcome.status == "succeeded" and outcome.published, outcome.errors
    root = harness.current_release()
    assert not (root / "site").exists()
    quality = (root / "wiki" / "_meta" / "quality.md").read_text(encoding="utf-8")
    assert "Not built: node and git not found" in quality
    stages = {stage.stage: stage for stage in outcome.report.stages}
    assert stages["site"].status == "skipped" and stages["site"].errors


async def test_failing_or_leaking_site_blocks_the_publish(make_harness, monkeypatch):
    harness = make_harness(build_site=True)
    _fake_lane(monkeypatch)
    first = await harness.run()
    assert first.published
    current = read_current_pointer(harness.storage)

    def broken(release_root: Path, out_dir: Path, **options: Any) -> Path:
        raise RuntimeError("the built site failed its checks: 3 broken links")

    monkeypatch.setattr(sitehook, "site_builder", lambda: broken)
    failed = await harness.run(kind="rebuild", force=True)
    assert failed.status == "failed" and not failed.published
    assert any("broken links" in error for error in failed.errors)
    assert read_current_pointer(harness.storage) == current

    _fake_lane(monkeypatch, html=f"<p>{CANARY}</p>")
    leaked = await harness.run(kind="rebuild", force=True)
    assert leaked.status == "failed" and not leaked.published
    assert any(gate.gate == "G08" and gate.status == "fail" for gate in leaked.report.gates)
    assert read_current_pointer(harness.storage) == current
    staged = leaked.staged_root
    assert staged is not None
    quality = (staged / "wiki" / "_meta" / "quality.md").read_text(encoding="utf-8")
    assert "canary scan found" in quality and CANARY not in quality
