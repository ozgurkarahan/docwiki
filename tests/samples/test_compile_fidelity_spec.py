"""The compile-fidelity spec expects only what the public corpus prints."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from evals.compile_fidelity import load_spec, value_found
from evals.textnorm import Values, extract_values, normalize_text
from samples.generators.textdump import Extracted

SPEC = Path(__file__).resolve().parents[2] / "evals" / "golden" / "compile-fidelity.yaml"


@pytest.fixture(scope="module")
def public_text(
    documents: list[dict[str, Any]], extracted: Callable[[str], Extracted]
) -> list[tuple[str, Values]]:
    texts = []
    for entry in documents:
        path = str(entry["path"])
        if not path.startswith("full/") or entry.get("sensitivity", "public") != "public":
            continue
        norm = normalize_text(extracted(path).text())
        texts.append((norm, extract_values(norm)))
    assert texts
    return texts


def _printed(value: str, texts: list[tuple[str, Values]]) -> bool:
    return any(value_found(value, norm, values) for norm, values in texts)


def test_every_expected_value_is_printed_in_a_public_document(
    public_text: list[tuple[str, Values]],
) -> None:
    spec = load_spec(SPEC)
    missing = [
        f"{item['id']}: {value}"
        for kind in ("facts", "cross")
        for item in spec[kind]
        if not item.get("ocr")
        for value in item["values"]
        if not _printed(str(value), public_text)
    ]
    assert not missing, "not printed in any public document: " + "; ".join(missing)


def test_abstain_terms_exist_elsewhere_in_the_corpus(public_text: list[tuple[str, Values]]) -> None:
    spec = load_spec(SPEC)
    for item in spec["scope_absent"]:
        for term in item["terms"]:
            assert _printed(str(term), public_text), f"{item['id']}: {term} never printed"


def test_revision_sources_exist(corpus_root: Path) -> None:
    for item in load_spec(SPEC)["revisions"]:
        for key in ("source_path", "superseded_by"):
            if item.get(key):
                assert (corpus_root / "full" / item[key]).is_file(), f"{item['id']}: {item[key]}"
