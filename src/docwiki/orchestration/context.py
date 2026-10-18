"""Wiring of a run: storage, queue, LLM client, engine and domain pack from settings."""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator, Callable
from pathlib import Path

from docwiki.contracts.storage import Storage
from docwiki.llm.client import LlmClient
from docwiki.orchestration.pipeline import RunContext
from docwiki.orchestration.registry import Engine, active_engine
from docwiki.orchestration.settings import EngineSettings, resolve_pack_path
from docwiki.stages.verify import load_canaries
from docwiki.storage.factory import storage_from_settings
from docwiki.storage.queue import StorageQueue, WorkQueue
from docwiki.storage.routed import DirectorySource, RoutedStorage

__all__ = ["open_queue", "open_run_context", "open_storage", "scratch_dir"]


def open_storage(settings: EngineSettings) -> Storage:
    """Blob Storage in azure mode; the work folder (raw from ``input_dir``) in local mode."""
    base = storage_from_settings(settings=settings)
    if settings.mode != "azure" and settings.input_dir is not None:
        return RoutedStorage(base, {"raw": DirectorySource(settings.input_dir)})
    return base


def open_queue(settings: EngineSettings, storage: Storage) -> WorkQueue:
    """Azure Storage Queue in azure mode, ``work/queue/`` of the storage in local mode."""
    if settings.mode == "azure":
        from docwiki.storage.queue import AzureStorageQueue

        return AzureStorageQueue(
            settings.queue_account_url, settings.queue_name, settings.poison_queue_name
        )
    return StorageQueue(storage)


def scratch_dir(settings: EngineSettings) -> Path:
    """Local scratch folder (staging releases, downloaded raw files)."""
    return settings.work_dir / ".scratch"


@contextlib.asynccontextmanager
async def open_run_context(
    settings: EngineSettings,
    *,
    lease_ok: Callable[[], bool] = lambda: True,
    storage: Storage | None = None,
    llm: LlmClient | None = None,
    engine: Engine | None = None,
    pack_path: Path | None = None,
    templates_dir: Path | None = None,
) -> AsyncIterator[RunContext]:
    """A :class:`RunContext`; an LLM client created here is closed afterwards."""
    pack = pack_path or resolve_pack_path(settings.domain)
    canaries = tuple(dict.fromkeys([*settings.canaries, *load_canaries(pack, env={})]))
    engine = engine or active_engine()
    storage = storage or open_storage(settings)
    owned = llm is None
    if llm is None:
        from docwiki.llm.factory import create_llm_client

        llm = create_llm_client()
    try:
        yield RunContext(
            storage=storage,
            llm=llm,
            engine=engine,
            settings=settings,
            pack_path=pack,
            scratch_dir=scratch_dir(settings),
            canaries=canaries,
            lease_ok=lease_ok,
            templates_dir=templates_dir,
        )
    finally:
        if owned:
            await llm.aclose()
