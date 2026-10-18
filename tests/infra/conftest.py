"""Fixtures for the infrastructure tests (azd hooks, preflight, teardown, Bicep, azure.yaml)."""

from __future__ import annotations

import pytest
from infra_testkit import FakeRunner


@pytest.fixture
def runner() -> FakeRunner:
    return FakeRunner()


@pytest.fixture(autouse=True)
def no_graph_token_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """DOCWIKI_GRAPH_TOKEN_SOURCE=azd is the operator's opt-in: a shell that sets it must not
    change what the tests expect, so the tests that need it set it themselves."""
    monkeypatch.delenv("DOCWIKI_GRAPH_TOKEN_SOURCE", raising=False)
