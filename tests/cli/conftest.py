"""Fixtures of the CLI tests: stub engine, fake LLM and a temporary local installation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ORCHESTRATION_TESTS = Path(__file__).resolve().parents[1] / "orchestration"
if str(ORCHESTRATION_TESTS) not in sys.path:
    sys.path.insert(0, str(ORCHESTRATION_TESTS))

from engine_stubs import CANARY, fake_llm, stub_engine, write_corpus  # noqa: E402

from docwiki.orchestration import registry  # noqa: E402

PACK = ORCHESTRATION_TESTS / "fixtures" / "test-pack"


@pytest.fixture
def cli_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Environment of a local installation: work folder, input corpus, stub engine, fake LLM."""
    work = tmp_path / "work"
    corpus = write_corpus(tmp_path / "input")
    for key in list(__import__("os").environ):
        if key.startswith("DOCWIKI_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("DOCWIKI_WORK_DIR", str(work))
    monkeypatch.setenv("DOCWIKI_DOMAIN", str(PACK))
    monkeypatch.setenv("DOCWIKI_AUDIENCE", "internal")
    monkeypatch.setenv("DOCWIKI_CANARIES", CANARY)
    monkeypatch.setenv("DOCWIKI_ORCHESTRATOR", "async")
    monkeypatch.setenv("DOCWIKI_DEBOUNCE_SECONDS", "0")
    monkeypatch.setattr(registry, "_ACTIVE", stub_engine())
    llm = fake_llm()
    import docwiki.llm.factory as factory

    monkeypatch.setattr(factory, "create_llm_client", lambda *args, **kwargs: llm)
    monkeypatch.chdir(tmp_path)
    return {"work": work, "input": corpus, "root": tmp_path}
