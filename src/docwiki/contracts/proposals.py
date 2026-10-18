"""Proposals ``work/proposals/<id>.json`` (pipeline §5): suggested changes awaiting a decision."""

# Pydantic copies mutable defaults per instance, so `= []` / `= {}` field defaults are safe.
# ruff: noqa: RUF012

from __future__ import annotations

from typing import Annotated, Any, Literal, Self

from pydantic import Field, TypeAdapter, model_validator

from docwiki.contracts._base import ContractModel, Kebab, LangCode, NonEmptyStr, UtcDateTime
from docwiki.contracts.ids import PROPOSAL_ID_RE, SOURCE_ID_RE, proposal_id_for

__all__ = [
    "EntityProposal",
    "EntityProposalPayload",
    "GlossaryProposal",
    "GlossaryProposalPayload",
    "InjectionProposal",
    "InjectionProposalPayload",
    "Proposal",
    "ProposalAlias",
    "ProposalEvidence",
    "RecompileProposal",
    "RecompileProposalPayload",
    "TopicProposal",
    "TopicProposalPayload",
    "new_proposal",
    "parse_proposal",
]

SourceId = Annotated[str, Field(pattern=SOURCE_ID_RE.pattern)]
Scalar = str | int | float | bool | None


class ProposalEvidence(ContractModel):
    source_id: SourceId
    block_id: Annotated[str, Field(pattern=r"^b\d{4,}$")]


class ProposalAlias(ContractModel):
    text: NonEmptyStr
    lang: LangCode


class EntityProposalPayload(ContractModel):
    type: Kebab
    key: Kebab
    label: NonEmptyStr
    aliases: list[ProposalAlias] = []
    attributes: dict[str, Scalar] = {}


class GlossaryProposalPayload(ContractModel):
    term: NonEmptyStr
    definition: NonEmptyStr
    synonyms: dict[str, list[str]] = {}
    see_also: list[str] = []


class TopicProposalPayload(ContractModel):
    slug: Kebab
    title: NonEmptyStr
    description: str = ""
    keywords: list[str] = []
    aliases: list[ProposalAlias] = []


class InjectionProposalPayload(ContractModel):
    source_id: SourceId
    block_id: Annotated[str, Field(pattern=r"^b\d{4,}$")]
    reason: NonEmptyStr
    excerpt: str | None = None


class RecompileProposalPayload(ContractModel):
    source_ids: Annotated[list[SourceId], Field(min_length=1)]
    hints: str = ""


class _ProposalBase(ContractModel):
    id: Annotated[str, Field(pattern=PROPOSAL_ID_RE.pattern)]
    kind: str
    payload: Any
    evidence: list[ProposalEvidence] = []
    created_at: UtcDateTime
    status: Literal["open", "accepted", "rejected"] = "open"
    decided_by: str | None = None
    decided_at: UtcDateTime | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _decision(self) -> Self:
        decided = self.status != "open"
        if decided and not self.decided_by:
            raise ValueError("accepted/rejected proposals need decided_by")
        if not decided and (self.decided_by or self.decided_at):
            raise ValueError("open proposals cannot have a decision")
        return self


class EntityProposal(_ProposalBase):
    kind: Literal["entity"] = "entity"
    payload: EntityProposalPayload


class GlossaryProposal(_ProposalBase):
    kind: Literal["glossary"] = "glossary"
    payload: GlossaryProposalPayload


class TopicProposal(_ProposalBase):
    kind: Literal["topic"] = "topic"
    payload: TopicProposalPayload


class InjectionProposal(_ProposalBase):
    kind: Literal["injection"] = "injection"
    payload: InjectionProposalPayload


class RecompileProposal(_ProposalBase):
    kind: Literal["recompile"] = "recompile"
    payload: RecompileProposalPayload


Proposal = Annotated[
    EntityProposal | GlossaryProposal | TopicProposal | InjectionProposal | RecompileProposal,
    Field(discriminator="kind"),
]
PROPOSAL_ADAPTER: TypeAdapter[Any] = TypeAdapter(Proposal)

_KIND_TO_MODEL: dict[str, type[_ProposalBase]] = {
    "entity": EntityProposal,
    "glossary": GlossaryProposal,
    "topic": TopicProposal,
    "injection": InjectionProposal,
    "recompile": RecompileProposal,
}


def parse_proposal(data: str | bytes | dict[str, Any]) -> Proposal:
    """Validate a proposal from JSON text or a dict."""
    if isinstance(data, str | bytes):
        return PROPOSAL_ADAPTER.validate_json(data)
    return PROPOSAL_ADAPTER.validate_python(data)


def new_proposal(
    kind: str,
    payload: ContractModel,
    *,
    created_at: Any,
    evidence: list[ProposalEvidence] | None = None,
) -> Proposal:
    """Open proposal with a deterministic id derived from ``(kind, payload)``."""
    model = _KIND_TO_MODEL[kind]
    payload_json = payload.to_json_dict()
    return model(
        id=proposal_id_for(kind, payload_json),
        payload=payload,
        evidence=evidence or [],
        created_at=created_at,
    )
