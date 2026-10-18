"""Azure Content Understanding adapter (GA REST API ``2025-11-01``) for PDF and image files.

Only PDFs and images go to the service; every other format keeps the deterministic local
adapters so that locators stay stable. The REST flow, verified against Microsoft Learn
("Content Analyzers - Analyze Binary" and "Content Analyzers - Get Result", api-version
2025-11-01):

1. ``POST {endpoint}/contentunderstanding/analyzers/{analyzerId}:analyzeBinary
   ?api-version=2025-11-01&stringEncoding=codePoint[&range=1-N]`` with the raw file as the body
   (``Content-Type: application/octet-stream``) → ``202 Accepted`` and an ``Operation-Location``
   header (``…/contentunderstanding/analyzerResults/{id}?api-version=2025-11-01``).
2. ``GET`` the operation location until ``status`` is ``Succeeded`` (or ``Failed``/``Canceled``);
   the ``result.contents[0]`` document holds ``pages``, ``paragraphs``, ``tables`` and
   ``figures`` whose ``source`` is ``D(page,x1,y1,…,x4,y4)`` (or ``D(page,left,top,width,
   height)``) in the content ``unit`` (inches for PDF, pixels for images).

Authentication is Microsoft Entra ID only (``DefaultAzureCredential``, scope
``https://cognitiveservices.azure.com/.default``); no keys. ``cu_mode`` selects ``live``,
``record`` (live + write one JSON recording per request hash) or ``replay`` (recordings only,
offline). Recordings never contain the endpoint, the operation id or the document bytes.
"""

from __future__ import annotations

import asyncio
import bisect
import json
import os
import random
import re
import statistics
import threading
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol
from urllib.parse import urlsplit

import httpx

from docwiki.contracts import canonical_json, sha256_hex
from docwiki.contracts.enums import BlockKind
from docwiki.contracts.locators import ImageRegionLocator, Locator, PdfPageLocator
from docwiki.engine_types import ExtractionError, ExtractSettings
from docwiki.extract._draft import CU_ADAPTER_VERSION, CU_API_VERSION, Draft, round_bbox
from docwiki.extract._images import crop_png
from docwiki.extract._tables import emit_table
from docwiki.extract._text import BULLET_RE, clean_text, one_line
from docwiki.extract.formats import FormatFamily
from docwiki.extract.local_image import FULL_IMAGE, load_page_image
from docwiki.extract.local_pdf import pdf_pages

__all__ = [
    "API_VERSION",
    "TOKEN_SCOPE",
    "AzureTokenProvider",
    "ContentUnderstandingClient",
    "ContentUnderstandingError",
    "CuServiceError",
    "TokenProvider",
    "client_factory",
    "cu_request",
    "extract_with_cu",
    "map_result",
    "recording_path",
    "request_hash",
]

API_VERSION = CU_API_VERSION
TOKEN_SCOPE = "https://cognitiveservices.azure.com/.default"
CONTENT_TYPE = "application/octet-stream"
STRING_ENCODING = "codePoint"
RECORDING_SCHEMA = 1


class ContentUnderstandingError(ExtractionError):
    """Content Understanding failed for a source (``retryable`` for throttling/outages).

    ``systemic`` errors are not the document's fault — throttling, outages, network errors,
    timeouts (``retryable``), HTTP 401/403 or no Entra token (``auth``): the orchestrator aborts
    the run so that it is retried instead of quarantining the source.
    """

    def __init__(
        self,
        source_id: str,
        reason: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
        auth: bool = False,
    ) -> None:
        super().__init__(source_id, reason)
        self.status_code = status_code
        self.retryable = retryable
        self.auth = auth or status_code in (401, 403)

    @property
    def systemic(self) -> bool:
        return self.retryable or self.auth


class CuServiceError(Exception):
    """Transport-level failure of a Content Understanding call (``auth``: 401/403 or no token)."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
        auth: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable
        self.auth = auth or status_code in (401, 403)


class TokenProvider(Protocol):
    async def get_token(self) -> str: ...


class AzureTokenProvider:
    """Entra ID bearer tokens from ``DefaultAzureCredential`` (cached until 5 minutes before
    expiry; the synchronous credential runs in a worker thread)."""

    def __init__(self, credential: Any | None = None) -> None:
        self._credential = credential
        self._token: str | None = None
        self._expires_on = 0.0
        self._lock = threading.Lock()

    def _fetch(self) -> tuple[str, float]:
        with self._lock:
            if self._token and time.time() < self._expires_on - 300:
                return self._token, self._expires_on
            if self._credential is None:
                try:
                    from azure.identity import DefaultAzureCredential
                except ImportError as exc:  # pragma: no cover - the azure extra is installed
                    raise CuServiceError(
                        "azure-identity is not installed (install the 'azure' extra)", auth=True
                    ) from exc
                self._credential = DefaultAzureCredential()
            try:
                access = self._credential.get_token(TOKEN_SCOPE)
            except Exception as exc:
                raise CuServiceError(
                    f"cannot get a Microsoft Entra ID token for Content Understanding "
                    f"({type(exc).__name__}); sign in with 'az login' or configure the "
                    "managed identity",
                    auth=True,
                ) from exc
            self._token, self._expires_on = access.token, float(access.expires_on)
            return self._token, self._expires_on

    async def get_token(self) -> str:
        if self._token and time.time() < self._expires_on - 300:
            return self._token
        token, _ = await asyncio.to_thread(self._fetch)
        return token


_SHARED_TOKENS: AzureTokenProvider | None = None
_SHARED_LOCK = threading.Lock()


def _shared_tokens() -> AzureTokenProvider:
    global _SHARED_TOKENS
    with _SHARED_LOCK:
        if _SHARED_TOKENS is None:
            _SHARED_TOKENS = AzureTokenProvider()
        return _SHARED_TOKENS


_RESOURCE_SUFFIXES = (".cognitiveservices.azure.com", ".services.ai.azure.com")


def _same_resource(host: str | None, endpoint: str) -> bool:
    """Same host as the endpoint, or the same Foundry resource under its other AI domain."""
    own = (urlsplit(endpoint).hostname or "").lower()
    host = (host or "").lower()
    if host == own:
        return True
    own_suffix = next((s for s in _RESOURCE_SUFFIXES if own.endswith(s)), None)
    host_suffix = next((s for s in _RESOURCE_SUFFIXES if host.endswith(s)), None)
    if own_suffix is None or host_suffix is None:
        return False
    return own[: -len(own_suffix)] == host[: -len(host_suffix)] != ""


def normalize_endpoint(endpoint: str) -> str:
    """``https://<resource>.cognitiveservices.azure.com`` (no trailing slash or API path).

    Content Understanding is an account-level API: a Foundry project endpoint
    (``https://<resource>.services.ai.azure.com/api/projects/<project>``, what the pipeline is
    configured with) is reduced to its account. Project paths only accept tokens for the
    ``https://ai.azure.com`` audience, so keeping the path makes every call fail with 401.
    """
    value = endpoint.strip().rstrip("/")
    value = re.sub(r"/contentunderstanding$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"/api/projects/[^/]+$", "", value, flags=re.IGNORECASE)
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.netloc or parts.query or parts.fragment:
        raise ValueError("cu_endpoint must be an https URL such as https://<resource>.<domain>")
    if parts.path not in ("", "/"):
        raise ValueError(
            "cu_endpoint must be the Foundry account endpoint (https://<resource>.<domain>), "
            f"not a path such as {parts.path!r}"
        )
    return value


class ContentUnderstandingClient:
    """Minimal async client for ``analyzeBinary`` + result polling, with retries."""

    def __init__(
        self,
        endpoint: str,
        *,
        tokens: TokenProvider | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        api_version: str = API_VERSION,
        poll_interval: float = 1.0,
        max_poll_interval: float = 10.0,
        timeout_s: float = 1800.0,
        max_retries: int = 4,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.endpoint = normalize_endpoint(endpoint)
        self.api_version = api_version
        self._tokens = tokens or _shared_tokens()
        self._http = httpx.AsyncClient(
            transport=transport, timeout=httpx.Timeout(120.0, connect=30.0), follow_redirects=False
        )
        self._poll_interval = poll_interval
        self._max_poll_interval = max_poll_interval
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._sleep = sleep

    async def aclose(self) -> None:
        await self._http.aclose()

    async def analyze_binary(
        self, analyzer_id: str, data: bytes, *, content_range: str | None = None
    ) -> dict[str, Any]:
        """Run the analyzer on ``data`` and return the final operation document (Succeeded)."""
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", analyzer_id):
            raise CuServiceError(f"invalid analyzer id {analyzer_id!r}")
        url = f"{self.endpoint}/contentunderstanding/analyzers/{analyzer_id}:analyzeBinary"
        params = {"api-version": self.api_version, "stringEncoding": STRING_ENCODING}
        if content_range:
            params["range"] = content_range
        response = await self._send(
            "POST", url, params=params, content=data, headers={"Content-Type": CONTENT_TYPE}
        )
        if response.status_code != 202:
            raise self._error(response)
        location = response.headers.get("Operation-Location")
        if not location:
            raise CuServiceError("the service did not return an Operation-Location header")
        self._check_same_host(location)
        return await self._poll(location)

    def _check_same_host(self, location: str) -> None:
        """Refuse to send the bearer token anywhere but this resource's own hosts."""
        target = urlsplit(location)
        if target.scheme != "https" or not _same_resource(target.hostname, self.endpoint):
            raise CuServiceError("Operation-Location points to another host; refusing to follow")

    async def _poll(self, location: str) -> dict[str, Any]:
        deadline = time.monotonic() + self._timeout_s
        interval = self._poll_interval
        while True:
            response = await self._send("GET", location)
            if response.status_code != 200:
                raise self._error(response)
            try:
                body = response.json()
            except ValueError as exc:
                raise CuServiceError("the operation status is not JSON", retryable=True) from exc
            status = str(body.get("status", "")).lower()
            if status == "succeeded":
                return body
            if status in ("failed", "canceled", "cancelled"):
                error = body.get("error") if isinstance(body.get("error"), dict) else {}
                code = error.get("code", "unknown")
                message = one_line(str(error.get("message", "")))[:300]
                raise CuServiceError(f"analysis {status}: {code}: {message}".rstrip(": "))
            if time.monotonic() > deadline:
                raise CuServiceError(
                    f"analysis did not finish within {self._timeout_s:.0f} s", retryable=True
                )
            await self._sleep(_retry_after(response) or interval)
            interval = min(interval * 1.5, self._max_poll_interval)

    async def _send(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        content: bytes | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        attempt = 0
        while True:
            token = await self._tokens.get_token()
            request_headers = {"Authorization": f"Bearer {token}", **(headers or {})}
            try:
                response = await self._http.request(
                    method, url, params=params, content=content, headers=request_headers
                )
            except httpx.TransportError as exc:
                if attempt >= self._max_retries:
                    raise CuServiceError(
                        f"network error calling Content Understanding: {type(exc).__name__}",
                        retryable=True,
                    ) from exc
                await self._sleep(_backoff(attempt))
                attempt += 1
                continue
            if response.status_code in (408, 429) or response.status_code >= 500:
                if attempt >= self._max_retries:
                    raise self._error(response, retryable=True)
                await self._sleep(_retry_after(response) or _backoff(attempt))
                attempt += 1
                continue
            return response

    @staticmethod
    def _error(response: httpx.Response, *, retryable: bool = False) -> CuServiceError:
        code = message = ""
        try:
            error = response.json().get("error", {})
            if isinstance(error, dict):
                code = str(error.get("code", ""))
                message = one_line(str(error.get("message", "")))[:300]
        except ValueError:
            pass
        status = response.status_code
        detail = f"HTTP {status}"
        if code:
            detail += f" {code}"
        if message:
            detail += f": {message}"
        if status in (401, 403):
            detail += " (the identity needs the 'Cognitive Services User' role on the resource)"
        return CuServiceError(
            f"Content Understanding request failed: {detail}",
            status_code=status,
            retryable=retryable,
        )


def _retry_after(response: httpx.Response) -> float | None:
    for name, scale in (("retry-after-ms", 0.001), ("retry-after", 1.0)):
        value = response.headers.get(name)
        if value:
            try:
                return min(60.0, max(0.0, float(value) * scale))
            except ValueError:
                continue
    return None


def _backoff(attempt: int) -> float:
    return min(30.0, 2.0 * (2**attempt)) + random.uniform(0.0, 0.5)


def _default_client(settings: ExtractSettings) -> ContentUnderstandingClient:
    if not settings.cu_endpoint:
        raise ValueError("ExtractSettings.cu_endpoint is required for Content Understanding")
    return ContentUnderstandingClient(settings.cu_endpoint)


client_factory: Callable[[ExtractSettings], ContentUnderstandingClient] = _default_client
"""Builds the client for live/record calls (tests replace it with a mock transport)."""


# --- recordings ------------------------------------------------------------------------------


def cu_request(*, analyzer: str, data: bytes, content_range: str | None) -> dict[str, Any]:
    """The request identity: everything that determines the service response."""
    return {
        "api_version": API_VERSION,
        "analyzer": analyzer,
        "content_sha256": sha256_hex(data),
        "content_type": CONTENT_TYPE,
        "range": content_range,
        "string_encoding": STRING_ENCODING,
    }


def request_hash(request: Mapping[str, Any]) -> str:
    return sha256_hex(canonical_json(dict(request)))


def recording_path(recordings_dir: Path, request: Mapping[str, Any]) -> Path:
    return Path(recordings_dir) / f"{request_hash(request)}.json"


def _scrub(response: Mapping[str, Any]) -> dict[str, Any]:
    """Drop the operation id (a service GUID) from a recorded response."""
    return {key: value for key, value in response.items() if key != "id"}


def save_recording(path: Path, request: Mapping[str, Any], response: Mapping[str, Any]) -> None:
    payload = {"schema": RECORDING_SCHEMA, "request": dict(request), "response": _scrub(response)}
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def load_recording(path: Path, request: Mapping[str, Any]) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != RECORDING_SCHEMA:
        raise ValueError(f"{path.name}: not a DocWiki Content Understanding recording")
    if payload.get("request") != dict(request):
        raise ValueError(f"{path.name}: the recorded request does not match this request")
    response = payload.get("response")
    if not isinstance(response, dict):
        raise ValueError(f"{path.name}: the recording has no response")
    return response


async def run_analysis(
    data: bytes, *, settings: ExtractSettings, source_id: str, content_range: str | None
) -> dict[str, Any]:
    """Live, record or replay one ``analyzeBinary`` call according to ``settings.cu_mode``."""
    request = cu_request(analyzer=settings.cu_analyzer, data=data, content_range=content_range)
    path = recording_path(settings.recordings_dir, request) if settings.recordings_dir else None
    if settings.cu_mode == "replay":
        if path is None or not path.is_file():
            name = path.name if path else f"{request_hash(request)}.json"
            raise ContentUnderstandingError(
                source_id,
                f"no Content Understanding recording {name} (cu_mode=replay); run once with "
                "cu_mode=record against a live resource to create it",
            )
        try:
            return load_recording(path, request)
        except (OSError, ValueError) as exc:
            raise ContentUnderstandingError(source_id, f"unusable recording: {exc}") from exc
    client = client_factory(settings)
    try:
        response = await client.analyze_binary(
            settings.cu_analyzer, data, content_range=content_range
        )
    except CuServiceError as exc:
        raise ContentUnderstandingError(
            source_id,
            str(exc),
            status_code=exc.status_code,
            retryable=exc.retryable,
            auth=exc.auth,
        ) from exc
    finally:
        await client.aclose()
    if settings.cu_mode == "record" and path is not None:
        save_recording(path, request, response)
    return response


# --- result mapping --------------------------------------------------------------------------


class CuResultError(ValueError):
    """The analysis result does not have the documented shape."""


_SOURCE_RE = re.compile(r"D\((\d+)((?:,[^,()]*)*)\)")
_ELEMENT_RE = re.compile(r"^/paragraphs/(\d+)$")


def parse_source(source: Any) -> list[tuple[int, tuple[float, float, float, float] | None]]:
    """``D(page,x1,y1,…)`` / ``D(page,left,top,width,height)`` → [(page, box in unit coords)]."""
    regions: list[tuple[int, tuple[float, float, float, float] | None]] = []
    if not isinstance(source, str):
        return regions
    for match in _SOURCE_RE.finditer(source):
        try:
            numbers = [float(value) for value in match[2].split(",")[1:]]
        except ValueError:
            numbers = []
        box: tuple[float, float, float, float] | None = None
        if len(numbers) == 4:
            left, top, width, height = numbers
            box = (left, top, left + width, top + height)
        elif len(numbers) >= 6 and len(numbers) % 2 == 0:
            xs, ys = numbers[0::2], numbers[1::2]
            box = (min(xs), min(ys), max(xs), max(ys))
        regions.append((int(match[1]), box))
    return regions


def _positive(value: Any) -> int:
    return value if isinstance(value, int) and value > 0 else 1


def _span(element: Mapping[str, Any]) -> tuple[int, int] | None:
    span = element.get("span")
    if isinstance(span, list):
        span = span[0] if span else None
    if not isinstance(span, dict):
        return None
    offset, length = span.get("offset"), span.get("length", 0)
    if isinstance(offset, int) and isinstance(length, int):
        return offset, length
    return None


@dataclass
class _Context:
    fmt: FormatFamily
    draft: Draft
    sizes: dict[int, tuple[float, float]]
    page_spans: list[tuple[int, int, int]]
    text_layer: Mapping[int, bool]
    page_images: Mapping[int, bytes]
    max_pages: int
    word_offsets: list[int]
    word_confidences: list[float]
    region: int = 0

    def provenance(self, page: int) -> Literal["native-text", "ocr"]:
        return "native-text" if self.text_layer.get(page) else "ocr"

    def page_of(self, element: Mapping[str, Any]) -> int:
        regions = parse_source(element.get("source"))
        if regions:
            return regions[0][0]
        span = _span(element)
        if span:
            for page, start, length in self.page_spans:
                if start <= span[0] < start + length:
                    return page
        return 1

    def bbox(self, element: Mapping[str, Any], page: int) -> list[float] | None:
        boxes = [
            box
            for number, box in parse_source(element.get("source"))
            if number == page and box is not None
        ]
        size = self.sizes.get(page)
        if not boxes or not size or size[0] <= 0 or size[1] <= 0:
            return None
        width, height = size
        return round_bbox(
            (
                min(b[0] for b in boxes) / width,
                min(b[1] for b in boxes) / height,
                max(b[2] for b in boxes) / width,
                max(b[3] for b in boxes) / height,
            )
        )

    def confidence(self, element: Mapping[str, Any]) -> float | None:
        span = _span(element)
        if span is None or not self.word_offsets:
            return None
        low = bisect.bisect_left(self.word_offsets, span[0])
        high = bisect.bisect_left(self.word_offsets, span[0] + max(1, span[1]))
        values = self.word_confidences[low:high]
        return round(statistics.fmean(values), 3) if values else None

    def locator(self, page: int, bbox: list[float] | None) -> Locator:
        """PDF page locator, or the next image region (regions follow the reading order)."""
        if self.fmt == "image":
            self.region += 1
            return ImageRegionLocator(region=self.region, bbox=bbox or list(FULL_IMAGE))
        return PdfPageLocator(page=page, bbox=bbox)


def _content(response: Mapping[str, Any], draft: Draft) -> dict[str, Any]:
    if str(response.get("status", "succeeded")).lower() != "succeeded":
        raise CuResultError(f"operation status is {response.get('status')!r}")
    result = response.get("result")
    if not isinstance(result, dict):
        raise CuResultError("missing 'result'")
    for warning in result.get("warnings") or []:
        if isinstance(warning, dict):
            code = one_line(str(warning.get("code", "warning")))[:60]
            message = one_line(str(warning.get("message", "")))[:200]
            draft.warn("cu-warning", f"{code}: {message}".rstrip(": "))
    contents = [
        item
        for item in result.get("contents") or []
        if isinstance(item, dict) and item.get("kind", "document") == "document"
    ]
    if not contents:
        raise CuResultError("no document content in the result")
    if len(contents) > 1:
        draft.warn("cu-contents", f"{len(contents)} document contents returned; using the first")
    return contents[0]


def map_result(
    response: Mapping[str, Any],
    *,
    fmt: FormatFamily,
    draft: Draft,
    text_layer: Mapping[int, bool],
    max_pages: int,
) -> None:
    """Turn a Content Understanding result into draft blocks, tables and figures."""
    content = _content(response, draft)
    sizes: dict[int, tuple[float, float]] = {}
    page_spans: list[tuple[int, int, int]] = []
    words: list[tuple[int, float]] = []
    for page in content.get("pages") or []:
        if not isinstance(page, dict) or not isinstance(page.get("pageNumber"), int):
            continue
        number = page["pageNumber"]
        width, height = page.get("width"), page.get("height")
        if isinstance(width, int | float) and isinstance(height, int | float):
            sizes[number] = (float(width), float(height))
        for span in page.get("spans") or []:
            if isinstance(span, dict) and isinstance(span.get("offset"), int):
                page_spans.append((number, span["offset"], int(span.get("length", 0))))
        for word in page.get("words") or []:
            if not isinstance(word, dict):
                continue
            span = _span(word)
            confidence = word.get("confidence")
            if span and isinstance(confidence, int | float):
                words.append((span[0], float(confidence)))
    words.sort()
    ctx = _Context(
        fmt=fmt,
        draft=draft,
        sizes=sizes,
        page_spans=page_spans,
        text_layer=text_layer,
        page_images=draft.page_images,
        max_pages=max_pages,
        word_offsets=[offset for offset, _ in words],
        word_confidences=[confidence for _, confidence in words],
    )

    paragraphs = [p for p in content.get("paragraphs") or [] if isinstance(p, dict)]
    tables = [t for t in content.get("tables") or [] if isinstance(t, dict)]
    figures = [f for f in content.get("figures") or [] if isinstance(f, dict)]
    in_tables: set[int] = set()
    for table in tables:
        for cell in table.get("cells") or []:
            for element in (cell.get("elements") or []) if isinstance(cell, dict) else []:
                match = _ELEMENT_RE.match(str(element))
                if match:
                    in_tables.add(int(match[1]))

    elements: list[tuple[str, int, Mapping[str, Any]]] = [
        ("paragraph", index, p) for index, p in enumerate(paragraphs) if index not in in_tables
    ]
    elements += [("table", index, t) for index, t in enumerate(tables)]
    elements += [("figure", index, f) for index, f in enumerate(figures)]
    rank = {"paragraph": 0, "table": 1, "figure": 2}
    use_spans = all(_span(element) is not None for _, _, element in elements)

    def order(item: tuple[str, int, Mapping[str, Any]]) -> tuple[float, float, int, int]:
        kind, index, element = item
        if use_spans:
            span = _span(element)
            return (float(span[0]) if span else 0.0, 0.0, rank[kind], index)
        page = ctx.page_of(element)
        box = ctx.bbox(element, page)
        return (float(page), box[1] if box else 0.0, rank[kind], index)

    elements.sort(key=order)

    if not paragraphs and not tables:
        _markdown_fallback(content, ctx)
    for kind, _, element in elements:
        page = ctx.page_of(element)
        if page > max_pages:
            continue
        if kind == "paragraph":
            _paragraph(element, page, ctx)
        elif kind == "table":
            _table(element, page, ctx)
        else:
            _figure(element, page, ctx)
    if fmt == "pdf" and draft.title_hint is None:
        titles = [
            one_line(str(p.get("content", ""))) for p in paragraphs if p.get("role") == "title"
        ]
        draft.title_hint = next((title for title in titles if title), None)
    if fmt == "image" and 1 in draft.page_images:
        region = ctx.region + 1
        locator = ImageRegionLocator(region=region, bbox=list(FULL_IMAGE))
        draft.figure(locator, draft.page_images[1], bbox=list(FULL_IMAGE))


def _paragraph(element: Mapping[str, Any], page: int, ctx: _Context) -> None:
    text = clean_text(str(element.get("content", "")))
    if not text:
        return
    role = element.get("role")
    level: int | None = None
    kind: BlockKind
    if role == "title":
        kind, level = "heading", 1
    elif role == "sectionHeading":
        kind, level = "heading", 2
    elif role == "footnote":
        kind = "note"
    elif BULLET_RE.match(text):
        kind = "list"
    else:
        kind = "paragraph"
    provenance = ctx.provenance(page)
    confidence = ctx.confidence(element) if provenance == "ocr" else None
    locator = ctx.locator(page, ctx.bbox(element, page))
    ctx.draft.block(kind, text, locator, provenance, level=level, confidence=confidence)


def _table(element: Mapping[str, Any], page: int, ctx: _Context) -> None:
    row_count, column_count = element.get("rowCount"), element.get("columnCount")
    if not isinstance(row_count, int) or not isinstance(column_count, int):
        ctx.draft.warn("cu-malformed", "a table without rowCount/columnCount was skipped")
        return
    row_count, column_count = min(row_count, 100_000), min(column_count, 500)
    grid = [[""] * column_count for _ in range(row_count)]
    row_cells: dict[int, list[Mapping[str, Any]]] = {}
    for cell in element.get("cells") or []:
        if not isinstance(cell, dict):
            continue
        row, column = cell.get("rowIndex"), cell.get("columnIndex")
        if not isinstance(row, int) or not isinstance(column, int):
            continue
        if not (0 <= row < row_count and 0 <= column < column_count):
            continue
        text = clean_text(str(cell.get("content", "")))
        row_span = _positive(cell.get("rowSpan"))
        column_span = _positive(cell.get("columnSpan"))
        for rr in range(row, min(row_count, row + row_span)):
            for cc in range(column, min(column_count, column + column_span)):
                grid[rr][cc] = text
        row_cells.setdefault(row, []).append(cell)
    provenance = ctx.provenance(page)
    table_locator = ctx.locator(page, ctx.bbox(element, page))
    region_table = ctx.region

    def row_locator(number: int) -> Locator:
        cells = row_cells.get(number - 1, [])
        row_page = ctx.page_of(cells[0]) if cells else page
        boxes = [box for box in (ctx.bbox(cell, row_page) for cell in cells) if box]
        bbox = (
            round_bbox(
                (
                    min(b[0] for b in boxes),
                    min(b[1] for b in boxes),
                    max(b[2] for b in boxes),
                    max(b[3] for b in boxes),
                )
            )
            if boxes
            else None
        )
        if ctx.fmt == "image":
            return ImageRegionLocator(region=region_table, bbox=bbox or list(FULL_IMAGE))
        return PdfPageLocator(page=row_page, bbox=bbox)

    emit_table(
        ctx.draft,
        header=grid[0] if grid else [],
        rows=[(index, cells) for index, cells in enumerate(grid[1:], 2)],
        locator=table_locator,
        provenance=provenance,
        row_locator=row_locator,
        what=f"table on p. {page}",
    )


def _figure(element: Mapping[str, Any], page: int, ctx: _Context) -> None:
    bbox = ctx.bbox(element, page)
    image = ctx.page_images.get(page)
    if bbox is None or image is None:
        return
    area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
    if area < 0.001:
        return
    png = crop_png(image, bbox)
    if png is None:
        return
    caption_value = element.get("caption")
    caption = None
    if isinstance(caption_value, dict):
        caption = one_line(str(caption_value.get("content", ""))) or None
    locator = ctx.locator(page, bbox)
    ctx.draft.figure(locator, png, caption=caption, bbox=bbox)


def _markdown_fallback(content: Mapping[str, Any], ctx: _Context) -> None:
    """No layout details (``returnDetails`` off): paragraphs from the per-page markdown."""
    markdown = content.get("markdown")
    if not isinstance(markdown, str) or not markdown.strip():
        return
    ctx.draft.warn("cu-no-layout", "the result has no paragraphs; blocks come from the markdown")
    spans = sorted(ctx.page_spans) or [(1, 0, len(markdown))]
    for page, start, length in spans:
        if page > ctx.max_pages:
            continue
        text = re.sub(r"<!--.*?-->", "", markdown[start : start + length], flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        for chunk in re.split(r"\n\s*\n", text):
            cleaned = clean_text(re.sub(r"^#+\s*", "", chunk.strip()))
            if cleaned:
                locator = ctx.locator(page, None)
                ctx.draft.block("paragraph", cleaned, locator, ctx.provenance(page))


async def extract_with_cu(
    data: bytes, *, fmt: FormatFamily, settings: ExtractSettings, source_id: str
) -> Draft:
    """Azure adapter for one PDF or image (page renders and text-layer checks stay local)."""
    draft = Draft(
        adapter="content-understanding",
        adapter_version=CU_ADAPTER_VERSION,
        analyzer=settings.cu_analyzer,
    )
    content_range: str | None = None
    if fmt == "pdf":
        pages = await asyncio.to_thread(
            pdf_pages,
            data,
            max_pages=settings.max_pages,
            dpi=settings.page_render_dpi,
            draft=draft,
        )
        draft.page_count = pages.page_count
        draft.page_images = pages.images
        text_layer: dict[int, bool] = pages.text_layer
        if pages.page_count > settings.max_pages:
            content_range = f"1-{settings.max_pages}"
            draft.warn(
                "max-pages",
                f"analysed the first {settings.max_pages} of {pages.page_count} pages",
            )
    else:
        draft.page_images[1] = await asyncio.to_thread(load_page_image, data, draft)
        draft.page_count = 1
        text_layer = {1: False}
    response = await run_analysis(
        data, settings=settings, source_id=source_id, content_range=content_range
    )
    try:
        map_result(
            response, fmt=fmt, draft=draft, text_layer=text_layer, max_pages=settings.max_pages
        )
    except CuResultError as exc:
        raise ContentUnderstandingError(
            source_id, f"unexpected Content Understanding result: {exc}"
        ) from exc
    return draft
