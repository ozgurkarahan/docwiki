"""Authentication and authorization of MCP callers.

* HTTP with ``DOCWIKI_AUTH_MODE=easyauth``: Azure Container Apps built-in authentication validates
  the bearer token and forwards the caller as ``X-MS-CLIENT-PRINCIPAL`` (base64 JSON with a list of
  claims), next to the original ``Authorization`` header. :class:`PrincipalMiddleware` validates
  that bearer token on every request as well (:mod:`docwiki.mcp.tokens`) and takes the caller's
  object id and app roles from the validated token: a missing or invalid token is answered with
  HTTP 401, so a forged principal header never grants access even when the platform's
  authentication is missing. A principal header that is present must be well formed and never adds
  roles. With ``DOCWIKI_MCP_TOKEN_VALIDATION=off`` (explicit opt-out, logged as a warning) the
  header alone is trusted, as before: HTTP 401 when it is missing, ambiguous or malformed. The
  header is trusted **only** in ``easyauth`` mode.
* ``DOCWIKI_AUTH_MODE=none`` (stdio or loopback HTTP only): the caller gets read tools, plus
  operations tools when the server was started with ``--allow-ops``.

Each tool checks the caller's access level itself (:func:`tool_denial`, used by the server's
tool wrapper) and answers a missing role with a normal result ``{"ok": false, "error": {"code":
"forbidden", ...}}``: Foundry aborts the whole agent turn on any MCP error (ADR 0003, F3).
:class:`AuthorizationMiddleware` lists every tool to a caller that holds at least one DocWiki
role (none to a caller without), logs every call and turns any remaining ``isError`` result into
the same structured form. The list is not filtered per role: Agent Service caches the tool list
of a project connection across the agents that share it, so a Researcher's read-only list would
hide the Librarian's operations tools (each agent's ``allowed_tools`` scopes what its model sees).

Only a hash of the principal id is ever logged; tokens and claims are not.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
import time
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

import anyio.to_thread

from docwiki.contracts._base import sha256_hex
from docwiki.contracts.settings import SettingsKeys
from docwiki.mcp.bounds import dumps
from docwiki.mcp.config import Level, McpConfig
from docwiki.mcp.errors import failure_payload
from docwiki.mcp.tokens import SigningKeysUnavailableError, TokenError, TokenValidator

__all__ = [
    "AUTHORIZATION_HEADER",
    "PRINCIPAL_HEADER",
    "PRINCIPAL_SCOPE_KEY",
    "AuthorizationMiddleware",
    "Principal",
    "PrincipalError",
    "PrincipalMiddleware",
    "decode_client_principal",
    "principal_from_claims",
    "principal_from_context",
    "principal_from_tool_context",
    "token_validator_for",
    "tool_denial",
]

logger = logging.getLogger("docwiki.mcp.auth")

PRINCIPAL_HEADER = "x-ms-client-principal"
PRINCIPAL_ID_HEADER = "x-ms-client-principal-id"
AUTHORIZATION_HEADER = "authorization"
PRINCIPAL_SCOPE_KEY = "docwiki.principal"
"""ASGI scope key under which :class:`PrincipalMiddleware` stores the decoded caller."""

MAX_HEADER_CHARS = 32768
TOKEN_ROLE_CLAIM = "roles"
"""App-role claim of Entra access tokens, always honoured next to ``DOCWIKI_ROLE_CLAIM``."""
UNAUTHORIZED_MESSAGE = "authentication required"
_ID_CLAIMS = (
    "http://schemas.microsoft.com/identity/claims/objectidentifier",
    "oid",
    "sub",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier",
    "appid",
    "azp",
)
"""Claims identifying the caller, best first (the ``oid`` of an agent identity in practice)."""


class PrincipalError(ValueError):
    """The ``X-MS-CLIENT-PRINCIPAL`` header is missing or malformed."""


@dataclass(frozen=True)
class Principal:
    """An authenticated (or local) caller: hashed id, app roles and granted access levels."""

    id_hash: str
    roles: frozenset[str]
    levels: frozenset[Level]
    source: str
    """``token`` for a validated bearer token, ``easyauth`` for a decoded principal header
    (token validation off), ``local`` for stdio / loopback without auth."""

    @classmethod
    def local(cls, config: McpConfig) -> Principal:
        return cls("local", frozenset(), config.local_levels, "local")

    @property
    def label(self) -> str:
        """Non-identifying label used in logs and in ``decided_by``."""
        return "local-operator" if self.source == "local" else f"principal:{self.id_hash}"

    def can(self, level: Level) -> bool:
        return level in self.levels


def _b64decode(value: str) -> bytes:
    text = "".join(value.split())
    padded = (text + "=" * (-len(text) % 4)).encode("ascii", errors="replace")
    try:
        return base64.b64decode(padded, validate=True)
    except (binascii.Error, ValueError):
        pass
    try:
        return base64.b64decode(padded, altchars=b"-_", validate=True)
    except (binascii.Error, ValueError) as exc:
        raise PrincipalError("principal header is not valid base64") from exc


def _role_values(value: str) -> list[str]:
    text = value.strip()
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return [text]
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    return [text] if text else []


def decode_client_principal(
    header: str,
    *,
    config: McpConfig,
    principal_id: str | None = None,
) -> Principal:
    """Decode an ``X-MS-CLIENT-PRINCIPAL`` header value into a :class:`Principal`.

    App roles are read from claims whose type is one of ``config.roles.claim_types`` (``roles``
    and the long-form role claim by default) or the principal's own ``role_typ``. A claim value
    holding a JSON array is expanded.
    """
    if not header or len(header) > MAX_HEADER_CHARS:
        raise PrincipalError("principal header is empty or too large")
    try:
        data = json.loads(_b64decode(header).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PrincipalError("principal header is not base64-encoded JSON") from exc
    if not isinstance(data, dict):
        raise PrincipalError("principal header must encode a JSON object")
    claims = data.get("claims")
    if not isinstance(claims, list):
        raise PrincipalError("principal header has no claims list")
    role_types = set(config.roles.claim_types)
    role_typ = data.get("role_typ")
    if isinstance(role_typ, str) and role_typ:
        role_types.add(role_typ)
    roles: set[str] = set()
    ids: dict[str, str] = {}
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        typ, val = claim.get("typ"), claim.get("val")
        if not isinstance(typ, str) or not isinstance(val, str):
            continue
        if typ in role_types:
            roles.update(_role_values(val))
        elif typ in _ID_CLAIMS and typ not in ids and val.strip():
            ids[typ] = val.strip()
    identity = next((ids[name] for name in _ID_CLAIMS if name in ids), None) or principal_id
    if not identity:
        raise PrincipalError("principal header carries no subject or object id")
    frozen = frozenset(roles)
    return Principal(
        id_hash=sha256_hex(identity.encode("utf-8"))[:16],
        roles=frozen,
        levels=config.roles.levels_for(frozen),
        source="easyauth",
    )


def principal_from_claims(claims: Mapping[str, Any], config: McpConfig) -> Principal:
    """The caller of a validated bearer token: its ``oid`` (else ``sub``) and its app roles.

    Roles come from the token's ``roles`` claim and from the claims named by
    ``config.roles.claim_types``; a string value holding a JSON array is expanded.
    """
    identity = claims.get("oid") or claims.get("sub")
    if not isinstance(identity, str) or not identity.strip():
        raise TokenError("bearer token without an object id")
    roles: set[str] = set()
    for name in dict.fromkeys((TOKEN_ROLE_CLAIM, *config.roles.claim_types)):
        value = claims.get(name)
        if isinstance(value, str):
            roles.update(_role_values(value))
        elif isinstance(value, list):
            roles.update(item.strip() for item in value if isinstance(item, str) and item.strip())
    frozen = frozenset(roles)
    return Principal(
        id_hash=sha256_hex(identity.strip().encode("utf-8"))[:16],
        roles=frozen,
        levels=config.roles.levels_for(frozen),
        source="token",
    )


def token_validator_for(
    config: McpConfig, validator: TokenValidator | None = None
) -> TokenValidator | None:
    """The bearer-token validator an HTTP app with ``config`` needs (None when it needs none).

    Raises ``ValueError`` in ``easyauth`` mode when the token settings are incomplete (the server
    refuses to start); logs a warning when validation is switched off.
    """
    if config.auth_mode != "easyauth":
        return None
    if not config.validates_tokens:
        logger.warning(
            "%s=off: the %s header is trusted without validating the bearer token; run this "
            "server only behind Container Apps built-in authentication",
            SettingsKeys.MCP_TOKEN_VALIDATION,
            PRINCIPAL_HEADER,
        )
        return None
    problem = config.token_settings_problem()
    if problem:
        raise ValueError(problem)
    return validator or TokenValidator.from_config(config)


def _headers(scope: Mapping[str, Any], name: bytes) -> list[str]:
    return [
        value.decode("latin-1") for key, value in scope.get("headers") or () if key.lower() == name
    ]


def _bearer_token(values: list[str]) -> str | None:
    """The token of exactly one ``Authorization: Bearer <token>`` header, else None."""
    if len(values) != 1:
        return None
    scheme, _, token = values[0].strip().partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token or any(char.isspace() for char in token):
        return None
    return token


class PrincipalMiddleware:
    """ASGI middleware: attach the caller to the scope, or answer 401 in ``easyauth`` mode.

    With a ``validator`` (required unless ``DOCWIKI_MCP_TOKEN_VALIDATION=off``) the caller comes
    from the validated bearer token; without one, from the principal header alone.
    """

    def __init__(
        self,
        app: Any,
        *,
        config: McpConfig,
        validator: TokenValidator | None = None,
        exempt_paths: Iterable[str] = ("/healthz", "/healthz/"),
    ) -> None:
        if config.validates_tokens and validator is None:
            raise ValueError(
                config.token_settings_problem() or "easyauth mode needs a bearer-token validator"
            )
        self.app = app
        self.config = config
        self.validator = validator if config.validates_tokens else None
        self.exempt = frozenset(exempt_paths)

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        kind = scope.get("type")
        if kind == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        if kind != "http" or scope.get("path") in self.exempt:
            await self.app(scope, receive, send)
            return
        scope.pop(PRINCIPAL_SCOPE_KEY, None)
        if self.config.auth_mode == "easyauth":
            if self.validator is not None:
                principal = await self._from_token(scope, send, self.validator)
            else:
                principal = await self._from_header(scope, send)
            if principal is None:
                return
        else:
            principal = Principal.local(self.config)
        scope[PRINCIPAL_SCOPE_KEY] = principal
        await self.app(scope, receive, send)

    def _decode_header(self, scope: Mapping[str, Any], header: str) -> Principal:
        ids = _headers(scope, PRINCIPAL_ID_HEADER.encode("ascii"))
        return decode_client_principal(
            header, config=self.config, principal_id=ids[0] if ids else None
        )

    async def _from_header(self, scope: Mapping[str, Any], send: Any) -> Principal | None:
        """Token validation off: the platform's principal header is the caller."""
        headers = _headers(scope, PRINCIPAL_HEADER.encode("ascii"))
        if len(headers) != 1:
            logger.warning("rejected request with %d %s headers", len(headers), PRINCIPAL_HEADER)
            await _unauthorized(send, UNAUTHORIZED_MESSAGE)
            return None
        try:
            return self._decode_header(scope, headers[0])
        except PrincipalError as exc:
            logger.warning("rejected request with an invalid principal header: %s", exc)
            await _unauthorized(send, "invalid principal")
            return None

    async def _from_token(
        self, scope: Mapping[str, Any], send: Any, validator: TokenValidator
    ) -> Principal | None:
        """The caller of a valid bearer token; a principal header never adds roles to it."""
        headers = _headers(scope, PRINCIPAL_HEADER.encode("ascii"))
        token = _bearer_token(_headers(scope, AUTHORIZATION_HEADER.encode("ascii")))
        if token is None:
            logger.warning(
                "rejected request without a valid bearer token header%s",
                f" but with a {PRINCIPAL_HEADER} header (forged, or the platform did not forward "
                "the Authorization header)"
                if headers
                else "",
            )
            await _unauthorized(send, UNAUTHORIZED_MESSAGE)
            return None
        if len(headers) > 1:
            logger.warning("rejected request with %d %s headers", len(headers), PRINCIPAL_HEADER)
            await _unauthorized(send, UNAUTHORIZED_MESSAGE)
            return None
        try:
            claims = await anyio.to_thread.run_sync(validator.validate, token)
            principal = principal_from_claims(claims, self.config)
        except TokenError as exc:
            logger.warning("rejected request: %s", exc)
            await _unauthorized(send, UNAUTHORIZED_MESSAGE)
            return None
        except SigningKeysUnavailableError as exc:
            logger.error("rejected request: %s", exc)
            await _unavailable(send)
            return None
        if headers:
            try:
                forwarded = self._decode_header(scope, headers[0])
            except PrincipalError as exc:
                logger.warning("rejected request with an invalid principal header: %s", exc)
                await _unauthorized(send, UNAUTHORIZED_MESSAGE)
                return None
            if forwarded.id_hash != principal.id_hash:
                logger.warning(
                    "%s names another caller than the bearer token: header ignored (%s)",
                    PRINCIPAL_HEADER,
                    principal.label,
                )
            extra = forwarded.roles - principal.roles
            if extra:
                logger.warning(
                    "%s claims %d app role(s) the bearer token does not grant: ignored (%s)",
                    PRINCIPAL_HEADER,
                    len(extra),
                    principal.label,
                )
        return principal


async def _respond(send: Any, status: int, payload: Mapping[str, str], *extra: Any) -> None:
    body = json.dumps(payload).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
                *extra,
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


async def _unauthorized(send: Any, message: str) -> None:
    await _respond(
        send,
        401,
        {"error": "unauthorized", "message": message},
        (b"www-authenticate", b"Bearer"),
    )


async def _unavailable(send: Any) -> None:
    await _respond(
        send,
        503,
        {"error": "unavailable", "message": "authentication is temporarily unavailable"},
    )


def principal_from_context(ctx: Any, config: McpConfig) -> Principal | None:
    """The caller of an MCP message: from the HTTP scope, or local for stdio in mode ``none``.

    Returns ``None`` (deny everything) when an HTTP request carries no principal or when the
    server runs in ``easyauth`` mode without an HTTP request.
    """
    request = getattr(ctx, "request", None)
    if request is not None:
        scope = getattr(request, "scope", None)
        found = scope.get(PRINCIPAL_SCOPE_KEY) if isinstance(scope, dict) else None
        return found if isinstance(found, Principal) else None
    if config.auth_mode == "none":
        return Principal.local(config)
    return None


def principal_from_tool_context(context: Any, config: McpConfig) -> Principal | None:
    """Caller of a tool call from the ``Context`` the MCP SDK injects into tools."""
    try:
        request_context = context.request_context if context is not None else None
    except ValueError:
        request_context = None
    if request_context is None:
        return Principal.local(config) if config.auth_mode == "none" else None
    return principal_from_context(request_context, config)


def tool_denial(
    principal: Principal | None, level: Level, config: McpConfig
) -> tuple[str, dict[str, Any]] | None:
    """``(message, details)`` when ``principal`` may not call a tool of ``level``, else None."""
    if principal is None:
        return (
            "no authenticated caller: this server only answers callers authenticated by the "
            "platform",
            {"required_role": config.roles.role_names(level)},
        )
    if principal.can(level):
        return None
    role = config.roles.role_names(level)
    return (
        f"this agent lacks the app role {role} required by this tool; do not retry, use "
        "another tool or report that the action is not permitted",
        {"required_role": role},
    )


def _failure_code(result: Mapping[str, Any]) -> str | None:
    """Error code of a structured failure result (``None`` for a success)."""
    for block in result.get("content") or ():
        text = block.get("text") if isinstance(block, Mapping) else None
        if isinstance(text, str) and text.startswith('{"ok":false'):
            try:
                error = json.loads(text).get("error") or {}
            except (json.JSONDecodeError, AttributeError):
                return "internal"
            return str(error.get("code") or "internal")
    return None


def _result_chars(result: Mapping[str, Any]) -> int:
    return sum(
        len(block["text"])
        for block in result.get("content") or ()
        if isinstance(block, Mapping) and isinstance(block.get("text"), str)
    )


def _annotate_span(**attributes: Any) -> None:
    try:
        from opentelemetry import trace
    except ImportError:  # pragma: no cover - opentelemetry ships with the MCP SDK
        return
    span = trace.get_current_span()
    for key, value in attributes.items():
        span.set_attribute(f"docwiki.{key}", value)


class AuthorizationMiddleware:
    """MCP server middleware: list the tools, log tool calls, never surface tool errors.

    Role enforcement happens in each tool (before argument validation), so a denied call comes
    back as a normal ``forbidden`` result. ``tools/list`` shows every DocWiki tool to a caller
    holding any DocWiki role: Agent Service caches a project connection's tool list across the
    agents sharing it (both agents use one connection, ADR 0003), and a list filtered by the
    Researcher's roles hid the Librarian's operations tools for minutes. Any ``isError`` result
    that still reaches this middleware (for example a call to an unknown tool) is rewritten into
    the structured ``{"ok": false, ...}`` form, because Foundry aborts the agent turn on tool
    errors.
    """

    def __init__(self, config: McpConfig, tool_levels: Mapping[str, Level]) -> None:
        self.config = config
        self.tool_levels = dict(tool_levels)

    async def __call__(self, ctx: Any, call_next: Callable[[Any], Awaitable[Any]]) -> Any:
        method = getattr(ctx, "method", "")
        if method == "tools/list":
            return self._visible(ctx, await call_next(ctx))
        if method != "tools/call":
            return await call_next(ctx)
        principal = principal_from_context(ctx, self.config)
        label = principal.label if principal else "anonymous"
        params = getattr(ctx, "params", None) or {}
        raw_name = params.get("name") if isinstance(params, Mapping) else None
        name = str(raw_name)[:64]
        level = self.tool_levels.get(name)
        _annotate_span(principal=label, access_level=level or "unknown")
        started = time.perf_counter()
        try:
            result = await call_next(ctx)
        except Exception as exc:
            logger.warning(
                "tool=%r outcome=protocol-error principal=%s level=%s ms=%d error=%s",
                name,
                label,
                level,
                (time.perf_counter() - started) * 1000,
                type(exc).__name__,
            )
            raise
        if isinstance(result, Mapping) and result.get("isError"):
            result = self._structured(name, result)
        code = _failure_code(result) if isinstance(result, Mapping) else None
        chars = _result_chars(result) if isinstance(result, Mapping) else 0
        _annotate_span(result_chars=chars, outcome=code or "ok")
        log = logger.warning if code == "forbidden" else logger.info
        log(
            "tool=%r outcome=%s principal=%s level=%s ms=%d chars=%d",
            name,
            code or "ok",
            label,
            level,
            (time.perf_counter() - started) * 1000,
            chars,
        )
        return result

    def _visible(self, ctx: Any, result: Any) -> Any:
        """Every DocWiki tool for a caller with any DocWiki role; none without (or anonymous)."""
        principal = principal_from_context(ctx, self.config)
        levels = principal.levels if principal else frozenset()
        if isinstance(result, Mapping) and isinstance(result.get("tools"), list):
            visible = [
                tool
                for tool in result["tools"]
                if levels
                and isinstance(tool, Mapping)
                and str(tool.get("name")) in self.tool_levels
            ]
            result = {**result, "tools": visible}
        return result

    @staticmethod
    def _structured(name: str, result: Mapping[str, Any]) -> dict[str, Any]:
        text = " ".join(
            block["text"]
            for block in result.get("content") or ()
            if isinstance(block, Mapping) and isinstance(block.get("text"), str)
        )
        if text.startswith("Unknown tool"):
            payload = failure_payload(
                "not_found",
                f"unknown tool {name!r}; call tools/list for the available tools",
                tool=name,
            )
        else:
            payload = failure_payload(
                "internal", "the tool failed unexpectedly; the server logged the details", tool=name
            )
        return {**result, "content": [{"type": "text", "text": dumps(payload)}], "isError": False}
