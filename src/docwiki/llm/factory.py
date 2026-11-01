"""Build the LLM and embedding clients selected by the settings (``DOCWIKI_LLM_MODE``)."""

from __future__ import annotations

from docwiki.llm.client import LlmClient
from docwiki.llm.embeddings import EmbeddingClient, RecordingEmbeddingClient, ReplayEmbeddingClient
from docwiki.llm.foundry import FoundryLlmClient
from docwiki.llm.foundry_embeddings import FoundryEmbeddingClient
from docwiki.llm.ledger import UsageLedger
from docwiki.llm.prices import PriceTable
from docwiki.llm.recording import RecordingLlmClient, ReplayLlmClient
from docwiki.llm.settings import LlmSettings


def create_llm_client(
    settings: LlmSettings | None = None, *, ledger: UsageLedger | None = None
) -> LlmClient:
    """``foundry`` (default): live calls; ``replay``: fixtures only; ``record``: live + fixtures.

    The ledger (created from the configured price table when omitted) receives every call, so
    ``ledger.receipt()`` gives the run's cost receipt whatever the mode.
    """
    settings = settings if settings is not None else LlmSettings.from_env()
    if ledger is None:
        ledger = UsageLedger(PriceTable.load(settings.price_table))
    if settings.mode == "replay":
        return ReplayLlmClient(settings.require_fixtures_dir(), ledger=ledger)
    if settings.mode == "record":
        fixtures_dir = settings.require_fixtures_dir()
        return RecordingLlmClient(FoundryLlmClient(settings, ledger=ledger), fixtures_dir)
    return FoundryLlmClient(settings, ledger=ledger)


def create_embedding_client(
    settings: LlmSettings | None = None, *, ledger: UsageLedger | None = None
) -> EmbeddingClient:
    """Same modes as :func:`create_llm_client`; fixtures live under ``embed-<purpose>/``.

    Replay cuts batches with ``DOCWIKI_EMBED_BATCH_SIZE`` and ``DOCWIKI_EMBED_DIMENSIONS``, so
    they must match the values used when recording.
    """
    settings = settings if settings is not None else LlmSettings.from_env()
    if ledger is None:
        ledger = UsageLedger(PriceTable.load(settings.price_table))
    if settings.mode == "replay":
        return ReplayEmbeddingClient(
            settings.require_fixtures_dir(),
            dimensions=settings.embed_dimensions,
            batch_size=settings.embed_batch_size,
            ledger=ledger,
        )
    if settings.mode == "record":
        fixtures_dir = settings.require_fixtures_dir()
        live = FoundryEmbeddingClient(settings, ledger=ledger)
        return RecordingEmbeddingClient(live, fixtures_dir)
    return FoundryEmbeddingClient(settings, ledger=ledger)