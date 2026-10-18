"""``docwiki.storage.storage_from_settings``: folder storage locally, Blob storage in azure mode."""

from __future__ import annotations

from pathlib import Path

import pytest

from docwiki.contracts.storage import FolderStorage
from docwiki.storage import storage_from_settings
from docwiki.storage.blob import BlobStorage


def test_local_mode_is_a_folder_storage_under_the_work_dir(tmp_path: Path):
    storage = storage_from_settings(
        "releases", env={"DOCWIKI_MODE": "local", "DOCWIKI_WORK_DIR": str(tmp_path)}
    )
    assert isinstance(storage, FolderStorage)
    storage.write_bytes("releases/current.json", b"{}")
    assert (tmp_path / "releases" / "current.json").read_bytes() == b"{}"
    assert isinstance(storage_from_settings(env={"DOCWIKI_WORK_DIR": str(tmp_path)}), FolderStorage)


def test_azure_mode_maps_logical_containers_with_managed_identity():
    env = {
        "DOCWIKI_MODE": "azure",
        "DOCWIKI_STORAGE_ACCOUNT": "docwikitest",
        "DOCWIKI_RELEASES_CONTAINER": "wiki-releases",
    }
    every = storage_from_settings(env=env)
    assert isinstance(every, BlobStorage)
    assert every._containers == {"raw": "raw", "work": "work", "releases": "wiki-releases"}
    releases = storage_from_settings("releases", env=env)
    assert releases._containers == {"releases": "wiki-releases"}
    with pytest.raises(ValueError):
        releases.read_bytes("work/state/lease")


def test_unknown_container_and_missing_account_are_rejected():
    with pytest.raises(ValueError):
        storage_from_settings("logs", env={})
    with pytest.raises(ValueError):
        storage_from_settings(env={"DOCWIKI_MODE": "azure"})
