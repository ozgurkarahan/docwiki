"""Microsoft Agent Framework workflow of a run (imported only when ``agent_framework`` exists).

Graph: ``dispatch`` → fan-out to the ``extract-<i>`` workers → fan-in ``join-extract`` →
fan-out ``classify-<i>`` → fan-in ``join-classify`` (resolves sensitivity) → fan-out
``compile-<i>`` → fan-in ``assemble`` (render … publish) which yields the run outcome.
Annotations are evaluated eagerly (no ``from __future__ import annotations``) because the
framework routes messages by the handlers' type hints.
"""

from dataclasses import dataclass, field
from typing import Never

from agent_framework import Executor, Workflow, WorkflowBuilder, WorkflowContext, handler

from docwiki.orchestration.pipeline import Pipeline, RunOutcome

__all__ = ["ShardDone", "StageBatch", "build_workflow", "run_workflow"]


@dataclass(frozen=True)
class StageBatch:
    """Broadcast to the workers of one stage; worker ``i`` of ``n`` takes ``ids[i::n]``."""

    stage: str
    ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ShardDone:
    stage: str
    worker: int
    processed: int


class _Dispatch(Executor):
    def __init__(self, pipeline: Pipeline) -> None:
        super().__init__(id="dispatch")
        self._pipeline = pipeline

    @handler
    async def start(self, batch: StageBatch, ctx: WorkflowContext[StageBatch]) -> None:
        self._pipeline.begin_stage(batch.stage)
        ids = tuple(self._pipeline.stage_ids(batch.stage))
        await ctx.send_message(StageBatch(batch.stage, ids))


class _Worker(Executor):
    def __init__(self, pipeline: Pipeline, stage: str, index: int, count: int) -> None:
        super().__init__(id=f"{stage}-{index}")
        self._pipeline = pipeline
        self._stage = stage
        self._index = index
        self._count = count

    @handler
    async def work(self, batch: StageBatch, ctx: WorkflowContext[ShardDone]) -> None:
        mine = batch.ids[self._index :: self._count]
        for source_id in mine:
            await self._pipeline.run_source_stage(self._stage, source_id)
        await ctx.send_message(ShardDone(self._stage, self._index, len(mine)))


class _Join(Executor):
    def __init__(self, pipeline: Pipeline, finished: str, following: str) -> None:
        super().__init__(id=f"join-{finished}")
        self._pipeline = pipeline
        self._finished = finished
        self._following = following

    @handler
    async def join(self, shards: list[ShardDone], ctx: WorkflowContext[StageBatch]) -> None:
        self._pipeline.end_stage(self._finished)
        if self._finished == "classify":
            self._pipeline.resolve()
        self._pipeline.begin_stage(self._following)
        ids = tuple(self._pipeline.stage_ids(self._following))
        await ctx.send_message(StageBatch(self._following, ids))


class _Assemble(Executor):
    def __init__(self, pipeline: Pipeline) -> None:
        super().__init__(id="assemble")
        self._pipeline = pipeline

    @handler
    async def assemble(
        self, shards: list[ShardDone], ctx: WorkflowContext[Never, RunOutcome]
    ) -> None:
        self._pipeline.end_stage("compile")
        await ctx.yield_output(await self._pipeline.assemble())


def build_workflow(pipeline: Pipeline) -> Workflow:
    """Executors and fan-out/fan-in edges; worker counts follow the stage concurrency."""

    def workers(stage: str) -> list[Executor]:
        count = pipeline.concurrency(stage)
        return [_Worker(pipeline, stage, index, count) for index in range(count)]

    dispatch = _Dispatch(pipeline)
    extract, classify, compile_ = workers("extract"), workers("classify"), workers("compile")
    join_extract = _Join(pipeline, "extract", "classify")
    join_classify = _Join(pipeline, "classify", "compile")
    assemble = _Assemble(pipeline)
    return (
        WorkflowBuilder(start_executor=dispatch, name="docwiki-run")
        .add_fan_out_edges(dispatch, extract)
        .add_fan_in_edges(extract, join_extract)
        .add_fan_out_edges(join_extract, classify)
        .add_fan_in_edges(classify, join_classify)
        .add_fan_out_edges(join_classify, compile_)
        .add_fan_in_edges(compile_, assemble)
        .build()
    )


async def run_workflow(pipeline: Pipeline) -> RunOutcome:
    """Run the workflow and return its single output."""
    result = await build_workflow(pipeline).run(StageBatch("extract"))
    outputs = [item for item in result.get_outputs() if isinstance(item, RunOutcome)]
    if len(outputs) != 1:
        raise RuntimeError(f"the workflow produced {len(outputs)} outcomes instead of one")
    return outputs[0]
