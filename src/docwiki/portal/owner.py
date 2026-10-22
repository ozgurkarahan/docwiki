"""The process API and the owner's upload, on the portal (ADR 0009).

``GET /api/process`` is public and read-only. The owner signs in on the same site through
Container Apps built-in authentication in ``AllowAnonymous`` mode, which injects the principal
headers (and strips any a client sends); this module then decides, fail closed: a call is the
owner's only when ``x-ms-client-principal-id`` names an object ID of ``DOCWIKI_PORTAL_OWNERS``.
Owner calls use GET and PUT only: built-in authentication refuses every browser POST that carries
its session cookie. A write also needs the ``X-DocWiki-Owner: 1`` header and a same-origin
request, so a cross-site page cannot make the owner's browser upload.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from docwiki.contracts.formats import SUPPORTED_EXTENSIONS
from docwiki.contracts.storage import StorageError
from docwiki.portal.process import (
    ProcessService,
    UploadConflictError,
    UploadError,
    UploadQuotaError,
    UploadTooLargeError,
)

__all__ = [
    "OWNER_HEADER",
    "OwnerConfig",
    "OwnerConfigError",
    "process_routes",
]

log = logging.getLogger("docwiki.portal.owner")

OWNERS_ENV = "DOCWIKI_PORTAL_OWNERS"
MAX_UPLOAD_MB_ENV = "DOCWIKI_PORTAL_MAX_UPLOAD_MB"
DAILY_UPLOADS_ENV = "DOCWIKI_PORTAL_DAILY_UPLOADS"
DEFAULT_MAX_UPLOAD_MB = 50
DEFAULT_DAILY_UPLOADS = 10

PRINCIPAL_ID = "x-ms-client-principal-id"
PRINCIPAL_NAME = "x-ms-client-principal-name"
OWNER_HEADER = "x-docwiki-owner"
RETURN_PAGE = "/pipeline"
SIGN_IN_URL = f"/.auth/login/aad?post_login_redirect_uri={RETURN_PAGE}"
SIGN_OUT_URL = f"/.auth/logout?post_logout_redirect_uri={RETURN_PAGE}"
NO_STORE = {"cache-control": "no-store"}


class OwnerConfigError(ValueError):
    """An invalid ``DOCWIKI_PORTAL_*`` owner setting."""


def _positive_int(value: str | None, default: int, name: str) -> int:
    if value is None or not value.strip():
        return default
    try:
        number = int(value)
    except ValueError as exc:
        raise OwnerConfigError(f"{name} must be a whole number") from exc
    if number <= 0:
        raise OwnerConfigError(f"{name} must be positive")
    return number


@dataclass(frozen=True)
class OwnerConfig:
    """Who the owner is and what an upload may be."""

    owners: frozenset[str] = frozenset()
    """Entra object IDs of the owners (lower case). Set only where built-in authentication runs
    in front of the portal: without it any client could send the principal header."""
    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_MB * 1024 * 1024
    daily_uploads: int = DEFAULT_DAILY_UPLOADS
    """Each upload of a new or changed file starts a pipeline run (model calls cost money)."""
    local_owner: bool = False
    """Loopback preview: every caller is the owner and there is no sign-in."""

    @classmethod
    def from_env(
        cls, env: Mapping[str, str] | None = None, *, local_owner: bool = False
    ) -> OwnerConfig:
        values = os.environ if env is None else env
        owners = frozenset(
            item.strip().lower()
            for item in (values.get(OWNERS_ENV) or "").split(",")
            if item.strip()
        )
        max_mb = _positive_int(
            values.get(MAX_UPLOAD_MB_ENV), DEFAULT_MAX_UPLOAD_MB, MAX_UPLOAD_MB_ENV
        )
        return cls(
            owners=owners,
            max_upload_bytes=max_mb * 1024 * 1024,
            daily_uploads=_positive_int(
                values.get(DAILY_UPLOADS_ENV), DEFAULT_DAILY_UPLOADS, DAILY_UPLOADS_ENV
            ),
            local_owner=local_owner,
        )

    @property
    def sign_in(self) -> bool:
        """Whether the site offers a sign-in (owners are declared and auth runs in front)."""
        return bool(self.owners) and not self.local_owner

    def principal(self, request: Request) -> str | None:
        value = (request.headers.get(PRINCIPAL_ID) or "").strip().lower()
        return value or None

    def is_owner(self, request: Request) -> bool:
        if self.local_owner:
            return True
        principal = self.principal(request)
        return principal is not None and principal in self.owners


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status, headers=NO_STORE)


def _cross_site(request: Request) -> str | None:
    if request.headers.get(OWNER_HEADER) != "1":
        return "missing X-DocWiki-Owner header"
    site = request.headers.get("sec-fetch-site")
    if site and site not in ("same-origin", "none"):
        return "cross-site request refused"
    origin = request.headers.get("origin")
    if origin and origin != "null":
        host = (request.headers.get("host") or "").lower()
        if urlsplit(origin).netloc.lower() != host:
            return "cross-origin request refused"
    return None


def process_routes(service: ProcessService | None, config: OwnerConfig) -> list[Route]:
    """``/api/process`` (public) and the owner's ``/api/owner/*`` routes. Without a storage
    (a static preview) the process view answers 503 and nobody can upload."""

    async def process(request: Request) -> JSONResponse:
        if service is None:
            return _error(503, "the process view needs the release storage (not a static preview)")
        try:
            view = await asyncio.to_thread(service.process, owner=config.is_owner(request))
        except StorageError:
            log.exception("process view failed")
            return _error(502, "the pipeline state is unavailable right now")
        return JSONResponse(view, headers=NO_STORE)

    async def status(_request: Request) -> JSONResponse:
        if service is None:
            return _error(503, "the status needs the release storage (not a static preview)")
        try:
            summary = await asyncio.to_thread(service.status)
        except StorageError:
            log.exception("status failed")
            return _error(502, "the pipeline state is unavailable right now")
        return JSONResponse(summary, headers=NO_STORE)

    def me(request: Request) -> JSONResponse:
        owner = config.is_owner(request) and service is not None
        principal = config.principal(request)
        return JSONResponse(
            {
                "sign_in": config.sign_in,
                "signed_in": principal is not None or config.local_owner,
                "owner": owner,
                "name": request.headers.get(PRINCIPAL_NAME) if owner else None,
                "sign_in_url": SIGN_IN_URL if config.sign_in else None,
                "sign_out_url": SIGN_OUT_URL if config.sign_in and principal else None,
                "upload": (
                    {
                        "max_mb": config.max_upload_bytes // (1024 * 1024),
                        "uploads_left": service.uploads_left(),
                        "extensions": list(SUPPORTED_EXTENSIONS),
                    }
                    if owner and service is not None
                    else None
                ),
            },
            headers=NO_STORE,
        )

    async def upload(request: Request) -> JSONResponse:
        if service is None:
            return _error(503, "uploads need the release storage (not a static preview)")
        if not config.is_owner(request):
            if config.principal(request) is None:
                return _error(401, "sign in as the owner to add documents")
            return _error(403, "this account may not add documents")
        refused = _cross_site(request)
        if refused is not None:
            return _error(403, refused)
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
            result: dict[str, Any] = await asyncio.to_thread(
                service.upload, path, bytes(body), replace=replace
            )
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
            return _error(502, "the storage refused the upload; the portal logs have the details")
        log.info("owner upload: raw/%s (%d bytes)", result["path"], result["size"])
        result["uploads_left"] = service.uploads_left()
        return JSONResponse(result, status_code=201, headers=NO_STORE)

    return [
        Route("/api/process", process, methods=["GET", "HEAD"]),
        Route("/api/status", status, methods=["GET", "HEAD"]),
        Route("/api/owner/me", me, methods=["GET", "HEAD"]),
        Route("/api/owner/documents/{path:path}", upload, methods=["PUT"]),
    ]
