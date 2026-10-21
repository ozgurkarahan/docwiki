"""Live "Ask this wiki": anonymous visitors ask the Researcher agent from the wiki's drawer.

ADR 0008. The portal serves the wiki, so the drawer calls the same origin::

    GET  /api/ask/status    {"enabled": bool}                  (always 200)
    POST /api/ask           {"question": "..."}  ->  202 {"job_id": "..."}
    GET  /api/ask/{job_id}  {"status", "elapsed_s", "answer"?, "message"?}

A question runs :meth:`AgentClient.ask` in an asyncio task and the browser polls the job (the
shape of ``docwiki.studio.jobs``, without its sign-in: the visitor is anonymous). The agent is
reached through a gateway that holds the real limits (per-visitor rate, token budgets, a daily
cut-off); the guards here only protect the portal and tell the visitor early:

* a body of at most 4 KB, a question of 3 to 500 characters, ``Content-Type: application/json``
  and, when the browser sends one, an ``Origin`` that is the request's own host;
* one running question per visitor, a few running in total, a few questions per visitor and
  window (in memory: a restart forgets them, the gateway does not);
* a finished job is forgotten after 15 minutes.

**Gate before display.** An answer is shown as verified only when every ``[n]`` of its text names
a source that is an evidence sidecar path (``evidence/<source_id>/<locator>.md``) AND whose page
exists in the site being served. Otherwise it is returned as ``unverified``: the text without its
citations and a message that says so. The converter turns the answer into the drawer's
``AskAnswer`` shape (``docwiki.site.answers``) with ``live: true``; the drawer renders it with DOM
nodes and ``textContent`` only. Exception text never reaches the visitor; it is logged. Questions
may contain personal data: they are not logged above DEBUG, and visitors are logged hashed.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import os
import re
import secrets
import time
import uuid
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal, Protocol

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from docwiki.agents_client.citations import Source, inline_citations
from docwiki.agents_client.client import AgentAnswer, AgentClient, AgentClientSettings
from docwiki.agents_client.errors import AgentConfigurationError, AgentInvocationError
from docwiki.answers.filing import NOT_FOUND_RE, tool_steps
from docwiki.contracts.enums import badge_for
from docwiki.contracts.safety import sanitize_markdown
from docwiki.site.answers import markdown_paragraphs

__all__ = [
    "BUSY_MESSAGE",
    "ENABLE_ENV",
    "LIVE_BANNER",
    "UNVERIFIED_MESSAGE",
    "VISITOR_HEADER",
    "LiveAsk",
    "LiveAskRefused",
    "LiveAskSettings",
    "live_answer",
    "live_ask_routes",
    "visitor_ip",
]

log = logging.getLogger("docwiki.portal.live_ask")

ENABLE_ENV = "DOCWIKI_LIVE_ASK"
VISITOR_HEADER = "X-Visitor-IP"
"""Header the gateway reads to rate-limit per visitor, and removes before the Foundry call."""
LIVE_BANNER = "Live answer from the Researcher agent — not reviewed by the owner."
UNVERIFIED_MESSAGE = (
    "This answer could not be checked against the sources, so it is not shown as verified."
)
BUSY_MESSAGE = (
    "The live agent has reached its limit for now. The answers below were reviewed and filed."
)
FAILED_MESSAGE = "The live agent could not answer. Please try again later."
TIMEOUT_MESSAGE = "The live agent took too long to answer. Please try again later."
EMPTY_MESSAGE = "The live agent did not return an answer. Please try again later."
HOME_SLUG = "index"

_CITE_RE = re.compile(r"[ \t]*\[(\d{1,3})\](?![(:])")
_EVIDENCE_SLUG = "evidence/{source_id}/{locator_key}"
_MAX_IP_CHARS = 64

JobStatus = Literal["running", "done", "unverified", "error", "busy"]


class LiveAskRefused(Exception):
    """A request the portal refuses before any model call (``status_code`` and a short message)."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


@dataclass(frozen=True)
class LiveAskSettings:
    """Guards of the live ask, each set by an environment variable (documented in
    ``docs/live-ask.md``)."""

    max_body_bytes: int = 4096
    min_question_chars: int = 3
    max_question_chars: int = 500
    questions_per_ip: int = 3
    ip_window_s: float = 300.0
    max_running: int = 3
    timeout_s: float = 200.0
    result_ttl_s: float = 900.0

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> LiveAskSettings:
        values = os.environ if env is None else env
        defaults = cls()

        def number(suffix: str, default: float, kind: type[int] | type[float]) -> Any:
            name = f"{ENABLE_ENV}_{suffix}"
            raw = (values.get(name) or "").strip()
            if not raw:
                return default
            try:
                value = kind(raw)
            except ValueError as exc:
                raise ValueError(f"{name} must be a number") from exc
            if value <= 0:
                raise ValueError(f"{name} must be positive")
            return value

        return cls(
            max_body_bytes=number("MAX_BODY_BYTES", defaults.max_body_bytes, int),
            min_question_chars=number("MIN_QUESTION_CHARS", defaults.min_question_chars, int),
            max_question_chars=number("MAX_QUESTION_CHARS", defaults.max_question_chars, int),
            questions_per_ip=number("QUESTIONS_PER_IP", defaults.questions_per_ip, int),
            ip_window_s=number("IP_WINDOW_SECONDS", defaults.ip_window_s, float),
            max_running=number("MAX_RUNNING", defaults.max_running, int),
            timeout_s=number("TIMEOUT_SECONDS", defaults.timeout_s, float),
            result_ttl_s=number("RESULT_TTL_SECONDS", defaults.result_ttl_s, float),
        )


class Asker(Protocol):
    async def ask(
        self, question: str, *, agent: str = ..., headers: Mapping[str, str] | None = ...
    ) -> AgentAnswer: ...

    async def aclose(self) -> None: ...


@dataclass
class LiveJob:
    id: str
    ip: str
    started: float
    status: JobStatus = "running"
    answer: dict[str, Any] | None = None
    message: str | None = None
    finished: float | None = None
    task: asyncio.Task[None] | None = field(default=None, repr=False)


# ---------------------------------------------------------------------- the gate and converter


def _evidence_page(site_root: Path | None, source: Source) -> bool:
    """The source is an evidence sidecar path and the served site has its page."""
    if site_root is None or not source.source_id or not source.locator_key:
        return False
    if source.path != f"evidence/{source.source_id}/{source.locator_key}.md":
        return False
    return (site_root / "evidence" / source.source_id / f"{source.locator_key}.html").is_file()


def _badge(provenance: str) -> str:
    """The badge of a live citation: never "quote verified", the quote is not checked here."""
    try:
        return badge_for(provenance, "unverified-paraphrase")
    except ValueError:
        return "paraphrase"


def live_answer(
    answer: AgentAnswer,
    *,
    question: str,
    job_id: str,
    site_root: Path | None,
    today: date,
) -> tuple[Literal["done", "unverified", "error"], dict[str, Any], str | None]:
    """``(status, AskAnswer, message)`` of a live answer, after the gate.

    ``done`` when every citation of the text resolves to an evidence page of the served site (or
    the agent honestly found nothing); ``unverified`` with the citations removed otherwise;
    ``error`` when no text is left.
    """
    body = sanitize_markdown(answer.body)[0].strip()
    used = inline_citations(body)
    listed = {source.n: source for source in answer.sources}
    valid = {n: source for n, source in listed.items() if _evidence_page(site_root, source)}
    abstains = not used and NOT_FOUND_RE.search(body) is not None
    verified = abstains or (bool(used) and all(n in valid for n in used))
    cites = set(used) if verified else set()
    text = _CITE_RE.sub(lambda match: f"[^c{match.group(1)}]", body)
    paragraphs = markdown_paragraphs(text, cites)
    steps = tool_steps(answer.tool_calls)
    provenance = (
        f"Answered live by the Researcher agent ({answer.agent} version {answer.version or '?'}) "
        f"on {today.isoformat()}."
    )
    citations = [
        {
            "n": n,
            "title": valid[n].title,
            "label": valid[n].locator_label,
            "href": _EVIDENCE_SLUG.format(
                source_id=valid[n].source_id, locator_key=valid[n].locator_key
            ),
            "badge": _badge(valid[n].provenance),
        }
        for n in used
        if verified and n in valid
    ]
    item: dict[str, Any] = {
        "id": f"live:{job_id}",
        "slug": HOME_SLUG,
        "question": question,
        "date": today.isoformat(),
        "banners": [LIVE_BANNER],
        "paragraphs": paragraphs,
        "citations": citations,
        "steps": steps,
        "provenance": provenance,
        "pages": [],
        "live": True,
    }
    if not paragraphs:
        return "error", item, EMPTY_MESSAGE
    if not verified:
        return "unverified", item, UNVERIFIED_MESSAGE
    return "done", item, None


# ---------------------------------------------------------------------- the service


def visitor_ip(request: Request) -> str:
    """Last entry of ``X-Forwarded-For``, else the client address (``unknown`` without one).

    The Container Apps edge appends the address it sees to the end of the header; earlier entries
    come from the visitor and can be forged, so they never key the per-visitor limits.
    """
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[-1].strip()
    client = request.client.host if request.client else ""
    return (forwarded or client or "unknown")[:_MAX_IP_CHARS]


class LiveAsk:
    """Questions in flight and recently answered, with the guards of the module docstring.

    ``site_root`` returns the folder of the site being served (the portal sets it); the gate
    checks the cited evidence pages there.
    """

    def __init__(
        self,
        settings: LiveAskSettings,
        client_factory: Callable[[], Asker],
        *,
        site_root: Callable[[], Path | None] = lambda: None,
        clock: Callable[[], float] = time.monotonic,
        today: Callable[[], date] = lambda: datetime.now(UTC).date(),
    ) -> None:
        self.settings = settings
        self.site_root = site_root
        self._client_factory = client_factory
        self._client: Asker | None = None
        self._clock = clock
        self._today = today
        self._jobs: dict[str, LiveJob] = {}
        self._asked: dict[str, deque[float]] = {}
        self._salt = secrets.token_bytes(16)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> LiveAsk | None:
        """The service when ``DOCWIKI_LIVE_ASK=1`` and the agent settings load, else ``None``."""
        values = os.environ if env is None else env
        if (values.get(ENABLE_ENV) or "").strip() != "1":
            return None
        try:
            settings = LiveAskSettings.from_env(values)
            # Fail fast: a 429 of the gateway must reach the visitor, not be retried here.
            agent_settings = replace(AgentClientSettings.from_env(values), max_retries=0)
        except (ValueError, AgentConfigurationError) as exc:
            log.error("live ask is off: %s", exc)
            return None
        return cls(settings, lambda: AgentClient(agent_settings))

    # -- guards ------------------------------------------------------------------------------

    def hashed(self, ip: str) -> str:
        return hashlib.sha256(self._salt + ip.encode("utf-8")).hexdigest()[:12]

    def _prune(self) -> None:
        now = self._clock()
        for job_id, job in list(self._jobs.items()):
            if job.finished is not None and now - job.finished > self.settings.result_ttl_s:
                del self._jobs[job_id]
        for ip, asked in list(self._asked.items()):
            while asked and now - asked[0] > self.settings.ip_window_s:
                asked.popleft()
            if not asked:
                del self._asked[ip]

    def start(self, question: str, ip: str) -> LiveJob:
        """Start a question (inside the event loop), or raise :class:`LiveAskRefused`."""
        text = (question or "").strip()
        limits = self.settings
        if len(text) < limits.min_question_chars:
            raise LiveAskRefused(400, "Please ask a complete question.")
        if len(text) > limits.max_question_chars:
            raise LiveAskRefused(
                400, f"Please keep the question under {limits.max_question_chars} characters."
            )
        self._prune()
        running = [job for job in self._jobs.values() if job.status == "running"]
        if any(job.ip == ip for job in running):
            raise LiveAskRefused(429, "Your previous question is still being answered.")
        if len(running) >= limits.max_running:
            raise LiveAskRefused(429, "The Researcher is busy with other visitors. Try again soon.")
        asked = self._asked.setdefault(ip, deque())
        if len(asked) >= limits.questions_per_ip:
            count, minutes = limits.questions_per_ip, max(round(limits.ip_window_s / 60), 1)
            raise LiveAskRefused(
                429,
                f"You can ask {count} question{'s' if count > 1 else ''} every "
                f"{minutes} minute{'s' if minutes > 1 else ''}. Please try again later.",
            )
        asked.append(self._clock())
        job = LiveJob(id=uuid.uuid4().hex, ip=ip, started=self._clock())
        self._jobs[job.id] = job
        log.info(
            "live_ask.start job=%s visitor=%s question_chars=%d", job.id, self.hashed(ip), len(text)
        )
        log.debug("live_ask.question job=%s text=%r", job.id, text)
        job.task = asyncio.get_running_loop().create_task(self._run(job, text))
        return job

    # -- running -----------------------------------------------------------------------------

    def _get_client(self) -> Asker:
        if self._client is None:
            self._client = self._client_factory()
        return self._client

    async def _run(self, job: LiveJob, question: str) -> None:
        try:
            async with asyncio.timeout(self.settings.timeout_s):
                answer = await self._get_client().ask(
                    question, agent="researcher", headers={VISITOR_HEADER: job.ip}
                )
        except TimeoutError:
            job.status, job.message = "error", TIMEOUT_MESSAGE
            log.warning("live_ask.timeout job=%s", job.id)
        except AgentInvocationError as exc:
            # The gateway answers 429 for rate limits and 403 once a daily token quota is spent.
            if exc.status_code in (429, 403):
                job.status, job.message = "busy", BUSY_MESSAGE
            else:
                job.status, job.message = "error", FAILED_MESSAGE
            log.warning("live_ask.failed job=%s http=%s error=%s", job.id, exc.status_code, exc)
        except asyncio.CancelledError:
            job.status, job.message = "error", FAILED_MESSAGE
            raise
        except Exception:
            job.status, job.message = "error", FAILED_MESSAGE
            log.exception("live_ask.failed job=%s", job.id)
        else:
            try:
                status, item, message = live_answer(
                    answer,
                    question=question,
                    job_id=job.id,
                    site_root=self.site_root(),
                    today=self._today(),
                )
            except Exception:
                job.status, job.message = "error", FAILED_MESSAGE
                log.exception("live_ask.gate_failed job=%s", job.id)
            else:
                job.status, job.answer, job.message = status, item, message
                log.info(
                    "live_ask.finish job=%s visitor=%s status=%s citations=%d tool_calls=%d "
                    "tokens=%d latency_s=%.1f",
                    job.id,
                    self.hashed(job.ip),
                    status,
                    len(item["citations"]),
                    len(answer.tool_calls),
                    answer.usage.total_tokens,
                    answer.latency_s,
                )
        finally:
            job.finished = self._clock()

    def view(self, job_id: str) -> dict[str, Any] | None:
        """The polling payload of a job, or ``None`` when it is unknown or expired."""
        self._prune()
        job = self._jobs.get(job_id)
        if job is None:
            return None
        end = job.finished if job.finished is not None else self._clock()
        payload: dict[str, Any] = {"status": job.status, "elapsed_s": round(end - job.started, 1)}
        if job.answer is not None:
            payload["answer"] = job.answer
        if job.message:
            payload["message"] = job.message
        return payload

    async def aclose(self) -> None:
        """Cancel the questions in flight and close the agent client."""
        tasks = [job.task for job in self._jobs.values() if job.task and not job.task.done()]
        for task in tasks:
            task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        if self._client is not None:
            client, self._client = self._client, None
            await client.aclose()


# ---------------------------------------------------------------------- HTTP routes

_NO_STORE = {"cache-control": "no-store"}


def _json(payload: dict[str, Any], status: int = 200) -> JSONResponse:
    return JSONResponse(payload, status_code=status, headers=_NO_STORE)


def _refusal(refused: LiveAskRefused) -> JSONResponse:
    return _json({"message": refused.message}, refused.status_code)


async def _read_body(request: Request, limit: int) -> bytes:
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        raise LiveAskRefused(413, "The question is too long.")
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > limit:
            raise LiveAskRefused(413, "The question is too long.")
    return bytes(body)


def _check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin is None:
        return
    host = request.headers.get("host", "")
    netloc = origin.split("://", 1)[1] if "://" in origin else origin
    if not host or netloc.lower() != host.lower():
        raise LiveAskRefused(403, "This request does not come from this site.")


def live_ask_routes(live: LiveAsk | None) -> list[Route]:
    """Routes of the live ask: the status always, the rest only when ``live`` is enabled."""

    async def status(_request: Request) -> Response:
        return _json({"enabled": live is not None})

    routes = [Route("/api/ask/status", status, methods=["GET"])]
    if live is None:
        return routes

    async def ask(request: Request) -> Response:
        try:
            media_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
            if media_type != "application/json":
                raise LiveAskRefused(415, "Send the question as JSON.")
            _check_origin(request)
            body = await _read_body(request, live.settings.max_body_bytes)
            try:
                payload = json.loads(body)
            except ValueError:
                payload = None
            question = payload.get("question") if isinstance(payload, dict) else None
            if not isinstance(question, str):
                raise LiveAskRefused(400, 'Send the question as JSON: {"question": "..."}.')
            job = live.start(question, visitor_ip(request))
        except LiveAskRefused as refused:
            return _refusal(refused)
        return _json({"job_id": job.id}, 202)

    async def poll(request: Request) -> Response:
        payload = live.view(request.path_params["job_id"])
        if payload is None:
            return _json({"message": "This question is unknown or has expired."}, 404)
        return _json(payload)

    routes += [
        Route("/api/ask", ask, methods=["POST"]),
        Route("/api/ask/{job_id}", poll, methods=["GET"]),
    ]
    return routes
