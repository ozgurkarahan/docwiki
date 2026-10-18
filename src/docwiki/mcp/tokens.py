"""Validation of the bearer token that Container Apps built-in authentication forwards.

In ``easyauth`` mode the platform validates the caller's access token and adds the
``X-MS-CLIENT-PRINCIPAL`` header. The server validates the original ``Authorization: Bearer``
token itself as well, so that a missing or disabled authentication sidecar cannot turn a forged
principal header into access (defense in depth):

* signature: RS256, with a key of the tenant's v2 signing keys (JWKS, fetched with PyJWT's
  :class:`jwt.PyJWKClient`, cached, fetched again when a token names an unknown key id, at most
  once a minute, and kept for a while when a fetch fails);
* issuer ``https://login.microsoftonline.com/<tenant>/v2.0`` (and ``tid``, when present);
* audience: one of ``DOCWIKI_MCP_AUDIENCE``;
* lifetime: ``exp`` and ``nbf`` with a small clock-skew leeway;
* caller: ``azp`` (v2 tokens) or ``appid`` (v1 tokens) in ``DOCWIKI_MCP_ALLOWED_CLIENT_IDS`` when
  that list is set;
* an object id (``oid``, else ``sub``) identifying the caller.

Failures raise :class:`TokenError` (HTTP 401). Their messages are written to the server log only
and never contain the token or its claims.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Iterable
from typing import Any

import jwt
from jwt import PyJWK, PyJWKClient

from docwiki.mcp.config import McpConfig

__all__ = [
    "ALGORITHMS",
    "AUTHORITY",
    "LEEWAY_S",
    "SigningKeys",
    "SigningKeysUnavailableError",
    "TokenError",
    "TokenValidator",
    "issuer_for",
    "jwks_url_for",
]

logger = logging.getLogger("docwiki.mcp.auth")

AUTHORITY = "https://login.microsoftonline.com"
ALGORITHMS = ("RS256",)
LEEWAY_S = 60
"""Clock skew tolerated on ``exp``, ``nbf`` and ``iat`` (seconds)."""
MAX_TOKEN_CHARS = 16384

KEYS_TTL_S = 3600.0
"""The signing keys are fetched again this long after the last successful fetch."""
REFRESH_INTERVAL_S = 60.0
"""Minimum interval between two fetches: unknown key ids cannot cause a fetch storm."""
RETRY_WITHOUT_KEYS_S = 5.0
"""Minimum interval between two fetch attempts while no key has been fetched yet."""
STALE_KEYS_S = 86400.0
"""How long cached keys stay usable after the last successful fetch while fetches fail."""
FETCH_TIMEOUT_S = 10.0


class TokenError(Exception):
    """The bearer token is not acceptable (HTTP 401; the message is only logged)."""


class SigningKeysUnavailableError(Exception):
    """No signing key of the tenant could be fetched (HTTP 503)."""


def issuer_for(tenant_id: str, authority: str = AUTHORITY) -> str:
    """Issuer of the tenant's v2 access tokens."""
    return f"{authority}/{tenant_id}/v2.0"


def jwks_url_for(tenant_id: str, authority: str = AUTHORITY) -> str:
    """The tenant's v2 signing keys (JSON Web Key Set)."""
    return f"{authority}/{tenant_id}/discovery/v2.0/keys"


class SigningKeys:
    """The tenant's token signing keys by key id, cached in memory.

    The keys are fetched with ``client`` (a :class:`jwt.PyJWKClient`) on first use, after
    ``ttl_s``, and when a token names an unknown key id (key rotation), but at most once per
    ``refresh_interval_s``. A failed fetch keeps the cached keys for up to ``stale_s``.
    """

    def __init__(
        self,
        client: PyJWKClient,
        *,
        ttl_s: float = KEYS_TTL_S,
        refresh_interval_s: float = REFRESH_INTERVAL_S,
        retry_without_keys_s: float = RETRY_WITHOUT_KEYS_S,
        stale_s: float = STALE_KEYS_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.client = client
        self.ttl_s = ttl_s
        self.refresh_interval_s = refresh_interval_s
        self.retry_without_keys_s = retry_without_keys_s
        self.stale_s = stale_s
        self._clock = clock
        self._lock = threading.Lock()
        self._keys: dict[str, PyJWK] = {}
        self._fetched_at: float | None = None
        self._attempted_at: float | None = None

    @classmethod
    def for_tenant(cls, tenant_id: str, **options: Any) -> SigningKeys:
        """Keys of the tenant's v2 JWKS endpoint (PyJWT's own caches off: this class caches)."""
        client = PyJWKClient(
            jwks_url_for(tenant_id),
            cache_keys=False,
            cache_jwk_set=False,
            timeout=FETCH_TIMEOUT_S,
        )
        return cls(client, **options)

    def get(self, kid: str) -> PyJWK:
        """The key named ``kid``: :class:`TokenError` when the tenant has no such key."""
        with self._lock:
            now = self._clock()
            fresh = self._fetched_at is not None and now - self._fetched_at < self.ttl_s
            if not fresh or kid not in self._keys:
                interval = self.refresh_interval_s if self._keys else self.retry_without_keys_s
                if self._attempted_at is None or now - self._attempted_at >= interval:
                    self._fetch(now)
            usable = self._fetched_at is not None and now - self._fetched_at <= self.stale_s
            if not usable or not self._keys:
                raise SigningKeysUnavailableError("the tenant's token signing keys are unavailable")
            key = self._keys.get(kid)
        if key is None:
            raise TokenError("bearer token signed with an unknown key")
        return key

    def _fetch(self, now: float) -> None:
        self._attempted_at = now
        try:
            keys = self.client.get_signing_keys(refresh=True)
        except (jwt.PyJWTError, OSError, ValueError) as exc:
            logger.warning(
                "could not fetch the token signing keys (%s)%s",
                type(exc).__name__,
                "; keeping the cached keys" if self._keys else "",
            )
            return
        self._keys = {key.key_id: key for key in keys if key.key_id}
        self._fetched_at = now


_REASONS: tuple[tuple[type[Exception], str], ...] = (
    (jwt.ExpiredSignatureError, "bearer token expired"),
    (jwt.ImmatureSignatureError, "bearer token not valid yet"),
    (jwt.InvalidAudienceError, "bearer token issued for another audience"),
    (jwt.InvalidIssuerError, "bearer token from another issuer"),
    (jwt.InvalidSignatureError, "bearer token signature does not verify"),
    (jwt.InvalidAlgorithmError, "bearer token algorithm not allowed"),
    (jwt.DecodeError, "malformed bearer token"),
)


def _reason(exc: jwt.PyJWTError) -> str:
    if isinstance(exc, jwt.MissingRequiredClaimError):
        return f"bearer token without the {exc.claim!r} claim"
    for kind, text in _REASONS:
        if isinstance(exc, kind):
            return text
    return f"invalid bearer token ({type(exc).__name__})"


class TokenValidator:
    """Validates access tokens for the MCP API issued by one Entra tenant (module docstring)."""

    def __init__(
        self,
        *,
        tenant_id: str,
        audiences: Iterable[str],
        allowed_client_ids: Iterable[str] = (),
        keys: SigningKeys | None = None,
        leeway_s: float = LEEWAY_S,
    ) -> None:
        self.tenant_id = tenant_id.strip().lower()
        self.audiences = tuple(audience for audience in audiences if audience)
        if not self.tenant_id or not self.audiences:
            raise ValueError("a tenant id and at least one audience are required")
        self.issuer = issuer_for(self.tenant_id)
        self.allowed_client_ids = frozenset(allowed_client_ids)
        self.keys = keys or SigningKeys.for_tenant(self.tenant_id)
        self.leeway_s = leeway_s

    @classmethod
    def from_config(cls, config: McpConfig, *, keys: SigningKeys | None = None) -> TokenValidator:
        """Validator for ``config`` (``ValueError`` when its token settings are incomplete)."""
        problem = config.token_settings_problem()
        if problem or not config.tenant_id:
            raise ValueError(problem or "token validation needs a tenant id")
        return cls(
            tenant_id=config.tenant_id,
            audiences=config.audiences,
            allowed_client_ids=config.allowed_client_ids,
            keys=keys,
        )

    def validate(self, token: str) -> dict[str, Any]:
        """Claims of a valid token. Raises :class:`TokenError` (HTTP 401) or
        :class:`SigningKeysUnavailableError` (HTTP 503); blocking (may fetch the keys)."""
        if not token or len(token) > MAX_TOKEN_CHARS:
            raise TokenError("bearer token is empty or too large")
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError:
            raise TokenError("malformed bearer token") from None
        if header.get("alg") not in ALGORITHMS:
            raise TokenError("bearer token algorithm not allowed")
        kid = header.get("kid")
        if not isinstance(kid, str) or not kid:
            raise TokenError("bearer token names no signing key")
        key = self.keys.get(kid)
        try:
            claims = jwt.decode(
                token,
                key.key,
                algorithms=list(ALGORITHMS),
                audience=list(self.audiences),
                issuer=self.issuer,
                leeway=self.leeway_s,
                options={"require": ["exp", "nbf", "iss", "aud"]},
            )
        except jwt.PyJWTError as exc:
            raise TokenError(_reason(exc)) from None
        tenant = claims.get("tid")
        if tenant is not None and str(tenant).lower() != self.tenant_id:
            raise TokenError("bearer token from another tenant")
        caller = claims.get("azp") or claims.get("appid")
        if self.allowed_client_ids and caller not in self.allowed_client_ids:
            raise TokenError("bearer token of a client application that is not allowed")
        subject = claims.get("oid") or claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise TokenError("bearer token without an object id")
        return claims
