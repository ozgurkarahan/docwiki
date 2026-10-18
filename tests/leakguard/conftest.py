from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOL_DIR = Path(__file__).resolve().parents[2] / "tools" / "leakguard"
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))


@pytest.fixture(autouse=True)
def _isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never inherit a real deny-list or CI redaction from the developer's environment."""
    monkeypatch.delenv("DOCWIKI_DENYLIST", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("LEAKGUARD_DEBUG", "1")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    from leakguard_fixtures import git

    path = tmp_path / "repo"
    path.mkdir()
    git(path, "init", "-q")
    return path


@pytest.fixture
def denylist(tmp_path: Path) -> Path:
    path = tmp_path / "private-denylist.txt"
    path.write_text("# fake private deny-list used by the tests\nzorblax[- ]?corp\n", "utf-8")
    return path
