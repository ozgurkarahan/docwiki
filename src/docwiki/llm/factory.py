"""Build the LLM client selected by the settings (``DOCWIKI_LLM_MODE``)."""

from __future__ import annotations

from docwiki.llm.client import LlmClient
from docwiki.llm.foundry import FoundryLlmClient
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
