"""The registry of systems under test and run labels (evals/registry.py, evals/runner.py)."""

from __future__ import annotations

import pytest
from evals.registry import get_system, register_system, system_names
from evals.runner import _parser, result_name


def test_builtin_systems_are_registered() -> None:
    names = system_names()
    assert {"docwiki-researcher", "baseline-rag", "baseline-long-context"} <= set(names)
    assert get_system("baseline-rag").indexes_documents
    assert not get_system("docwiki-researcher").indexes_documents
    with pytest.raises(ValueError, match="unknown system"):
        get_system("nope")


def test_a_name_cannot_be_taken_twice() -> None:
    def factory(options, corpus):  # pragma: no cover - never built
        raise AssertionError

    register_system("test-registry-only", factory)
    register_system("test-registry-only", factory)  # same factory: idempotent
    with pytest.raises(ValueError, match="already registered"):
        register_system("test-registry-only", lambda options, corpus: None)


def test_run_label_names_repetitions() -> None:
    assert result_name("x", "dev", "2026-11-10", limit=None, complete=True) == (
        "2026-11-10-x-dev.json"
    )
    assert result_name("x", "dev", "2026-11-10", limit=3, complete=False, run_label="r2") == (
        "2026-11-10-x-dev-limit3-r2.json"
    )
    args = _parser().parse_args(
        ["--system", "baseline-rag", "--questions", "q.jsonl", "--run-label", "r1"]
    )
    assert args.run_label == "r1"
