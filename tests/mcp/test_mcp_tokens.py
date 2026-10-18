"""Bearer-token validation in easyauth mode: signature, issuer, audience, lifetime, caller
allowlist, signing-key rotation, settings and the server's refusal to start without them.

Tokens are signed with locally generated RSA keys and validated against an in-memory key set
(no network)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import jwt
import pytest
from mcp_testkit import (
    API_CLIENT_ID,
    AUDIENCES,
    FIXTURE_ROOT,
    ISSUER,
    TENANT_ID,
    TokenMint,
    principal_header,
    signing_key,
    unsigned_token,
)
from starlette.testclient import TestClient

from docwiki.contracts._base import sha256_hex
from docwiki.contracts.settings import SETTINGS_DEFAULTS, SettingsKeys
from docwiki.mcp import READ_TOOLS
from docwiki.mcp.auth import principal_from_claims, token_validator_for
from docwiki.mcp.config import LONG_ROLE_CLAIM, McpConfig, RoleConfig
from docwiki.mcp.server import create_app
from docwiki.mcp.tokens import (
    SigningKeys,
    SigningKeysUnavailableError,
    TokenError,
    TokenValidator,
    issuer_for,
    jwks_url_for,
)

HEADERS = {
    "accept": "application/json, text/event-stream",
    "content-type": "application/json",
    "mcp-protocol-version": "2025-11-25",
}


class Clock:
    """Monotonic clock moved by hand."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def mint() -> TokenMint:
    return TokenMint()


def validator(mint: TokenMint, **overrides: Any) -> TokenValidator:
    return mint.validator(mint.config(**overrides))


def rejected(check: TokenValidator, token: str) -> str:
    with pytest.raises(TokenError) as raised:
        check.validate(token)
    return str(raised.value)


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


def test_valid_token_yields_the_caller_and_roles_from_the_token(mint: TokenMint) -> None:
    config = mint.config()
    claims = mint.validator(config).validate(
        mint.token("Wiki.Read", "Wiki.Operate", subject="librarian-oid")
    )
    assert claims["oid"] == "librarian-oid" and claims["iss"] == ISSUER
    principal = principal_from_claims(claims, config)
    assert principal.roles == {"Wiki.Read", "Wiki.Operate"}
    assert principal.levels == {"read", "operate"}
    assert principal.source == "token"
    assert principal.id_hash == sha256_hex(b"librarian-oid")[:16], "same hash as the header path"


def test_both_audience_forms_are_accepted(mint: TokenMint) -> None:
    check = validator(mint)
    for audience in AUDIENCES:
        assert check.validate(mint.token("Wiki.Read", audience=audience))["aud"] == audience


@pytest.mark.parametrize(
    ("options", "reason"),
    [
        ({"audience": "api://another-api.example"}, "another audience"),
        ({"issuer": issuer_for("other-tenant")}, "another issuer"),
        ({"issuer": f"https://sts.windows.net/{TENANT_ID}/"}, "another issuer"),
        ({"lifetime_s": -600}, "expired"),
        ({"issued_s": 600, "lifetime_s": 3600}, "not valid yet"),
        ({"exp": None}, "'exp' claim"),
        ({"nbf": None}, "'nbf' claim"),
        ({"tid": "another-tenant"}, "another tenant"),
        ({"oid": None, "sub": None}, "object id"),
    ],
)
def test_invalid_claims_are_rejected(mint: TokenMint, options: dict[str, Any], reason: str) -> None:
    assert reason in rejected(validator(mint), mint.token("Wiki.Read", **options))


def test_small_clock_skew_is_tolerated(mint: TokenMint) -> None:
    check = validator(mint)
    assert check.validate(mint.token("Wiki.Read", lifetime_s=-30))
    assert check.validate(mint.token("Wiki.Read", issued_s=30))


def test_signature_must_verify_with_a_tenant_key(mint: TokenMint) -> None:
    check = validator(mint)
    forged = mint.token("Wiki.Read", "Wiki.Operate", key=signing_key("attacker"))
    assert "signature does not verify" in rejected(check, forged)
    tampered = mint.token("Wiki.Read").split(".")
    other = mint.token("Wiki.Read", "Wiki.Operate").split(".")
    assert "signature" in rejected(check, ".".join([tampered[0], other[1], tampered[2]]))


@pytest.mark.parametrize("algorithm", ["none", "HS256", "RS512", "ES256"])
def test_only_rs256_is_accepted(mint: TokenMint, algorithm: str) -> None:
    claims = jwt.decode(mint.token("Wiki.Operate"), options={"verify_signature": False})
    token = unsigned_token({"alg": algorithm, "kid": mint.kid, "typ": "JWT"}, claims)
    assert "algorithm not allowed" in rejected(validator(mint), token)
    assert mint.jwks.fetches == 0, "an unacceptable header never reaches the key set"


@pytest.mark.parametrize("token", ["", "not-a-jwt", "a.b.c", "x" * 20000])
def test_malformed_tokens_are_rejected(mint: TokenMint, token: str) -> None:
    rejected(validator(mint), token)


def test_token_without_key_id_is_rejected(mint: TokenMint) -> None:
    token = jwt.encode(
        {"aud": API_CLIENT_ID, "iss": ISSUER, "exp": 4102444800, "nbf": 0, "oid": "x"},
        signing_key(),
        algorithm="RS256",
    )
    assert "names no signing key" in rejected(validator(mint), token)


def test_caller_allowlist_uses_azp_or_appid(mint: TokenMint) -> None:
    check = validator(mint, allowed_client_ids=("researcher-client", "librarian-client"))
    assert check.validate(mint.token("Wiki.Read", client="researcher-client"))
    assert "not allowed" in rejected(check, mint.token("Wiki.Read", client="other-client"))
    v1 = mint.token("Wiki.Read", azp=None, appid="librarian-client")
    assert check.validate(v1)["appid"] == "librarian-client", "v1 tokens carry appid"
    anonymous = mint.token("Wiki.Read", azp=None)
    assert "not allowed" in rejected(check, anonymous)
    assert validator(mint).validate(mint.token("Wiki.Read", client="any-client")), (
        "no allowlist configured: any caller with a valid token"
    )


def test_roles_come_from_token_role_claims(mint: TokenMint) -> None:
    config = mint.config()
    claims = mint.validator(config).validate(mint.token("Wiki.Operate"))
    assert principal_from_claims(claims, config).levels == {"operate"}
    custom = McpConfig(
        auth_mode="easyauth",
        tenant_id=TENANT_ID,
        audiences=AUDIENCES,
        roles=RoleConfig(claim_types=("app_roles",)),
    )
    extra = {"oid": "agent-oid", "roles": ["Wiki.Read"], "app_roles": '["Wiki.Operate"]'}
    assert principal_from_claims(extra, custom).levels == {"read", "operate"}, (
        "the standard roles claim is always honoured"
    )
    with pytest.raises(TokenError):
        principal_from_claims({"roles": ["Wiki.Read"]}, config)


# ---------------------------------------------------------------------------
# Signing keys: cache, rotation, outages
# ---------------------------------------------------------------------------


def test_signing_keys_are_cached_and_refreshed_after_their_lifetime(mint: TokenMint) -> None:
    clock = Clock()
    keys = SigningKeys(mint.jwks, clock=clock, ttl_s=3600)
    check = TokenValidator.from_config(mint.config(), keys=keys)
    for _ in range(3):
        check.validate(mint.token("Wiki.Read"))
    assert mint.jwks.fetches == 1, "one fetch serves many tokens"
    clock.now += 3601
    check.validate(mint.token("Wiki.Read"))
    assert mint.jwks.fetches == 2, "fetched again after the cache lifetime"


def test_key_rotation_fetches_the_new_key_once(mint: TokenMint) -> None:
    clock = Clock()
    keys = SigningKeys(mint.jwks, clock=clock, refresh_interval_s=60)
    check = TokenValidator.from_config(mint.config(), keys=keys)
    check.validate(mint.token("Wiki.Read"))
    clock.now += 120
    mint.jwks.keys["rotated-key"] = signing_key("rotated")
    rotated = mint.token("Wiki.Read", kid="rotated-key", key=signing_key("rotated"))
    assert check.validate(rotated)["oid"] == "researcher-agent"
    assert mint.jwks.fetches == 2, "an unknown key id triggers one fetch"
    check.validate(rotated)
    assert mint.jwks.fetches == 2


def test_unknown_key_ids_cannot_cause_a_fetch_storm(mint: TokenMint) -> None:
    clock = Clock()
    keys = SigningKeys(mint.jwks, clock=clock, refresh_interval_s=60)
    check = TokenValidator.from_config(mint.config(), keys=keys)
    check.validate(mint.token("Wiki.Read"))
    for index in range(20):
        token = mint.token("Wiki.Read", kid=f"made-up-{index}", key=signing_key("attacker"))
        assert "unknown key" in rejected(check, token)
    assert mint.jwks.fetches == 1, "refreshes are throttled"
    clock.now += 61
    assert "unknown key" in rejected(check, mint.token("Wiki.Read", kid="made-up-x"))
    assert mint.jwks.fetches == 2


def test_fetch_failures_keep_cached_keys_and_fail_closed_without_keys(
    mint: TokenMint, caplog: pytest.LogCaptureFixture
) -> None:
    clock = Clock()
    keys = SigningKeys(mint.jwks, clock=clock, ttl_s=3600, stale_s=7200)
    check = TokenValidator.from_config(mint.config(), keys=keys)
    mint.jwks.failure = jwt.PyJWKClientConnectionError("endpoint unreachable")
    with pytest.raises(SigningKeysUnavailableError):
        check.validate(mint.token("Wiki.Read"))
    mint.jwks.failure = None
    clock.now += 10
    check.validate(mint.token("Wiki.Read"))
    clock.now += 3700
    mint.jwks.failure = jwt.PyJWKClientConnectionError("endpoint unreachable")
    with caplog.at_level(logging.WARNING, logger="docwiki.mcp.auth"):
        assert check.validate(mint.token("Wiki.Read")), "stale keys still verify"
    assert "keeping the cached keys" in caplog.text
    clock.now += 7200
    with pytest.raises(SigningKeysUnavailableError):
        check.validate(mint.token("Wiki.Read"))


def test_default_key_source_is_the_tenant_v2_jwks() -> None:
    keys = SigningKeys.for_tenant(TENANT_ID)
    assert keys.client.uri == jwks_url_for(TENANT_ID)
    assert keys.client.uri == f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"
    check = TokenValidator(tenant_id=TENANT_ID.upper(), audiences=AUDIENCES)
    assert check.issuer == f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"
    with pytest.raises(ValueError):
        TokenValidator(tenant_id=TENANT_ID, audiences=())


# ---------------------------------------------------------------------------
# Settings and start-up
# ---------------------------------------------------------------------------


def test_token_settings_from_environment() -> None:
    config = McpConfig.from_env(
        {
            "DOCWIKI_AUTH_MODE": "easyauth",
            "DOCWIKI_MCP_TENANT_ID": TENANT_ID.upper(),
            "DOCWIKI_MCP_AUDIENCE": f" api://{API_CLIENT_ID} , {API_CLIENT_ID} ,",
            "DOCWIKI_MCP_ALLOWED_CLIENT_IDS": "researcher-client,librarian-client",
        }
    )
    assert config.tenant_id == TENANT_ID
    assert config.audiences == AUDIENCES
    assert config.allowed_client_ids == ("researcher-client", "librarian-client")
    assert config.token_validation == "required" and config.validates_tokens
    assert config.token_settings_problem() is None
    assert SETTINGS_DEFAULTS[SettingsKeys.MCP_TOKEN_VALIDATION] == "required"
    off = McpConfig.from_env(
        {"DOCWIKI_AUTH_MODE": "easyauth", "DOCWIKI_MCP_TOKEN_VALIDATION": "OFF"}
    )
    assert off.token_validation == "off" and not off.validates_tokens
    assert not McpConfig.from_env({}).validates_tokens, "mode none never validates tokens"
    with pytest.raises(ValueError, match="DOCWIKI_MCP_TOKEN_VALIDATION"):
        McpConfig.from_env({"DOCWIKI_MCP_TOKEN_VALIDATION": "maybe"})
    with pytest.raises(ValueError, match="DOCWIKI_MCP_TENANT_ID"):
        McpConfig.from_env({"DOCWIKI_MCP_TENANT_ID": "wiki.example"})


def test_easyauth_refuses_to_start_without_token_settings(tmp_path: Path) -> None:
    for config, missing in (
        (McpConfig(auth_mode="easyauth"), "DOCWIKI_MCP_TENANT_ID and DOCWIKI_MCP_AUDIENCE"),
        (McpConfig(auth_mode="easyauth", tenant_id=TENANT_ID), "DOCWIKI_MCP_AUDIENCE"),
        (McpConfig(auth_mode="easyauth", audiences=AUDIENCES), "DOCWIKI_MCP_TENANT_ID"),
    ):
        with pytest.raises(ValueError, match=missing):
            create_app(FIXTURE_ROOT, config=config, ops=None, bind_host="0.0.0.0")
    assert token_validator_for(McpConfig()) is None, "mode none needs no validator"


def test_token_validation_off_is_logged_as_a_warning(caplog: pytest.LogCaptureFixture) -> None:
    config = McpConfig(auth_mode="easyauth", token_validation="off")
    with caplog.at_level(logging.WARNING, logger="docwiki.mcp.auth"):
        assert token_validator_for(config) is None
    assert "DOCWIKI_MCP_TOKEN_VALIDATION=off" in caplog.text
    assert "x-ms-client-principal header is trusted without validating" in caplog.text


# ---------------------------------------------------------------------------
# HTTP app
# ---------------------------------------------------------------------------


def _list(client: TestClient, headers: dict[str, str]) -> Any:
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    return client.post("/mcp", json=body, headers={**HEADERS, **headers})


@pytest.mark.parametrize(
    "options",
    [
        {"audience": "api://another-api.example"},
        {"issuer": issuer_for("other-tenant")},
        {"lifetime_s": -600},
        {"client": "unknown-client"},
        {"key": "attacker"},
    ],
)
def test_http_answers_401_to_invalid_tokens(
    mint: TokenMint, options: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    config = mint.config(allowed_client_ids=("researcher-agent",))
    app = create_app(
        FIXTURE_ROOT,
        config=config,
        ops=None,
        bind_host="0.0.0.0",
        token_validator=mint.validator(config),
    )
    if options.get("key"):
        options = {**options, "key": signing_key(options["key"])}
    headers = mint.headers("Wiki.Read", "Wiki.Operate", **options)
    with TestClient(app) as client, caplog.at_level(logging.WARNING, "docwiki.mcp.auth"):
        response = _list(client, headers)
        assert response.status_code == 401
        assert response.json() == {"error": "unauthorized", "message": "authentication required"}
        assert response.headers["www-authenticate"] == "Bearer"
        assert _list(client, mint.headers("Wiki.Read")).status_code == 200
    token = headers["authorization"].split(" ", 1)[1]
    assert "rejected request: bearer token" in caplog.text
    assert token not in caplog.text and "researcher-agent" not in caplog.text


def test_http_answers_503_when_signing_keys_are_unavailable(mint: TokenMint) -> None:
    config = mint.config()
    app = create_app(
        FIXTURE_ROOT,
        config=config,
        ops=None,
        bind_host="0.0.0.0",
        token_validator=mint.validator(config),
    )
    mint.jwks.failure = jwt.PyJWKClientConnectionError("endpoint unreachable")
    with TestClient(app) as client:
        response = _list(client, mint.headers("Wiki.Read"))
        assert response.status_code == 503
        assert response.json()["error"] == "unavailable"
        assert client.get("/healthz").status_code == 200, "/healthz needs no token"


def test_http_token_roles_win_over_a_forged_header(mint: TokenMint) -> None:
    config = mint.config()
    app = create_app(
        FIXTURE_ROOT,
        config=config,
        ops=None,
        bind_host="0.0.0.0",
        token_validator=mint.validator(config),
    )
    headers = {
        "authorization": mint.headers("Wiki.Read")["authorization"],
        "x-ms-client-principal": principal_header(
            "Wiki.Read", "Wiki.Operate", claim_type=LONG_ROLE_CLAIM
        ),
    }
    with TestClient(app) as client:
        listed = _list(client, headers)
        assert listed.status_code == 200
        assert {tool["name"] for tool in listed.json()["result"]["tools"]} == set(READ_TOOLS)
