"""``FoundryEmbeddingClient``: the Foundry resource's OpenAI ``embeddings`` endpoint, Entra auth.

Same retry, rate-limit and concurrency rules as :class:`~docwiki.llm.foundry.FoundryLlmClient`:
``DefaultAzureCredential`` (never keys), SDK retries disabled, Retry-After honoured, one
token-bucket limiter for the embedding deployment. The project-scoped ``/openai/v1`` route that
the Responses client uses answers 404 for ``embeddings``, so the vectors come from the
``/openai/v1`` route of the Foundry resource that hosts the project (same host, token scope
``https://cognitiveservices.azure.com/.default``, role Cognitive Services User). The project
client still describes the deployment.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
import time
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar
from urllib.parse import urlsplit

from docwiki import __version__
from docwiki.llm.embeddings import (
    BaseEmbeddingClient,
    EmbeddingBatch,
    EmbeddingInfo,
    EmbedRequest,
)
from docwiki.llm.errors import (
    LlmAuthError,
    LlmConfigurationError,
    LlmContentFiltered,
    LlmError,
    LlmRateLimited,
    LlmServiceError,
    LlmTimeout,
)
from docwiki.llm.foundry import (
    _azure_transport,
    _classify_exception,
    _Failure,
    _is_azure_auth_error,
    _is_azure_not_found,
    _require,
)
from docwiki.llm.ledger import UsageLedger
from docwiki.llm.prices import PriceTable
from docwiki.llm.ratelimit import Clock, DeploymentRateLimiter, LoopLocal, Sleep
from docwiki.llm.retry import RetryPolicy
from docwiki.llm.settings import ENV_EMBED_DEPLOYMENT, ENV_TIMEOUT, LlmSettings
from docwiki.llm.types import EMBED_ROLE, LlmUsage, Origin, split_model_version

logger = logging.getLogger("docwiki.llm")

RESOURCE_TOKEN_SCOPE = "https://cognitiveservices.azure.com/.default"


def resource_openai_base_url(project_endpoint: str) -> str:
    """``https://<resource host>/openai/v1`` for a ``https://<resource host>/api/projects/<p>``
    Foundry project endpoint."""
    parts = urlsplit(project_endpoint)
    if parts.scheme != "https" or not parts.netloc:
        raise LlmConfigurationError("the Foundry project endpoint must be an https:// URL")
    return f"https://{parts.netloc}/openai/v1"


def _token_provider(credential: Any) -> Callable[[], Awaitable[str]]:
    async def token() -> str:
        return (await credential.get_token(RESOURCE_TOKEN_SCOPE)).token

    return token


class FoundryEmbeddingClient(BaseEmbeddingClient):
    """Live embedding client for the deployment named by ``DOCWIKI_EMBED_DEPLOYMENT``."""

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
        super().__init__(
            dimensions=settings.embed_dimensions,
            batch_size=settings.embed_batch_size,
            ledger=ledger,
            tracer_provider=tracer_provider,
        )
        if project_client is None:
            settings.require_embedding()
        self.settings = settings
        self.deployment = settings.embedding_deployment()
        self._credential = credential
        self._owns_credential = credential is None
        self._project = project_client
        self._owns_project = project_client is None
        self._http_client = http_client
        self._openai: Any | None = None
        self._openai_loop: asyncio.AbstractEventLoop | None = None
        self._retry = retry_policy or RetryPolicy.from_settings(settings)
        self._sleep = sleep
        self._rng = rng if rng is not None else random.Random()
        self._semaphore: LoopLocal[asyncio.Semaphore] = LoopLocal(
            functools.partial(asyncio.Semaphore, settings.concurrency)
        )
        self.limiter = DeploymentRateLimiter(
            self.deployment, settings.embed_rate_limit, clock=clock, sleep=sleep
        )
        self._described: EmbeddingInfo | None = None

    async def describe(self) -> EmbeddingInfo:
        """Ask the Foundry project which model and version the embedding deployment serves."""
        if self._described is not None:
            return self._described
        try:
            found = await self._ensure_project().deployments.get(self.deployment)
        except Exception as exc:
            raise _describe_error(exc, self.deployment) from exc
        sku = getattr(found, "sku", None)
        self._described = EmbeddingInfo(
            deployment=self.deployment,
            model_name=getattr(found, "model_name", None),
            model_version=getattr(found, "model_version", None),
            dimensions=self.dimensions,
            sku=getattr(sku, "name", None),
            capacity=getattr(sku, "capacity", None),
            source="service",
        )
        return self._described

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

    def _pricing_model(self) -> str | None:
        return self.settings.embed_model

    async def _run(self, request: EmbedRequest) -> EmbeddingBatch:
        try:
            return await self._embed(request)
        except LlmError as exc:
            exc.with_context(deployment=self.deployment)
            raise

    async def _embed(self, request: EmbedRequest) -> EmbeddingBatch:
        client = self._ensure_openai()
        estimate = request.estimated_input_tokens()
        retries = 0
        waited = 0.0
        while True:
            waited += await self.limiter.acquire(estimate)
            cause: BaseException | None = None
            try:
                async with self._semaphore.get():
                    response = await client.embeddings.create(
                        model=self.deployment,
                        input=list(request.texts),
                        dimensions=request.dimensions,
                        encoding_format="float",
                    )
            except Exception as exc:
                failure = _classify_exception(exc)
                if failure is None:
                    raise
                cause = exc
            else:
                return _batch(response, request, self.deployment, retries, waited)
            exhausted = retries >= self._retry.max_retries
            too_long = not self._retry.allows_retry_after(failure.retry_after_s)
            if not failure.retryable or exhausted or too_long:
                raise self._error(failure, retries, too_long) from cause
            delay = self._retry.delay(retries, failure.retry_after_s, self._rng)
            retries += 1
            logger.warning(
                "embed retry %d/%d: deployment=%s reason=%s status=%s delay=%.2fs",
                retries,
                self._retry.max_retries,
                self.deployment,
                failure.kind,
                failure.status_code,
                delay,
            )
            if failure.kind == "rate_limited":
                self.limiter.penalize(delay)
            else:
                await self._sleep(delay)
                waited += delay

    def _error(self, failure: _Failure, retries: int, retry_after_too_long: bool) -> LlmError:
        attempts = retries + 1
        where = f"Foundry embedding deployment '{self.deployment}'"
        tried = f"after {attempts} attempt{'s' if attempts > 1 else ''}"
        status = f"HTTP {failure.status_code}" if failure.status_code else failure.kind
        context: dict[str, Any] = {
            "deployment": self.deployment,
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
                    "DOCWIKI_EMBED_BATCH_SIZE, DOCWIKI_EMBED_TPM or raise the deployment capacity"
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
                "DefaultAzureCredential can get a token and that the identity has the Cognitive "
                "Services User role on the Foundry resource",
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
                f"{where} was not found (HTTP 404); check {ENV_EMBED_DEPLOYMENT} and the "
                f"Foundry project endpoint{detail}"
            )
        elif failure.retryable:
            message = f"{where} failed ({status}) {tried}{detail}"
        else:
            message = f"{where} rejected the request ({status}){detail}"
        return LlmServiceError(message, code=failure.code, **context)

    def _ensure_credential(self) -> Any:
        if self._credential is None:
            identity_aio = _require("azure.identity.aio")
            self._credential = identity_aio.DefaultAzureCredential(**_azure_transport())
        return self._credential

    def _ensure_project(self) -> Any:
        if self._project is None:
            projects_aio = _require("azure.ai.projects.aio")
            self._ensure_credential()
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
            openai = _require("openai")
            options: dict[str, Any] = {
                "base_url": resource_openai_base_url(_endpoint(self.settings)),
                "api_key": _token_provider(self._ensure_credential()),
                "max_retries": 0,
                "timeout": self.settings.timeout_s,
                "default_headers": {"User-Agent": f"docwiki/{__version__}"},
            }
            if self._http_client is not None:
                options["http_client"] = self._http_client
            self._openai = openai.AsyncOpenAI(**options)
            self._openai_loop = loop
        return self._openai


def _endpoint(settings: LlmSettings) -> str:
    if not settings.project_endpoint:
        raise LlmConfigurationError("the Foundry project endpoint is not set")
    return settings.project_endpoint


def _batch(
    response: Any, request: EmbedRequest, deployment: str, retries: int, waited: float
) -> EmbeddingBatch:
    """Vectors sorted by the service's ``index``; any gap or duplicate is a service error."""
    usage_info = getattr(response, "usage", None)
    usage = LlmUsage(input_tokens=int(getattr(usage_info, "prompt_tokens", 0) or 0))
    model, model_version = split_model_version(getattr(response, "model", None))
    data = list(getattr(response, "data", None) or [])
    indexes = sorted(int(getattr(item, "index", -1)) for item in data)
    if indexes != list(range(len(request.texts))):
        raise LlmServiceError(
            f"Embedding deployment '{deployment}' returned {len(data)} vectors with indexes "
            f"that do not cover the {len(request.texts)} texts sent",
            deployment=deployment,
            model=model,
            usage=usage,
            retries=retries,
            attempts=retries + 1,
        )
    ordered = sorted(data, key=lambda item: int(item.index))
    return EmbeddingBatch(
        vectors=tuple(tuple(float(value) for value in item.embedding) for item in ordered),
        usage=usage,
        deployment=deployment,
        model=model,
        model_version=model_version,
        wait_s=waited,
        retries=retries,
        attempts=retries + 1,
        origin="foundry",
    )


def _describe_error(exc: BaseException, deployment: str) -> LlmError:
    status = getattr(exc, "status_code", None)
    context: dict[str, Any] = {"tier": EMBED_ROLE, "deployment": deployment, "status_code": status}
    if _is_azure_auth_error(exc) or status in (401, 403):
        return LlmAuthError(
            f"Cannot read deployment '{deployment}' from the Foundry project (authentication "
            "or authorization failed); check the identity's Azure AI User role",
            **context,
        )
    if status == 404 or _is_azure_not_found(exc):
        return LlmConfigurationError(
            f"Deployment '{deployment}' does not exist in the Foundry project; check "
            f"{ENV_EMBED_DEPLOYMENT}",
            **context,
        )
    return LlmServiceError(
        f"Cannot read deployment '{deployment}' from the Foundry project ({type(exc).__name__})",
        **context,
    )
