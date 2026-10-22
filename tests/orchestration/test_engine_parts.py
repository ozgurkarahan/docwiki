"""Engine building blocks: settings, registry, artifacts, codecs and telemetry."""

from __future__ import annotations

import sys
import types
from datetime import UTC, datetime
from pathlib import Path

import pytest
from engine_stubs import STUB_FUNCTIONS, compile_source, fake_llm

from docwiki.contracts.compiled import CompiledSource
from docwiki.contracts.locators import CsvRowsLocator, TextLinesLocator
from docwiki.contracts.proposals import InjectionProposalPayload, new_proposal
from docwiki.contracts.storage import FolderStorage
from docwiki.engine_types import CitedLocator, CompiledResult, VerifiedCitation
from docwiki.orchestration import registry
from docwiki.orchestration.artifacts import ArtifactStore
from docwiki.orchestration.codec import (
    decode_cited,
    decode_compiled_result,
    encode_cited,
    encode_compiled_result,
)
from docwiki.orchestration.settings import (
    EngineSettings,
    SettingsError,
    parse_dotenv,
    resolve_pack_path,
)

KEY = "a" * 64


def test_settings_from_environment_and_overrides():
    env = {
        "DOCWIKI_MODE": "azure",
        "DOCWIKI_STORAGE_ACCOUNT": "lamnawiki01",
        "DOCWIKI_AUDIENCE": "public",
        "DOCWIKI_DEBOUNCE_SECONDS": "5",
        "DOCWIKI_LEASE_SECONDS": "45",
        "DOCWIKI_RELEASE_RETENTION": "3",
        "DOCWIKI_CANARIES": "A, B,,A",
        "DOCWIKI_ORCHESTRATOR": "ASYNC",
        "DOCWIKI_CONTENT_UNDERSTANDING": "true",
    }
    settings = EngineSettings.from_env(env, retention=7)
    assert settings.mode == "azure" and settings.audience == "public"
    assert settings.debounce_s == 5.0 and settings.lease_s == 45.0
    assert settings.retention == 7
    assert settings.canaries == ("A", "B")
    assert settings.orchestrator == "async"
    assert settings.content_understanding is True
    assert settings.blob_account_url == "https://lamnawiki01.blob.core.windows.net"
    assert settings.queue_account_url == "https://lamnawiki01.queue.core.windows.net"
    assert settings.build_site is None and settings.site_enabled
    defaults = EngineSettings.from_env({})
    assert (defaults.mode, defaults.audience, defaults.debounce_s) == ("local", "internal", 30.0)
    assert defaults.orchestrator is None and not defaults.site_enabled
    assert EngineSettings.from_env({"DOCWIKI_SITE_BUILD": "true"}).site_enabled
    assert not EngineSettings.from_env({**env, "DOCWIKI_SITE_BUILD": "off"}).site_enabled
    for bad in (
        {"DOCWIKI_MODE": "cloud"},
        {"DOCWIKI_AUDIENCE": "everyone"},
        {"DOCWIKI_LEASE_SECONDS": "soon"},
        {"DOCWIKI_ORCHESTRATOR": "airflow"},
        {"DOCWIKI_CONTENT_UNDERSTANDING": "maybe"},
        {"DOCWIKI_SITE_BUILD": "sometimes"},
    ):
        with pytest.raises(SettingsError):
            EngineSettings.from_env(bad)
    with pytest.raises(SettingsError):
        _ = EngineSettings.from_env({}).blob_account_url
    url = EngineSettings.from_env(
        {"DOCWIKI_STORAGE_ACCOUNT": "https://lamnawiki01.blob.core.windows.net/"}
    )
    assert url.queue_account_url == "https://lamnawiki01.queue.core.windows.net"


def test_dotenv_parsing_and_pack_resolution(tmp_path: Path):
    text = "# comment\nexport A=1\nB = 'two words'\nC=\"x # y\"\nD=v # trailing\nnot a line\n"
    assert parse_dotenv(text) == {"A": "1", "B": "two words", "C": "x # y", "D": "v"}
    pack = tmp_path / "domains" / "my-pack"
    pack.mkdir(parents=True)
    assert resolve_pack_path(str(pack)) == pack
    assert resolve_pack_path("my-pack", search=(tmp_path / "domains",)) == pack
    with pytest.raises(SettingsError):
        resolve_pack_path(None)
    with pytest.raises(SettingsError):
        resolve_pack_path("no-such-pack")


def test_registry_reports_missing_lanes_and_accepts_overrides(monkeypatch):
    missing = registry.missing_engine_functions()
    for name in ("classify_source", "compile_source"):
        if name in missing:
            with pytest.raises(registry.EngineUnavailableError) as info:
                registry.load_engine()
            assert name in info.value.missing
            break
    engine = registry.load_engine(STUB_FUNCTIONS, versions={"compile": "pinned"})
    assert engine.version("compile") == "pinned"
    assert engine.version("extract") == "stub-1"
    assert engine.origins["compile_source"].endswith(":compile_source")
    monkeypatch.setattr(registry, "_ACTIVE", None)
    with registry.use_engine(engine):
        assert registry.active_engine() is engine
    assert registry._ACTIVE is None


def test_prompt_versions_are_collected_and_matched_per_stage(monkeypatch, tmp_path: Path):
    package = types.ModuleType("docwiki.stages.prompts")
    package.__path__ = [str(tmp_path)]  # type: ignore[attr-defined]
    (tmp_path / "compile_map.py").write_text('PROMPT_VERSION = "c-3"\n', encoding="utf-8")
    (tmp_path / "topics.py").write_text(
        'PROMPT_VERSIONS = {"topic-synthesis": "t-2"}\n', encoding="utf-8"
    )
    monkeypatch.setitem(sys.modules, "docwiki.stages.prompts", package)
    versions = registry.collect_prompt_versions()
    assert versions["compile_map"] == "c-3" and versions["topic-synthesis"] == "t-2"
    engine = registry.load_engine(STUB_FUNCTIONS)
    assert engine.prompts_for("compile") == "compile_map=c-3"
    assert engine.prompts_for("topics") == "topic-synthesis=t-2"
    assert "compile_map=c-3" in (engine.prompts_for("classify") or "")
    assert engine.prompts_for("render") is None
    for name in ("docwiki.stages.prompts.compile_map", "docwiki.stages.prompts.topics"):
        sys.modules.pop(name, None)


def test_module_version_falls_back_to_a_source_hash():
    module = types.ModuleType("plain")
    assert registry.module_version(module) == "unknown"
    assert registry.module_version(sys.modules[compile_source.__module__]) == "stub-1"
    assert registry.module_version(registry).startswith("src-")


def test_artifacts_are_verified_on_load(tmp_path: Path):
    storage = FolderStorage(tmp_path, fsync=False)
    store = ArtifactStore(storage)
    assert store.load("compile", KEY) is None
    store.save("compile", KEY, {"result.json": b"{}", "figures/f01.png": b"png"})
    loaded = store.load("compile", KEY)
    assert loaded is not None and loaded.bytes("figures/f01.png") == b"png"
    assert loaded.names("figures/") == ["figures/f01.png"]
    storage.write_bytes(f"work/artifacts/compile/{KEY}/result.json", b"{tampered}")
    assert store.load("compile", KEY) is None
    storage.delete(f"work/artifacts/compile/{KEY}/result.json")
    assert store.load("compile", KEY) is None
    with pytest.raises(ValueError):
        store.save("compile", KEY, {"_complete.json": b"x"})


def test_compiled_results_and_cited_locators_round_trip():
    locator = TextLinesLocator(line_start=3, line_end=3)
    compiled = CompiledSource(
        title="T",
        summary="S",
        key_facts=[],
        sections=[],
        entity_mentions=[],
        unknown_entities=[],
        glossary_candidates=[],
        injection_flags=[],
    )
    result = CompiledResult(
        source_id="src-0123456789ab",
        compiled=compiled,
        citations=[
            VerifiedCitation(
                "kf1", "src-0123456789ab", ("b0003",), "q", "verified", "native-text", locator
            ),
            VerifiedCitation(
                "kf2", "src-0123456789ab", (), None, "failed", "ocr", None, "no match"
            ),
        ],
        proposals=[
            new_proposal(
                "injection",
                InjectionProposalPayload(
                    source_id="src-0123456789ab", block_id="b0004", reason="AI address"
                ),
                created_at=datetime(2026, 2, 1, tzinfo=UTC),
            )
        ],
        usage={"calls": 1, "when": datetime(2026, 2, 1, tzinfo=UTC)},
    )
    decoded = decode_compiled_result(encode_compiled_result(result))
    assert decoded.citations == result.citations
    assert decoded.proposals == result.proposals
    assert decoded.compiled == compiled
    cited = [
        CitedLocator(
            "src-0123456789ab",
            CsvRowsLocator(row_start=2, row_end=4),
            ("b0001",),
            ("x",),
            "deterministic-table",
        )
    ]
    assert decode_cited(encode_cited(cited)) == cited


def test_stage_spans_are_recorded_when_a_tracer_is_configured(monkeypatch):
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from docwiki.orchestration import telemetry

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(telemetry, "_tracer", lambda: provider.get_tracer("test"))
    with telemetry.stage_span("compile", run_id="run-x", source_id="src-1", ignored=None) as span:
        span.set(items=3)
    (recorded,) = exporter.get_finished_spans()
    assert recorded.name == "docwiki.stage.compile"
    assert recorded.attributes["docwiki.run_id"] == "run-x"
    assert recorded.attributes["docwiki.items"] == 3
    monkeypatch.setattr(telemetry, "_tracer", lambda: None)
    with telemetry.stage_span("compile") as span:
        span.set(items=1)


def test_jobs_export_to_application_insights_when_configured(monkeypatch):
    """The jobs got the connection string but never configured an exporter: no stage or LLM
    spans and no warnings reached Application Insights."""
    from docwiki.orchestration import telemetry

    calls: list[dict[str, object]] = []
    fake = types.ModuleType("azure.monitor.opentelemetry")
    fake.configure_azure_monitor = lambda **kwargs: calls.append(kwargs)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "azure.monitor.opentelemetry", fake)
    monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
    assert telemetry.configure_exporter() is False and calls == []
    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "InstrumentationKey=test")
    assert telemetry.configure_exporter() is True
    assert calls == [{"logger_name": "docwiki"}]


def test_starlette_requests_become_server_spans_except_health_probes():
    """configure_azure_monitor does not instrument plain Starlette: the portal sent no requests
    to Application Insights."""
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.trace import SpanKind
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient

    from docwiki.orchestration import telemetry

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    ok = lambda _request: PlainTextResponse("ok")  # noqa: E731
    app = Starlette(routes=[Route("/healthz", ok), Route("/{path:path}", ok)])
    client = TestClient(telemetry.instrument_asgi(app, tracer_provider=provider))
    assert client.get("/healthz").status_code == 200
    assert client.get("/topics/pumps").status_code == 200
    spans = exporter.get_finished_spans()
    assert [span.kind for span in spans] == [SpanKind.SERVER]
    assert spans[0].attributes["http.status_code"] == 200


def test_worker_configures_console_logs_and_the_exporter(monkeypatch, tmp_path):
    from docwiki import cli
    from docwiki.orchestration import telemetry

    order: list[str] = []
    monkeypatch.setattr(telemetry, "console_logs", lambda: order.append("console"))
    monkeypatch.setattr(telemetry, "configure_exporter", lambda: order.append("exporter") or True)
    monkeypatch.setattr(telemetry, "flush_exporter", lambda: order.append("flush"))

    class Stop(Exception):
        pass

    def stop(*_args: object, **_kwargs: object) -> None:
        raise Stop

    monkeypatch.setattr("docwiki.orchestration.context.open_storage", stop)
    with pytest.raises(Stop):
        cli._worker("ingest", "event", object())
    # console output survives the exporter handler; buffered spans are exported before exit
    assert order == ["console", "exporter", "flush"]


def test_flush_exporter_flushes_trace_and_log_providers(monkeypatch):
    from opentelemetry import _logs, trace

    from docwiki.orchestration import telemetry

    flushed: list[tuple[str, int]] = []

    class Provider:
        def __init__(self, name: str) -> None:
            self.name = name

        def force_flush(self, timeout_millis: int) -> bool:
            flushed.append((self.name, timeout_millis))
            return True

    monkeypatch.setattr(trace, "get_tracer_provider", lambda: Provider("traces"))
    monkeypatch.setattr(_logs, "get_logger_provider", lambda: Provider("logs"))
    telemetry.flush_exporter(5_000)
    assert flushed == [("traces", 5_000), ("logs", 5_000)]


async def test_fake_llm_handles_every_stub_schema():
    llm = fake_llm()
    info = await llm.describe("smart")
    assert info.deployment == "fake-smart"


def test_overlay_sync_skips_items_already_merged_by_the_mcp_server(tmp_path: Path, pack_dir: Path):
    import json

    from docwiki.contracts.layout import StorageKeys, proposal_key
    from docwiki.contracts.proposals import GlossaryProposalPayload
    from docwiki.domain.loader import load_pack
    from docwiki.domain.overlay import Overlay, add_proposal, dump_overlay
    from docwiki.orchestration.proposals import APPLIED_KEY, ProposalStore

    storage = FolderStorage(tmp_path / "work", fsync=False)
    proposal = new_proposal(
        "glossary",
        GlossaryProposalPayload(term="HT", definition="Price excluding VAT.", synonyms={}),
        created_at=datetime(2026, 2, 1, tzinfo=UTC),
    ).model_copy(
        update={
            "status": "accepted",
            "decided_by": "librarian",
            "decided_at": datetime(2026, 2, 2, tzinfo=UTC),
        }
    )
    storage.write_bytes(proposal_key(proposal.id), proposal.to_json().encode("utf-8"))
    merged = dump_overlay(add_proposal(Overlay(), proposal)).encode("utf-8")
    storage.write_bytes(StorageKeys.OVERLAY, merged)
    store = ProposalStore(storage)
    pack = load_pack(pack_dir)
    sync = store.sync_overlay(pack)
    assert sync.applied == [] and sync.rejected == []
    assert len(sync.overlay.glossary) == 1
    assert storage.read_bytes(StorageKeys.OVERLAY) == merged
    assert json.loads(storage.read_bytes(APPLIED_KEY))["applied"] == [proposal.id]
    domain, _ = store.domain_pack(pack)
    assert [term.term for term in domain.glossary.terms if term.term == "HT"] == ["HT"]


def test_lane_package_versions_feed_the_stage_version(monkeypatch: pytest.MonkeyPatch):
    package = types.ModuleType("docwiki.extract")
    package.__path__ = []  # type: ignore[attr-defined]
    package.ADAPTER_VERSION = "9.9.9"  # type: ignore[attr-defined]
    package.extractor_versions = lambda: {"local": "9.9.9", "pypdfium2": "1.0"}  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "docwiki.extract", package)
    assert registry.package_versions("docwiki.extract") == {
        "adapter_version": "9.9.9",
        "local": "9.9.9",
        "pypdfium2": "1.0",
    }
    assert registry.package_versions("docwiki.stages.links") == {}

    async def extract_source(*args: object, **kwargs: object) -> None:
        return None

    extract_source.__module__ = "docwiki.extract.fake"
    engine = registry.load_engine({**STUB_FUNCTIONS, "extract_source": extract_source})
    assert engine.version("extract").count("+") == 1
    assert engine.version_details == {
        "extract.adapter_version": "9.9.9",
        "extract.local": "9.9.9",
        "extract.pypdfium2": "1.0",
    }
    package.extractor_versions = lambda: {"local": "9.9.9", "pypdfium2": "2.0"}  # type: ignore[attr-defined]
    bumped = registry.load_engine({**STUB_FUNCTIONS, "extract_source": extract_source})
    assert bumped.version("extract") != engine.version("extract")
    assert registry.load_engine(STUB_FUNCTIONS).version_details == {}
