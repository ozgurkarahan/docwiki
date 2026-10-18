"""Principal decoding, role mapping and configuration of authorization."""

from __future__ import annotations

import base64
import json

import pytest
from mcp_testkit import principal_header

from docwiki.contracts._base import sha256_hex
from docwiki.mcp.auth import Principal, PrincipalError, decode_client_principal
from docwiki.mcp.config import LONG_ROLE_CLAIM, McpConfig, is_loopback


def test_roles_from_short_and_long_form_claims() -> None:
    config = McpConfig(auth_mode="easyauth")
    reader = decode_client_principal(
        principal_header("Wiki.Read", claim_type="roles", role_typ=None), config=config
    )
    assert reader.roles == {"Wiki.Read"} and reader.levels == {"read"}
    assert reader.source == "easyauth" and len(reader.id_hash) == 16
    assert "researcher-agent" not in reader.label
    librarian = decode_client_principal(
        principal_header("Wiki.Read", "Wiki.Operate", claim_type=LONG_ROLE_CLAIM, subject="lib"),
        config=config,
    )
    assert librarian.levels == {"read", "operate"}
    assert librarian.id_hash != reader.id_hash


def test_default_role_claim_setting_accepts_the_long_role_uri() -> None:
    """With DOCWIKI_ROLE_CLAIM unset, the default (``roles`` plus the long role URI) applies, so
    long-form role claims count even when the payload carries no ``role_typ``."""
    config = McpConfig.from_env({"DOCWIKI_AUTH_MODE": "easyauth"})
    assert config.roles.claim_types == ("roles", LONG_ROLE_CLAIM)
    bare = principal_header("Wiki.Read", "Wiki.Operate", role_typ=None)
    assert decode_client_principal(bare, config=config).levels == {"read", "operate"}


def test_principal_shaped_like_the_identity_spike() -> None:
    """``auth_typ`` Bearer, object id in the long ``objectidentifier`` claim, one long-form role
    claim per role and ``role_typ`` naming it (docs/spikes/identity-spike.md section 4.7)."""
    config = McpConfig.from_env({"DOCWIKI_AUTH_MODE": "easyauth"})
    payload = json.loads(base64.b64decode(principal_header("Wiki.Read", subject="agent-oid-1")))
    assert payload["auth_typ"] == "Bearer" and payload["role_typ"] == LONG_ROLE_CLAIM
    researcher = decode_client_principal(
        principal_header("Wiki.Read", subject="agent-oid-1"), config=config
    )
    librarian = decode_client_principal(
        principal_header("Wiki.Operate", "Wiki.Read", subject="agent-oid-2"), config=config
    )
    assert researcher.levels == {"read"} and librarian.levels == {"read", "operate"}
    assert researcher.id_hash == sha256_hex(b"agent-oid-1")[:16], "hash of the object id"
    assert researcher.id_hash != librarian.id_hash


def test_role_claim_setting_is_a_comma_separated_list() -> None:
    config = McpConfig.from_env({"DOCWIKI_ROLE_CLAIM": " app_roles , extra_roles ,"})
    assert config.roles.claim_types == ("app_roles", "extra_roles")
    extra = principal_header("Wiki.Read", claim_type="extra_roles", role_typ=None)
    assert decode_client_principal(extra, config=config).levels == {"read"}
    long_form = principal_header("Wiki.Read", role_typ=None)
    assert decode_client_principal(long_form, config=config).levels == frozenset()
    named = principal_header("Wiki.Read")
    assert decode_client_principal(named, config=config).levels == {"read"}, (
        "the payload's role_typ is always honoured"
    )


def test_role_claim_type_from_principal_and_json_arrays() -> None:
    config = McpConfig(auth_mode="easyauth")
    custom = principal_header("Wiki.Operate", claim_type="app_roles", role_typ="app_roles")
    assert decode_client_principal(custom, config=config).levels == {"operate"}
    claims = [
        {"typ": "sub", "val": "agent-2"},
        {"typ": "roles", "val": json.dumps(["Wiki.Read", "Wiki.Operate"])},
    ]
    raw = base64.b64encode(json.dumps({"claims": claims}).encode()).decode().rstrip("=")
    assert decode_client_principal(raw, config=config).levels == {"read", "operate"}
    unknown = decode_client_principal(principal_header("Other.Role"), config=config)
    assert unknown.levels == frozenset()


def test_configurable_role_mapping_from_environment() -> None:
    config = McpConfig.from_env(
        {
            "DOCWIKI_AUTH_MODE": "easyauth",
            "DOCWIKI_ROLE_CLAIM": "app_roles",
            "DOCWIKI_READ_ROLE": "Docs.Reader, Wiki.Operate",
            "DOCWIKI_OPERATE_ROLE": "Docs.Admin",
            "DOCWIKI_MCP_MAX_CHARS": "8000",
            "DOCWIKI_MCP_POINTER_TTL_SECONDS": "5",
        }
    )
    assert config.roles.claim_types[0] == "app_roles"
    assert config.max_chars == 8000 and config.pointer_ttl_s == 5
    header = principal_header("Wiki.Operate", claim_type="app_roles", role_typ="other")
    assert decode_client_principal(header, config=config).levels == {"read"}
    admin = decode_client_principal(principal_header("Docs.Admin"), config=config)
    assert admin.levels == {"operate"}
    assert config.roles.role_names("read") == "Docs.Reader or Wiki.Operate"


@pytest.mark.parametrize(
    "header",
    [
        "%%% not base64 %%%",
        base64.b64encode(b"not json").decode(),
        base64.b64encode(b"[1, 2]").decode(),
        base64.b64encode(json.dumps({"claims": "x"}).encode()).decode(),
        base64.b64encode(
            json.dumps({"claims": [{"typ": "roles", "val": "Wiki.Read"}]}).encode()
        ).decode(),
        "",
    ],
)
def test_malformed_principals_are_rejected(header: str) -> None:
    with pytest.raises(PrincipalError):
        decode_client_principal(header, config=McpConfig(auth_mode="easyauth"))


def test_principal_id_header_is_a_fallback_identity() -> None:
    claims = [{"typ": "roles", "val": "Wiki.Read"}]
    raw = base64.b64encode(json.dumps({"claims": claims}).encode()).decode()
    principal = decode_client_principal(
        raw, config=McpConfig(auth_mode="easyauth"), principal_id="fallback-id"
    )
    assert principal.levels == {"read"}


def test_local_principal_levels() -> None:
    assert Principal.local(McpConfig()).levels == {"read"}
    assert Principal.local(McpConfig(allow_ops=True)).levels == {"read", "operate"}
    assert Principal.local(McpConfig()).label == "local-operator"


def test_config_validation() -> None:
    with pytest.raises(ValueError, match="DOCWIKI_AUTH_MODE"):
        McpConfig.from_env({"DOCWIKI_AUTH_MODE": "anonymous"})
    with pytest.raises(ValueError, match="DOCWIKI_MODE"):
        McpConfig.from_env({"DOCWIKI_MODE": "cloud"})
    with pytest.raises(ValueError, match="must be a number"):
        McpConfig.from_env({"DOCWIKI_MCP_MAX_CHARS": "lots"})
    with pytest.raises(ValueError, match="QUERY_TABLE_MAX_ROWS"):
        McpConfig(query_max_rows=500)
    defaults = McpConfig.from_env({})
    assert defaults.auth_mode == "none" and defaults.max_chars == 12000
    assert defaults.roles.read_roles == {"Wiki.Read"}


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("127.0.0.1", True),
        ("127.1.2.3", True),
        ("localhost", True),
        ("::1", True),
        ("[::1]", True),
        ("0.0.0.0", False),
        ("10.0.0.4", False),
        ("example.org", False),
    ],
)
def test_is_loopback(host: str, expected: bool) -> None:
    assert is_loopback(host) is expected
