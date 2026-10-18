"""Orchestration of DocWiki runs: pipeline, workflow, run control, registry and settings.

Typical use::

    settings = EngineSettings.from_env()
    storage = open_storage(settings)
    result = await run_worker(
        lambda lease_ok: open_run_context(settings, lease_ok=lease_ok, storage=storage),
        storage=storage,
        settings=settings,
        queue=open_queue(settings, storage),
    )

Names are imported lazily so that the stage modules can use small helpers of this package
without importing the whole pipeline.
"""

from __future__ import annotations

import importlib
from typing import Any

_EXPORTS = {
    "Engine": "docwiki.orchestration.registry",
    "EngineUnavailableError": "docwiki.orchestration.registry",
    "active_engine": "docwiki.orchestration.registry",
    "load_engine": "docwiki.orchestration.registry",
    "set_engine": "docwiki.orchestration.registry",
    "use_engine": "docwiki.orchestration.registry",
    "EngineSettings": "docwiki.orchestration.settings",
    "load_dotenv": "docwiki.orchestration.settings",
    "Pipeline": "docwiki.orchestration.pipeline",
    "RunContext": "docwiki.orchestration.pipeline",
    "RunOutcome": "docwiki.orchestration.pipeline",
    "RunRequest": "docwiki.orchestration.pipeline",
    "choose_orchestrator": "docwiki.orchestration.workflow",
    "execute_run": "docwiki.orchestration.workflow",
    "WorkerResult": "docwiki.orchestration.runner",
    "run_worker": "docwiki.orchestration.runner",
    "open_queue": "docwiki.orchestration.context",
    "open_run_context": "docwiki.orchestration.context",
    "open_storage": "docwiki.orchestration.context",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    module = _EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module 'docwiki.orchestration' has no attribute {name!r}")
    return getattr(importlib.import_module(module), name)
