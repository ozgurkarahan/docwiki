"""Fixtures for the docwiki.evidence tests (reuses the synthetic documents of tests/extract)."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

EXTRACT_TESTS = Path(__file__).resolve().parents[1] / "extract"
if str(EXTRACT_TESTS) not in sys.path:
    sys.path.insert(0, str(EXTRACT_TESTS))

from extract_fixtures import Corpus, build_corpus  # noqa: E402

from docwiki.contracts import VersionInfo  # noqa: E402
from docwiki.release.writer import ReleaseWriter  # noqa: E402


@pytest.fixture(scope="session")
def corpus(tmp_path_factory: pytest.TempPathFactory) -> Corpus:
    return build_corpus(tmp_path_factory.mktemp("evidence-corpus"))


@pytest.fixture
def writer(tmp_path: Path) -> ReleaseWriter:
    return ReleaseWriter(
        tmp_path / "release",
        created_at=datetime(2026, 2, 15, 9, 0, tzinfo=UTC),
        audience="public",
        versions=VersionInfo(docwiki="0.1.0", domain_pack="wind-ops", domain_pack_hash="test"),
    )
