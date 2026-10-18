"""Orchestrators of a run: Microsoft Agent Framework workflow or plain asyncio.

Both drive the same :class:`~docwiki.orchestration.pipeline.Pipeline` steps:

``prepare`` → fan-out ``extract`` → fan-in → fan-out ``classify`` → fan-in + ``resolve`` →
fan-out ``compile`` → fan-in → ``assemble`` (render … publish).

The Agent Framework workflow (:mod:`docwiki.orchestration.af_workflow`) models each per-source
stage as *N* worker executors (``N`` = the stage's concurrency limit) between fan-out and fan-in
edges. No checkpoint storage is configured: correctness comes from the content-addressed
artifacts, so a crashed run is simply run again. ``DOCWIKI_ORCHESTRATOR=af|async`` selects the
implementation (default ``af`` when ``agent_framework`` is importable).
"""

from __future__ import annotations

import asyncio
import importlib.util
from collections.abc import Awaitable, Callable
from typing import Literal

from docwiki.orchestration.pipeline import Pipeline, RunContext, RunOutcome, RunRequest

__all__ = [
    "PER_SOURCE_STAGES",
    "Orchestrator",
    "af_available",
    "choose_orchestrator",
    "execute_run",
    "run_with_af",
    "run_with_asyncio",
]

PER_SOURCE_STAGES = ("extract", "classify", "compile")
Orchestrator = Callable[[Pipeline], Awaitable[RunOutcome]]


def af_available() -> bool:
    return importlib.util.find_spec("agent_framework") is not None


def _first_error(group: BaseExceptionGroup) -> BaseException:
    for exc in group.exceptions:
        if isinstance(exc, BaseExceptionGroup):
            return _first_error(exc)
        return exc
    return group


async def _fan_out(pipeline: Pipeline, stage: str) -> None:
    ids = pipeline.stage_ids(stage)
    semaphore = asyncio.Semaphore(pipeline.concurrency(stage))

    async def one(source_id: str) -> None:
        async with semaphore:
            await pipeline.run_source_stage(stage, source_id)

    try:
        async with asyncio.TaskGroup() as group:
            for source_id in ids:
                group.create_task(one(source_id))
    except BaseExceptionGroup as exc:
        raise _first_error(exc) from None


async def run_with_asyncio(pipeline: Pipeline) -> RunOutcome:
    """Plain-asyncio orchestrator (bounded fan-out per source with semaphores)."""
    for stage in PER_SOURCE_STAGES:
        pipeline.begin_stage(stage)
        await _fan_out(pipeline, stage)
        pipeline.end_stage(stage)
        if stage == "classify":
            pipeline.resolve()
    return await pipeline.assemble()


async def run_with_af(pipeline: Pipeline) -> RunOutcome:
    """Microsoft Agent Framework workflow orchestrator."""
    from docwiki.orchestration.af_workflow import run_workflow

    return await run_workflow(pipeline)


def choose_orchestrator(name: Literal["af", "async"] | None = None) -> Orchestrator:
    """``af`` (Agent Framework) or ``async``; ``None`` picks ``af`` when it is installed."""
    if name == "async":
        return run_with_asyncio
    if name == "af":
        if not af_available():
            raise RuntimeError("DOCWIKI_ORCHESTRATOR=af but agent-framework-core is not installed")
        return run_with_af
    return run_with_af if af_available() else run_with_asyncio


async def execute_run(
    ctx: RunContext,
    request: RunRequest,
    *,
    run_id: str | None = None,
    orchestrator: Orchestrator | None = None,
) -> RunOutcome:
    """Prepare and run the pipeline; run failures are reported in ``outcome.status``."""
    pipeline = Pipeline(ctx, request, run_id=run_id)
    try:
        await pipeline.prepare()
        if pipeline.no_op:
            return pipeline.finish_no_op()
        runner = orchestrator or choose_orchestrator(ctx.settings.orchestrator)
        return await runner(pipeline)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        return pipeline.fail(exc)
