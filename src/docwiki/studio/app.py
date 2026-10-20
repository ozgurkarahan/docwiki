"""DocWiki Studio: the signed-in web app around the pipeline and the two agents.

* **Documents**: upload into ``raw/`` (Event Grid wakes the ingest job), with each file's pipeline
  status and a link to its wiki page.
* **Pipeline**: the served release, recent run reports (stages, gates, cost) and the queue.
* **Ask**: the Researcher (cited answers) and the Librarian (operations; every mutating tool call
  waits for Approve / Deny in the browser). A Researcher answer can be filed to the wiki after a
  preview: it becomes a query page in the answers inbox, which the next run publishes.

It runs behind Azure Container Apps built-in authentication (Entra sign-in, owner only). The app
checks it again: ``/api`` calls need the platform's principal headers and an allowed object ID;
writes need the ``X-DocWiki-Studio`` header and a same-origin request (no CORS), which together
stop cross-site request forgery. ``--local`` (loopback only) skips the sign-in checks.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from starlette.applications import Starlette
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from docwiki.answers import FilingError
from docwiki.contracts.storage import StorageError
from docwiki.extract.formats import SUPPORTED_EXTENSIONS
from docwiki.portal.app import SECURITY_HEADERS, SecurityHeadersMiddleware
from docwiki.studio.config import StudioConfig
from docwiki.studio.filing import FilingConflictError, FilingQuotaError, FilingRefusedError
from docwiki.studio.jobs import (
    AGENTS,
    AgentJobs,
    JobBusyError,
    JobNotFoundError,
    JobStateError,
    QuestionError,
    QuotaExceededError,
)
from docwiki.studio.service import (
    StudioService,
    UploadConflictError,
    UploadError,
    UploadQuotaError,
    UploadTooLargeError,
)

__all__ = ["CSRF_HEADER", "STATIC_DIR", "STUDIO_HEADERS", "ApiGuard", "create_app"]

log = logging.getLogger("docwiki.studio")

STATIC_DIR = Path(__file__).resolve().parent / "static"
PRINCIPAL_ID = "x-ms-client-principal-id"
PRINCIPAL_NAME = "x-ms-client-principal-name"
CSRF_HEADER = "x-docwiki-studio"
MAX_JSON_BYTES = 16 * 1024
NO_STORE = {"cache-control": "no-store"}
SAFE_METHODS = frozenset({"GET", "HEAD"})

STUDIO_CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)
STUDIO_HEADERS: dict[str, str] = {**SECURITY_HEADERS, "content-security-policy": STUDIO_CSP}


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status, headers=NO_STORE)


class _RevalidatedStaticFiles(StaticFiles):
    """Static files revalidated on every load (ETag), so a new deployment never mixes an old
    script with a new page."""

    def file_response(self, *args: Any, **kwargs: Any) -> Response:
        response = super().file_response(*args, **kwargs)
        response.headers["cache-control"] = "no-cache"
        return response


class ApiGuard:
    """Sign-in and CSRF checks in front of every ``/api/`` route (pure ASGI middleware)."""

    def __init__(self, app: Any, config: StudioConfig) -> None:
        self.app = app
        self.config = config

    def problem(self, method: str, headers: Headers) -> tuple[int, str] | None:
        if self.config.require_sign_in:
            principal = (headers.get(PRINCIPAL_ID) or "").strip().lower()
            if not principal:
                return 401, "sign-in required"
            if not self.config.allowed_principals:
                return 403, "no account is allowed in: set DOCWIKI_STUDIO_ALLOWED_PRINCIPALS"
            if principal not in self.config.allowed_principals:
                return 403, "this account is not allowed in the Studio"
        if method not in SAFE_METHODS:
            if headers.get(CSRF_HEADER) != "1":
                return 403, "missing X-DocWiki-Studio header"
            site = headers.get("sec-fetch-site")
            if site and site not in ("same-origin", "none"):
                return 403, "cross-site request refused"
            origin = headers.get("origin")
            if origin and origin != "null":
                host = (headers.get("host") or "").lower()
                if urlsplit(origin).netloc.lower() != host:
                    return 403, "cross-origin request refused"
        return None

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] == "http" and scope["path"].startswith("/api/"):
            found = self.problem(scope["method"], Headers(scope=scope))
            if found is not None:
                await _error(*found)(scope, receive, send)
                return
        await self.app(scope, receive, send)


async def _json_body(request: Request) -> dict[str, Any]:
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_JSON_BYTES:
        raise QuestionError("the request body is too large")
    raw = await request.body()
    if len(raw) > MAX_JSON_BYTES:
        raise QuestionError("the request body is too large")
    try:
        data = json.loads(raw or b"{}")
    except ValueError as exc:
        raise QuestionError("the request body is not JSON") from exc
    if not isinstance(data, dict):
        raise QuestionError("the request body must be a JSON object")
    return data


def create_app(
    service: StudioService,
    jobs: AgentJobs | None,
    config: StudioConfig,
    *,
    static_dir: Path = STATIC_DIR,
) -> Starlette:
    """The Studio ASGI app (``jobs=None`` hides the agents, for example without Foundry)."""

    def user(request: Request) -> str | None:
        if not config.require_sign_in:
            return request.headers.get(PRINCIPAL_NAME) or "local"
        return request.headers.get(PRINCIPAL_NAME)

    async def index(_request: Request) -> Response:
        return FileResponse(
            static_dir / "index.html", media_type="text/html; charset=utf-8", headers=NO_STORE
        )

    async def live(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "alive"}, headers=NO_STORE)

    async def health(_request: Request) -> JSONResponse:
        storage_ok = await asyncio.to_thread(service.storage_ok)
        agents_ok = await jobs.healthy() if jobs is not None else None
        healthy = storage_ok and agents_ok is not False
        return JSONResponse(
            {"status": "ok" if healthy else "degraded", "storage": storage_ok, "agents": agents_ok},
            status_code=200 if healthy else 503,
            headers=NO_STORE,
        )

    def me(request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "user": user(request),
                "wiki_url": config.wiki_url,
                "agents": list(AGENTS) if jobs is not None else [],
                "questions_left": jobs.questions_left() if jobs is not None else 0,
                "uploads_left": service.uploads_left(),
                "filings_left": service.filing.filings_left(),
                "max_upload_mb": config.max_upload_bytes // (1024 * 1024),
                "extensions": list(SUPPORTED_EXTENSIONS),
                "sign_out_url": "/.auth/logout" if config.require_sign_in else None,
            },
            headers=NO_STORE,
        )

    def documents(_request: Request) -> JSONResponse:
        return JSONResponse(service.documents(), headers=NO_STORE)

    async def upload(request: Request) -> JSONResponse:
        path = request.path_params["path"]
        replace = request.query_params.get("replace", "").lower() in ("1", "true", "yes")
        limit = config.max_upload_bytes
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            return _error(413, f"the file is larger than {limit // (1024 * 1024)} MB")
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > limit:
                return _error(413, f"the file is larger than {limit // (1024 * 1024)} MB")
        try:
            result = await asyncio.to_thread(service.upload, path, bytes(body), replace=replace)
        except UploadTooLargeError as exc:
            return _error(413, str(exc))
        except UploadConflictError as exc:
            return _error(409, str(exc))
        except UploadError as exc:
            return _error(400, str(exc))
        except UploadQuotaError as exc:
            return _error(429, str(exc))
        except StorageError:
            log.exception("upload of %s failed", path)
            return _error(502, "the storage refused the upload; the Studio logs have the details")
        log.info("upload by %s: raw/%s", user(request), result["path"])
        result["uploads_left"] = service.uploads_left()
        return JSONResponse(result, status_code=201, headers=NO_STORE)

    def pipeline(_request: Request) -> JSONResponse:
        return JSONResponse(service.pipeline(), headers=NO_STORE)

    async def ask(request: Request) -> JSONResponse:
        if jobs is None:
            return _error(503, "the agents are not configured (DOCWIKI_FOUNDRY_PROJECT_ENDPOINT)")
        body = await _json_body(request)
        job = jobs.start(
            str(body.get("agent") or "researcher"),
            str(body.get("question") or ""),
            request.headers.get(PRINCIPAL_ID),
        )
        log.info("question %s for the %s by %s", job.id, job.agent, user(request))
        return JSONResponse(
            {"job_id": job.id, "questions_left": jobs.questions_left()},
            status_code=202,
            headers=NO_STORE,
        )

    async def job(request: Request) -> JSONResponse:
        if jobs is None:
            return _error(404, "no agents")
        job_id = request.path_params["job_id"]
        if request.method == "DELETE":
            jobs.cancel(job_id)
            return JSONResponse({"cancelled": job_id}, status_code=202, headers=NO_STORE)
        view = jobs.view(jobs.get(job_id), config.wiki_url)
        view["filed"] = service.filing.filed(job_id)
        return JSONResponse(view, headers=NO_STORE)

    async def job_list(_request: Request) -> JSONResponse:
        if jobs is None:
            return JSONResponse({"active": None, "jobs": []}, headers=NO_STORE)
        return JSONResponse(jobs.recent(), headers=NO_STORE)

    async def approval(request: Request) -> JSONResponse:
        if jobs is None:
            return _error(404, "no agents")
        body = await _json_body(request)
        approve = body.get("approve")
        if not isinstance(approve, bool):
            return _error(400, "approve must be true or false")
        job_id = request.path_params["job_id"]
        approval_id = request.path_params["approval_id"]
        jobs.decide(job_id, approval_id, approve)
        log.info(
            "%s %s approval %s of question %s",
            user(request),
            "granted" if approve else "refused",
            approval_id,
            job_id,
        )
        return JSONResponse({"approval_id": approval_id, "approved": approve}, headers=NO_STORE)

    async def filing_preview(request: Request) -> JSONResponse:
        if jobs is None:
            return _error(404, "no agents")
        job = jobs.get(request.path_params["job_id"])
        try:
            preview = await asyncio.to_thread(service.filing.preview, job)
        except FilingError as exc:
            return _error(422, f"this answer cannot be filed: {exc}")
        return JSONResponse(preview, headers=NO_STORE)

    async def file_answer(request: Request) -> JSONResponse:
        if jobs is None:
            return _error(404, "no agents")
        body = await _json_body(request)
        digest = body.get("digest")
        if digest is not None and not isinstance(digest, str):
            return _error(400, "digest must be the string returned by the preview")
        job = jobs.get(request.path_params["job_id"])
        try:
            result = await asyncio.to_thread(service.filing.file, job, digest=digest)
        except FilingError as exc:
            return _error(422, f"this answer cannot be filed: {exc}")
        except StorageError:
            log.exception("filing the answer of question %s failed", job.id)
            return _error(502, "the storage refused the filing; the Studio logs have the details")
        if not result["repeated"]:
            log.info("answer of question %s filed by %s: %s", job.id, user(request), result["path"])
        return JSONResponse(
            result, status_code=200 if result["repeated"] else 201, headers=NO_STORE
        )

    async def not_found(_request: Request, exc: Exception) -> JSONResponse:
        return _error(404, str(exc))

    async def conflict(_request: Request, exc: Exception) -> JSONResponse:
        return _error(409, str(exc))

    async def bad_request(_request: Request, exc: Exception) -> JSONResponse:
        return _error(400, str(exc))

    async def too_many(_request: Request, exc: Exception) -> JSONResponse:
        return _error(429, str(exc))

    async def storage_failed(_request: Request, exc: Exception) -> JSONResponse:
        log.warning("storage error: %s", exc)
        return _error(502, "the storage is unavailable; try again shortly")

    @contextlib.asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if jobs is not None:
                await jobs.aclose()

    app = Starlette(
        routes=[
            Route("/", index, methods=["GET", "HEAD"]),
            Route("/livez", live, methods=["GET", "HEAD"]),
            Route("/healthz", live, methods=["GET", "HEAD"]),
            Route("/api/health", health, methods=["GET"]),
            Route("/api/me", me, methods=["GET"]),
            Route("/api/documents", documents, methods=["GET"]),
            Route("/api/documents/{path:path}", upload, methods=["PUT"]),
            Route("/api/pipeline", pipeline, methods=["GET"]),
            Route("/api/ask", ask, methods=["POST"]),
            Route("/api/jobs", job_list, methods=["GET"]),
            Route("/api/jobs/{job_id}", job, methods=["GET", "DELETE"]),
            Route("/api/jobs/{job_id}/approvals/{approval_id}", approval, methods=["POST"]),
            Route("/api/questions/{job_id}/filing", filing_preview, methods=["GET"]),
            Route("/api/questions/{job_id}/file", file_answer, methods=["POST"]),
            Mount("/static", _RevalidatedStaticFiles(directory=static_dir), name="static"),
        ],
        exception_handlers={
            JobNotFoundError: not_found,
            JobStateError: conflict,
            JobBusyError: conflict,
            QuestionError: bad_request,
            QuotaExceededError: too_many,
            FilingRefusedError: bad_request,
            FilingConflictError: conflict,
            FilingQuotaError: too_many,
            StorageError: storage_failed,
        },
        lifespan=lifespan,
    )
    app.add_middleware(ApiGuard, config=config)
    app.add_middleware(SecurityHeadersMiddleware, headers=STUDIO_HEADERS)
    app.state.service = service
    app.state.jobs = jobs
    app.state.config = config
    return app
