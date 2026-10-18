"""``FoundryLlmClient``: Microsoft Foundry project endpoint, Entra auth and the Responses API.

The client authenticates with ``DefaultAzureCredential`` (never API keys), obtains an
``AsyncOpenAI`` client from ``azure.ai.projects.aio.AIProjectClient.get_openai_client()``
(base URL ``<project endpoint>/openai/v1``, token scope ``https://ai.azure.com/.default``) and
calls ``responses.create`` with a strict JSON-schema text format, no tools and ``store=False``.
Retries, Retry-After handling, rate limiting and concurrency are handled here, with the OpenAI
SDK's own retries disabled (``max_retries=0``) so the policy is applied exactly once.
"""

from __future__ import annotations

import asyncio
import functools
import importlib
import importlib.util
import json
import logging
import random
import time
from dataclasses import dataclass
from types import ModuleType
from typing import Any, ClassVar, Literal

from pydantic import ValidationError

from docwiki import __version__
from docwiki.llm.client import BaseLlmClient
from docwiki.llm.errors import (
    LlmAuthError,
    LlmConfigurationError,
    LlmContentFiltered,
    LlmError,
    LlmInvalidOutput,
    LlmOutputTruncated,
    LlmRateLimited,
    LlmServiceError,
    LlmTimeout,
)
from docwiki.llm.ledger import UsageLedger
from docwiki.llm.prices import PriceTable
from docwiki.llm.ratelimit import Clock, DeploymentRateLimiter, LoopLocal, Sleep
from docwiki.llm.request import LlmRequest, estimate_text_tokens
from docwiki.llm.retry import RetryPolicy, parse_retry_after
from docwiki.llm.settings import ENV_DEPLOYMENT, ENV_TIMEOUT, LlmSettings, RateLimit
from docwiki.llm.types import (
    TIERS,
    DeploymentInfo,
    LlmUsage,
    Origin,
    StructuredResult,
    TextPart,
    Tier,
    split_model_version,
)

logger = logging.getLogger("docwiki.llm")

FailureKind = Literal[
    "rate_limited", "timeout", "server", "connection", "auth", "content_filter", "client"
]
_CONTENT_FILTER_CODES = frozenset(
    {"content_filter", "content_policy_violation", "responsibleaipolicyviolation"}
)
_POLICY_RESPONSE_CODES = frozenset(
    {"image_content_policy_violation", "bio_policy", "misalignment_policy_violation"}
)
_MAX_MESSAGE_CHARS = 500
_MAX_REPAIR_ERRORS = 20
_MAX_RAW_OUTPUT_CHARS = 20_000


@dataclass
class _Failure:
    kind: FailureKind
    retryable: bool
    detail: str
    status_code: int | None = None
    code: str | None = None
    request_id: str | None = None
    retry_after_s: float | None = None


class FoundryLlmClient(BaseLlmClient):
    """Live client for the Foundry project endpoint (Responses API, strict structured outputs)."""

    origin: ClassVar[Origin] = "foundry"

    def __init__(
        self,
        settings: LlmSettings | None = None,
        *,
        ledger: UsageLedger | None = None,
        credential: Any | None = None,
        project_client: Any | None = None,
        http_client: Any | None = None,
        retry_policy: RetryPolicy | None = None,
        clock: Clock = time.monotonic,
        sleep: Sleep = asyncio.sleep,
        rng: random.Random | None = None,
        tracer_provider: Any | None = None,
    ) -> None:
        settings = settings if settings is not None else LlmSettings.from_env()
        if ledger is None:
            ledger = UsageLedger(PriceTable.load(settings.price_table))
        super().__init__(ledger=ledger, tracer_provider=tracer_provider)
        if project_client is None:
            settings.require_foundry(tiers=())
        self.settings = settings
        self._credential = credential
        self._owns_credential = credential is None
        self._project = project_client
        self._owns_project = project_client is None
        self._http_client = http_client
        self._openai: Any | None = None
        self._openai_loop: asyncio.AbstractEventLoop | None = None
        self._retry = retry_policy or RetryPolicy.from_settings(settings)
        self._clock = clock
        self._sleep = sleep
        self._rng = rng if rng is not None else random.Random()
        self._semaphore: LoopLocal[asyncio.Semaphore] = LoopLocal(
            functools.partial(asyncio.Semaphore, settings.concurrency)
        )
        self._limiters: dict[str, DeploymentRateLimiter] = {}
        for name, limit in self._deployment_limits().items():
            self._limiters[name] = DeploymentRateLimiter(name, limit, clock=clock, sleep=sleep)
        self._described: dict[Tier, DeploymentInfo] = {}

    # ------------------------------------------------------------------ public helpers

    def limiter(self, deployment: str) -> DeploymentRateLimiter:
        """The rate limiter of ``deployment`` (shared by every tier using it)."""
        limiter = self._limiters.get(deployment)
        if limiter is None:
            limiter = DeploymentRateLimiter(
                deployment, RateLimit(), clock=self._clock, sleep=self._sleep
            )
            self._limiters[deployment] = limiter
        return limiter

    async def describe(self, tier: Tier) -> DeploymentInfo:
        """Ask the Foundry project which model and version the tier's deployment serves."""
        cached = self._described.get(tier)
        if cached is not None:
            return cached
        deployment = self.settings.deployment(tier)
        project = self._ensure_project()
        try:
            found = await project.deployments.get(deployment)
        except Exception as exc:
            raise _describe_error(exc, tier, deployment) from exc
        sku = getattr(found, "sku", None)
        info = DeploymentInfo(
            tier=tier,
            deployment=deployment,
            model_name=getattr(found, "model_name", None),
            model_version=getattr(found, "model_version", None),
            model_publisher=getattr(found, "model_publisher", None),
            sku=getattr(sku, "name", None),
            capacity=getattr(sku, "capacity", None),
            source="service",
        )
        self._described[tier] = info
        return info

    async def aclose(self) -> None:
        """Close the clients this instance created (injected ones are left open)."""
        openai_client, self._openai = self._openai, None
        if openai_client is not None:
            await openai_client.close()
        if self._owns_project and self._project is not None:
            project, self._project = self._project, None
            await project.close()
        if self._owns_credential and self._credential is not None:
            credential, self._credential = self._credential, None
            await credential.close()

    # ------------------------------------------------------------------ BaseLlmClient hooks

    def _pricing_model(self, tier: Tier) -> str | None:
        return self.settings.model_for(tier)

    async def _run(self, request: LlmRequest) -> StructuredResult[Any]:
        deployment = self.settings.deployment(request.tier)
        try:
            return await self._structured(request, deployment)
        except LlmError as exc:
            exc.with_context(deployment=deployment)
            raise

    # ------------------------------------------------------------------ implementation

    async def _structured(self, request: LlmRequest, deployment: str) -> StructuredResult[Any]:
        client = self._ensure_openai()
        limiter = self.limiter(deployment)
        input_items: list[dict[str, Any]] = [_user_message(request)]
        usage = LlmUsage()
        retries = 0
        attempts = 0
        wait_s = 0.0
        model: str | None = None
        extra_tokens = 0
        for repairing in (False, True):
            try:
                response, call_retries, call_wait = await self._create(
                    client, request, deployment, limiter, input_items, extra_tokens
                )
            except LlmError as exc:
                exc.retries += retries
                exc.attempts = attempts
                exc.usage = usage + exc.usage
                exc.model = exc.model or model
                raise
            retries += call_retries
            wait_s += call_wait
            attempts += 1
            usage = usage + _usage_of(response)
            model = getattr(response, "model", None) or model
            context: dict[str, Any] = {
                "deployment": deployment,
                "model": model,
                "retries": retries,
                "attempts": attempts,
                "usage": usage,
            }
            text = _output_text(response, request, context)
            try:
                data = _parse_json_object(text)
                parsed = request.output.model_validate(data)
            except ValueError as exc:  # json errors and pydantic ValidationError
                errors = _validation_messages(exc)
                if repairing:
                    raise LlmInvalidOutput(
                        f"Output for schema '{request.schema_name}' did not validate against "
                        f"{request.output.__name__} after one repair attempt: {errors[0]}",
                        errors=errors,
                        raw_output=text[:_MAX_RAW_OUTPUT_CHARS],
                        **context,
                    ) from exc
                logger.warning(
                    "llm output for schema %s did not validate (%d error(s)); asking for a repair",
                    request.schema_name,
                    len(errors),
                )
                repair_items = _repair_messages(text, errors, request.schema_name)
                input_items = [*input_items, *repair_items]
                extra_tokens = sum(
                    estimate_text_tokens(str(item["content"])) for item in repair_items
                )
                continue
            _, version = split_model_version(model)
            return StructuredResult(
                output=parsed,
                output_json=data,
                usage=usage,
                tier=request.tier,
                deployment=deployment,
                model=model,
                model_version=version,
                schema_name=request.schema_name,
                prompt_version=request.prompt_version,
                request_hash=request.request_hash,
                latency_s=0.0,
                wait_s=wait_s,
                retries=retries,
                attempts=attempts,
                origin="foundry",
                response_id=getattr(response, "id", None),
            )
        raise AssertionError("unreachable")  # pragma: no cover

    async def _create(
        self,
        client: Any,
        request: LlmRequest,
        deployment: str,
        limiter: DeploymentRateLimiter,
        input_items: list[dict[str, Any]],
        extra_tokens: int,
    ) -> tuple[Any, int, float]:
        """One model call with rate limiting, concurrency control and transport retries."""
        estimate = request.estimated_input_tokens() + extra_tokens + request.max_output_tokens
        retries = 0
        waited = 0.0
        while True:
            waited += await limiter.acquire(estimate)
            cause: BaseException | None = None
            try:
                async with self._semaphore.get():
                    response = await client.responses.create(
                        model=deployment,
                        instructions=request.system,
                        input=input_items,
                        text={
                            "format": {
                                "type": "json_schema",
                                "name": request.schema_name,
                                "schema": request.json_schema,
                                "strict": True,
                            }
                        },
                        max_output_tokens=request.max_output_tokens,
                        store=False,
                    )
            except Exception as exc:
                failure = _classify_exception(exc)
                if failure is None:
                    raise
                cause = exc
            else:
                failure = _classify_response(response)
                if failure is None:
                    return response, retries, waited
            exhausted = retries >= self._retry.max_retries
            too_long = not self._retry.allows_retry_after(failure.retry_after_s)
            if not failure.retryable or exhausted or too_long:
                raise self._error(failure, request, deployment, retries, too_long) from cause
            delay = self._retry.delay(retries, failure.retry_after_s, self._rng)
            retries += 1
            logger.warning(
                "llm retry %d/%d: tier=%s deployment=%s reason=%s status=%s delay=%.2fs",
                retries,
                self._retry.max_retries,
                request.tier,
                deployment,
                failure.kind,
                failure.status_code,
                delay,
            )
            if failure.kind == "rate_limited":
                limiter.penalize(delay)
            else:
                await self._sleep(delay)
                waited += delay

    def _error(
        self,
        failure: _Failure,
        request: LlmRequest,
        deployment: str,
        retries: int,
        retry_after_too_long: bool,
    ) -> LlmError:
        attempts = retries + 1
        where = f"Foundry deployment '{deployment}' ({request.tier} tier)"
        tried = f"after {attempts} attempt{'s' if attempts > 1 else ''}"
        status = f"HTTP {failure.status_code}" if failure.status_code else failure.kind
        context: dict[str, Any] = {
            "deployment": deployment,
            "status_code": failure.status_code,
            "request_id": failure.request_id,
            "retries": retries,
        }
        detail = f": {failure.detail}" if failure.detail else ""
        if failure.kind == "rate_limited":
            if retry_after_too_long:
                message = (
                    f"{where} is rate limited ({status}) and asked to wait "
                    f"{failure.retry_after_s:.0f} s, more than the allowed "
                    f"{self._retry.max_retry_after_s:.0f} s (DOCWIKI_LLM_MAX_RETRY_AFTER_SECONDS)"
                )
            else:
                message = (
                    f"{where} is still rate limited ({status}) {tried}; lower "
                    "DOCWIKI_LLM_CONCURRENCY or the tier's TPM/RPM settings, or raise the "
                    "deployment capacity"
                )
            return LlmRateLimited(message, retry_after_s=failure.retry_after_s, **context)
        if failure.kind == "timeout":
            return LlmTimeout(
                f"Request to {where} timed out {tried} (client timeout "
                f"{self.settings.timeout_s:.0f} s, {ENV_TIMEOUT}){detail}",
                **context,
            )
        if failure.kind == "auth":
            return LlmAuthError(
                f"Entra authentication failed for {where} ({status}){detail}. Make sure "
                "DefaultAzureCredential can get a token (managed identity with AZURE_CLIENT_ID "
                "in Azure, `az login` locally) and that the identity has the Azure AI User role "
                "on the Foundry project",
                **context,
            )
        if failure.kind == "content_filter":
            return LlmContentFiltered(
                f"{where} blocked the request with content filtering ({status}){detail}",
                reason=failure.code or "content_filter",
                **context,
            )
        if failure.status_code == 404:
            message = (
                f"{where} was not found (HTTP 404); check {ENV_DEPLOYMENT[request.tier]} and "
                f"the Foundry project endpoint{detail}"
            )
        elif failure.retryable:
            message = f"{where} failed ({status}) {tried}{detail}"
        else:
            message = f"{where} rejected the request ({status}){detail}"
        return LlmServiceError(message, code=failure.code, **context)

    def _deployment_limits(self) -> dict[str, RateLimit]:
        limits: dict[str, RateLimit] = {}
        for tier in TIERS:
            name = self.settings.deployment_name(tier)
            if not name:
                continue
            limit = self.settings.rate_limit(tier)
            limits[name] = limits[name].merge(limit) if name in limits else limit
        return limits

    def _ensure_project(self) -> Any:
        if self._project is None:
            projects_aio = _require("azure.ai.projects.aio")
            if self._credential is None:
                identity_aio = _require("azure.identity.aio")
                self._credential = identity_aio.DefaultAzureCredential(**_azure_transport())
            self._project = projects_aio.AIProjectClient(
                endpoint=self.settings.project_endpoint,
                credential=self._credential,
                user_agent=f"docwiki/{__version__}",
                **_azure_transport(),
            )
        return self._project

    def _ensure_openai(self) -> Any:
        loop = asyncio.get_running_loop()
        if self._openai is None or self._openai_loop is not loop:
            # httpx connection pools are bound to the event loop that created them.
            options: dict[str, Any] = {"max_retries": 0, "timeout": self.settings.timeout_s}
            if self._http_client is not None:
                options["http_client"] = self._http_client
            self._openai = self._ensure_project().get_openai_client(**options)
            self._openai_loop = loop
        return self._openai


# ---------------------------------------------------------------------- module helpers


def _require(module: str) -> ModuleType:
    try:
        return importlib.import_module(module)
    except ImportError as exc:
        raise LlmConfigurationError(
            f"FoundryLlmClient needs the '{module.split('.')[0]}' packages from the azure extra "
            "(uv sync --extra azure)"
        ) from exc


@functools.cache
def _openai() -> ModuleType:
    return _require("openai")


def _azure_transport() -> dict[str, Any]:
    """azure-core async pipelines default to aiohttp; fall back to requests when it is absent."""
    if importlib.util.find_spec("aiohttp") is not None:
        return {}
    transport = _require("azure.core.pipeline.transport")
    return {"transport": transport.AsyncioRequestsTransport()}


def _user_message(request: LlmRequest) -> dict[str, Any]:
    content: list[dict[str, Any]] = []
    for part in request.parts:
        if isinstance(part, TextPart):
            content.append({"type": "input_text", "text": part.text})
        else:
            content.append(
                {"type": "input_image", "image_url": part.data_url(), "detail": part.detail}
            )
    return {"role": "user", "content": content}


def _repair_messages(
    previous_output: str, errors: tuple[str, ...], schema_name: str
) -> list[dict[str, Any]]:
    listed = "\n".join(f"- {error}" for error in errors[:_MAX_REPAIR_ERRORS])
    feedback = (
        f"Your previous answer did not validate against the required JSON schema "
        f"'{schema_name}'.\nValidation errors:\n{listed}\n"
        "Return the complete, corrected JSON object only."
    )
    items: list[dict[str, Any]] = []
    if previous_output.strip():
        items.append({"role": "assistant", "content": previous_output})
    items.append({"role": "user", "content": feedback})
    return items


def _usage_of(response: Any) -> LlmUsage:
    usage = getattr(response, "usage", None)
    if usage is None:
        return LlmUsage()
    input_details = getattr(usage, "input_tokens_details", None)
    output_details = getattr(usage, "output_tokens_details", None)
    return LlmUsage(
        input_tokens=getattr(usage, "input_tokens", 0) or 0,
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
        cached_input_tokens=getattr(input_details, "cached_tokens", 0) or 0,
        reasoning_tokens=getattr(output_details, "reasoning_tokens", 0) or 0,
    )


def _output_text(response: Any, request: LlmRequest, context: dict[str, Any]) -> str:
    status = getattr(response, "status", None)
    if status == "incomplete":
        details = getattr(response, "incomplete_details", None)
        reason = getattr(details, "reason", None)
        if reason == "max_output_tokens":
            raise LlmOutputTruncated(
                f"Output for schema '{request.schema_name}' hit max_output_tokens="
                f"{request.max_output_tokens} before the JSON object was complete; raise the "
                "budget or split the input",
                raw_output=_safe_output_text(response)[:_MAX_RAW_OUTPUT_CHARS],
                **context,
            )
        if reason == "content_filter":
            raise LlmContentFiltered(
                "The completion was blocked by content filtering",
                reason="content_filter",
                **context,
            )
        raise LlmInvalidOutput(f"The response is incomplete (reason: {reason})", **context)
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", None) != "message":
            continue
        for content in getattr(item, "content", None) or []:
            if getattr(content, "type", None) == "refusal":
                refusal = str(getattr(content, "refusal", "") or "")
                raise LlmContentFiltered(
                    f"The model refused to answer: {refusal[:_MAX_MESSAGE_CHARS]}",
                    reason="refusal",
                    **context,
                )
    return _safe_output_text(response)


def _safe_output_text(response: Any) -> str:
    text = getattr(response, "output_text", "")
    return text if isinstance(text, str) else ""


def _parse_json_object(text: str) -> dict[str, Any]:
    if not text.strip():
        raise ValueError("the output is empty")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("the output is not a JSON object")
    return data


def _validation_messages(exc: ValueError) -> tuple[str, ...]:
    if isinstance(exc, ValidationError):
        messages = tuple(
            f"{'.'.join(str(part) for part in error['loc']) or '<root>'}: {error['msg']}"
            for error in exc.errors(include_url=False, include_input=False)
        )
        return messages or ("<root>: invalid output",)
    if isinstance(exc, json.JSONDecodeError):
        return (f"<root>: invalid JSON ({exc.msg} at line {exc.lineno} column {exc.colno})",)
    return (f"<root>: {exc}",)


def _request_id(headers: Any) -> str | None:
    if headers is None:
        return None
    for name in ("x-request-id", "apim-request-id", "x-ms-request-id"):
        value = headers.get(name)
        if value:
            return str(value)
    return None


def _service_detail(exc: Any) -> str:
    body = getattr(exc, "body", None)
    message = None
    if isinstance(body, dict):
        message = body.get("message")
    if not message:
        message = getattr(exc, "message", None) or str(exc)
    return str(message)[:_MAX_MESSAGE_CHARS]


def _is_content_filter(exc: Any) -> bool:
    codes = {str(getattr(exc, "code", "") or "").lower()}
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        codes.add(str(body.get("code", "") or "").lower())
        inner = body.get("innererror") or body.get("inner_error")
        if isinstance(inner, dict):
            codes.add(str(inner.get("code", "") or "").lower())
    return bool(codes & _CONTENT_FILTER_CODES)


def _is_azure_auth_error(exc: BaseException) -> bool:
    try:
        from azure.core.exceptions import ClientAuthenticationError
    except ImportError:
        return False
    return isinstance(exc, ClientAuthenticationError)


def _classify_exception(exc: BaseException) -> _Failure | None:
    """Map SDK/credential exceptions to a failure kind; ``None`` for unexpected exceptions."""
    if _is_azure_auth_error(exc):
        first_line = (str(exc).strip().splitlines() or [""])[0]
        return _Failure("auth", False, f"credential error: {first_line[:_MAX_MESSAGE_CHARS]}")
    openai = _openai()
    if isinstance(exc, openai.APITimeoutError):
        return _Failure("timeout", True, "")
    if isinstance(exc, openai.APIConnectionError):
        return _Failure("connection", True, "connection error")
    if isinstance(exc, openai.APIStatusError):
        status = exc.status_code
        headers = exc.response.headers
        common: dict[str, Any] = {
            "status_code": status,
            "code": getattr(exc, "code", None),
            "request_id": _request_id(headers),
        }
        detail = _service_detail(exc)
        if status == 429:
            retry_after = parse_retry_after(headers)
            return _Failure("rate_limited", True, detail, retry_after_s=retry_after, **common)
        if status in (401, 403):
            return _Failure("auth", False, detail, **common)
        if status == 408:
            return _Failure("timeout", True, detail, **common)
        if status >= 500:
            retry_after = parse_retry_after(headers)
            return _Failure("server", True, detail, retry_after_s=retry_after, **common)
        if _is_content_filter(exc):
            return _Failure("content_filter", False, detail, **common)
        return _Failure("client", False, detail, **common)
    if isinstance(exc, openai.OpenAIError):
        return _Failure("client", False, str(exc)[:_MAX_MESSAGE_CHARS])
    return None


def _classify_response(response: Any) -> _Failure | None:
    """Failures reported inside a 200 response body (``status`` failed/cancelled/queued...)."""
    status = getattr(response, "status", None)
    if status in (None, "completed", "incomplete"):
        return None
    if status == "failed":
        error = getattr(response, "error", None)
        code = getattr(error, "code", None)
        detail = str(getattr(error, "message", "") or "")[:_MAX_MESSAGE_CHARS]
        if code == "server_error":
            return _Failure("server", True, detail, code=code)
        if code == "rate_limit_exceeded":
            return _Failure("rate_limited", True, detail, code=code)
        if code in _POLICY_RESPONSE_CODES:
            return _Failure("content_filter", False, detail, code=code)
        return _Failure("client", False, detail, code=code)
    return _Failure("client", False, f"unexpected response status '{status}'")


def _describe_error(exc: BaseException, tier: Tier, deployment: str) -> LlmError:
    status = getattr(exc, "status_code", None)
    context: dict[str, Any] = {"tier": tier, "deployment": deployment, "status_code": status}
    if _is_azure_auth_error(exc) or status in (401, 403):
        return LlmAuthError(
            f"Cannot read deployment '{deployment}' from the Foundry project (authentication "
            "or authorization failed); check the identity's Azure AI User role",
            **context,
        )
    if status == 404 or _is_azure_not_found(exc):
        return LlmConfigurationError(
            f"Deployment '{deployment}' does not exist in the Foundry project; check "
            f"{ENV_DEPLOYMENT[tier]}",
            **context,
        )
    return LlmServiceError(
        f"Cannot read deployment '{deployment}' from the Foundry project ({type(exc).__name__})",
        **context,
    )


def _is_azure_not_found(exc: BaseException) -> bool:
    try:
        from azure.core.exceptions import ResourceNotFoundError
    except ImportError:
        return False
    return isinstance(exc, ResourceNotFoundError)
