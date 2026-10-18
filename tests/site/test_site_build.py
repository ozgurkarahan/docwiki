from __future__ import annotations

import json
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest
from site_testkit import MOCK_RELEASE, MOCK_RELEASE_DIR, OVERLAY, FakeTools, write_site

from docwiki.contracts.markdown import BACKLINKS_END, BACKLINKS_START
from docwiki.site import (
    DEFAULT_BANNER,
    SiteBuildError,
    apply_overlay,
    assemble_content,
    build_site,
    detect_fictional,
    normalize_base_url,
    open_release,
    read_quartz_version,
    site_settings,
)
from docwiki.site import build as build_module


def test_pinned_quartz_version() -> None:
    assert read_quartz_version(OVERLAY) == "v4.5.2"


def test_invalid_quartz_version(tmp_path: Path) -> None:
    (tmp_path / "QUARTZ_VERSION").write_text("main\n", encoding="utf-8")
    with pytest.raises(SiteBuildError, match="invalid Quartz tag"):
        read_quartz_version(tmp_path)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("  ", None),
        ("docwiki.ozgurkarahan.com", "docwiki.ozgurkarahan.com"),
        ("https://docwiki.ozgurkarahan.com/", "docwiki.ozgurkarahan.com"),
        ("HTTP://Docs.Example.org/Wiki/", "docs.example.org/Wiki"),
        ("localhost:8080", "localhost:8080"),
    ],
)
def test_normalize_base_url(value: str | None, expected: str | None) -> None:
    assert normalize_base_url(value) == expected


@pytest.mark.parametrize("value", ["docs example.org", "https://", "-bad.example.org", "a/b?c"])
def test_normalize_base_url_rejects(value: str) -> None:
    with pytest.raises(SiteBuildError):
        normalize_base_url(value)


def test_detect_fictional() -> None:
    index = (MOCK_RELEASE_DIR / "wiki" / "index.md").read_text(encoding="utf-8")
    assert detect_fictional(index)
    assert detect_fictional("> **FICTIONAL** sample\n")
    assert not detect_fictional("---\ntitle: x\n---\n\n# Real wiki\n\nNot fictional.\n")
    assert not detect_fictional("Text mentioning FICTIONAL in a sentence.\n")


@pytest.mark.parametrize(
    "location", [MOCK_RELEASE, MOCK_RELEASE / "releases", MOCK_RELEASE_DIR]
)
def test_open_release_locations(location: Path) -> None:
    release = open_release(location)
    assert release.root.resolve() == MOCK_RELEASE_DIR.resolve()
    assert release.release_id == "20260215T090000Z-decd4b59"
    assert release.release_date == "2026-02-15"
    assert release.audience == "public"


def test_open_release_without_manifest(tmp_path: Path) -> None:
    """The pipeline's site stage runs on the staged release, before manifest.json exists."""
    staged = tmp_path / "staged"
    shutil.copytree(MOCK_RELEASE_DIR / "wiki", staged / "wiki")
    assert open_release(staged).release_id == "20260215T090000Z-decd4b59"
    (staged / "wiki" / "catalog.json").unlink()
    with pytest.raises(SiteBuildError, match="no catalog"):
        open_release(staged)
    with pytest.raises(SiteBuildError, match="no release or portable wiki"):
        open_release(tmp_path / "nothing")


def test_assemble_content_mounts_evidence(tmp_path: Path) -> None:
    content = tmp_path / "content"
    (content / "stale").mkdir(parents=True)
    count = assemble_content(MOCK_RELEASE_DIR, content)
    assert not (content / "stale").exists()
    assert (content / "index.md").is_file()
    assert (content / "sources" / "sop-gbx-010-rev-b.md").is_file()
    assert (content / "evidence" / "src-f2750f41f3fa" / "p0001.md").is_file()
    assert (content / "evidence" / "src-f2750f41f3fa" / "img" / "p0001.png").is_file()
    assert count == sum(1 for p in content.rglob("*") if p.is_file())
    assert not any(part.startswith(".") for p in content.rglob("*") for part in p.parts[-1:])
    page = (content / "sources" / "sop-gbx-010-rev-b.md").read_text(encoding="utf-8")
    assert BACKLINKS_START in page and BACKLINKS_END in page  # stripped by the transformer


def test_assemble_content_refuses_reserved_evidence_folder(tmp_path: Path) -> None:
    release = tmp_path / "release"
    shutil.copytree(MOCK_RELEASE_DIR / "wiki", release / "wiki")
    (release / "wiki" / "evidence").mkdir()
    with pytest.raises(SiteBuildError, match="reserved"):
        assemble_content(release, tmp_path / "content")
    with pytest.raises(SiteBuildError, match="no release or portable wiki"):
        assemble_content(tmp_path / "empty", tmp_path / "content")


def test_apply_overlay(tmp_path: Path) -> None:
    checkout = write_site(
        tmp_path / "quartz",
        {
            "quartz.config.ts": "stock",
            "quartz/styles/custom.scss": "stock",
            "quartz/static/giscus/dark.css": "@import url(https://cdn.example.net/x.css);",
            "quartz/static/icon.png": "png",
            "quartz/static/og-image.png": "png",
        },
    )
    written = apply_overlay(OVERLAY, checkout)
    assert {"quartz.config.ts", "quartz.layout.ts", "quartz/styles/custom.scss"} <= set(written)
    assert "quartz/plugins/transformers/docwiki.ts" in written
    assert "quartz/static/docwiki/content-index.js" in written
    assert (checkout / "quartz.config.ts").read_text(encoding="utf-8") != "stock"
    assert not (checkout / "quartz" / "static" / "giscus").exists()
    assert not (checkout / "quartz" / "static" / "icon.png").exists()
    with pytest.raises(SiteBuildError, match="overlay file missing"):
        apply_overlay(tmp_path / "no-overlay", checkout)


def test_site_settings_from_the_mock_release() -> None:
    release = open_release(MOCK_RELEASE)
    settings = site_settings(
        release,
        base_url="docwiki.ozgurkarahan.com",
        page_title=None,
        banner=None,
        repo_url="https://github.com/ozgurkarahan/docwiki",
        quartz_version="v4.5.2",
    )
    assert settings["pageTitle"] == "Contoso Renewables mock wiki"
    assert settings["banner"] == DEFAULT_BANNER
    assert settings["releaseId"] == "20260215T090000Z-decd4b59"
    assert settings["releaseDate"] == "2026-02-15"
    assert settings["sources"]["src-4d9c65e05302"] == {
        "page": "sources/sop-gbx-010-rev-b",
        "title": "Gearbox oil change SOP rev B",
        "original": None,
    }
    assert len(settings["sources"]) == 3
    custom = site_settings(
        release,
        base_url=None,
        page_title="Wind O&M wiki",
        banner="",
        repo_url="https://github.com/ozgurkarahan/docwiki",
        quartz_version="v4.5.2",
    )
    assert custom["pageTitle"] == "Wind O&M wiki"
    assert custom["banner"] is None and custom["baseUrl"] is None


def test_site_settings_lists_published_originals(tmp_path: Path) -> None:
    release_dir = tmp_path / "release"
    shutil.copytree(MOCK_RELEASE_DIR, release_dir)
    (release_dir / "evidence" / "src-f2750f41f3fa" / "original.pdf").write_bytes(b"%PDF-")
    settings = site_settings(
        open_release(release_dir),
        base_url=None,
        page_title=None,
        banner=None,
        repo_url="https://github.com/ozgurkarahan/docwiki",
        quartz_version="v4.5.2",
    )
    assert settings["sources"]["src-f2750f41f3fa"]["original"] == (
        "evidence/src-f2750f41f3fa/original.pdf"
    )


def test_build_site_orchestration_is_idempotent(tmp_path: Path, tools: FakeTools) -> None:
    cache, out = tmp_path / "cache", tmp_path / "out"
    result = build_site(
        MOCK_RELEASE, out, base_url="https://docwiki.ozgurkarahan.com", cache_dir=cache,
        runner=tools, env={},
    )
    assert result == out.resolve()
    assert (out / "index.html").read_text(encoding="utf-8").startswith(
        "<title>Contoso Renewables mock wiki</title>"
    )
    checkout = cache / "v4.5.2"
    settings = json.loads((checkout / "docwiki-site.json").read_text(encoding="utf-8"))
    assert settings["baseUrl"] == "docwiki.ozgurkarahan.com"
    assert (checkout / "content" / "evidence" / "src-43c97f7dfcde" / "index.md").is_file()
    assert (checkout / "quartz" / "plugins" / "transformers" / "docwiki.ts").is_file()
    assert not (checkout / "quartz" / "static" / "giscus").exists()
    tools_used = [command[:2] for command in tools.commands]
    assert ("git", "-c") in tools_used  # clone
    assert ("npm", "ci") in tools_used
    assert tools.commands[-1] == (
        "node", "quartz/bootstrap-cli.mjs", "build", "-d", "content", "-o", "public"
    )
    assert "--ignore-scripts" in next(c for c in tools.commands if c[0] == "npm")

    tools.commands.clear()
    build_site(MOCK_RELEASE, out, cache_dir=cache, runner=tools, env={})
    used = [command for command in tools.commands]
    assert not any("clone" in command for command in used)
    assert not any(command[0] == "npm" for command in used)
    assert any("reset" in command for command in used)
    assert any("clean" in command for command in used)


def test_build_site_base_url_from_environment(tmp_path: Path, tools: FakeTools) -> None:
    build_site(
        MOCK_RELEASE,
        tmp_path / "out",
        cache_dir=tmp_path / "cache",
        runner=tools,
        env={"DOCWIKI_SITE_BASE_URL": "docs.example.org"},
    )
    settings = json.loads(
        (tmp_path / "cache" / "v4.5.2" / "docwiki-site.json").read_text(encoding="utf-8")
    )
    assert settings["baseUrl"] == "docs.example.org"


def test_build_site_refuses_to_replace_other_folders(tmp_path: Path, tools: FakeTools) -> None:
    precious = write_site(tmp_path / "precious", {"notes.txt": "keep me"})
    with pytest.raises(SiteBuildError, match="refusing to replace"):
        build_site(MOCK_RELEASE, precious, cache_dir=tmp_path / "cache", runner=tools, env={})
    assert (precious / "notes.txt").read_text(encoding="utf-8") == "keep me"
    assert tools.commands == []  # checked before anything is built
    with pytest.raises(SiteBuildError, match="must not contain the release"):
        build_site(MOCK_RELEASE, MOCK_RELEASE, cache_dir=tmp_path / "c", runner=tools, env={})


def test_build_site_fails_when_checks_fail(tmp_path: Path, tools: FakeTools) -> None:
    original = tools.__call__

    def broken(args: Sequence[str], *, cwd: Path) -> str:
        output = original(args, cwd=cwd)
        if Path(args[0]).name == "node":
            (cwd / "public" / "index.html").write_text(
                '<a href="missing">x</a><iframe src="x"></iframe><script src="postscript.js">'
                "</script>",
                encoding="utf-8",
            )
        return output

    out = tmp_path / "out"
    with pytest.raises(SiteBuildError, match="failed its checks") as error:
        build_site(MOCK_RELEASE, out, cache_dir=tmp_path / "cache", runner=broken, env={})
    assert "missing-target" in str(error.value) and "iframe" in str(error.value)
    assert (out / "index.html").is_file()  # kept for review
    build_site(MOCK_RELEASE, out, cache_dir=tmp_path / "cache", runner=broken, env={}, check=False)


def test_failed_commands_raise_site_build_errors(tmp_path: Path) -> None:
    with pytest.raises(SiteBuildError, match="exit 3"):
        build_module.subprocess_runner(
            [sys.executable, "-c", "import sys; sys.exit(3)"], cwd=tmp_path
        )
    with pytest.raises(SiteBuildError, match="cannot run"):
        build_module.subprocess_runner([str(tmp_path / "no-such-tool")], cwd=tmp_path)
