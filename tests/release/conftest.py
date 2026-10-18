import importlib.util
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "samples" / "fixtures" / "mock-release"


def load_builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "docwiki_mock_build_fixture", FIXTURE_ROOT / "build_fixture.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def builder() -> ModuleType:
    return load_builder()


@pytest.fixture
def fixture_copy(tmp_path: Path) -> Path:
    """A writable copy of the committed mock release (machine files included)."""
    target = tmp_path / "mock-release"
    shutil.copytree(FIXTURE_ROOT, target, ignore=shutil.ignore_patterns("__pycache__"))
    return target
