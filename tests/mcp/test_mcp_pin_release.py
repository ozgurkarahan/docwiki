"""``DOCWIKI_MCP_PIN_RELEASE``: an evaluation server serves one immutable release, whatever the
current pointer says."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest
from mcp_testkit import FIXTURE_ROOT, NOW, RELEASE_ID, copy_fixture, stage_release

from docwiki.contracts.storage import FolderStorage
from docwiki.mcp.config import McpConfig
from docwiki.mcp.server import make_source
from docwiki.mcp.source import FolderReleaseSource, ReleaseUnavailableError, StorageReleaseSource
from docwiki.mcp.tools_read import ReadTools
from docwiki.release import publish_release


def test_config_validation() -> None:
    config = McpConfig.from_env({"DOCWIKI_MCP_PIN_RELEASE": RELEASE_ID})
    assert config.pin_release == RELEASE_ID
    with pytest.raises(ValueError, match="DOCWIKI_MCP_PIN_RELEASE"):
        McpConfig.from_env({"DOCWIKI_MCP_PIN_RELEASE": "../current.json"})


@pytest.mark.parametrize("storage_mode", [False, True])
def test_pin_ignores_pointer_and_works_without_one(tmp_path: Path, storage_mode: bool) -> None:
    root = copy_fixture(tmp_path / "releases-root")
    remote = FolderStorage(root, fsync=False)
    staged = stage_release(tmp_path / "staged", created_at=NOW + timedelta(days=1))
    publish_release(remote, staged)
    (root / "releases" / "current.json").unlink()
    if storage_mode:
        source = StorageReleaseSource(remote, tmp_path / "cache", pin_release=RELEASE_ID, ttl_s=0)
    else:
        source = make_source(root, McpConfig(pin_release=RELEASE_ID, pointer_ttl_s=0))
    assert source.current().release_id == RELEASE_ID
    (root / "releases" / "current.json").write_text("broken pointer", encoding="utf-8")
    source.invalidate()
    reads = ReadTools(source, McpConfig())
    assert json.loads(reads.search("menuiseries"))["release_id"] == RELEASE_ID
    assert source.last_error is None


def test_pin_direct_folder_and_missing_release(tmp_path: Path) -> None:
    direct = FIXTURE_ROOT / "releases" / RELEASE_ID
    assert make_source(direct, McpConfig(pin_release=RELEASE_ID)).current().release_id == RELEASE_ID
    missing = "20990101T000000Z-00000000"
    for source in (
        FolderReleaseSource(direct, pin_release=missing),
        FolderReleaseSource(FIXTURE_ROOT, pin_release=missing),
        StorageReleaseSource(FolderStorage(FIXTURE_ROOT), tmp_path / "cache", pin_release=missing),
    ):
        with pytest.raises(ReleaseUnavailableError, match="pinned release"):
            source.current()


def test_azure_pin_uses_existing_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from docwiki.mcp import blob

    root = copy_fixture(tmp_path / "remote")
    (root / "releases" / "current.json").unlink()
    storage = FolderStorage(root, fsync=False)
    monkeypatch.setattr(blob, "AzureBlobStorage", lambda account, **kwargs: storage)
    config = McpConfig(mode="azure", pin_release=RELEASE_ID)
    source = make_source(None, config, cache_dir=tmp_path / "cache")
    assert isinstance(source, StorageReleaseSource) and source.storage is storage
    assert json.loads(ReadTools(source, config).search("menuiseries"))["release_id"] == RELEASE_ID
