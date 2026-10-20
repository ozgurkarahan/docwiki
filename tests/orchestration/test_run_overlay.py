"""Accepted proposals that the domain pack cannot apply never stop a run."""

from __future__ import annotations

from datetime import UTC, datetime

from docwiki.contracts.layout import StorageKeys, proposal_key
from docwiki.contracts.proposals import (
    EntityProposalPayload,
    GlossaryProposalPayload,
    new_proposal,
)
from docwiki.domain.models import DomainPack
from docwiki.domain.overlay import Overlay, add_proposal, dump_overlay
from docwiki.release.validate import validate_release

CREATED = datetime(2026, 2, 1, tzinfo=UTC)
DECIDED = {
    "status": "accepted",
    "decided_by": "librarian",
    "decided_at": datetime(2026, 2, 2, tzinfo=UTC),
}


async def test_invalid_overlay_entries_are_left_out_and_never_stop_a_run(harness):
    untyped = new_proposal(
        "entity",
        EntityProposalPayload(type="unknown", key="concrete-plant", label="Concrete plant"),
        created_at=CREATED,
    ).model_copy(update=DECIDED)
    glossary = new_proposal(
        "glossary",
        GlossaryProposalPayload(term="HT", definition="Price excluding VAT."),
        created_at=CREATED,
    ).model_copy(update=DECIDED)
    for proposal in (untyped, glossary):
        harness.storage.write_bytes(proposal_key(proposal.id), proposal.to_json().encode("utf-8"))
    # what decide_proposal wrote before it validated decisions against the pack
    harness.storage.write_bytes(
        StorageKeys.OVERLAY, dump_overlay(add_proposal(Overlay(), untyped)).encode("utf-8")
    )

    outcome = await harness.run()
    assert outcome.status == "succeeded", outcome.errors
    warnings = outcome.report.warnings
    assert any("unknown:concrete-plant" in w and "unknown entity type" in w for w in warnings)
    root = harness.current_release()
    assert "## HT" in (root / "wiki" / "glossary.md").read_text(encoding="utf-8")
    assert validate_release(root, canaries=[], glossary_seeded=True) == []
    recorded = DomainPack.from_json(harness.storage.read_bytes(StorageKeys.DOMAIN_PACK))
    assert recorded.name == "test-batiment" and not recorded.overlay_applied

    second = await harness.run()
    assert second.status == "no-op"


async def test_unconvertible_accepted_proposals_are_reported_not_raised(harness):
    bad = new_proposal(
        "glossary",
        GlossaryProposalPayload(term="Dalle", definition="Slab.", synonyms={"x y": ["?"]}),
        created_at=CREATED,
    ).model_copy(update=DECIDED)
    harness.storage.write_bytes(proposal_key(bad.id), bad.to_json().encode("utf-8"))
    outcome = await harness.run()
    assert outcome.status == "succeeded", outcome.errors
    assert any(bad.id in warning for warning in outcome.report.warnings)
