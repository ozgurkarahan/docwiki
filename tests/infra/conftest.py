"""Fixtures for the infrastructure tests (azd hooks, preflight, teardown, Bicep, azure.yaml)."""

from __future__ import annotations

import pytest
from infra_testkit import FakeRunner


@pytest.fixture
def runner() -> FakeRunner:
    return FakeRunner()
