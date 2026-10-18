"""JSON codecs of the engine types stored in artifacts (extract, classify, compile, pages)."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from pydantic import TypeAdapter

from docwiki.contracts._base import canonical_json, sha256_hex
from docwiki.contracts.compiled import CompiledSource
from docwiki.contracts.extracted import ExtractedDoc
from docwiki.contracts.locators import Locator
from docwiki.contracts.pages import Page
from docwiki.contracts.proposals import parse_proposal
from docwiki.engine_types import (
    CitedLocator,
    Classification,
    CompiledResult,
    ExtractResult,
    TopicSkip,
    VerifiedCitation,
)

__all__ = [
    "content_digest",
    "decode_cited",
    "decode_classification",
    "decode_compiled_result",
    "decode_extract_result",
    "decode_pages",
    "decode_topic_skips",
    "encode_cited",
    "encode_classification",
    "encode_compiled_result",
    "encode_extract_result",
    "encode_pages",
    "encode_topic_skips",
    "json_bytes",
]

_LOCATOR: TypeAdapter[Any] = TypeAdapter(Locator)


def json_bytes(value: Any) -> bytes:
    """Deterministic pretty JSON bytes (sorted keys, LF, trailing newline)."""
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _locator_json(locator: Any) -> Any:
    return None if locator is None else _LOCATOR.dump_python(locator, mode="json")


def _locator(value: Any) -> Any:
    return None if value is None else _LOCATOR.validate_python(value)


# -- extract -------------------------------------------------------------------------------


def encode_extract_result(result: ExtractResult) -> dict[str, bytes]:
    files: dict[str, bytes] = {
        "doc.json": result.doc.to_json().encode("utf-8"),
        "warnings.json": json_bytes(list(result.warnings)),
    }
    for figure_id, data in sorted(result.figures.items()):
        files[f"figures/{figure_id}.png"] = bytes(data)
    for page, data in sorted(result.page_images.items()):
        files[f"pages/{int(page):04d}.png"] = bytes(data)
    return files


def decode_extract_result(files: Mapping[str, bytes]) -> ExtractResult:
    doc = ExtractedDoc.from_json(files["doc.json"])
    figures = {
        name.removeprefix("figures/").removesuffix(".png"): data
        for name, data in files.items()
        if name.startswith("figures/") and name.endswith(".png")
    }
    pages = {
        int(name.removeprefix("pages/").removesuffix(".png")): data
        for name, data in files.items()
        if name.startswith("pages/") and name.endswith(".png")
    }
    warnings = json.loads(files["warnings.json"]) if "warnings.json" in files else []
    return ExtractResult(doc=doc, figures=figures, page_images=pages, warnings=list(warnings))


# -- classify ------------------------------------------------------------------------------


def encode_classification(classification: Classification) -> bytes:
    return json_bytes(classification.model_dump(mode="json"))


def decode_classification(data: bytes) -> Classification:
    return Classification.model_validate(json.loads(data))


# -- compile -------------------------------------------------------------------------------


def _citation_json(citation: VerifiedCitation) -> dict[str, Any]:
    return {
        "ref": citation.ref,
        "source_id": citation.source_id,
        "block_ids": list(citation.block_ids),
        "quote": citation.quote,
        "status": citation.status,
        "provenance": citation.provenance,
        "locator": _locator_json(citation.locator),
        "reason": citation.reason,
    }


def _citation(value: Mapping[str, Any]) -> VerifiedCitation:
    return VerifiedCitation(
        ref=str(value["ref"]),
        source_id=str(value["source_id"]),
        block_ids=tuple(value.get("block_ids", ())),
        quote=value.get("quote"),
        status=value["status"],
        provenance=value["provenance"],
        locator=_locator(value.get("locator")),
        reason=value.get("reason"),
    )


def encode_compiled_result(result: CompiledResult) -> bytes:
    return json_bytes(
        {
            "source_id": result.source_id,
            "compiled": result.compiled.to_json_dict(),
            "citations": [_citation_json(citation) for citation in result.citations],
            "proposals": [proposal.to_json_dict() for proposal in result.proposals],
            "usage": json.loads(json.dumps(result.usage, default=str)),
        }
    )


def decode_compiled_result(data: bytes) -> CompiledResult:
    value = json.loads(data)
    return CompiledResult(
        source_id=str(value["source_id"]),
        compiled=CompiledSource.model_validate_json(json.dumps(value["compiled"])),
        citations=[_citation(item) for item in value.get("citations", [])],
        proposals=[parse_proposal(item) for item in value.get("proposals", [])],
        usage=dict(value.get("usage", {})),
    )


# -- pages and cited locators ------------------------------------------------------------


def encode_pages(pages: Iterable[Page]) -> bytes:
    return json_bytes([{"path": page.path, "text": page.render()} for page in pages])


def decode_pages(data: bytes) -> list[Page]:
    return [Page.parse(item["text"], item["path"]) for item in json.loads(data)]


def _cited_json(cited: CitedLocator) -> dict[str, Any]:
    return {
        "source_id": cited.source_id,
        "locator": _locator_json(cited.locator),
        "block_ids": list(cited.block_ids),
        "quotes": list(cited.quotes),
        "provenance": cited.provenance,
    }


def encode_cited(cited: Sequence[CitedLocator]) -> bytes:
    return json_bytes([_cited_json(item) for item in cited])


def decode_cited(data: bytes) -> list[CitedLocator]:
    return [
        CitedLocator(
            source_id=str(item["source_id"]),
            locator=_locator(item["locator"]),
            block_ids=tuple(item.get("block_ids", ())),
            quotes=tuple(item.get("quotes", ())),
            provenance=item.get("provenance", "native-text"),
        )
        for item in json.loads(data)
    ]


def encode_topic_skips(skips: Sequence[TopicSkip]) -> bytes:
    return json_bytes(
        [
            {"topic_slug": skip.topic_slug, "reason": skip.reason, "sources": list(skip.sources)}
            for skip in skips
        ]
    )


def decode_topic_skips(data: bytes) -> list[TopicSkip]:
    return [
        TopicSkip(
            topic_slug=str(item["topic_slug"]),
            reason=item["reason"],
            sources=tuple(item.get("sources", ())),
        )
        for item in json.loads(data)
    ]


def content_digest(value: Any) -> str:
    """SHA-256 of a JSON-able value in canonical form (for cache-key inputs)."""
    return sha256_hex(canonical_json(value))
