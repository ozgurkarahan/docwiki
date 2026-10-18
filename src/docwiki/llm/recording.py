"""Record live LLM responses as JSON fixtures and replay them offline.

One fixture file per request: ``<fixtures_dir>/<schema_name>/<request_hash>.json``, pretty
printed with sorted keys and LF line endings. The ``request`` field is exactly the object whose
canonical JSON is hashed into ``request_hash`` (images appear as SHA-256 digests), so fixtures
are self-describing and verifiable.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from docwiki.llm.client import BaseLlmClient, LlmClient
from docwiki.llm.errors import LlmConfigurationError, LlmInvalidOutput, LlmReplayMissing
from docwiki.llm.hashing import canonical_hash
from docwiki.llm.ledger import UsageLedger
from docwiki.llm.request import LlmRequest
from docwiki.llm.settings import ENV_DEPLOYMENT, ENV_FIXTURES, ENV_MODE, ENV_PROJECT_ENDPOINT
from docwiki.llm.types import (
    ContentPart,
    DeploymentInfo,
    LlmUsage,
    Origin,
    StructuredResult,
    T,
    Tier,
)

RECORDING_FORMAT: Final = "docwiki.llm.recording/v1"


class Recording(BaseModel):
    """Content of one fixture file."""

    model_config = ConfigDict(extra="forbid")

    format: Literal["docwiki.llm.recording/v1"] = RECORDING_FORMAT
    request_hash: str
    request: dict[str, Any]
    response: dict[str, Any]
    usage: LlmUsage
    deployment: str
    model: str | None = None
    model_version: str | None = None


def fixture_path(fixtures_dir: Path | str, schema_name: str, request_hash: str) -> Path:
    return Path(fixtures_dir) / schema_name / f"{request_hash}.json"


def write_recording(
    fixtures_dir: Path | str, request: LlmRequest, result: StructuredResult[Any]
) -> Path:
    """Write (or overwrite) the fixture of ``request`` atomically and return its path."""
    recording = Recording(
        request_hash=request.request_hash,
        request=request.hash_payload(),
        response=result.output_json,
        usage=result.usage,
        deployment=result.deployment,
        model=result.model,
        model_version=result.model_version,
    )
    path = fixture_path(fixtures_dir, request.schema_name, request.request_hash)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = recording.model_dump(mode="json")
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(text + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, path)
    return path


def read_recording(path: Path) -> Recording:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        recording = Recording.model_validate(raw)
    except (OSError, ValueError) as exc:
        raise LlmConfigurationError(
            f"LLM fixture {path.parent.name}/{path.name} is unreadable or malformed: {exc}"
        ) from exc
    if canonical_hash(recording.request) != recording.request_hash:
        raise LlmConfigurationError(
            f"LLM fixture {path.parent.name}/{path.name} does not match its request hash "
            "(was the request section edited?); re-record it"
        )
    return recording


class RecordingLlmClient:
    """Wraps any client and stores every successful response as a fixture file."""

    def __init__(self, inner: LlmClient, fixtures_dir: Path | str) -> None:
        self.inner = inner
        self.fixtures_dir = Path(fixtures_dir)
        self.recorded: list[Path] = []

    @property
    def ledger(self) -> UsageLedger | None:
        return getattr(self.inner, "ledger", None)

    async def structured(
        self,
        tier: Tier,
        system: str,
        user: str | Sequence[ContentPart],
        output: type[T],
        schema_name: str,
        prompt_version: str,
        max_output_tokens: int,
        metadata: Mapping[str, Any] | None = None,
    ) -> StructuredResult[T]:
        request = LlmRequest.build(
            tier, system, user, output, schema_name, prompt_version, max_output_tokens, metadata
        )
        result = await self.inner.structured(
            tier, system, user, output, schema_name, prompt_version, max_output_tokens, metadata
        )
        self.recorded.append(write_recording(self.fixtures_dir, request, result))
        return result

    async def describe(self, tier: Tier) -> DeploymentInfo:
        return await self.inner.describe(tier)

    async def aclose(self) -> None:
        await self.inner.aclose()

    async def __aenter__(self) -> RecordingLlmClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()


class ReplayLlmClient(BaseLlmClient):
    """Serves recorded fixtures; a missing recording raises :class:`LlmReplayMissing`."""

    origin: ClassVar[Origin] = "replay"
    measures_latency: ClassVar[bool] = False

    def __init__(
        self,
        fixtures_dir: Path | str,
        *,
        ledger: UsageLedger | None = None,
        tracer_provider: Any | None = None,
    ) -> None:
        super().__init__(ledger=ledger, tracer_provider=tracer_provider)
        self.fixtures_dir = Path(fixtures_dir)

    async def describe(self, tier: Tier) -> DeploymentInfo:
        return DeploymentInfo(tier=tier, deployment=f"replay-{tier}", source="replay")

    async def _run(self, request: LlmRequest) -> StructuredResult[Any]:
        path = fixture_path(self.fixtures_dir, request.schema_name, request.request_hash)
        if not path.is_file():
            raise LlmReplayMissing(
                self._missing_message(request, path),
                fixture=str(path),
                deployment=f"replay-{request.tier}",
            )
        recording = read_recording(path)
        if recording.request_hash != request.request_hash:
            raise LlmConfigurationError(
                f"LLM fixture {request.schema_name}/{path.name} was recorded for another request "
                f"hash ({recording.request_hash}); re-record it"
            )
        try:
            parsed = request.output.model_validate(recording.response)
        except ValidationError as exc:
            errors = tuple(
                f"{'.'.join(str(part) for part in error['loc']) or '<root>'}: {error['msg']}"
                for error in exc.errors(include_url=False, include_input=False)
            )
            raise LlmInvalidOutput(
                f"Recorded response {request.schema_name}/{path.name} no longer validates "
                f"against {request.output.__name__} ({errors[0]}); re-record it",
                errors=errors,
                deployment=recording.deployment,
                model=recording.model,
                attempts=1,
            ) from exc
        return StructuredResult(
            output=parsed,
            output_json=recording.response,
            usage=recording.usage,
            tier=request.tier,
            deployment=recording.deployment,
            model=recording.model,
            model_version=recording.model_version,
            schema_name=request.schema_name,
            prompt_version=request.prompt_version,
            request_hash=request.request_hash,
            latency_s=0.0,
            origin="replay",
        )

    def _missing_message(self, request: LlmRequest, path: Path) -> str:
        schema_dir = path.parent
        others = len(list(schema_dir.glob("*.json"))) if schema_dir.is_dir() else 0
        hint = (
            f" {others} other recording(s) exist for this schema: the prompt, prompt version, "
            "output model or input probably changed."
            if others
            else ""
        )
        return (
            f"No recorded LLM response for schema '{request.schema_name}' (tier "
            f"'{request.tier}', prompt version '{request.prompt_version}', request hash "
            f"{request.request_hash}) in the fixtures directory '{self.fixtures_dir}': expected "
            f"{request.schema_name}/{path.name}.{hint} To record it, run the same code against a "
            f"live Foundry project with {ENV_MODE}=record and {ENV_FIXTURES} set to the fixtures "
            f"directory (plus {ENV_PROJECT_ENDPOINT} and {ENV_DEPLOYMENT[request.tier]}), or wrap "
            "a FoundryLlmClient in RecordingLlmClient; then commit the new JSON file."
        )
