"""Typed access to ``work/`` (architecture §3) for the operations tools.

Reads state shards, run reports, proposals, extraction artifacts, the domain overlay and the
domain pack recorded by the pipeline; writes proposal decisions and the overlay with ETag
conditions, and health reports. Never touches ``raw/`` or ``releases/``.
"""

from __future__ import annotations

from pydantic import ValidationError

from docwiki.contracts.frontmatter import FrontmatterError, load_yaml_mapping
from docwiki.contracts.ids import PROPOSAL_ID_RE, RUN_ID_RE, SOURCE_ID_RE
from docwiki.contracts.layout import (
    StorageKeys,
    health_report_key,
    proposal_key,
    run_report_key,
    source_state_key,
)
from docwiki.contracts.proposals import Proposal, parse_proposal
from docwiki.contracts.runs import RunReport
from docwiki.contracts.state import SourceState
from docwiki.contracts.storage import KeyNotFoundError, Storage
from docwiki.domain.models import DomainPack
from docwiki.domain.overlay import Overlay, dump_overlay

__all__ = ["WorkStore"]


class WorkStore:
    """``work/`` container (or folder) seen by the MCP server."""

    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    def _read(self, key: str) -> bytes | None:
        try:
            return self.storage.read_bytes(key)
        except KeyNotFoundError:
            return None

    # --- source state -------------------------------------------------------------------

    def source_states(self) -> tuple[list[SourceState], list[str]]:
        """All state shards and the keys that failed to parse."""
        states: list[SourceState] = []
        broken: list[str] = []
        for key in self.storage.list(StorageKeys.SOURCE_STATE_DIR + "/"):
            if not key.endswith(".json"):
                continue
            data = self._read(key)
            if data is None:
                continue
            try:
                states.append(SourceState.from_json(data))
            except (ValidationError, ValueError):
                broken.append(key)
        return states, broken

    def source_state(self, source_id: str) -> SourceState | None:
        data = self._read(source_state_key(source_id))
        return SourceState.from_json(data) if data is not None else None

    # --- runs ------------------------------------------------------------------------------

    def run_ids(self) -> list[str]:
        prefix = StorageKeys.RUNS_DIR + "/"
        ids = {
            key[len(prefix) :].split("/", 1)[0]
            for key in self.storage.list(prefix)
            if key.endswith("/report.json")
        }
        return sorted(run_id for run_id in ids if RUN_ID_RE.match(run_id))

    def run_report(self, run_id: str) -> RunReport | None:
        if not RUN_ID_RE.match(run_id):
            raise ValueError(f"invalid run id: {run_id!r}")
        data = self._read(run_report_key(run_id))
        return RunReport.from_json(data) if data is not None else None

    # --- proposals -------------------------------------------------------------------------

    def proposals(self) -> tuple[list[Proposal], list[str]]:
        found: list[Proposal] = []
        broken: list[str] = []
        for key in self.storage.list(StorageKeys.PROPOSALS_DIR + "/"):
            if not key.endswith(".json"):
                continue
            data = self._read(key)
            if data is None:
                continue
            try:
                found.append(parse_proposal(data))
            except (ValidationError, ValueError):
                broken.append(key)
        return found, broken

    def proposal(self, proposal_id: str) -> tuple[Proposal, str] | None:
        if not PROPOSAL_ID_RE.match(proposal_id):
            raise ValueError(f"invalid proposal id: {proposal_id!r}")
        try:
            data, etag = self.storage.read_with_etag(proposal_key(proposal_id))
        except KeyNotFoundError:
            return None
        return parse_proposal(data), etag

    def save_proposal(self, proposal: Proposal, *, if_match: str) -> str:
        return self.storage.write_bytes(
            proposal_key(proposal.id), proposal.to_json().encode("utf-8"), if_match=if_match
        )

    # --- overlay -----------------------------------------------------------------------------

    def overlay(self) -> tuple[Overlay, str | None]:
        try:
            data, etag = self.storage.read_with_etag(StorageKeys.OVERLAY)
        except KeyNotFoundError:
            return Overlay(), None
        text = data.decode("utf-8")
        if not text.strip():
            return Overlay(), etag
        try:
            return Overlay.model_validate(load_yaml_mapping(text, where="overlay.yaml")), etag
        except (FrontmatterError, ValidationError) as exc:
            raise ValueError(f"work/state/overlay.yaml is invalid: {exc}") from exc

    def save_overlay(self, overlay: Overlay, *, etag: str | None) -> str:
        data = dump_overlay(overlay).encode("utf-8")
        if etag is None:
            return self.storage.write_bytes(StorageKeys.OVERLAY, data, if_none_match="*")
        return self.storage.write_bytes(StorageKeys.OVERLAY, data, if_match=etag)

    def domain_pack(self) -> DomainPack | None:
        """The base domain pack recorded by the last ingest run (``None`` before the first)."""
        data = self._read(StorageKeys.DOMAIN_PACK)
        if data is None:
            return None
        try:
            return DomainPack.from_json(data)
        except ValidationError as exc:
            raise ValueError(f"{StorageKeys.DOMAIN_PACK} is invalid: {exc}") from exc

    # --- artifacts and reports -----------------------------------------------------------

    def artifact_files(self, stage: str, cache_key: str) -> list[tuple[str, bytes]]:
        """JSON files stored under ``work/artifacts/<stage>/<cache_key>/`` as raw bytes."""
        prefix = f"{StorageKeys.ARTIFACTS_DIR}/{stage}/{cache_key}/"
        documents: list[tuple[str, bytes]] = []
        for key in self.storage.list(prefix):
            if not key.endswith(".json"):
                continue
            data = self._read(key)
            if data is not None:
                documents.append((key, data))
        return documents

    def write_health_report(self, day: str, text: str) -> tuple[str, bool]:
        """Write ``work/reports/health-<day>.md``; returns ``(key, replaced)``."""
        key = health_report_key(day)
        replaced = self.storage.exists(key)
        self.storage.write_bytes(key, text.encode("utf-8"))
        return key, replaced

    @staticmethod
    def check_source_id(source_id: str) -> str:
        if not SOURCE_ID_RE.match(source_id):
            raise ValueError(f"invalid source_id {source_id!r} (expected src- and 12 hex digits)")
        return source_id
