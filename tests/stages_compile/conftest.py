"""Fixtures of the compile-lane tests (no network: FakeLlmClient only)."""

from __future__ import annotations

import pytest
from compile_testkit import FIXED_NOW, load_test_pack

from docwiki.domain import DomainPack
from docwiki.stages import compile as compile_stage


@pytest.fixture(scope="session")
def pack() -> DomainPack:
    return load_test_pack()


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(compile_stage, "_now", lambda: FIXED_NOW)
