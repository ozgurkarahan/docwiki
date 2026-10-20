"""Portable wiki folders: wiki at the root, ``evidence/`` inside, ``.docwiki/`` machine files."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from site_testkit import (
    MOCK_RELEASE,
    MOCK_RELEASE_DIR,
    MOCK_RELEASE_ID,
    MOCK_TITLE,
    PLAN_A,
    PLAN_B,
    FakeTools,
    make_portable,
)

import docwiki.release
from docwiki.release import ReleaseReader
from docwiki.site import (
    PORTABLE_DIR,
    SiteBuildError,
    assemble_content,
    build_site,
    is_portable_wiki,
    open_release,
    site_settings,
)


@pytest.fixture
def portable(tmp_path: Path) -> Path:
    return make_portable(tmp_path / "wiki")


def files(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


def settings_of(location: Path) -> dict[str, object]:
    return site_settings(
        open_release(location),
        base_url=None,
        page_title=None,
        banner=None,
        repo_url="https://github.com/ozgurkarahan/docwiki",
        quartz_version="v4.5.2",
    )


def test_detection(portable: Path, tmp_path: Path) -> None:
    assert is_portable_wiki(portable)
    assert not is_portable_wiki(MOCK_RELEASE_DIR)
    assert not is_portable_wiki(MOCK_RELEASE)
    (portable / PORTABLE_DIR / "manifest.json").unlink()
    assert is_portable_wiki(portable)  # the pointer alone also marks the layout
    (portable / PORTABLE_DIR / "current.json").unlink()
    assert not is_portable_wiki(portable)
    with pytest.raises(SiteBuildError, match="no release or portable wiki"):
        open_release(portable)


def test_open_portable(portable: Path) -> None:
    release = open_release(portable)
    assert release.layout == "portable"
    assert release.root == release.wiki_dir == portable
    assert release.evidence_dir == portable / "evidence"
    assert release.release_id == MOCK_RELEASE_ID
    assert release.release_date == "2026-04-01"
    assert release.audience == "public"


def test_catalog_falls_back_to_the_machine_folder(portable: Path) -> None:
    shutil.move(portable / "catalog.json", portable / PORTABLE_DIR / "catalog.json")
    assert open_release(portable).release_id == MOCK_RELEASE_ID
    (portable / PORTABLE_DIR / "catalog.json").unlink()
    with pytest.raises(SiteBuildError, match=r"no catalog\.json in portable"):
        open_release(portable)


def test_portable_content_equals_the_release_content(portable: Path, tmp_path: Path) -> None:
    from_portable = tmp_path / "content-portable"
    from_release = tmp_path / "content-release"
    count = assemble_content(portable, from_portable)
    assemble_content(MOCK_RELEASE_DIR, from_release)
    assert files(from_portable) == files(from_release)
    assert count == len(files(from_portable))
    assert f"evidence/{PLAN_A}/img/p0001.png" in files(from_portable)
    assert not (from_portable / PORTABLE_DIR).exists()
    for hidden in (".agents", ".claude", ".github"):
        assert (portable / hidden).is_dir() and not (from_portable / hidden).exists()


def test_portable_settings_equal_the_release_settings(portable: Path) -> None:
    assert settings_of(portable) == settings_of(MOCK_RELEASE)
    (portable / "evidence" / PLAN_A / "original.pdf").write_bytes(b"%PDF-")
    sources = settings_of(portable)["sources"]
    assert isinstance(sources, dict)
    assert sources[PLAN_A]["original"] == f"evidence/{PLAN_A}/original.pdf"


def test_build_site_from_a_portable_folder(
    portable: Path, tmp_path: Path, tools: FakeTools
) -> None:
    messages: list[str] = []
    cache, out = tmp_path / "cache", tmp_path / "public"
    assert build_site(portable, out, cache_dir=cache, runner=tools, env={}, log=messages.append)
    checkout = cache / "v4.5.2"
    content = checkout / "content"
    assert (content / "index.md").is_file()
    assert (content / "evidence" / PLAN_B / "sheet-planning-r0006-r0009.md").is_file()
    assert not (content / PORTABLE_DIR).exists()
    settings = json.loads((checkout / "docwiki-site.json").read_text(encoding="utf-8"))
    assert settings["pageTitle"] == MOCK_TITLE
    assert any(f"portable {MOCK_RELEASE_ID}" in message for message in messages)
    assert (out / "index.html").is_file()


def test_build_site_keeps_the_output_out_of_the_wiki(
    portable: Path, tmp_path: Path, tools: FakeTools
) -> None:
    cache = tmp_path / "cache"
    with pytest.raises(SiteBuildError, match="outside a portable wiki folder"):
        build_site(portable, portable / "public", cache_dir=cache, runner=tools, env={})
    assert tools.commands == []
    inside_machine_folder = portable / PORTABLE_DIR / "site"
    build_site(portable, inside_machine_folder, cache_dir=cache, runner=tools, env={})
    assert (inside_machine_folder / "index.html").is_file()
    assert is_portable_wiki(portable)


def test_export_portable_when_available(tmp_path: Path, tools: FakeTools) -> None:
    export = getattr(docwiki.release, "export_portable", None)
    if export is None:
        pytest.skip("docwiki.release.export_portable is not available yet")
    dest = tmp_path / "exported"
    try:
        result = export(MOCK_RELEASE_DIR, dest)
    except (TypeError, AttributeError):
        shutil.rmtree(dest, ignore_errors=True)
        result = export(ReleaseReader.open(MOCK_RELEASE_DIR), dest)
    exported = Path(result) if isinstance(result, (str, Path)) else dest
    assert is_portable_wiki(exported)
    release = open_release(exported)
    assert release.layout == "portable"
    assert release.release_id == MOCK_RELEASE_ID
    content = tmp_path / "content"
    assemble_content(release, content)
    assert files(content) == files(_release_content(tmp_path))
    build_site(exported, tmp_path / "public", cache_dir=tmp_path / "cache", runner=tools, env={})


def _release_content(tmp_path: Path) -> Path:
    content = tmp_path / "content-release"
    assemble_content(MOCK_RELEASE_DIR, content)
    return content
