"""DocWiki MCP server: stdio for local agents, stateless streamable HTTP at ``/mcp`` for Foundry.

```text
python -m docwiki.mcp.server --stdio --release <dir>                    # local agents
python -m docwiki.mcp.server --http 127.0.0.1:8765 --release <dir>     # local HTTP
python -m docwiki.mcp.server --http :8080 --storage blob               # Azure (easyauth)
```

``main`` parses flags on top of the ``DOCWIKI_*`` environment (:class:`McpConfig`);
``create_app`` returns the ASGI application (``/mcp`` + ``/healthz``) used in HTTP mode.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Annotated, Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.tools import Tool
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from docwiki import __version__
from docwiki.contracts.settings import SettingsKeys
from docwiki.contracts.storage import (
    FolderStorage,
    KeyNotFoundError,
    PreconditionFailedError,
    StorageError,
)
from docwiki.logs import quiet_sdk_http_logs
from docwiki.mcp import OPS_TOOLS, READ_TOOLS
from docwiki.mcp.auth import (
    AuthorizationMiddleware,
    PrincipalMiddleware,
    principal_from_tool_context,
    token_validator_for,
    tool_denial,
)
from docwiki.mcp.bounds import ResultTooLargeError, dumps
from docwiki.mcp.config import Level, McpConfig, is_loopback
from docwiki.mcp.descriptions import INSTRUCTIONS, PARAMS, TOOLS
from docwiki.mcp.errors import ErrorCode, ToolFailure, failure_payload
from docwiki.mcp.ingest_queue import AzureStorageQueue, FolderQueue, IngestQueue
from docwiki.mcp.source import (
    FolderReleaseSource,
    ReleaseSource,
    ReleaseUnavailableError,
    StorageReleaseSource,
)
from docwiki.mcp.tokens import TokenValidator
from docwiki.mcp.tools_ops import OpsTools
from docwiki.mcp.tools_read import ANSWER_CONTEXT_HITS, MAX_ANSWER_CONTEXT_HITS, ReadTools
from docwiki.mcp.workstore import WorkStore

__all__ = ["SERVER_NAME", "build_server", "create_app", "main", "make_ops", "make_source"]

logger = logging.getLogger("docwiki.mcp")

SERVER_NAME = "docwiki"
DEFAULT_CACHE_DIR = Path(tempfile.gettempdir()) / "docwiki-mcp-cache"
_LOOPBACK_HOSTS = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
_LOOPBACK_ORIGINS = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]

SearchKind = Literal["page-section", "source-block"]
PageTypeName = Literal[
    "source", "entity", "topic", "hub", "view", "query", "index", "meta", "glossary", "log"
]
SourceStatusName = Literal["failed", "quarantined", "pending", "deleted", "done"]
ProposalStatusName = Literal["open", "accepted", "rejected"]
SourceIdStr = Annotated[str, Field(pattern=r"^src-[0-9a-f]{12}$")]


class IngestScope(BaseModel):
    """Optional narrowing of ``ingest_start``."""

    model_config = ConfigDict(extra="forbid")

    source_ids: list[SourceIdStr] | None = Field(
        default=None, max_length=50, description="Existing sources to re-process."
    )
    prefix: str | None = Field(
        default=None, max_length=512, description="raw/ path prefix such as 'procedures/'."
    )


def _desc(key: str) -> Any:
    return Field(description=PARAMS[key])


def _clean_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Inline ``$defs`` references and drop generated titles (smaller, simpler tool schemas)."""
    defs = schema.get("$defs", {})

    def clean(node: Any) -> Any:
        if isinstance(node, list):
            return [clean(item) for item in node]
        if not isinstance(node, dict):
            return node
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            merged = {
                **defs[ref.rsplit("/", 1)[-1]],
                **{k: v for k, v in node.items() if k != "$ref"},
            }
            return clean(merged)
        out: dict[str, Any] = {}
        for key, value in node.items():
            if key in ("$defs", "title"):
                continue
            if key == "properties" and isinstance(value, dict):
                out[key] = {name: clean(sub) for name, sub in value.items()}
            else:
                out[key] = clean(value)
        return out

    return clean(schema)


def _failure(
    tool: str, code: ErrorCode, message: str, details: dict[str, Any] | None = None
) -> CallToolResult:
    """A failed call as a normal tool result (Foundry aborts the turn on MCP errors)."""
    text = dumps(failure_payload(code, message, tool=tool, details=details))
    return CallToolResult(content=[TextContent(type="text", text=text)])


def _upstream(exc: BaseException) -> tuple[ErrorCode, str] | None:
    """Classify storage, queue and network failures (no internal details in the message)."""
    kind = type(exc).__name__
    if isinstance(exc, KeyNotFoundError):
        return "not_found", "the requested object does not exist in the work store"
    if isinstance(exc, PreconditionFailedError):
        return "conflict", "the object changed concurrently; read it again and retry"
    try:
        from azure.core.exceptions import (
            AzureError,
            ServiceRequestTimeoutError,
            ServiceResponseTimeoutError,
        )
    except ImportError:  # pragma: no cover - the azure extra is optional
        azure_error: tuple[type[BaseException], ...] = ()
        azure_timeout: tuple[type[BaseException], ...] = ()
    else:
        azure_error = (AzureError,)
        azure_timeout = (ServiceRequestTimeoutError, ServiceResponseTimeoutError)
    if isinstance(exc, (TimeoutError, *azure_timeout)):
        return "timeout", f"an upstream call timed out ({kind}); retry later"
    if isinstance(exc, (StorageError, OSError, *azure_error)):
        return "unavailable", f"storage or the queue is unavailable ({kind}); retry later"
    return None


def _result(tool: str, action: Callable[[], str]) -> CallToolResult:
    """Run a tool body; anticipated and upstream failures become ``ok: false`` results."""
    try:
        text = action()
    except ToolFailure as exc:
        return _failure(tool, exc.code, exc.message, exc.details)
    except ReleaseUnavailableError as exc:
        logger.warning("no release available: %s", exc)
        return _failure(
            tool,
            "unavailable",
            "no release is available yet (none published, or it failed to load); retry later "
            "or ask an operator to run an ingest",
        )
    except ResultTooLargeError:
        return _failure(
            tool,
            "too_large",
            "the result does not fit in the output budget; narrow the request (one section, "
            "filters, fewer columns or rows)",
        )
    except Exception as exc:
        classified = _upstream(exc)
        if classified is None:
            raise
        logger.warning("tool %s upstream failure: %s", tool, type(exc).__name__)
        return _failure(tool, *classified)
    return CallToolResult(content=[TextContent(type="text", text=text)])


def _validation_failure(exc: ValidationError) -> tuple[ErrorCode, str]:
    errors = exc.errors(include_url=False)
    kinds = {str(error.get("type")) for error in errors}
    code: ErrorCode = (
        "too_large" if kinds and kinds <= {"string_too_long", "too_long"} else "invalid_argument"
    )
    parts = [
        f"{'.'.join(str(part) for part in error.get('loc', ())) or 'arguments'}: {error['msg']}"
        for error in errors[:5]
    ]
    more = f" (+{len(errors) - 5} more)" if len(errors) > 5 else ""
    return code, "invalid arguments: " + "; ".join(parts) + more + ". Check the input schema."


class GuardedTool(Tool):
    """A DocWiki tool: role check first, then argument validation; never raises to the client.

    Every outcome is a normal MCP result whose JSON says ``"ok": true`` or ``"ok": false`` with
    an error code, because Foundry aborts the whole agent turn on a JSON-RPC error or an
    ``isError`` result (docs/adr/0003-mcp-agent-identity.md, F3).
    """

    level: str = Field(default="read", exclude=True)
    access: Any = Field(default=None, exclude=True)

    async def run(
        self, arguments: dict[str, Any], context: Any, convert_result: bool = False
    ) -> Any:
        config: McpConfig = self.access
        principal = principal_from_tool_context(context, config)
        denial = tool_denial(principal, self.level, config)  # type: ignore[arg-type]
        if denial is not None:
            return _failure(self.name, "forbidden", *denial)
        try:
            self.fn_metadata.validate_arguments(arguments)
        except ValidationError as exc:
            return _failure(self.name, *_validation_failure(exc))
        try:
            return await super().run(arguments, context, convert_result=convert_result)
        except Exception:
            logger.exception("tool %s failed unexpectedly", self.name)
            return _failure(
                self.name, "internal", "the tool failed unexpectedly; the server logged the details"
            )


def tool_levels() -> dict[str, Level]:
    """Access level required by every DocWiki tool (unlisted tools are refused)."""
    levels: dict[str, Level] = dict.fromkeys(READ_TOOLS, "read")
    levels.update(dict.fromkeys(OPS_TOOLS, "operate"))
    return levels


_READ_ONLY = {"read_only_hint": True, "open_world_hint": False}
_TITLES = {
    "answer_context": "Answer context",
    "search": "Search the wiki",
    "read_page": "Read a wiki page",
    "get_index": "Read an index",
    "get_links": "Page relations",
    "glossary": "Glossary lookup",
    "get_evidence": "Open evidence",
    "query_table": "Query source tables",
    "get_skill": "Read a skill",
    "list_skills": "List skills",
    "recent_changes": "Recent changes",
    "ingest_start": "Start an ingest",
    "run_status": "Run status",
    "list_sources": "List sources",
    "quality_report": "Quality report",
    "explain_source": "Explain a source",
    "recompile": "Recompile sources",
    "list_proposals": "List proposals",
    "decide_proposal": "Decide a proposal",
    "write_health_report": "Write the health report",
}
_ANNOTATIONS: dict[str, dict[str, bool]] = {
    **dict.fromkeys(READ_TOOLS, _READ_ONLY),
    "run_status": _READ_ONLY,
    "list_sources": _READ_ONLY,
    "quality_report": _READ_ONLY,
    "explain_source": _READ_ONLY,
    "list_proposals": _READ_ONLY,
    "ingest_start": {"read_only_hint": False, "destructive_hint": False, "open_world_hint": False},
    "recompile": {"read_only_hint": False, "destructive_hint": False, "open_world_hint": False},
    "decide_proposal": {
        "read_only_hint": False,
        "destructive_hint": True,
        "idempotent_hint": True,
        "open_world_hint": False,
    },
    "write_health_report": {
        "read_only_hint": False,
        "destructive_hint": False,
        "idempotent_hint": True,
        "open_world_hint": False,
    },
}


def _tool(fn: Callable[..., Any], name: str, config: McpConfig) -> Tool:
    tool = GuardedTool.from_function(
        fn,
        name=name,
        title=_TITLES[name],
        description=TOOLS[name],
        annotations=ToolAnnotations(title=_TITLES[name], **_ANNOTATIONS[name]),
    )
    return tool.model_copy(
        update={
            "parameters": _clean_schema(tool.parameters),
            "level": tool_levels()[name],
            "access": config,
        }
    )


def _read_tools(reads: ReadTools, config: McpConfig) -> list[Tool]:
    def answer_context(
        question: Annotated[str, Field(min_length=1, max_length=500), _desc("question")],
        within: Annotated[str | None, Field(max_length=64), _desc("within")] = None,
        limit: Annotated[
            int, Field(ge=1, le=MAX_ANSWER_CONTEXT_HITS), _desc("context_limit")
        ] = ANSWER_CONTEXT_HITS,
        offset: Annotated[int, Field(ge=0, le=100), _desc("offset")] = 0,
        lang: Annotated[str | None, Field(max_length=16), _desc("lang")] = None,
    ) -> CallToolResult:
        return _result(
            "answer_context",
            lambda: reads.answer_context(question, within, limit, offset, lang),
        )

    def search(
        query: Annotated[str, Field(min_length=1, max_length=500), _desc("query")],
        kinds: Annotated[list[SearchKind] | None, _desc("kinds")] = None,
        types: Annotated[list[PageTypeName] | None, _desc("types")] = None,
        entity: Annotated[str | None, Field(max_length=140), _desc("entity")] = None,
        topic: Annotated[str | None, Field(max_length=140), _desc("topic")] = None,
        limit: Annotated[int, Field(ge=1, le=50), _desc("limit")] = 10,
        offset: Annotated[int, Field(ge=0, le=1000), _desc("offset")] = 0,
        within: Annotated[str | None, Field(max_length=64), _desc("within")] = None,
        lang: Annotated[str | None, Field(max_length=16), _desc("lang")] = None,
    ) -> CallToolResult:
        return _result(
            "search",
            lambda: reads.search(query, kinds, types, entity, topic, limit, offset, within, lang),
        )

    def read_page(
        page: Annotated[str, Field(min_length=1, max_length=300), _desc("page")],
        section: Annotated[str | None, Field(max_length=200), _desc("section")] = None,
        offset: Annotated[int, Field(ge=0), _desc("text_offset")] = 0,
        lang: Annotated[str | None, Field(max_length=16), _desc("lang")] = None,
    ) -> CallToolResult:
        return _result("read_page", lambda: reads.read_page(page, section, offset, lang))

    def get_index(
        scope: Annotated[str, Field(min_length=1, max_length=100), _desc("scope")] = "home",
        offset: Annotated[int, Field(ge=0), _desc("text_offset")] = 0,
        within: Annotated[str | None, Field(max_length=64), _desc("within_index")] = None,
        lang: Annotated[str | None, Field(max_length=16), _desc("lang")] = None,
    ) -> CallToolResult:
        return _result("get_index", lambda: reads.get_index(scope, offset, within, lang))

    def get_links(
        page: Annotated[str, Field(min_length=1, max_length=300), _desc("page")],
        offset: Annotated[int, Field(ge=0), _desc("offset")] = 0,
    ) -> CallToolResult:
        return _result("get_links", lambda: reads.get_links(page, offset))

    def glossary(
        term: Annotated[str | None, Field(max_length=200), _desc("term")] = None,
        offset: Annotated[int, Field(ge=0), _desc("offset")] = 0,
    ) -> CallToolResult:
        return _result("glossary", lambda: reads.glossary(term, offset))

    def get_evidence(
        source_id: Annotated[str, Field(min_length=1, max_length=40), _desc("source_id")],
        locator_key: Annotated[str, Field(min_length=1, max_length=200), _desc("locator_key")],
        offset: Annotated[int, Field(ge=0), _desc("text_offset")] = 0,
    ) -> CallToolResult:
        return _result("get_evidence", lambda: reads.get_evidence(source_id, locator_key, offset))

    def query_table(
        source_id: Annotated[str, Field(min_length=1, max_length=40), _desc("source_id")],
        sql: Annotated[str, Field(min_length=1, max_length=4000), _desc("sql")],
    ) -> CallToolResult:
        return _result("query_table", lambda: reads.query_table(source_id, sql))

    def get_skill(
        name: Annotated[str, Field(min_length=1, max_length=64), _desc("skill_name")],
        offset: Annotated[int, Field(ge=0), _desc("text_offset")] = 0,
    ) -> CallToolResult:
        return _result("get_skill", lambda: reads.get_skill(name, offset))

    def list_skills() -> CallToolResult:
        return _result("list_skills", reads.list_skills)

    def recent_changes(
        since: Annotated[date | None, _desc("since")] = None,
        limit: Annotated[int, Field(ge=1, le=100), _desc("limit")] = 20,
        offset: Annotated[int, Field(ge=0), _desc("offset")] = 0,
    ) -> CallToolResult:
        return _result("recent_changes", lambda: reads.recent_changes(since, limit, offset))

    functions: dict[str, Callable[..., Any]] = {
        "answer_context": answer_context,
        "search": search,
        "read_page": read_page,
        "get_index": get_index,
        "get_links": get_links,
        "glossary": glossary,
        "get_evidence": get_evidence,
        "query_table": query_table,
        "get_skill": get_skill,
        "list_skills": list_skills,
        "recent_changes": recent_changes,
    }
    return [_tool(functions[name], name, config) for name in READ_TOOLS]


def _ops_tools(ops: OpsTools, config: McpConfig) -> list[Tool]:
    def ingest_start(
        reason: Annotated[str, Field(min_length=1, max_length=500), _desc("reason")],
        scope: Annotated[IngestScope | None, _desc("ingest_scope")] = None,
    ) -> CallToolResult:
        return _result(
            "ingest_start",
            lambda: ops.ingest_start(
                reason,
                source_ids=scope.source_ids if scope else None,
                prefix=scope.prefix if scope else None,
            ),
        )

    def run_status(
        run_id: Annotated[str | None, Field(max_length=40), _desc("run_id")] = None,
    ) -> CallToolResult:
        return _result("run_status", lambda: ops.run_status(run_id))

    def list_sources(
        status: Annotated[SourceStatusName | None, _desc("source_status")] = None,
        limit: Annotated[int, Field(ge=1, le=200), _desc("limit")] = 50,
        offset: Annotated[int, Field(ge=0), _desc("offset")] = 0,
    ) -> CallToolResult:
        return _result("list_sources", lambda: ops.list_sources(status, limit, offset))

    def quality_report(
        release: Annotated[str | None, Field(max_length=40), _desc("release")] = None,
    ) -> CallToolResult:
        return _result("quality_report", lambda: ops.quality_report(release))

    def explain_source(
        source_id: Annotated[str, Field(min_length=1, max_length=40), _desc("source_id")],
    ) -> CallToolResult:
        return _result("explain_source", lambda: ops.explain_source(source_id))

    def recompile(
        source_ids: Annotated[list[str], Field(min_length=1, max_length=50), _desc("source_ids")],
        hints: Annotated[str, Field(min_length=1, max_length=2000), _desc("hints")],
    ) -> CallToolResult:
        return _result("recompile", lambda: ops.recompile(source_ids, hints))

    def list_proposals(
        status: Annotated[ProposalStatusName | None, _desc("proposal_status")] = None,
        limit: Annotated[int, Field(ge=1, le=100), _desc("limit")] = 20,
        offset: Annotated[int, Field(ge=0), _desc("offset")] = 0,
    ) -> CallToolResult:
        return _result("list_proposals", lambda: ops.list_proposals(status, limit, offset))

    def decide_proposal(
        id: Annotated[str, Field(min_length=1, max_length=40), _desc("proposal_id")],
        decision: Annotated[Literal["accept", "reject"], _desc("decision")],
        note: Annotated[str, Field(min_length=1, max_length=1000), _desc("note")],
        ctx: Context | None = None,
    ) -> CallToolResult:
        principal = principal_from_tool_context(ctx, config)
        actor = principal.label if principal else "unknown"
        return _result(
            "decide_proposal", lambda: ops.decide_proposal(id, decision, note, actor=actor)
        )

    def write_health_report(
        markdown: Annotated[str, Field(min_length=1, max_length=20000), _desc("markdown")],
    ) -> CallToolResult:
        return _result("write_health_report", lambda: ops.write_health_report(markdown))

    functions: dict[str, Callable[..., Any]] = {
        "ingest_start": ingest_start,
        "run_status": run_status,
        "list_sources": list_sources,
        "quality_report": quality_report,
        "explain_source": explain_source,
        "recompile": recompile,
        "list_proposals": list_proposals,
        "decide_proposal": decide_proposal,
        "write_health_report": write_health_report,
    }
    return [_tool(functions[name], name, config) for name in OPS_TOOLS]


def build_server(
    source: ReleaseSource, *, config: McpConfig, ops: OpsTools | None = None
) -> MCPServer:
    """MCP server with the read tools, plus the operations tools when ``ops`` is given."""
    tools = _read_tools(ReadTools(source, config), config)
    if ops is not None:
        tools += _ops_tools(ops, config)
    return MCPServer(
        SERVER_NAME,
        title="DocWiki",
        description="Cited, agent-ready Markdown wiki of a document corpus.",
        instructions=INSTRUCTIONS,
        version=__version__,
        tools=tools,
        middleware=[AuthorizationMiddleware(config, tool_levels())],
        subscriptions=False,
        log_level="WARNING",
    )


def make_source(
    release: str | Path | None, config: McpConfig, *, cache_dir: str | Path | None = None
) -> ReleaseSource:
    """Folder source for ``--release``; Blob (``mode=azure``) or ``<work_dir>`` otherwise."""
    if release:
        return FolderReleaseSource(release, ttl_s=config.pointer_ttl_s)
    if config.mode == "azure":
        from docwiki.mcp.blob import AzureBlobStorage

        storage = AzureBlobStorage(
            config.storage_account,
            containers={"work": config.work_container, "releases": config.releases_container},
        )
        return StorageReleaseSource(
            storage, cache_dir or DEFAULT_CACHE_DIR, ttl_s=config.pointer_ttl_s
        )
    return FolderReleaseSource(config.work_dir, ttl_s=config.pointer_ttl_s)


def make_ops(source: ReleaseSource, config: McpConfig) -> OpsTools:
    """Operations backend: Blob ``work`` + Storage queue (azure) or a work folder (local)."""
    shared: dict[str, Any] = {}

    def storage() -> Any:
        if "storage" not in shared:
            if config.mode == "azure":
                from docwiki.mcp.blob import AzureBlobStorage

                shared["storage"] = AzureBlobStorage(
                    config.storage_account,
                    containers={
                        "work": config.work_container,
                        "releases": config.releases_container,
                    },
                )
            else:
                shared["storage"] = FolderStorage(config.work_dir)
        return shared["storage"]

    def queue() -> IngestQueue:
        if config.mode == "azure":
            return AzureStorageQueue(config.storage_account, config.queue_name)
        return FolderQueue(storage())

    return OpsTools(source, config, store_factory=lambda: WorkStore(storage()), queue_factory=queue)


def _transport_security(bind_host: str, enabled: bool | None) -> TransportSecuritySettings:
    protect = is_loopback(bind_host) if enabled is None else enabled
    if not protect:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_LOOPBACK_HOSTS,
        allowed_origins=_LOOPBACK_ORIGINS,
    )


def create_app(
    release: str | Path | ReleaseSource | None = None,
    *,
    config: McpConfig | None = None,
    ops: OpsTools | Literal["auto"] | None = "auto",
    bind_host: str = "127.0.0.1",
    cache_dir: str | Path | None = None,
    dns_rebinding_protection: bool | None = None,
    token_validator: TokenValidator | None = None,
) -> Starlette:
    """ASGI app: stateless streamable HTTP MCP endpoint at ``/mcp`` and ``GET /healthz``.

    ``bind_host`` is the address the app will be served on: with ``DOCWIKI_AUTH_MODE=none``
    only loopback addresses are accepted. ``ops="auto"`` enables the operations tools in
    ``easyauth`` mode (role-checked) or with ``config.allow_ops``. In ``easyauth`` mode every
    call needs a valid bearer token (``token_validator``, built from the ``DOCWIKI_MCP_*``
    token settings by default; ``ValueError`` when they are incomplete) unless
    ``DOCWIKI_MCP_TOKEN_VALIDATION=off``.
    """
    config = config or McpConfig.from_env()
    if config.auth_mode == "none" and not is_loopback(bind_host):
        raise ValueError(
            f"refusing {SettingsKeys.AUTH_MODE}=none on non-loopback address {bind_host!r}: "
            "use easyauth behind Container Apps authentication, or bind 127.0.0.1"
        )
    validator = token_validator_for(config, token_validator)
    source = (
        release
        if isinstance(release, ReleaseSource)
        else make_source(release, config, cache_dir=cache_dir)
    )
    if ops == "auto":
        enabled = config.auth_mode == "easyauth" or config.allow_ops
        ops = make_ops(source, config) if enabled else None
    server = build_server(source, config=config, ops=ops)

    @server.custom_route("/healthz", methods=["GET"], include_in_schema=False)
    async def healthz(request: Request) -> JSONResponse:
        import anyio.to_thread

        try:
            snapshot = await anyio.to_thread.run_sync(source.current)
        except ReleaseUnavailableError:
            return JSONResponse(
                {"status": "unavailable", "release_id": None, "version": __version__},
                status_code=503,
            )
        return JSONResponse(
            {
                "status": "ok",
                "release_id": snapshot.release_id,
                "audience": snapshot.audience,
                "version": __version__,
            }
        )

    app = server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        transport_security=_transport_security(bind_host, dns_rebinding_protection),
        host=bind_host,
    )
    app.add_middleware(PrincipalMiddleware, config=config, validator=validator)
    app.state.docwiki_source = source
    app.state.mcp_server = server
    return app


def _parse_bind(value: str) -> tuple[str, int]:
    text = value.strip()
    if text.isdigit():
        return "127.0.0.1", int(text)
    host, sep, port = text.rpartition(":")
    if not sep or not port.isdigit():
        raise ValueError(f"--http expects HOST:PORT, got {value!r}")
    host = host.strip("[]") or "0.0.0.0"
    return host, int(port)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docwiki-mcp",
        description="DocWiki MCP server (stdio for local agents, streamable HTTP at /mcp).",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--stdio", action="store_true", help="serve over stdio (default)")
    mode.add_argument(
        "--http",
        metavar="HOST:PORT",
        help="serve stateless streamable HTTP at /mcp (':8080' binds all interfaces)",
    )
    parser.add_argument(
        "--release",
        help="portable wiki folder (.docwiki/manifest.json), release folder, releases/ folder "
        "with current.json, or a folder containing releases/current.json "
        f"(default: ${SettingsKeys.RELEASE})",
    )
    parser.add_argument(
        "--storage",
        choices=("folder", "blob"),
        help=f"where releases and work state live (default from ${SettingsKeys.MODE}: "
        "azure = blob)",
    )
    parser.add_argument(
        "--work-dir", help=f"local work folder (default ${SettingsKeys.WORK_DIR} or .local)"
    )
    parser.add_argument("--cache-dir", help="local cache for releases downloaded from blob storage")
    parser.add_argument(
        "--allow-ops",
        action="store_true",
        help="development only: expose the operations tools without authentication "
        "(stdio or loopback)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="log level (logs go to stderr)",
    )
    return parser


def _configure_telemetry() -> None:
    """Export traces and ``docwiki`` logs to Application Insights when it is configured.

    The SDK creates one OpenTelemetry span per MCP message; the authorization middleware adds
    the caller's hashed principal, access level and result size to tool-call spans.
    """
    if not os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        return
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
    except ImportError:
        logger.warning(
            "Application Insights is configured but azure-monitor-opentelemetry is missing"
        )
        return
    configure_azure_monitor(logger_name="docwiki")
    logger.info("exporting telemetry to Application Insights")


def main(argv: list[str] | None = None) -> int:
    """Run the server; returns the process exit code (2 for configuration errors)."""
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=args.log_level,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    quiet_sdk_http_logs(args.log_level)

    def fail(message: str) -> int:
        print(f"docwiki-mcp: {message}", file=sys.stderr)
        return 2

    try:
        config = McpConfig.from_env()
    except ValueError as exc:
        return fail(str(exc))
    changes: dict[str, Any] = {"allow_ops": args.allow_ops}
    if args.work_dir:
        changes["work_dir"] = args.work_dir
    if args.storage:
        changes["mode"] = "azure" if args.storage == "blob" else "local"
    config = config.with_overrides(**changes)
    if config.mode == "azure" and not config.storage_account:
        return fail(f"{SettingsKeys.STORAGE_ACCOUNT} is required with blob storage")
    release = args.release or os.environ.get(SettingsKeys.RELEASE) or None

    if args.http:
        try:
            host, port = _parse_bind(args.http)
        except ValueError as exc:
            return fail(str(exc))
        if config.auth_mode == "easyauth" and config.allow_ops:
            logger.warning("--allow-ops is ignored in easyauth mode: roles come from the token")
            config = config.with_overrides(allow_ops=False)
        try:
            app = create_app(release, config=config, bind_host=host, cache_dir=args.cache_dir)
        except ValueError as exc:
            return fail(str(exc))
        _configure_telemetry()
        import uvicorn

        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level=args.log_level.lower(),
            proxy_headers=True,
            forwarded_allow_ips="*",
            server_header=False,
        )
        return 0

    if config.auth_mode != "none":
        return fail(
            f"{SettingsKeys.AUTH_MODE}={config.auth_mode} needs --http; stdio is local only"
        )
    source = make_source(release, config, cache_dir=args.cache_dir)
    try:
        snapshot = source.current()
    except ReleaseUnavailableError as exc:
        return fail(f"cannot load the release: {exc}")
    logger.info("serving release %s over stdio", snapshot.release_id)
    server = build_server(
        source, config=config, ops=make_ops(source, config) if config.allow_ops else None
    )
    import anyio

    anyio.run(server.run_stdio_async)
    return 0


if __name__ == "__main__":
    sys.exit(main())
