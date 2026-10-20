"""Private portal: a minimal static server for the current release's site (site.md §5).

It serves the folder kept up to date by :class:`~docwiki.portal.sync.SiteSync` (or a local folder),
maps Quartz's extensionless URLs to ``.html`` files, answers ``404.html`` for missing pages and sets
security headers on every response. It is designed to run behind Azure Container Apps built-in
authentication (interactive Entra sign-in): the app itself does no authentication.

With ``live_ask`` (``DOCWIKI_LIVE_ASK=1``, see :mod:`docwiki.portal.live_ask`) it also answers the
questions that anonymous visitors ask the Researcher agent from the wiki's drawer (``/api/ask``).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator, Awaitable, Callable, MutableMapping
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from starlette.routing import Route

from docwiki.portal.live_ask import LiveAsk, live_ask_routes
from docwiki.portal.sync import SiteState, SiteSync, site_state_from_dir

__all__ = [
    "CONTENT_SECURITY_POLICY",
    "SECURITY_HEADERS",
    "SecurityHeadersMiddleware",
    "create_app",
]

log = logging.getLogger("docwiki.portal")

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        # Quartz's explorer evaluates its configured sort/filter functions and the graph
        # (PixiJS) compiles shader code at runtime; every script is still same-origin.
        "script-src 'self' 'unsafe-eval'",
        # Quartz components set inline style attributes (layout of the toolbar, popovers).
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self'",
        "connect-src 'self'",
        "worker-src 'self' blob:",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)

SECURITY_HEADERS: dict[str, str] = {
    "content-security-policy": CONTENT_SECURITY_POLICY,
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "x-frame-options": "DENY",
    "cross-origin-opener-policy": "same-origin",
    "cross-origin-resource-policy": "same-origin",
    "permissions-policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
}

CONTENT_TYPES: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".json": "application/json",
    ".xml": "application/xml",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".pdf": "application/pdf",
    ".csv": "text/csv; charset=utf-8",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
"""Explicit types (Windows' registry-based guesses are unreliable); others are downloads."""

CACHE_CONTROL = "private, no-cache"

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


class SecurityHeadersMiddleware:
    """Add :data:`SECURITY_HEADERS` to every HTTP response (errors and redirects included)."""

    def __init__(self, app: ASGIApp, headers: dict[str, str] | None = None) -> None:
        self.app = app
        self.headers = [
            (name.encode("latin-1"), value.encode("latin-1"))
            for name, value in (headers or SECURITY_HEADERS).items()
        ]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                existing = {name.lower() for name, _ in message.get("headers", [])}
                extra = [(name, value) for name, value in self.headers if name not in existing]
                message["headers"] = [*message.get("headers", []), *extra]
            await send(message)

        await self.app(scope, receive, send_with_headers)


def _content_type(path: Path) -> str:
    return CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")


def _candidates(url_path: str) -> tuple[list[str], str | None]:
    """Site files to try for a URL path, and the folder to redirect to (``x`` → ``x/``)."""
    path = url_path.lstrip("/")
    if not path or path.endswith("/"):
        return [f"{path}index.html"], None
    return [path, f"{path}.html"], f"{path}/index.html"


def _is_safe(url_path: str) -> bool:
    if "\x00" in url_path or "\\" in url_path:
        return False
    parts = [part for part in url_path.split("/") if part]
    return not any(part in (".", "..") or part.startswith(".") for part in parts)


class _Portal:
    def __init__(
        self,
        sync: SiteSync | None,
        static: SiteState | None,
        poll_seconds: float,
    ) -> None:
        self.sync = sync
        self.static = static
        self.poll_seconds = poll_seconds

    @property
    def state(self) -> SiteState | None:
        return self.static or (self.sync.state if self.sync else None)

    def _file(self, state: SiteState, rel: str) -> Path | None:
        candidate = state.root.joinpath(*rel.split("/"))
        try:
            resolved = candidate.resolve()
        except OSError:
            return None
        if resolved.is_file() and resolved.is_relative_to(state.root):
            return resolved
        return None

    def _respond(
        self, request: Request, state: SiteState, rel: str, file: Path, status: int
    ) -> Response:
        etag = state.hashes.get(rel)
        headers = {"cache-control": CACHE_CONTROL}
        if etag:
            headers["etag"] = f'"{etag}"'
            if status == 200 and request.headers.get("if-none-match") == headers["etag"]:
                return Response(status_code=304, headers=headers)
        return FileResponse(
            file, status_code=status, headers=headers, media_type=_content_type(file)
        )

    async def page(self, request: Request) -> Response:
        state = self.state
        if state is None:
            return PlainTextResponse(
                "No site has been published yet.",
                status_code=503,
                headers={"retry-after": "30", "cache-control": "no-store"},
            )
        url_path = request.scope["path"]
        if _is_safe(url_path):
            candidates, folder_index = _candidates(url_path)
            for rel in candidates:
                file = self._file(state, rel)
                if file is not None:
                    return self._respond(request, state, rel, file, 200)
            if folder_index and self._file(state, folder_index) is not None:
                raw = request.scope.get("raw_path") or url_path.encode("utf-8")
                query = request.url.query
                location = raw.decode("latin-1") + "/" + (f"?{query}" if query else "")
                return Response(status_code=308, headers={"location": location})
        not_found = self._file(state, "404.html")
        if not_found is not None:
            return self._respond(request, state, "404.html", not_found, 404)
        return PlainTextResponse("Not found", status_code=404)

    async def health(self, _request: Request) -> JSONResponse:
        state = self.state
        payload: dict[str, Any] = {
            "status": "ok" if state else "unavailable",
            "release_id": state.release_id if state else None,
            "manifest_sha256": state.manifest_sha256 if state else None,
            "synced_at": state.synced_at.isoformat() if state else None,
            "error": self.sync.last_error if self.sync else None,
        }
        return JSONResponse(
            payload, status_code=200 if state else 503, headers={"cache-control": "no-store"}
        )

    async def live(self, _request: Request) -> JSONResponse:
        return JSONResponse({"status": "alive"}, headers={"cache-control": "no-store"})

    async def refresh(self) -> None:
        if self.sync is None:
            return
        try:
            if await asyncio.to_thread(self.sync.refresh):
                state = self.sync.state
                log.info("serving release %s", state.release_id if state else None)
        except Exception:
            log.exception("site sync failed; still serving the previous site")

    async def poll(self) -> None:
        while True:
            await asyncio.sleep(self.poll_seconds)
            await self.refresh()


def create_app(
    sync: SiteSync | None = None,
    *,
    site_dir: str | Path | None = None,
    poll_seconds: float = 30.0,
    headers: dict[str, str] | None = None,
    live_ask: LiveAsk | None = None,
) -> Starlette:
    """Portal ASGI app serving ``sync``'s current site (polled every ``poll_seconds``) or, for a
    local preview, an already built ``site_dir``. ``live_ask`` adds the visitors' questions to the
    Researcher; ``/api/ask/status`` reports whether it is enabled."""
    if (sync is None) == (site_dir is None):
        raise ValueError("pass exactly one of sync or site_dir")
    static = site_state_from_dir(Path(site_dir)) if site_dir is not None else None
    portal = _Portal(sync, static, poll_seconds)
    if live_ask is not None:
        live_ask.site_root = lambda: portal.state.root if portal.state else None

    @contextlib.asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncIterator[None]:
        await portal.refresh()
        task = asyncio.create_task(portal.poll()) if sync and poll_seconds > 0 else None
        try:
            yield
        finally:
            if live_ask is not None:
                await live_ask.aclose()
            if task is not None:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    app = Starlette(
        routes=[
            *live_ask_routes(live_ask),
            Route("/healthz", portal.health, methods=["GET", "HEAD"]),
            Route("/livez", portal.live, methods=["GET", "HEAD"]),
            Route("/{path:path}", portal.page, methods=["GET", "HEAD"]),
        ],
        lifespan=lifespan,
    )
    app.add_middleware(SecurityHeadersMiddleware, headers=headers)
    app.state.portal = portal
    return app
