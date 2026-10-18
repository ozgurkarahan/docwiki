"""Build the Studio from the environment: storage, Azure listings and the agent client."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from typing import Any

from starlette.applications import Starlette

from docwiki.orchestration.context import open_storage
from docwiki.orchestration.settings import EngineSettings
from docwiki.studio.app import create_app
from docwiki.studio.config import StudioConfig
from docwiki.studio.jobs import AgentJobs
from docwiki.studio.service import QueueDepth, RawBlob, RawLister, StudioService

__all__ = [
    "QUEUE_PEEK_LIMIT",
    "azure_queue_depth",
    "azure_raw_lister",
    "build_app",
    "build_parts",
    "check",
]

QUEUE_PEEK_LIMIT = 32
"""Storage queues peek at most 32 messages: the dashboard shows "32+" beyond that."""


def azure_raw_lister(account_url: str, container: str, credential: Any) -> RawLister:
    """``raw/`` with sizes and modification times (``Storage.list`` only returns names)."""
    from azure.storage.blob import ContainerClient

    client = ContainerClient(account_url, container, credential=credential)

    def list_raw() -> list[RawBlob]:
        return [
            RawBlob(
                path=str(item.name),
                size=int(item.size) if item.size is not None else None,
                modified=item.last_modified,
            )
            for item in client.list_blobs()
            if not str(item.name).endswith("/")
        ]

    return list_raw


def azure_queue_depth(account_url: str, queue_name: str, credential: Any) -> QueueDepth:
    """Messages waiting in the ingest queue (peek: needs only Storage Queue Data Reader)."""
    from azure.storage.queue import QueueClient

    client = QueueClient(account_url, queue_name, credential=credential)

    def depth() -> int:
        return len(list(client.peek_messages(max_messages=QUEUE_PEEK_LIMIT)))

    return depth


def build_parts(
    env: Mapping[str, str] | None = None, *, local: bool = False
) -> tuple[StudioService, AgentJobs | None, StudioConfig]:
    """Service, agent jobs and settings for the current environment (``DOCWIKI_MODE=azure``
    uses Blob Storage and the managed identity, or your ``az login`` when run locally)."""
    values = dict(os.environ if env is None else env)
    config = StudioConfig.from_env(values, local=local)
    settings = EngineSettings.from_env(values)
    storage = open_storage(settings)
    list_raw: RawLister | None = None
    queue_depth: QueueDepth | None = None
    if settings.mode == "azure":
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()
        list_raw = azure_raw_lister(settings.blob_account_url, settings.raw_container, credential)
        queue_depth = azure_queue_depth(settings.queue_account_url, settings.queue_name, credential)
    service = StudioService(storage, config, list_raw=list_raw, queue_depth=queue_depth)
    jobs: AgentJobs | None = None
    if config.agents_enabled:
        from docwiki.agents_client.client import AgentClient

        jobs = AgentJobs(
            AgentClient,
            daily_questions=config.daily_questions,
            approval_timeout_s=config.approval_timeout_s,
            question_timeout_s=config.question_timeout_s,
        )
    return service, jobs, config


def build_app(env: Mapping[str, str] | None = None, *, local: bool = False) -> Starlette:
    """The Studio ASGI app for the current environment."""
    service, jobs, config = build_parts(env, local=local)
    return create_app(service, jobs, config)


def check(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Storage and agent access with this process' identity (``python -m docwiki.studio
    --check``, for example through ``az containerapp exec``): no sign-in, nothing written."""
    service, jobs, _config = build_parts(env)

    async def agents_ok() -> bool | None:
        if jobs is None:
            return None
        try:
            return await jobs.healthy()
        finally:
            await jobs.aclose()

    storage = service.storage_ok()
    agents = asyncio.run(agents_ok())
    queue = service.pipeline()["queued"]
    return {
        "storage": storage,
        "agents": agents,
        "queue_readable": queue is not None,
        "ok": storage and agents is not False,
    }
