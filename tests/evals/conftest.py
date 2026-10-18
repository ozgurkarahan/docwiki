"""Fixtures of the evaluation tests: no network, no Azure, no real model."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals.corpus import CorpusContext  # noqa: E402
from evals_testkit import mini_corpus  # noqa: E402


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def corpus() -> CorpusContext:
    """A small synthetic corpus covering every locator kind of the golden set."""
    return mini_corpus()
