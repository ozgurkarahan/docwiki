"""Fixtures of the orchestration tests: stub engine, fake LLM, synthetic corpus, local harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from engine_stubs import CANARY, fake_llm, stub_engine, write_corpus

from docwiki.contracts.storage import Storage
from docwiki.llm import FakeLlmClient
from docwiki.orchestration.context import open_run_context, open_storage
from docwiki.orchestration.pipeline import RunOutcome, RunRequest
from docwiki.orchestration.registry import Engine
from docwiki.orchestration.runner import WorkerResult, run_worker
from docwiki.orchestration.settings import EngineSettings
from docwiki.release.publish import read_current_pointer
from docwiki.storage.queue import WorkQueue

PACK = Path(__file__).resolve().parent / "fixtures" / "test-pack"


@dataclass
class Harness:
    """A local DocWiki installation in a temporary folder, driven like the CLI."""

    settings: EngineSettings
    llm: FakeLlmClient
    engine: Engine
    storage: Storage = field(init=False)
    pack: Path = PACK

    def __post_init__(self) -> None:
        self.storage = open_storage(self.settings)

    def context(self, lease_ok: Any) -> Any:
        return open_run_context(
            self.settings,
            lease_ok=lease_ok,
            storage=self.storage,
            llm=self.llm,
            engine=self.engine,
            pack_path=self.pack,
        )

    async def worker(
        self,
        *,
        queue: WorkQueue | None = None,
        request: RunRequest | None = None,
        **kwargs: Any,
    ) -> WorkerResult:
        return await run_worker(
            self.context,
            storage=self.storage,
            settings=self.settings,
            queue=queue,
            base_request=request,
            **kwargs,
        )

    async def run(self, **request: Any) -> RunOutcome:
        result = await self.worker(request=RunRequest(**request), max_cycles=1)
        assert result.status != "lease-held"
        assert len(result.outcomes) == 1, result.errors
        return result.outcomes[0]

    def current_release(self) -> Path:
        pointer = read_current_pointer(self.storage)
        assert pointer is not None, "no release was published"
        return self.settings.work_dir / "releases" / pointer[0].release_id


@pytest.fixture
def pack_dir() -> Path:
    return PACK


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    return write_corpus(tmp_path / "input")


def make_settings(tmp_path: Path, corpus: Path, **overrides: Any) -> EngineSettings:
    values: dict[str, Any] = {
        "mode": "local",
        "work_dir": tmp_path / "work",
        "input_dir": corpus,
        "domain": str(PACK),
        "audience": "internal",
        "debounce_s": 0.0,
        "lease_s": 15.0,
        "canaries": (CANARY,),
        "orchestrator": "async",
        "extract_concurrency": 2,
        "llm_concurrency": 2,
        "visibility_timeout_s": 30,
    }
    values.update(overrides)
    return EngineSettings(**values)


@pytest.fixture
def harness(tmp_path: Path, corpus: Path) -> Harness:
    return Harness(make_settings(tmp_path, corpus), fake_llm(), stub_engine())


@pytest.fixture
def make_harness(tmp_path: Path, corpus: Path) -> Any:
    def factory(**overrides: Any) -> Harness:
        llm = overrides.pop("llm", None) or fake_llm()
        engine = overrides.pop("engine", None) or stub_engine()
        pack = overrides.pop("pack", None) or PACK
        return Harness(make_settings(tmp_path, corpus, **overrides), llm, engine, pack)

    return factory
