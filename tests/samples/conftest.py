"""Shared fixtures for the sample corpus, domain pack and golden set tests."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from samples.generators.textdump import Extracted, extract  # noqa: E402

CORPUS_ROOT = REPO_ROOT / "samples" / "corpus"
_CACHE: dict[str, Extracted] = {}


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def corpus_root() -> Path:
    return CORPUS_ROOT


@pytest.fixture(scope="session")
def manifest() -> dict[str, Any]:
    return json.loads((CORPUS_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def bible() -> dict[str, Any]:
    return yaml.safe_load((REPO_ROOT / "samples/fiction/bible.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def documents(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Manifest entries of the generated documents (quickstart copies excluded)."""
    return [entry for entry in manifest["files"] if entry["copy_of"] is None]


@pytest.fixture(scope="session")
def extracted() -> Callable[[str], Extracted]:
    """Cached text extraction of a corpus file given its path relative to samples/corpus."""

    def get(rel_path: str) -> Extracted:
        if rel_path not in _CACHE:
            _CACHE[rel_path] = extract(CORPUS_ROOT / rel_path)
        return _CACHE[rel_path]

    return get
