"""Classify stage (pipeline.md §1 stage 3): domain-pack rules first, LLM fallback.

Rules: ``docwiki.domain.match_doc_type`` on the file name and the head of the extracted text;
the document number and revision come from the pack's supersession rules (file name first, then
the extractor metadata, the title hint and the text head). When no rule matches, one ``fast``
structured-output call chooses the doc type and category from enums built from the pack.
"""

from __future__ import annotations

import posixpath
import re
from functools import lru_cache
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, create_model

from docwiki.contracts._base import sha256_hex
from docwiki.contracts.extracted import ExtractedDoc
from docwiki.domain import DomainPack, match_doc_type, parse_doc_number, parse_revision
from docwiki.domain.rules import revision_rank, scope_axes
from docwiki.engine_types import Classification
from docwiki.llm import LlmClient
from docwiki.stages.prompts import load_prompt
from docwiki.stages.verify_citations import normalize_text

__all__ = [
    "MAX_OUTPUT_TOKENS",
    "PROMPT_VERSION",
    "STAGE_VERSION",
    "TEXT_HEAD_CHARS",
    "classification_output_model",
    "classify_source",
]

STAGE_VERSION = "1"
PROMPT_VERSION = load_prompt("classify").version
TEXT_HEAD_CHARS = 2000
MAX_OUTPUT_TOKENS = 400
SCHEMA_NAME = "classify"

_LANG_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
_UNKNOWN_LANGS = frozenset({"und", "mul", "zxx", "mis"})


@lru_cache(maxsize=64)
def classification_output_model(
    doc_types: tuple[str, ...], categories: tuple[str, ...]
) -> type[BaseModel]:
    """Structured-output model whose ``doc_type`` and ``category`` are enums of the pack."""
    if not doc_types or not categories:
        raise ValueError("the domain pack defines no doc types or categories")
    doc_type_enum: Any = Literal[doc_types]
    category_enum: Any = Literal[categories]
    return create_model(
        "ClassificationOutput",
        __config__=ConfigDict(extra="forbid"),
        doc_type=(doc_type_enum, Field(description="Key of the chosen document type.")),
        category=(category_enum, Field(description="Category of the chosen document type.")),
        confidence=(
            float,
            Field(ge=0.0, le=1.0, description="Probability that doc_type is correct."),
        ),
        doc_number=(str | None, Field(description="Document number as printed, or null.")),
        revision=(str | None, Field(description="Revision as printed, or null.")),
        lang=(str, Field(description="ISO 639-1 code of the main language.")),
    )


def _output_model(pack: DomainPack) -> type[BaseModel]:
    doc_types = tuple(doc_type.key for doc_type in pack.taxonomy.doc_types)
    categories = tuple(category.key for category in pack.taxonomy.categories)
    return classification_output_model(doc_types, categories)


def canonical_revision(pack: DomainPack, revision: str | None) -> str | None:
    """The revision spelled as in the pack's ``revision_order`` (None when it is not valid)."""
    if revision is None or not revision.strip():
        return None
    value = revision.strip()
    if pack.supersession is None:
        return value
    try:
        revision_rank(pack, value)
    except ValueError:
        return None
    order = pack.supersession.revision_order
    if order == "numeric":
        return str(int(value))
    for item in order:
        if item.casefold() == value.casefold():
            return item
    return None  # pragma: no cover - revision_rank accepted it


def _rule_numbers(
    pack: DomainPack, doc: ExtractedDoc, filename: str, head: str
) -> tuple[str | None, str | None]:
    meta = doc.metadata
    title = doc.title_hint or ""
    doc_number = parse_doc_number(pack, filename, meta.doc_number or "", title, head)
    if doc_number is None and pack.supersession is None and meta.doc_number:
        doc_number = meta.doc_number.strip() or None
    revision = parse_revision(pack, filename, meta.revision or "", title, head)
    if revision is None and meta.revision:
        revision = meta.revision
    return doc_number, canonical_revision(pack, revision)


def _document_lang(doc: ExtractedDoc, suggested: str | None = None) -> str:
    if doc.lang not in _UNKNOWN_LANGS:
        return doc.lang
    candidate = (suggested or "").strip().lower()
    if _LANG_RE.match(candidate) and candidate not in _UNKNOWN_LANGS:
        return candidate
    return doc.lang


def data_nonce(text: str) -> str:
    """Delimiter nonce derived from the delimited content (a document cannot contain its hash)."""
    return sha256_hex(text.encode("utf-8"))[:12]


def _user_message(doc: ExtractedDoc, pack: DomainPack, filename: str, head: str) -> str:
    categories = {category.key: category for category in pack.taxonomy.categories}
    lines = [
        "# Task",
        "Classify the document whose beginning is given below.",
        "",
        f"# Catalog of document types (reviewed domain pack {pack.name!r})",
    ]
    for doc_type in pack.taxonomy.doc_types:
        category = categories[doc_type.category]
        detail = f": {category.description}" if category.description else ""
        lines.append(
            f"- {doc_type.key}: {doc_type.title} (category {category.key}, "
            f"{category.title}{detail})"
        )
    data_lines = [
        f"file name: {filename}",
        f"media type: {doc.media_type}",
        f"title hint: {doc.title_hint or 'none'}",
        "text:",
        head,
    ]
    data = "\n".join(data_lines)
    nonce = data_nonce(data)
    lines += [
        "",
        "# Document",
        f"BEGIN DOCUMENT DATA {nonce}",
        data,
        f"END DOCUMENT DATA {nonce}",
    ]
    return "\n".join(lines)


def _llm_doc_number(pack: DomainPack, value: str | None, haystack: str) -> str | None:
    if not value or not value.strip():
        return None
    candidate = value.strip()
    if pack.supersession is not None:
        parsed = parse_doc_number(pack, candidate)
        if parsed is None:
            return None
        candidate = parsed
    return candidate if normalize_text(candidate) in haystack else None


async def classify_source(doc: ExtractedDoc, pack: DomainPack, llm: LlmClient) -> Classification:
    """Classification of one source: its scope and axes from the raw path (v1.7, ADR 0011), a
    document type named by the path first, then the rules, then a ``fast`` LLM fallback with the
    pack's enums. Scope, phase and lot never come from the model."""
    axes = scope_axes(pack, doc.source_path)
    found = await _classify(doc, pack, llm, axes.doc_type)
    return found.model_copy(update={"scope": axes.scope, "phase": axes.phase, "lot": axes.lot})


async def _classify(
    doc: ExtractedDoc, pack: DomainPack, llm: LlmClient, path_type: str | None
) -> Classification:
    filename = posixpath.basename(doc.source_path)
    text = doc.text()
    head = text[:TEXT_HEAD_CHARS]
    match = match_doc_type(pack, filename, text)
    doc_number, revision = _rule_numbers(pack, doc, filename, head)
    if path_type is not None:
        doc_type = pack.doc_type(path_type)
        return Classification(
            doc_type=doc_type.key,
            category=doc_type.category,
            authority=doc_type.authority,
            doc_number=doc_number,
            revision=revision,
            lang=_document_lang(doc),
            confidence=1.0,
            rule_id=None,
            method="path",
        )
    if match is not None:
        return Classification(
            doc_type=match.doc_type,
            category=match.category,
            authority=match.authority,
            doc_number=doc_number,
            revision=revision,
            lang=_document_lang(doc),
            confidence=1.0,
            rule_id=match.rule_id,
            method="rule",
        )
    result = await llm.structured(
        tier="fast",
        system=load_prompt("classify").text,
        user=_user_message(doc, pack, filename, head),
        output=_output_model(pack),
        schema_name=SCHEMA_NAME,
        prompt_version=PROMPT_VERSION,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        metadata={"stage": "classify", "source_id": doc.source_id},
    )
    output: Any = result.output
    doc_type = pack.doc_type(output.doc_type)
    confidence = min(max(float(output.confidence), 0.0), 1.0)
    if output.category != doc_type.category:
        confidence = min(confidence, 0.5)
    if doc_number is None:
        haystack = normalize_text(f"{filename}\n{doc.title_hint or ''}\n{text}")
        doc_number = _llm_doc_number(pack, output.doc_number, haystack)
    if revision is None and output.revision:
        parsed = parse_revision(pack, output.revision)
        revision = canonical_revision(pack, parsed or output.revision)
    return Classification(
        doc_type=doc_type.key,
        category=doc_type.category,
        authority=doc_type.authority,
        doc_number=doc_number,
        revision=revision,
        lang=_document_lang(doc, output.lang),
        confidence=round(confidence, 4),
        rule_id=None,
        method="llm",
    )
