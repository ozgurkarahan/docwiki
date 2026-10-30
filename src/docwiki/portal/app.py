"""Private portal: a minimal static server for the current release's site (site.md §5).

It serves the folder kept up to date by :class:`~docwiki.portal.sync.SiteSync` (or a local folder),
maps Quartz's extensionless URLs to ``.html`` files, answers ``404.html`` for missing pages and sets
security headers on every response. It is designed to run behind Azure Container Apps built-in
authentication (interactive Entra sign-in): the app itself does no authentication.

With ``live_ask`` (``DOCWIKI_LIVE_ASK=1``, see :mod:`docwiki.portal.live_ask`) it also answers the
questions that anonymous visitors ask the Researcher agent from the wiki's drawer (``/api/ask``).

When the site declares mirror languages (``static/docwiki/languages.json``, first language
canonical, ADR 0012), a browser navigation to a canonical page is redirected (302) to its twin
under ``/<lang>/`` when the reader prefers a mirror language: the ``docwiki_lang`` cookie set by the
site's language switch wins, then ``Accept-Language``. Mirror pages are never redirected back.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import math
import re
from collections.abc import AsyncIterator, Awaitable, Callable, MutableMapping
from pathlib import Path, PurePosixPath
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from starlette.routing import Route

from docwiki.portal.live_ask import LiveAsk, live_ask_routes
from docwiki.portal.owner import OwnerConfig, process_routes
from docwiki.portal.process import ProcessService
from docwiki.portal.sync import SiteState, SiteSync, gzip_path, site_state_from_dir

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
"""Revalidate every time: signed-in readers, non-public releases and language redirects."""
PAGE_CACHE_CONTROL = "public, max-age=60, stale-while-revalidate=600"
"""Public pages and data files: a new release shows within about a minute."""
ASSET_CACHE_CONTROL = "public, max-age=3600"
"""Public styles, scripts, fonts and images. Quartz does not put content hashes in their names
(``index.css``, ``postscript.js``), so they are cached for an hour, not forever."""
ASSET_SUFFIXES = frozenset(
    {
        ".css",
        ".js",
        ".mjs",
        ".woff",
        ".woff2",
        ".ttf",
        ".svg",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".ico",
    }
)
PRINCIPAL_HEADERS = ("x-ms-client-principal", "x-ms-client-principal-id", "authorization")
"""Built-in authentication adds the first two for a signed-in caller: their responses stay
private (a portal behind sign-in, or the owner on the public portal)."""
_MAX_ACCEPT_ENCODING = 512

PAGE_ALIASES: dict[str, str] = {"/how-it-works": "/pipeline"}
"""Old page URLs that redirect permanently (ADR 0010 renamed the process page), also under a
language prefix (``/en/how-it-works`` → ``/en/pipeline``)."""

LANGUAGES_FILE = "static/docwiki/languages.json"
"""Written by the site build: ``{"schema": 1, "canonical": "fr", "languages": ["fr", "en"]}``."""
LANGUAGE_COOKIE = "docwiki_lang"
"""Set by the site's client-side language switch; it beats ``Accept-Language``."""
LANGUAGE_VARY = "Accept-Language, Cookie"
_LANGUAGE_CODE = re.compile(r"[a-z]{2}")
_LANGUAGE_TAG = re.compile(r"[a-z]{1,8}(?:-[a-z0-9]{1,8})*")
_NEVER_NEGOTIATED = frozenset({"static", "evidence", "api", "404.html"})
"""First path segments (or files) of the site that are never language-negotiated."""
_MAX_ACCEPT_LANGUAGE = 512
_MAX_ACCEPT_ITEMS = 32

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


def _alias_target(url_path: str) -> str | None:
    """Target of an old page URL (``/how-it-works``, ``/en/how-it-works/``), or ``None``."""
    stem = url_path[:-1] if url_path.endswith("/") else url_path
    if stem in PAGE_ALIASES:
        return PAGE_ALIASES[stem]
    prefix, sep, rest = stem.removeprefix("/").partition("/")
    target = PAGE_ALIASES.get(f"/{rest}") if sep else None
    if target and _LANGUAGE_CODE.fullmatch(prefix):
        return f"/{prefix}{target}"
    return None


def _read_languages(file: Path | None) -> tuple[str, ...]:
    """The site's languages (canonical first), or ``()`` when the file is missing or invalid."""
    if file is None:
        return ()
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        log.warning("%s is unreadable; serving without language mirrors", LANGUAGES_FILE)
        return ()
    languages = data.get("languages") if isinstance(data, dict) else None
    if (
        not isinstance(data, dict)
        or data.get("schema", 1) != 1
        or not isinstance(languages, list)
        or not languages
        or not all(isinstance(c, str) and _LANGUAGE_CODE.fullmatch(c) for c in languages)
        or len(set(languages)) != len(languages)
        or data.get("canonical", languages[0]) != languages[0]
    ):
        log.warning("%s is invalid; serving without language mirrors", LANGUAGES_FILE)
        return ()
    return tuple(languages)


def _accept_language(header: str, languages: tuple[str, ...]) -> dict[str, float]:
    """Best q-value of each of ``languages`` in an ``Accept-Language`` header (absent = 0,
    ``*`` counts for the languages not listed), matched on the primary subtag."""
    best: dict[str, float] = {}
    star = 0.0
    for item in header[:_MAX_ACCEPT_LANGUAGE].split(",")[:_MAX_ACCEPT_ITEMS]:
        tag, *params = (part.strip() for part in item.split(";"))
        tag = tag.lower()
        q: float | None = 1.0
        for param in params:
            name, _, value = param.partition("=")
            if name.strip().lower() == "q":
                try:
                    q = float(value.strip())
                except ValueError:
                    q = None
        if q is None or math.isnan(q) or not 0.0 <= q <= 1.0:
            continue
        if tag == "*":
            star = max(star, q)
        elif _LANGUAGE_TAG.fullmatch(tag):
            primary = tag.split("-", 1)[0]
            best[primary] = max(best.get(primary, 0.0), q)
    return {language: best.get(language, star) for language in languages}


def _reader_language(request: Request, languages: tuple[str, ...]) -> str | None:
    """The mirror language the reader prefers over the canonical one, or ``None``."""
    cookie = request.cookies.get(LANGUAGE_COOKIE, "").strip().lower()
    if cookie in languages:
        return cookie if cookie != languages[0] else None
    header = request.headers.get("accept-language")
    if not header:
        return None
    q = _accept_language(header, languages)
    mirror = max(languages[1:], key=lambda language: q[language])
    return mirror if q[mirror] > q[languages[0]] else None


def _is_safe(url_path: str) -> bool:
    if "\x00" in url_path or "\\" in url_path:
        return False
    parts = [part for part in url_path.split("/") if part]
    return not any(part in (".", "..") or part.startswith(".") for part in parts)


def _accepts_gzip(header: str | None) -> bool:
    """Whether an ``Accept-Encoding`` header accepts gzip (``gzip``/``x-gzip`` or ``*``, q > 0)."""
    if not header:
        return False
    gzip_q: float | None = None
    star_q = 0.0
    for item in header[:_MAX_ACCEPT_ENCODING].split(",")[:_MAX_ACCEPT_ITEMS]:
        coding, *params = (part.strip() for part in item.split(";"))
        q = 1.0
        for param in params:
            name, _, value = param.partition("=")
            if name.strip().lower() == "q":
                try:
                    q = float(value.strip())
                except ValueError:
                    q = 0.0
        if math.isnan(q):
            q = 0.0
        coding = coding.lower()
        if coding in ("gzip", "x-gzip"):
            gzip_q = max(gzip_q or 0.0, q)
        elif coding == "*":
            star_q = max(star_q, q)
    return (gzip_q if gzip_q is not None else star_q) > 0.0


def _etag_matches(header: str | None, etag: str) -> bool:
    """``If-None-Match`` (weak comparison, lists and ``*``) against a quoted ETag."""
    if not header:
        return False
    tags = [tag.strip() for tag in header.split(",")]
    return any(tag == "*" or tag.removeprefix("W/") == etag for tag in tags)


def _add_vary(current: str | None, name: str) -> str:
    return f"{current}, {name}" if current else name


class _Portal:
    def __init__(
        self,
        sync: SiteSync | None,
        static: SiteState | None,
        poll_seconds: float,
        public_cache: bool | None = None,
    ) -> None:
        self.sync = sync
        self.static = static
        self.poll_seconds = poll_seconds
        self.public_cache = public_cache
        self._languages: tuple[tuple[Path, str | None, str | None], tuple[str, ...]] | None = None

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

    def languages(self, state: SiteState) -> tuple[str, ...]:
        """The served site's languages, canonical first (read once per site state)."""
        key = (state.root, state.release_id, state.manifest_sha256)
        if self._languages is None or self._languages[0] != key:
            self._languages = (key, _read_languages(self._file(state, LANGUAGES_FILE)))
        return self._languages[1]

    def _negotiate(
        self, request: Request, state: SiteState, rel: str, headers: dict[str, str]
    ) -> Response | None:
        """Redirect a navigation to a canonical page to its mirror twin when the reader prefers
        the mirror language; mark negotiable responses with ``Vary`` (added to ``headers``)."""
        languages = self.languages(state)
        mirrors = languages[1:]
        first = rel.split("/", 1)[0]
        if not mirrors or not rel.endswith(".html") or first in mirrors:
            return None
        if first in _NEVER_NEGOTIATED or rel in _NEVER_NEGOTIATED:
            return None
        headers["vary"] = LANGUAGE_VARY
        if request.headers.get("sec-fetch-dest", "document").strip().lower() != "document":
            return None
        language = _reader_language(request, languages)
        if language is None or self._file(state, f"{language}/{rel}") is None:
            return None
        raw = request.scope.get("raw_path") or request.scope["path"].encode("utf-8")
        query = request.url.query
        location = f"/{language}" + raw.decode("latin-1") + (f"?{query}" if query else "")
        return Response(
            status_code=302,
            headers={"location": location, "cache-control": CACHE_CONTROL, **headers},
        )

    def _shared(self, request: Request, state: SiteState) -> bool:
        """Whether shared caches may keep the response: an anonymous request for a public site
        (``public_cache``, or by default a release whose audience is ``public``)."""
        if self.public_cache is False:
            return False
        if any(name in request.headers for name in PRINCIPAL_HEADERS):
            return False
        return self.public_cache is True or state.audience == "public"

    def _cache_control(self, request: Request, state: SiteState, rel: str) -> str:
        if not self._shared(request, state):
            return CACHE_CONTROL
        if PurePosixPath(rel).suffix.lower() in ASSET_SUFFIXES:
            return ASSET_CACHE_CONTROL
        return PAGE_CACHE_CONTROL

    def _respond(
        self,
        request: Request,
        state: SiteState,
        rel: str,
        file: Path,
        status: int,
        extra: dict[str, str] | None = None,
    ) -> Response:
        etag = state.hashes.get(rel)
        headers = {"cache-control": self._cache_control(request, state, rel), **(extra or {})}
        served = file
        if rel in state.compressed:
            headers["vary"] = _add_vary(headers.get("vary"), "Accept-Encoding")
            packed = gzip_path(state.root, rel)
            if (
                _accepts_gzip(request.headers.get("accept-encoding"))
                and "range" not in request.headers
                and packed.is_file()
            ):
                served = packed
                headers["content-encoding"] = "gzip"
                etag = f"{etag}-gz" if etag else None
        if etag:
            headers["etag"] = f'"{etag}"'
            if status == 200 and _etag_matches(
                request.headers.get("if-none-match"), headers["etag"]
            ):
                headers.pop("content-encoding", None)
                return Response(status_code=304, headers=headers)
        return FileResponse(
            served, status_code=status, headers=headers, media_type=_content_type(file)
        )

    async def page(self, request: Request) -> Response:
        url_path = request.scope["path"]
        target = _alias_target(url_path)
        if target is not None:
            query = request.url.query
            return Response(
                status_code=308, headers={"location": target + (f"?{query}" if query else "")}
            )
        state = self.state
        if state is None:
            return PlainTextResponse(
                "No site has been published yet.",
                status_code=503,
                headers={"retry-after": "30", "cache-control": "no-store"},
            )
        if _is_safe(url_path):
            candidates, folder_index = _candidates(url_path)
            for rel in candidates:
                file = self._file(state, rel)
                if file is not None:
                    vary: dict[str, str] = {}
                    redirect = self._negotiate(request, state, rel, vary)
                    if redirect is not None:
                        return redirect
                    return self._respond(request, state, rel, file, 200, vary)
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
    process: ProcessService | None = None,
    owner: OwnerConfig | None = None,
    public_cache: bool | None = None,
) -> Starlette:
    """Portal ASGI app serving ``sync``'s current site (polled every ``poll_seconds``) or, for a
    local preview, an already built ``site_dir``. ``live_ask`` adds the visitors' questions to the
    Researcher; ``/api/ask/status`` reports whether it is enabled. ``process`` serves the live
    process view and, for the owners of ``owner``, the uploads (ADR 0009). A site that declares
    mirror languages sends the readers who prefer one of them to its mirror pages (ADR 0012).

    Site files are cacheable by shared caches only for anonymous requests (no built-in
    authentication principal) to a public site: by default when the release's audience is
    ``public``; ``public_cache`` forces it on (still anonymous requests only) or off. Every other
    response is ``private, no-cache``. Precompressed copies (:mod:`docwiki.portal.sync`) are sent
    to clients that accept gzip."""
    if (sync is None) == (site_dir is None):
        raise ValueError("pass exactly one of sync or site_dir")
    static = site_state_from_dir(Path(site_dir)) if site_dir is not None else None
    portal = _Portal(sync, static, poll_seconds, public_cache)
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
            *process_routes(process, owner or OwnerConfig()),
            Route("/healthz", portal.health, methods=["GET", "HEAD"]),
            Route("/livez", portal.live, methods=["GET", "HEAD"]),
            Route("/{path:path}", portal.page, methods=["GET", "HEAD"]),
        ],
        lifespan=lifespan,
    )
    app.add_middleware(SecurityHeadersMiddleware, headers=headers)
    app.state.portal = portal
    return app
