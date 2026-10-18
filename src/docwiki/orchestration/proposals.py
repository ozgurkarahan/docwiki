"""Proposals ``work/proposals/<id>.json`` and the domain overlay ``work/state/overlay.yaml``.

Proposals produced by compilation are filed create-only (a decision taken by the Librarian is
never overwritten). Accepted entity, glossary and topic proposals are merged into the overlay at
the start of the next run; ``work/state/overlay-applied.json`` records which proposals were
merged so that hand edits of the overlay are preserved. Overlay entries that do not apply to the
domain pack (an unknown entity type, an undeclared language...) are left out one by one and
reported; they never stop a run.

Every run also records the base domain pack in ``work/state/domain-pack.json`` so that the MCP
server can refuse decisions that the pipeline could not apply.
"""

from __future__ import annotations

import json
from collections.abc import Iterable

from pydantic import ValidationError

from docwiki.contracts.frontmatter import FrontmatterError, load_yaml_mapping
from docwiki.contracts.layout import StorageKeys, proposal_key
from docwiki.contracts.proposals import Proposal, parse_proposal
from docwiki.contracts.storage import KeyNotFoundError, PreconditionFailedError, Storage
from docwiki.domain.loader import PackError, PackValidationError, errors_from_validation
from docwiki.domain.models import DomainPack
from docwiki.domain.overlay import (
    Overlay,
    add_proposal,
    apply_overlay,
    dump_overlay,
    filter_overlay,
    overlay_size,
)

__all__ = ["APPLIED_KEY", "OverlaySync", "ProposalStore", "pack_snapshot"]

APPLIED_KEY = "work/state/overlay-applied.json"
OVERLAY_KINDS = ("entity", "glossary", "topic")
OVERLAY_FIELDS = {"entity": "entities", "glossary": "glossary", "topic": "topics"}


def pack_snapshot(pack: DomainPack) -> bytes:
    """Bytes of ``work/state/domain-pack.json`` for ``pack`` (JSON, parsed by ``DomainPack``)."""
    return pack.to_json().encode("utf-8")


def _first_error(exc: PackValidationError) -> str:
    return exc.errors[0].message if exc.errors else str(exc)


class OverlaySync:
    """Outcome of :meth:`ProposalStore.sync_overlay` (and :meth:`ProposalStore.domain_pack`).

    ``rejected`` lists, one line each, the accepted proposals that could not be merged and the
    overlay entries that were left out of the pack.
    """

    def __init__(self, overlay: Overlay, applied: list[str], rejected: list[str]) -> None:
        self.overlay = overlay
        self.applied = applied
        self.rejected = rejected


class ProposalStore:
    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    def save_new(self, proposals: Iterable[Proposal]) -> int:
        """File proposals that do not exist yet; returns how many were written."""
        written = 0
        for proposal in proposals:
            try:
                self.storage.write_bytes(
                    proposal_key(proposal.id),
                    proposal.to_json().encode("utf-8"),
                    if_none_match="*",
                )
            except PreconditionFailedError:
                continue
            written += 1
        return written

    def list(self, status: str | None = None) -> list[Proposal]:
        proposals: list[Proposal] = []
        for key in self.storage.list(StorageKeys.PROPOSALS_DIR + "/"):
            if not key.endswith(".json"):
                continue
            try:
                proposal = parse_proposal(self.storage.read_bytes(key))
            except (KeyNotFoundError, ValidationError, ValueError):
                continue
            if status is None or proposal.status == status:
                proposals.append(proposal)
        return sorted(proposals, key=lambda item: item.id)

    def load_overlay(self) -> tuple[Overlay, str | None]:
        try:
            data, etag = self.storage.read_with_etag(StorageKeys.OVERLAY)
        except KeyNotFoundError:
            return Overlay(), None
        try:
            mapping = load_yaml_mapping(data.decode("utf-8"), where="overlay.yaml")
        except FrontmatterError as exc:
            raise PackValidationError([PackError("overlay.yaml", "", str(exc))]) from exc
        try:
            return Overlay.model_validate(mapping), etag
        except ValidationError as exc:
            raise PackValidationError(errors_from_validation("overlay.yaml", exc)) from exc

    def _applied(self) -> tuple[list[str], str | None]:
        try:
            data, etag = self.storage.read_with_etag(APPLIED_KEY)
        except KeyNotFoundError:
            return [], None
        return list(json.loads(data).get("applied", [])), etag

    def sync_overlay(self, base: DomainPack) -> OverlaySync:
        """Merge accepted proposals that are not in the overlay yet; returns the overlay.

        A proposal is merged only when it applies on top of the overlay entries that themselves
        apply to ``base``; entries already in the overlay (for example merged by the MCP
        server's ``decide_proposal`` tool) are validated by :meth:`domain_pack`.
        """
        overlay, overlay_etag = self.load_overlay()
        applied, applied_etag = self._applied()
        done = set(applied)
        pending = [
            proposal
            for proposal in self.list("accepted")
            if proposal.kind in OVERLAY_KINDS and proposal.id not in done
        ]
        pending.sort(key=lambda item: (item.decided_at or item.created_at, item.id))
        usable = filter_overlay(base, overlay)[0] if pending else overlay
        merged: list[str] = []
        present: list[str] = []
        rejected: list[str] = []
        for proposal in pending:
            field = OVERLAY_FIELDS[proposal.kind]
            try:
                items = getattr(add_proposal(Overlay(), proposal), field)
                candidate = add_proposal(usable, proposal)
            except PackValidationError as exc:
                rejected.append(f"proposal {proposal.id} not merged: {_first_error(exc)}")
                continue
            if items and all(item in getattr(overlay, field) for item in items):
                # already merged, e.g. by the MCP server's decide_proposal tool
                present.append(proposal.id)
                continue
            try:
                apply_overlay(base, candidate)
            except PackValidationError as exc:
                rejected.append(f"proposal {proposal.id} not merged: {_first_error(exc)}")
                continue
            overlay = add_proposal(overlay, proposal)
            usable = candidate
            merged.append(proposal.id)
        if merged:
            data = dump_overlay(overlay).encode("utf-8")
            if overlay_etag is None:
                self.storage.write_bytes(StorageKeys.OVERLAY, data, if_none_match="*")
            else:
                self.storage.write_bytes(StorageKeys.OVERLAY, data, if_match=overlay_etag)
        if merged or present:
            done_ids = [*applied, *merged, *present]
            record = (json.dumps({"applied": done_ids}, indent=2) + "\n").encode()
            if applied_etag is None:
                self.storage.write_bytes(APPLIED_KEY, record, if_none_match="*")
            else:
                self.storage.write_bytes(APPLIED_KEY, record, if_match=applied_etag)
        return OverlaySync(overlay, merged, rejected)

    def domain_pack(self, base: DomainPack) -> tuple[DomainPack, OverlaySync]:
        """``base`` with the (synchronised) overlay applied.

        Overlay entries that do not apply to ``base`` are left out one at a time and listed in
        ``sync.rejected``; an invalid entry never makes the run fail.
        """
        sync = self.sync_overlay(base)
        if not overlay_size(sync.overlay):
            return base, sync
        usable, problems = filter_overlay(base, sync.overlay)
        sync.rejected.extend(f"entry left out of the pack: {problem}" for problem in problems)
        if not overlay_size(usable):
            return base, sync
        return apply_overlay(base, usable), sync

    def record_pack(self, base: DomainPack) -> bool:
        """Write ``work/state/domain-pack.json`` when it differs; returns whether it was written."""
        data = pack_snapshot(base)
        try:
            if self.storage.read_bytes(StorageKeys.DOMAIN_PACK) == data:
                return False
        except KeyNotFoundError:
            pass
        self.storage.write_bytes(StorageKeys.DOMAIN_PACK, data)
        return True
