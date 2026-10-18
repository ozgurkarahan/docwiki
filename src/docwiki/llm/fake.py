"""``FakeLlmClient``: deterministic, offline test double driven by per-schema handlers."""

from __future__ import annotations

import inspect
import json
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, ClassVar

from pydantic import BaseModel, ValidationError

from docwiki.llm.client import BaseLlmClient
from docwiki.llm.errors import LlmFakeHandlerMissing, LlmInvalidOutput
from docwiki.llm.ledger import UsageLedger
from docwiki.llm.request import LlmRequest, estimate_text_tokens
from docwiki.llm.types import DeploymentInfo, LlmUsage, Origin, StructuredResult, Tier

FakeValue = BaseModel | Mapping[str, Any]
FakeHandler = Callable[[LlmRequest], FakeValue | Awaitable[FakeValue]]

FAKE_MODEL = "fake-model"


class FakeLlmClient(BaseLlmClient):
    """Answers each ``schema_name`` with a registered handler; never touches the network.

    A handler is a pydantic object, a JSON-like mapping, or a (sync or async) callable that
    receives the :class:`LlmRequest` and returns one of those. The value is validated against the
    requested output model exactly like a live response. Usage is deterministic: input tokens are
    the request's 4-characters-per-token estimate, output tokens the estimate of the output JSON.
    Every request is appended to :attr:`requests` for assertions.
    """

    origin: ClassVar[Origin] = "fake"
    measures_latency: ClassVar[bool] = False

    def __init__(
        self,
        handlers: Mapping[str, FakeHandler | FakeValue] | None = None,
        *,
        ledger: UsageLedger | None = None,
        model: str = FAKE_MODEL,
        tracer_provider: Any | None = None,
    ) -> None:
        super().__init__(ledger=ledger, tracer_provider=tracer_provider)
        self.model = model
        self.requests: list[LlmRequest] = []
        self._handlers: dict[str, FakeHandler | FakeValue] = {}
        for schema_name, handler in (handlers or {}).items():
            self.register(schema_name, handler)

    def register(self, schema_name: str, handler: FakeHandler | FakeValue) -> None:
        if isinstance(handler, type):
            raise TypeError("register a pydantic instance, a mapping or a callable, not a class")
        if not (isinstance(handler, BaseModel | Mapping) or callable(handler)):
            raise TypeError("a fake handler must be a pydantic instance, a mapping or a callable")
        self._handlers[schema_name] = handler

    @staticmethod
    def deployment_for(tier: Tier) -> str:
        return f"fake-{tier}"

    async def describe(self, tier: Tier) -> DeploymentInfo:
        return DeploymentInfo(
            tier=tier, deployment=self.deployment_for(tier), model_name=self.model, source="fake"
        )

    async def _run(self, request: LlmRequest) -> StructuredResult[Any]:
        self.requests.append(request)
        deployment = self.deployment_for(request.tier)
        handler = self._handlers.get(request.schema_name)
        if handler is None:
            registered = ", ".join(sorted(self._handlers)) or "none"
            raise LlmFakeHandlerMissing(
                f"FakeLlmClient has no handler for schema '{request.schema_name}' "
                f"(registered: {registered}); call client.register('{request.schema_name}', ...)",
                deployment=deployment,
            )
        value: Any = handler if isinstance(handler, BaseModel | Mapping) else handler(request)
        if inspect.isawaitable(value):
            value = await value
        data = _json_object(value)
        try:
            parsed = request.output.model_validate(data)
        except ValidationError as exc:
            errors = tuple(
                f"{'.'.join(str(part) for part in error['loc']) or '<root>'}: {error['msg']}"
                for error in exc.errors(include_url=False, include_input=False)
            )
            raise LlmInvalidOutput(
                f"Fake handler for schema '{request.schema_name}' returned data that does not "
                f"validate against {request.output.__name__}: {errors[0]}",
                errors=errors,
                deployment=deployment,
                model=self.model,
                attempts=1,
            ) from exc
        usage = LlmUsage(
            input_tokens=request.estimated_input_tokens(),
            output_tokens=estimate_text_tokens(json.dumps(data, ensure_ascii=False)),
        )
        return StructuredResult(
            output=parsed,
            output_json=data,
            usage=usage,
            tier=request.tier,
            deployment=deployment,
            model=self.model,
            model_version=None,
            schema_name=request.schema_name,
            prompt_version=request.prompt_version,
            request_hash=request.request_hash,
            latency_s=0.0,
            origin="fake",
        )


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        try:
            return json.loads(json.dumps(dict(value), ensure_ascii=False))
        except (TypeError, ValueError) as exc:
            raise TypeError(f"fake handler returned a mapping that is not JSON: {exc}") from exc
    raise TypeError(
        f"fake handlers must return a pydantic object or a mapping, got {type(value).__name__}"
    )
