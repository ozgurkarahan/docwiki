from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from mcp_testkit import FIXTURE_ROOT, NOW, seed_work

from docwiki.contracts.storage import FolderStorage
from docwiki.mcp.config import McpConfig
from docwiki.mcp.ingest_queue import FolderQueue
from docwiki.mcp.source import FolderReleaseSource
from docwiki.mcp.tools_ops import OpsTools
from docwiki.mcp.tools_read import ReadTools
from docwiki.mcp.workstore import WorkStore


@pytest.fixture
def config() -> McpConfig:
    return McpConfig()


@pytest.fixture
def source(config: McpConfig) -> FolderReleaseSource:
    """The committed mock release, read in place (never written)."""
    return FolderReleaseSource(FIXTURE_ROOT, ttl_s=config.pointer_ttl_s)


@pytest.fixture
def reads(source: FolderReleaseSource, config: McpConfig) -> ReadTools:
    return ReadTools(source, config)


@pytest.fixture
def work_storage(tmp_path: Path) -> FolderStorage:
    return FolderStorage(tmp_path / "work-root", fsync=False)


@pytest.fixture
def seeded(work_storage: FolderStorage) -> dict[str, Any]:
    return seed_work(work_storage)


@pytest.fixture
def ops(source: FolderReleaseSource, config: McpConfig, work_storage: FolderStorage) -> OpsTools:
    return OpsTools(
        source,
        config,
        store_factory=lambda: WorkStore(work_storage),
        queue_factory=lambda: FolderQueue(work_storage),
        clock=lambda: NOW,
    )


@pytest.fixture
def as_json() -> Callable[[str], dict[str, Any]]:
    def parse(text: str) -> dict[str, Any]:
        data = json.loads(text)
        assert isinstance(data, dict)
        return data

    return parse
