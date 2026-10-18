from __future__ import annotations

import pytest
from site_testkit import FakeTools

from docwiki.site import build as build_module


@pytest.fixture
def tools(monkeypatch: pytest.MonkeyPatch) -> FakeTools:
    """Fake git/npm/node; every tool is "found" on PATH."""
    monkeypatch.setattr(build_module.shutil, "which", lambda name: name)
    return FakeTools()
