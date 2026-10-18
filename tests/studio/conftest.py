from __future__ import annotations

from pathlib import Path

import pytest
from studio_testkit import OWNER, WIKI_URL, seed_storage

from docwiki.contracts.storage import FolderStorage
from docwiki.studio.config import StudioConfig


@pytest.fixture
def storage(tmp_path: Path) -> FolderStorage:
    return seed_storage(tmp_path / "store")


@pytest.fixture
def config() -> StudioConfig:
    return StudioConfig(wiki_url=WIKI_URL, allowed_principals=frozenset({OWNER}))
