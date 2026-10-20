"""Invoke the deployed DocWiki agents through the project's Responses API (``docwiki ask``).

    answer = await ask("When are the windows of the extension delivered?")
    print(answer.text, answer.sources)

The call follows the Foundry pattern for prompt agents (verified against azure-ai-projects 2.9 and
openai 3.28):

* ``AIProjectClient.agents.get(name)`` resolves the latest version, which is then pinned so that
  the answer records the exact agent version (and its definition hash) that produced it;
* ``AIProjectClient.get_openai_client()`` returns an ``AsyncOpenAI`` client bound to
  ``<project endpoint>/openai/v1`` with an Entra bearer token (scope
  ``https://ai.azure.com/.default``);
* ``responses.create(input=..., extra_body={"agent_reference": {"type": "agent_reference",
  "name": ..., "version": ...}})`` runs the agent (``conversation=`` continues a conversation);
* when the agent calls an MCP tool that requires approval, the response holds
  ``mcp_approval_request`` items: the ``approve`` callback decides (default: deny) and the client
  continues with ``previous_response_id`` and ``mcp_approval_response`` items until the agent is
  done.
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
import os
import sys
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from types import ModuleType
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, Field

from docwiki import __version__
from docwiki.agents_client.citations import Source, parse_answer, split_answer
from docwiki.agents_client.definitions import HASH_METADATA_KEY, foundry_agent_name
from docwiki.agents_client.errors import (
    AgentAuthError,
    AgentConfigurationError,
    AgentInvocationError,
    AgentNotFoundError,
)

__all__ = [
    "PROJECT_ENDPOINT_ENV",
    "TIMEOUT_ENV",
    "AgentAnswer",
    "AgentClient",
    "AgentClientSettings",
    "AgentUsage",
    "ApprovalCallback",
    "ApprovalDecision",
    "ApprovalRequest",
    "ToolCall",
    "ask",
    "format_answer",
    "prompt_approval",
]

PROJECT_ENDPOINT_ENV = "DOCWIKI_FOUNDRY_PROJECT_ENDPOINT"
TIMEOUT_ENV = "DOCWIKI_AGENT_TIMEOUT_SECONDS"
MAX_RETRIES_ENV = "DOCWIKI_AGENT_MAX_RETRIES"
DEFAULT_TIMEOUT_S = 600.0  # an answer may chain several MCP calls of up to 100 s each
DEFAULT_MAX_RETRIES = 2
DEFAULT_MAX_APPROVAL_ROUNDS = 10


class ApprovalRequest(BaseModel):
    """An MCP tool call that waits for a human decision."""

    id: str
    agent: str
    server_label: str
    name: str
    arguments: dict[str, Any] | str


class ApprovalDecision(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] | str
    approved: bool


class ToolCall(BaseModel):
    """A tool call made while answering (``status="denied"`` for a refused approval)."""

    name: str
    arguments: dict[str, Any] | str = Field(default_factory=dict)
    status: str
    server_label: str | None = None
    error: str | None = None
    output: str | None = None


class AgentUsage(BaseModel):
    """Token usage summed over every Responses API call of one question."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0
    responses: int = 0


class AgentAnswer(BaseModel):
    """The answer of a deployed agent, with parsed sources and what it took to produce it."""

    text: str
    sources: list[Source] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    approvals: list[ApprovalDecision] = Field(default_factory=list)
    usage: AgentUsage = Field(default_factory=AgentUsage)
    agent: str
    version: str | None = None
    latency_s: float = 0.0
    conversation_id: str | None = None
    response_id: str | None = None
    definition_sha256: str | None = None

    @property
    def body(self) -> str:
        """The answer without its source list."""
        return split_answer(self.text)[0]


ApprovalCallback = Callable[[ApprovalRequest], bool | Awaitable[bool]]


@dataclass(frozen=True)
class AgentClientSettings:
    project_endpoint: str
    timeout_s: float = DEFAULT_TIMEOUT_S
    # The OpenAI SDK retries 408, 409, 429, 5xx and connection errors, honouring Retry-After.
    # A 429 is rejected before the run starts; tools with side effects need human approval and
    # the operations queue messages are idempotent, so a small number of retries is safe.
    max_retries: int = DEFAULT_MAX_RETRIES
    max_approval_rounds: int = DEFAULT_MAX_APPROVAL_ROUNDS

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> AgentClientSettings:
        values = os.environ if env is None else env
        endpoint = (values.get(PROJECT_ENDPOINT_ENV) or "").strip()
        if not endpoint:
            raise AgentConfigurationError(
                f"{PROJECT_ENDPOINT_ENV} is not set (Foundry project endpoint "
                "https://<account>.services.ai.azure.com/api/projects/<project>)"
            )
        parts = urlsplit(endpoint)
        if parts.scheme != "https" or not parts.netloc:
            raise AgentConfigurationError(f"{PROJECT_ENDPOINT_ENV} must be an https URL")
        raw_timeout = (values.get(TIMEOUT_ENV) or "").strip()
        try:
            timeout = float(raw_timeout) if raw_timeout else DEFAULT_TIMEOUT_S
        except ValueError as exc:
            raise AgentConfigurationError(f"{TIMEOUT_ENV} must be a number of seconds") from exc
        if timeout <= 0:
            raise AgentConfigurationError(f"{TIMEOUT_ENV} must be positive")
        raw_retries = (values.get(MAX_RETRIES_ENV) or "").strip()
        try:
            retries = int(raw_retries) if raw_retries else DEFAULT_MAX_RETRIES
        except ValueError as exc:
            raise AgentConfigurationError(f"{MAX_RETRIES_ENV} must be an integer") from exc
        if retries < 0:
            raise AgentConfigurationError(f"{MAX_RETRIES_ENV} must be zero or more")
        return cls(project_endpoint=endpoint, timeout_s=timeout, max_retries=retries)


class AgentClient:
    """Reusable client for many questions (the evaluation runner keeps one open)."""

    def __init__(
        self,
        settings: AgentClientSettings | None = None,
        *,
        credential: Any | None = None,
        project_client: Any | None = None,
        openai_client: Any | None = None,
        http_client: Any | None = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        if settings is None and project_client is None:
            settings = AgentClientSettings.from_env()
        self.settings = settings
        self._credential = credential
        self._owns_credential = False
        self._project = project_client
        self._owns_project = False
        self._openai = openai_client
        self._owns_openai = False
        self._http_client = http_client
        self._clock = clock

    async def __aenter__(self) -> AgentClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the clients this instance created (injected ones are left open)."""
        if self._owns_openai and self._openai is not None:
            client, self._openai = self._openai, None
            await client.close()
        if self._owns_project and self._project is not None:
            project, self._project = self._project, None
            await project.close()
        if self._owns_credential and self._credential is not None:
            credential, self._credential = self._credential, None
            await credential.close()

    @property
    def _max_rounds(self) -> int:
        return self.settings.max_approval_rounds if self.settings else DEFAULT_MAX_APPROVAL_ROUNDS

    def _ensure_project(self) -> Any:
        if self._project is None:
            if self.settings is None:
                raise AgentConfigurationError("no Foundry project settings")
            projects_aio = _require("azure.ai.projects.aio")
            if self._credential is None:
                identity_aio = _require("azure.identity.aio")
                self._credential = identity_aio.DefaultAzureCredential()
                self._owns_credential = True
            self._project = projects_aio.AIProjectClient(
                endpoint=self.settings.project_endpoint,
                credential=self._credential,
                user_agent=f"docwiki/{__version__}",
            )
            self._owns_project = True
        return self._project

    def _ensure_openai(self) -> Any:
        if self._openai is None:
            options: dict[str, Any] = {}
            if self.settings is not None:
                options["timeout"] = self.settings.timeout_s
                options["max_retries"] = self.settings.max_retries
            if self._http_client is not None:
                options["http_client"] = self._http_client
            self._openai = self._ensure_project().get_openai_client(**options)
            self._owns_openai = True
        return self._openai

    async def latest_version(self, agent: str) -> tuple[str, str | None]:
        """``(version, definition_sha256)`` of the latest version of an agent."""
        name = foundry_agent_name(agent)
        try:
            details = await self._ensure_project().agents.get(name)
        except Exception as exc:
            error = _azure_error(exc, name)
            if error is None:
                raise
            raise error from exc
        latest = _get(_get(details, "versions"), "latest")
        version = _get(latest, "version")
        if version is None:
            raise AgentInvocationError(f"agent {name} has no version")
        metadata = _get(latest, "metadata") or {}
        return str(version), _get(metadata, HASH_METADATA_KEY)

    async def ask(
        self,
        question: str,
        *,
        agent: str = "researcher",
        conversation_id: str | None = None,
        approve: ApprovalCallback | None = None,
        version: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> AgentAnswer:
        """Ask a deployed agent (``researcher``, ``librarian`` or a Foundry agent name).

        ``approve`` is called for every MCP tool call that needs approval and must return ``True``
        to approve it; without a callback every such call is denied. ``version`` pins an agent
        version; by default the latest version is resolved and pinned. ``headers`` are extra HTTP
        headers of every Responses API call of this question (a gateway reads them, for example
        to rate-limit per visitor).
        """
        if not question.strip():
            raise ValueError("the question is empty")
        name = foundry_agent_name(agent)
        started = self._clock()
        definition_sha256: str | None = None
        if version is None:
            version, definition_sha256 = await self.latest_version(name)
        reference = {"type": "agent_reference", "name": name, "version": version}
        openai = self._ensure_openai()
        request: dict[str, Any] = {"input": question, "extra_body": {"agent_reference": reference}}
        if conversation_id:
            request["conversation"] = conversation_id
        if headers:
            request["extra_headers"] = dict(headers)
        response = await self._create(openai, name, request)
        responses = [response]
        approvals: list[ApprovalDecision] = []
        tool_calls = _tool_calls(response)
        waiting = 0.0
        rounds = 0
        while True:
            pending = _approval_requests(response, name)
            if not pending:
                break
            if rounds >= self._max_rounds:
                raise AgentInvocationError(
                    f"{name} still requests approvals after {self._max_rounds} rounds"
                )
            rounds += 1
            items: list[dict[str, Any]] = []
            for pending_request in pending:
                waited_from = self._clock()
                approved = await _decide(approve, pending_request)
                waiting += self._clock() - waited_from
                approvals.append(
                    ApprovalDecision(
                        id=pending_request.id,
                        name=pending_request.name,
                        arguments=pending_request.arguments,
                        approved=approved,
                    )
                )
                if not approved:
                    tool_calls.append(
                        ToolCall(
                            name=pending_request.name,
                            arguments=pending_request.arguments,
                            status="denied",
                            server_label=pending_request.server_label,
                        )
                    )
                items.append(
                    {
                        "type": "mcp_approval_response",
                        "approve": approved,
                        "approval_request_id": pending_request.id,
                    }
                )
            follow_up = {
                "input": items,
                "previous_response_id": _get(response, "id"),
                "extra_body": {"agent_reference": reference},
            }
            if headers:
                follow_up["extra_headers"] = dict(headers)
            response = await self._create(openai, name, follow_up)
            responses.append(response)
            tool_calls.extend(_tool_calls(response))
        text = "\n\n".join(chunk for item in responses for chunk in _message_texts(item))
        conversation = _get(_get(response, "conversation"), "id") or conversation_id
        return AgentAnswer(
            text=text,
            sources=parse_answer(text),
            tool_calls=tool_calls,
            approvals=approvals,
            usage=_usage(responses),
            agent=name,
            version=version,
            latency_s=round(max(self._clock() - started - waiting, 0.0), 3),
            conversation_id=conversation,
            response_id=_get(response, "id"),
            definition_sha256=definition_sha256,
        )

    async def _create(self, openai: Any, name: str, request: dict[str, Any]) -> Any:
        try:
            response = await openai.responses.create(**request)
        except Exception as exc:
            error = _openai_error(exc, name)
            if error is None:
                raise
            raise error from exc
        _check_response(response, name)
        return response


async def ask(
    question: str,
    *,
    agent: str = "researcher",
    conversation_id: str | None = None,
    approve: ApprovalCallback | None = None,
    version: str | None = None,
    headers: Mapping[str, str] | None = None,
    client: AgentClient | None = None,
) -> AgentAnswer:
    """Ask a deployed DocWiki agent; see :meth:`AgentClient.ask`.

    Without ``client`` a client is built from the environment (``DOCWIKI_FOUNDRY_PROJECT_ENDPOINT``,
    ``DefaultAzureCredential``) and closed afterwards.
    """
    options: dict[str, Any] = {
        "agent": agent,
        "conversation_id": conversation_id,
        "approve": approve,
        "version": version,
    }
    if headers:  # callers that pass their own client keep working without the new argument
        options["headers"] = headers
    if client is not None:
        return await client.ask(question, **options)
    async with AgentClient() as owned:
        return await owned.ask(question, **options)


async def prompt_approval(request: ApprovalRequest) -> bool:
    """Interactive approval on the console (used by ``docwiki ask`` in a terminal)."""
    arguments = (
        json.dumps(request.arguments, indent=2, ensure_ascii=False)
        if isinstance(request.arguments, dict)
        else request.arguments
    )
    print(
        f"\n{request.agent} wants to call {request.server_label}.{request.name} with:\n{arguments}",
        file=sys.stderr,
    )
    reply = await asyncio.to_thread(input, "Approve this call? [y/N] ")
    return reply.strip().lower() in ("y", "yes")


def format_answer(answer: AgentAnswer) -> str:
    """Answer text followed by a one-line receipt (agent, version, tool calls, tokens, latency)."""
    receipt = (
        f"[{answer.agent} v{answer.version or '?'} · {len(answer.tool_calls)} tool calls · "
        f"{answer.usage.total_tokens} tokens · {answer.latency_s:.1f} s]"
    )
    denied = [decision.name for decision in answer.approvals if not decision.approved]
    if denied:
        receipt += f"\n[denied: {', '.join(denied)}]"
    return f"{answer.text.strip()}\n\n{receipt}"


# ---------------------------------------------------------------------- response helpers


def _require(module: str) -> ModuleType:
    try:
        return importlib.import_module(module)
    except ImportError as exc:
        raise AgentConfigurationError(
            f"docwiki.agents_client needs '{module.split('.')[0]}' from the azure extra "
            "(uv sync --extra azure)"
        ) from exc


def _get(item: Any, name: str, default: Any = None) -> Any:
    if item is None:
        return default
    if isinstance(item, Mapping):
        return item.get(name, default)
    return getattr(item, name, default)


def _output(response: Any) -> Sequence[Any]:
    return _get(response, "output") or ()


def _arguments(raw: Any) -> dict[str, Any] | str:
    if isinstance(raw, Mapping):
        return dict(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            return raw
        return parsed if isinstance(parsed, dict) else raw
    return {} if raw is None else str(raw)


def _error_text(error: Any) -> str | None:
    if error is None or error == "":
        return None
    if isinstance(error, str):
        return error
    message = _get(error, "message")
    code = _get(error, "code")
    if message:
        return f"{code}: {message}" if code is not None else str(message)
    content = _get(error, "content")
    if content is not None:
        return str(content)
    return str(error)


def _message_texts(response: Any) -> list[str]:
    texts: list[str] = []
    for item in _output(response):
        if _get(item, "type") != "message":
            continue
        parts = [
            _get(part, "text") or ""
            for part in _get(item, "content") or ()
            if _get(part, "type") == "output_text"
        ]
        text = "".join(parts).strip()
        if text:
            texts.append(text)
    return texts


def _tool_failure(output: Any) -> str | None:
    """``"<code>: <message>"`` when a DocWiki MCP result is ``{"ok": false, "error": {...}}``.

    The MCP server returns tool failures as normal results because any MCP error aborts the
    Foundry turn (docwiki.mcp.errors); the client still reports them as failed calls. The output
    may also arrive as MCP content parts (``[{"type": "text", "text": "{...}"}]``).
    """
    if not isinstance(output, str) or output.lstrip()[:1] not in ("{", "["):
        return None
    try:
        payload = json.loads(output)
        if isinstance(payload, list):
            texts = [part.get("text") for part in payload if isinstance(part, dict)]
            payload = json.loads(texts[0]) if len(texts) == 1 and texts[0] else None
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict) or payload.get("ok") is not False:
        return None
    return _error_text(payload.get("error")) or "failed without error details"


def _tool_calls(response: Any) -> list[ToolCall]:
    calls: list[ToolCall] = []
    for item in _output(response):
        kind = str(_get(item, "type") or "")
        if kind == "mcp_call":
            output = _get(item, "output")
            error = _error_text(_get(item, "error"))
            status = _get(item, "status") or ("failed" if error else "completed")
            failure = None if error else _tool_failure(output)
            if failure is not None:
                status, error = "failed", failure
            calls.append(
                ToolCall(
                    name=str(_get(item, "name") or ""),
                    arguments=_arguments(_get(item, "arguments")),
                    status=str(status),
                    server_label=_get(item, "server_label"),
                    error=error,
                    output=output,
                )
            )
        elif kind == "mcp_list_tools" and _get(item, "error"):
            # A failed tool listing (unreachable server, 401/403) explains an answer without tools.
            calls.append(
                ToolCall(
                    name="mcp_list_tools",
                    status="failed",
                    server_label=_get(item, "server_label"),
                    error=_error_text(_get(item, "error")),
                )
            )
        elif kind.endswith("_call"):
            calls.append(
                ToolCall(
                    name=str(_get(item, "name") or kind),
                    arguments=_arguments(_get(item, "arguments")),
                    status=str(_get(item, "status") or "completed"),
                )
            )
    return calls


def _approval_requests(response: Any, agent: str) -> list[ApprovalRequest]:
    return [
        ApprovalRequest(
            id=str(_get(item, "id")),
            agent=agent,
            server_label=str(_get(item, "server_label") or ""),
            name=str(_get(item, "name") or ""),
            arguments=_arguments(_get(item, "arguments")),
        )
        for item in _output(response)
        if _get(item, "type") == "mcp_approval_request"
    ]


async def _decide(approve: ApprovalCallback | None, request: ApprovalRequest) -> bool:
    if approve is None:
        return False
    decision = approve(request)
    if inspect.isawaitable(decision):
        decision = await decision
    return decision is True


def _usage(responses: Sequence[Any]) -> AgentUsage:
    usage = AgentUsage(responses=len(responses))
    for response in responses:
        data = _get(response, "usage")
        if data is None:
            continue
        usage.input_tokens += int(_get(data, "input_tokens") or 0)
        usage.output_tokens += int(_get(data, "output_tokens") or 0)
        usage.total_tokens += int(_get(data, "total_tokens") or 0)
        usage.cached_input_tokens += int(
            _get(_get(data, "input_tokens_details"), "cached_tokens") or 0
        )
        usage.reasoning_tokens += int(
            _get(_get(data, "output_tokens_details"), "reasoning_tokens") or 0
        )
    return usage


def _check_response(response: Any, name: str) -> None:
    status = _get(response, "status")
    if status == "failed":
        error = _get(response, "error")
        code = _get(error, "code")
        raise AgentInvocationError(
            f"{name} failed: {_error_text(error) or 'no error details'}",
            code=str(code) if code is not None else None,
        )
    if status in ("incomplete", "cancelled"):
        reason = _get(_get(response, "incomplete_details"), "reason")
        raise AgentInvocationError(f"{name} returned a {status} response ({reason or 'unknown'})")
    if any(_get(item, "type") == "oauth_consent_request" for item in _output(response)):
        raise AgentInvocationError(
            f"{name} asks for OAuth consent: the DocWiki MCP connection must use an Entra identity "
            "(agentic-identity or project-managed-identity), see agents/README.md"
        )


def _openai_error(exc: Exception, name: str) -> AgentInvocationError | None:
    try:
        openai = importlib.import_module("openai")
    except ImportError:  # pragma: no cover - openai is installed with the azure extra
        return None
    if isinstance(exc, openai.APIStatusError):
        status = exc.status_code
        code = getattr(exc, "code", None)
        request_id = getattr(exc, "request_id", None)
        detail = f"HTTP {status}" + (f" ({code})" if code else "")
        if status in (401, 403):
            return AgentAuthError(
                f"not allowed to call {name}: {detail}; the caller needs the Foundry User "
                "(Azure AI User) role on the project",
                status_code=status,
                code=code,
                request_id=request_id,
            )
        if status == 404:
            return AgentNotFoundError(
                f"{name} was not found: {detail}; deploy it with `uv run python agents/deploy.py`",
                status_code=status,
                code=code,
                request_id=request_id,
            )
        if code == "tool_user_error":
            # Foundry ends the whole turn when an MCP tool answers with a protocol error
            # (ADR 0003); DocWiki tools return failures as {"ok": false} results instead.
            return AgentInvocationError(
                f"{name} failed: {detail}: Foundry ended the turn because an MCP tool call "
                "returned an error; check the MCP server log and its version",
                status_code=status,
                code=code,
                request_id=request_id,
            )
        return AgentInvocationError(
            f"{name} failed: {detail}: {exc.message}",
            status_code=status,
            code=code,
            request_id=request_id,
        )
    if isinstance(exc, openai.APITimeoutError):
        return AgentInvocationError(f"{name} did not answer in time ({TIMEOUT_ENV})")
    if isinstance(exc, openai.APIConnectionError):
        return AgentInvocationError(f"could not reach the Foundry project to call {name}: {exc}")
    return None


def _azure_error(exc: Exception, name: str) -> AgentInvocationError | None:
    try:
        azure_errors = importlib.import_module("azure.core.exceptions")
    except ImportError:  # pragma: no cover - azure-core is installed with the azure extra
        return None
    if isinstance(exc, azure_errors.ResourceNotFoundError):
        return AgentNotFoundError(
            f"agent {name} is not deployed; deploy it with `uv run python agents/deploy.py`",
            status_code=404,
        )
    if isinstance(exc, azure_errors.ClientAuthenticationError):
        return AgentAuthError(
            f"cannot authenticate to the Foundry project to read {name}: {exc.message}; sign in "
            "(az login) or use a managed identity with the Foundry User role",
            status_code=exc.status_code,
        )
    if isinstance(exc, azure_errors.HttpResponseError):
        status = exc.status_code
        if status == 403:
            return AgentAuthError(
                f"not allowed to read {name}: the caller needs the Foundry User role",
                status_code=status,
            )
        return AgentInvocationError(f"reading {name} failed: {exc.message}", status_code=status)
    return None
