import base64
import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from docwiki.contracts.catalog import Catalog, catalog_page_for
from docwiki.contracts.compiled import CompiledSource
from docwiki.contracts.enums import (
    BADGES,
    PROVENANCES,
    allowed_for_audience,
    badge_for,
    max_sensitivity,
)
from docwiki.contracts.extracted import ExtractedDoc, row_id_for
from docwiki.contracts.gates import GATES, Violation, gate_results
from docwiki.contracts.manifest import CurrentPointer, ReleaseInputs, ReleaseManifest
from docwiki.contracts.pages import parse_frontmatter
from docwiki.contracts.proposals import (
    EntityProposalPayload,
    InjectionProposal,
    new_proposal,
    parse_proposal,
)
from docwiki.contracts.queue import QueueMessage, parse_queue_message
from docwiki.contracts.runs import CostReceipt, RunReport, VersionInfo
from docwiki.contracts.settings import SETTINGS_DEFAULTS, SettingsKeys
from docwiki.contracts.state import SourceState
from docwiki.contracts.strict_schema import check_strict_schema, is_nullable, strict_json_schema

NOW = datetime(2026, 1, 31, 8, 5, 9, tzinfo=UTC)
SOURCE_ID = "src-0123456789ab"
VERSIONS = VersionInfo(docwiki="0.1.0", domain_pack="mini-batiment", domain_pack_hash="abc")


def extracted(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "schema": 1,
        "source_id": SOURCE_ID,
        "source_path": "planning/planning.xlsx",
        "source_hash": "sha256:" + "b" * 64,
        "media_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "lang": "fr",
        "title_hint": None,
        "metadata": {
            "doc_number": None,
            "revision": None,
            "authored": "2026-01-02",
            "page_count": None,
        },
        "blocks": [
            {
                "id": "b0001",
                "kind": "paragraph",
                "text": "Planning de chantier",
                "locator": {
                    "kind": "xlsx-rows",
                    "sheet": "Planning",
                    "row_start": 1,
                    "row_end": 1,
                },
                "provenance": "deterministic-table",
            }
        ],
        "tables": [
            {
                "id": "t01",
                "locator": {
                    "kind": "xlsx-rows",
                    "sheet": "Planning",
                    "row_start": 1,
                    "row_end": 3,
                },
                "provenance": "deterministic-table",
                "columns": ["Tâche", "Désignation"],
                "rows": [
                    {"row_id": "r0002", "cells": ["T07", "Livraison des menuiseries"]},
                    {"row_id": "r0003", "cells": ["T08", "Pose des menuiseries"]},
                ],
                "artifact": "tables/t01.parquet",
            }
        ],
        "figures": [],
        "extraction": {"adapter": "local", "adapter_version": "1.0", "warnings": []},
    }
    data.update(overrides)
    return data


def test_extracted_doc_json_round_trip_and_helpers() -> None:
    doc = ExtractedDoc.model_validate_json(json.dumps(extracted()))
    assert doc.block("b0001").locator_key == "sheet-planning-r0001-r0001"
    assert doc.table("t01").rows[1].row_id == row_id_for(3)
    assert ExtractedDoc.from_json(doc.to_json()) == doc
    assert doc.text() == "Planning de chantier"


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        ({"blocks": [{"id": "b1"}]}, "pattern"),
        ({"source_hash": "sha256:xyz"}, "pattern"),
        ({"schema": 2}, "1"),
    ],
)
def test_extracted_doc_rejects_bad_values(patch: dict[str, object], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        ExtractedDoc.model_validate_json(json.dumps(extracted(**patch)))


def test_table_shape_and_figures_are_validated() -> None:
    data = extracted()
    data["tables"][0]["rows"].append({"row_id": "r0004", "cells": ["only one"]})  # type: ignore[index]
    with pytest.raises(ValidationError, match="expected 2"):
        ExtractedDoc.model_validate_json(json.dumps(data))
    data = extracted()
    data["tables"][0]["rows"][1]["row_id"] = "r0002"  # type: ignore[index]
    with pytest.raises(ValidationError, match="duplicate row_id"):
        ExtractedDoc.model_validate_json(json.dumps(data))
    figure = {
        "id": "f01",
        "locator": {"kind": "pdf-page", "page": 1},
        "image": "figures/f01.png",
        "description": "A photo of delivered pallets.",
        "description_provenance": None,
    }
    with pytest.raises(ValidationError, match="go together"):
        ExtractedDoc.model_validate_json(json.dumps(extracted(figures=[figure])))
    data = extracted()
    data["blocks"].append(data["blocks"][0])  # type: ignore[union-attr]
    with pytest.raises(ValidationError, match="unique"):
        ExtractedDoc.model_validate_json(json.dumps(data))


def test_strict_mode_does_not_coerce() -> None:
    with pytest.raises(ValidationError):
        VersionInfo(docwiki=1, domain_pack="x", domain_pack_hash="y")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        CostReceipt(price_table="t", duration_s="1.5")  # type: ignore[arg-type]


def test_compiled_source_strict_schema() -> None:
    schema = strict_json_schema(CompiledSource)
    check_strict_schema(schema)
    text = json.dumps(schema)
    assert "$ref" not in text and "$defs" not in text and '"default"' not in text

    def walk(node: object) -> None:
        if isinstance(node, dict):
            assert "title" not in node or isinstance(node.get("title"), dict)
            for key, value in node.items():
                if key == "properties":
                    for prop in value.values():
                        walk(prop)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(schema)
    citation = schema["properties"]["key_facts"]["items"]["properties"]["citations"]["items"]
    assert citation["required"] == ["block_id", "quote"]
    assert is_nullable(citation["properties"]["quote"])
    assert not is_nullable(citation["properties"]["block_id"])
    assert CompiledSource.response_format()["strict"] is True
    output = {
        "title": "Quote DEV-2026-014 indice B",
        "summary": "Current revision of the quote.",
        "key_facts": [
            {
                "text": "The total is 44943,60 € including VAT.",
                "citations": [{"block_id": "b0004", "quote": None}],
                "numbers": ["44943,60 €"],
            }
        ],
        "sections": [
            {"heading": "Totals", "body": "Check the totals.[[cite:b0005]]", "table_refs": []}
        ],
        "entity_mentions": [{"entity_id": "building-element:baie-f1", "block_ids": ["b0001"]}],
        "unknown_entities": [{"label": "Pergola P-2", "type_guess": None, "block_ids": []}],
        "glossary_candidates": [],
        "injection_flags": [],
    }
    assert (
        CompiledSource.model_validate_json(json.dumps(output)).key_facts[0].citations[0].quote
        is None
    )
    with pytest.raises(ValidationError):
        CompiledSource.model_validate_json(json.dumps({**output, "extra": 1}))


def test_check_strict_schema_rejects_non_strict_shapes() -> None:
    with pytest.raises(ValueError, match="required"):
        check_strict_schema(
            {
                "type": "object",
                "properties": {"a": {"type": "string"}},
                "additionalProperties": False,
            }
        )
    with pytest.raises(ValueError, match="additionalProperties"):
        check_strict_schema({"type": "object", "properties": {}, "required": []})
    with pytest.raises(ValueError, match="unsupported"):
        check_strict_schema({"type": "string", "pattern": "x"})


def test_queue_message_round_trip_and_rules() -> None:
    message = QueueMessage(kind="ingest", requested_by="cli", idempotency_key="k1", created_at=NOW)
    body = message.to_body()
    assert json.loads(body)["schema"] == "docwiki.ingest/v1"
    assert parse_queue_message(body) == message
    assert parse_queue_message(base64.b64encode(body.encode()).decode()) == message
    with pytest.raises(ValidationError, match="source_ids"):
        QueueMessage(
            kind="recompile", requested_by="librarian", idempotency_key="k", created_at=NOW
        )
    with pytest.raises(ValueError):
        parse_queue_message('{"schema": "other/v1"}')
    with pytest.raises(ValueError):
        parse_queue_message("not json at all !")


def test_event_grid_and_cloud_events_become_ingest_messages() -> None:
    event = {
        "id": "evt-1",
        "eventType": "Microsoft.Storage.BlobCreated",
        "subject": "/blobServices/default/containers/raw/blobs/devis/devis-b.pdf",
        "eventTime": "2026-01-31T08:05:09.1234567Z",
        "data": {},
        "dataVersion": "",
        "metadataVersion": "1",
    }
    message = parse_queue_message(json.dumps([event]))
    assert (message.kind, message.requested_by, message.idempotency_key) == (
        "ingest",
        "event",
        "event:evt-1",
    )
    assert message.hints == {
        "event_type": "Microsoft.Storage.BlobCreated",
        "blob": "devis/devis-b.pdf",
    }
    assert message.created_at == NOW
    cloud = {
        "specversion": "1.0",
        "type": "Microsoft.Storage.BlobDeleted",
        "id": "c1",
        "time": "2026-01-31T08:05:09Z",
        "subject": "x",
    }
    assert (
        parse_queue_message(json.dumps(cloud)).hints["event_type"]
        == "Microsoft.Storage.BlobDeleted"
    )
    with pytest.raises(ValueError, match="unsupported event"):
        parse_queue_message(json.dumps({**event, "eventType": "Microsoft.Storage.BlobRenamed"}))


def test_source_state_shard() -> None:
    state = SourceState(
        source_id="src-" + __import__("hashlib").sha256(b"devis/devis-b.pdf").hexdigest()[:12],
        raw_path="devis/devis-b.pdf",
        content_hash="sha256:" + "c" * 64,
        size=10,
        media_type="application/pdf",
        sensitivity="internal",
        stages={"extract": {"status": "quarantined", "error": "no text layer"}},
        first_seen_at=NOW,
        updated_at=NOW,
    )
    assert state.quarantined
    assert SourceState.from_json(state.to_json()) == state
    with pytest.raises(ValidationError, match="does not match raw_path"):
        SourceState.model_validate(
            {**state.model_dump(by_alias=True), "raw_path": "devis/autre.pdf"}
        )
    with pytest.raises(ValidationError, match="go together"):
        SourceState.model_validate({**state.model_dump(by_alias=True), "deleted": True})
    with pytest.raises(ValidationError):
        SourceState.model_validate(
            {**state.model_dump(by_alias=True), "stages": {"teleport": {"status": "done"}}}
        )


def test_run_report_minimal() -> None:
    report = RunReport(
        run_id="run-20260131-080509-0a1b2c3d",
        kind="ingest",
        requested_by="event",
        status="succeeded",
        started_at=NOW,
        audience="public",
        versions=VERSIONS,
        cost=CostReceipt(
            price_table="2026-01",
            llm=[{"role": "smart", "deployment": "smart", "model": "m", "input_tokens": 10}],
        ),
    )
    assert RunReport.from_json(report.to_json()) == report


def test_proposals_are_typed_and_deterministic() -> None:
    payload = EntityProposalPayload(type="building-element", key="fenetre-f2", label="Fenêtre F2")
    proposal = new_proposal("entity", payload, created_at=NOW)
    again = new_proposal(
        "entity",
        EntityProposalPayload(type="building-element", key="fenetre-f2", label="Fenêtre F2"),
        created_at=NOW,
    )
    assert proposal.id == again.id
    assert parse_proposal(proposal.to_json()) == proposal
    raw = {
        "id": "prop-0123456789ab",
        "kind": "injection",
        "payload": {
            "source_id": SOURCE_ID,
            "block_id": "b0007",
            "reason": "addresses AI assistants",
        },
        "evidence": [{"source_id": SOURCE_ID, "block_id": "b0007"}],
        "created_at": "2026-01-31T08:05:09Z",
    }
    assert isinstance(parse_proposal(raw), InjectionProposal)
    with pytest.raises(ValidationError):
        parse_proposal({**raw, "kind": "entity"})
    with pytest.raises(ValidationError, match="decided_by"):
        parse_proposal({**raw, "status": "accepted"})
    with pytest.raises(ValidationError, match="cannot have a decision"):
        parse_proposal({**raw, "decided_by": "operator"})


def test_release_manifest_identity_and_pointer() -> None:
    inputs = ReleaseInputs(sources={SOURCE_ID: "sha256:" + "d" * 64})
    release_id = ReleaseManifest.compute_release_id(
        created_at=NOW, audience="public", run_id=None, inputs=inputs, versions=VERSIONS
    )
    assert release_id.startswith("20260131T080509Z-")
    manifest = ReleaseManifest(
        release_id=release_id,
        created_at=NOW,
        audience="public",
        inputs=inputs,
        versions=VERSIONS,
        files={"a.md": {"sha256": "e" * 64, "size": 1}},
    )
    assert ReleaseManifest.from_json(manifest.to_json()) == manifest
    for tamper in (
        {"audience": "internal"},
        {"inputs": {"sources": {}}},
        {"created_at": "2026-01-31T08:05:10Z"},
    ):
        with pytest.raises(ValidationError, match="identity"):
            ReleaseManifest.model_validate_json(json.dumps({**manifest.to_json_dict(), **tamper}))
    with pytest.raises(ValidationError, match="cannot list itself"):
        ReleaseManifest.model_validate_json(
            json.dumps(
                {
                    **manifest.to_json_dict(),
                    "files": {"manifest.json": {"sha256": "e" * 64, "size": 1}},
                }
            )
        )
    with pytest.raises(ValueError, match="second precision"):
        ReleaseManifest.compute_release_id(
            created_at=NOW.replace(microsecond=5),
            audience="public",
            run_id=None,
            inputs=inputs,
            versions=VERSIONS,
        )
    pointer = CurrentPointer(
        release_id=release_id, created_at=NOW, audience="public", manifest_sha256="f" * 64
    )
    assert CurrentPointer.from_json(pointer.to_json()) == pointer


def test_gate_results_fold_violations() -> None:
    violations = [
        Violation(gate="G02", code="link-unresolved", message="x"),
        Violation(gate="G13", code="orphan-pages", severity="warning", message="y"),
        Violation(gate="G15", code="quarantine", message="z"),
        Violation(gate="G05", code="bare-url", severity="warning", message="w"),
    ]
    results = {result.gate: result for result in gate_results(violations, skipped=["G04"])}
    assert len(results) == len(GATES) == 17
    assert results["G02"].status == "fail" and results["G02"].blocks_publish
    assert results["G13"].status == "warn" and not results["G13"].blocks_publish
    assert results["G15"].status == "warn"
    assert results["G05"].status == "warn"
    assert results["G04"].status == "skipped"
    assert results["G16"].status == "pass" and results["G16"].blocking
    assert results["G01"].status == "pass"


def test_catalog_validation_and_page_entries() -> None:
    fm = parse_frontmatter(
        {
            "id": "topic:site-progress",
            "type": "topic",
            "title": "Site progress",
            "summary": "Progress of the works.",
            "sensitivity": "public",
            "updated": "2026-01-31",
            "docwiki": {"schema": 1, "release": "20260131T080509Z-01234567"},
            "topic_slug": "site-progress",
            "sources": [SOURCE_ID],
            "confidence": "medium",
        }
    )
    entry = catalog_page_for(fm, "topics/site-progress.md")
    assert entry.sources == [SOURCE_ID] and entry.status is None
    base = {
        "schema": 1,
        "release_id": "20260131T080509Z-01234567",
        "audience": "public",
        "generated_at": "2026-01-31T08:05:09Z",
    }
    catalog = Catalog.model_validate_json(
        json.dumps({**base, "pages": [entry.to_json_dict()], "edges": []})
    )
    assert catalog.to_json_dict()["schema"] == 1
    edge = {"from": "topic:site-progress", "to": "src-ffffffffffff", "kind": "cites"}
    with pytest.raises(ValidationError, match="unknown page"):
        Catalog.model_validate_json(
            json.dumps({**base, "pages": [entry.to_json_dict()], "edges": [edge]})
        )
    with pytest.raises(ValidationError, match="unique"):
        Catalog.model_validate_json(json.dumps({**base, "pages": [entry.to_json_dict()] * 2}))


def test_badges_and_sensitivity_helpers() -> None:
    assert badge_for("native-text") == "✓ quote verified"
    assert badge_for("native-text", "unverified-paraphrase") == "paraphrase"
    assert badge_for("deterministic-table", "unverified-paraphrase") == "table"
    assert badge_for("ocr") == "OCR"
    assert badge_for("model-description") == "generated description"
    assert {badge_for(p) for p in PROVENANCES} <= set(BADGES)
    with pytest.raises(ValueError):
        badge_for("native-text", "failed")
    assert max_sensitivity("public", "restricted", "internal") == "restricted"
    assert max_sensitivity() == "public"
    assert allowed_for_audience("internal", "internal") and not allowed_for_audience(
        "restricted", "internal"
    )
    with pytest.raises(ValueError):
        allowed_for_audience("secret", "public")


def test_settings_keys() -> None:
    keys = [value for name, value in vars(SettingsKeys).items() if name.isupper()]
    assert keys and all(key.startswith("DOCWIKI_") for key in keys)
    assert len(keys) == len(set(keys))
    assert set(SETTINGS_DEFAULTS) <= set(keys)
    assert SETTINGS_DEFAULTS[SettingsKeys.RELEASE_RETENTION] == "10"
