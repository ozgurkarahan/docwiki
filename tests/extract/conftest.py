"""Fixtures for the docwiki.extract tests (synthetic documents generated once per session)."""

from __future__ import annotations

import pytest
from extract_fixtures import Corpus, build_corpus


@pytest.fixture(scope="session")
def corpus(tmp_path_factory: pytest.TempPathFactory) -> Corpus:
    return build_corpus(tmp_path_factory.mktemp("corpus"))
