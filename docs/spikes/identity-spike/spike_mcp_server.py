"""Reference MCP server from the identity spike (ADR 0003). Not production code.

Two tools behind Azure Container Apps built-in authentication (Easy Auth):

- ``whoami`` returns the caller identity decoded from the ``X-MS-CLIENT-PRINCIPAL`` header.
- ``operate`` succeeds only when the caller holds the ``Wiki.Operate`` app role.

The header is trusted only when ``DOCWIKI_AUTH_MODE=easyauth``: Easy Auth validates the bearer
token, drops any client-supplied ``X-MS-*`` headers and injects its own principal header.

Run locally (no Easy Auth, every call is anonymous): ``python spike_mcp_server.py``.
Requires ``mcp>=2.3`` (``MCPServer`` API) and ``uvicorn``.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import logging
import os
import time
from typing import Any

import uvicorn
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.shared.exceptions import MCPError
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

AUTH_MODE = os.environ.get("DOCWIKI_AUTH_MODE", "easyauth")
# tool-error: isError result; jsonrpc: protocol error. Foundry aborts the agent turn on both.
FORBIDDEN_STYLE = os.environ.get("SPIKE_FORBIDDEN_STYLE", "tool-error")
FORBIDDEN_CODE = -32003
ROLE_READ = "Wiki.Read"
ROLE_OPERATE = "Wiki.Operate"

# Easy Auth maps some JWT claims to long claim-type URIs; normalise them.
CLAIM_ALIASES = {
    "http://schemas.microsoft.com/identity/claims/objectidentifier": "oid",
    "http://schemas.microsoft.com/identity/claims/tenantid": "tid",
    "http://schemas.microsoft.com/identity/claims/scope": "scp",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier": "sub",
    "http://schemas.microsoft.com/ws/2008/06/identity/claims/role": "roles",
}

STARTED_AT = time.time()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("spike")

mcp = MCPServer(
    name="docwiki-identity-spike",
    instructions="Identity spike: call whoami to see the caller, operate to test Wiki.Operate.",
)


class Principal:
    def __init__(
        self, auth_typ: str | None, claims: dict[str, list[str]], raw: dict[str, Any]
    ) -> None:
        self.auth_typ = auth_typ
        self.claims = claims
        self.raw_claim_types = sorted({c.get("typ", "") for c in raw.get("claims", [])})
        self.name_typ = raw.get("name_typ")
        self.role_typ = raw.get("role_typ")

    def one(self, name: str) -> str | None:
        values = self.claims.get(name)
        return values[0] if values else None

    @property
    def roles(self) -> list[str]:
        return sorted(set(self.claims.get("roles", [])))

    @property
    def principal_type(self) -> str:
        idtyp = self.one("idtyp")
        if idtyp:
            return idtyp
        return "user" if self.one("scp") else "app"

    def id_hash(self) -> str:
        return hashlib.sha256((self.one("oid") or "").encode("utf-8")).hexdigest()[:12]


def decode_principal(headers: Any) -> Principal | None:
    if AUTH_MODE != "easyauth" or headers is None:
        return None
    raw = headers.get("x-ms-client-principal")
    if not raw:
        return None
    try:
        data = json.loads(base64.b64decode(raw))
    except (binascii.Error, ValueError):
        return None
    claims: dict[str, list[str]] = {}
    for claim in data.get("claims", []):
        typ = CLAIM_ALIASES.get(claim.get("typ", ""), claim.get("typ", ""))
        claims.setdefault(typ, []).append(str(claim.get("val", "")))
    return Principal(data.get("auth_typ"), claims, data)


def forbidden() -> Exception:
    if FORBIDDEN_STYLE == "jsonrpc":
        return MCPError(code=FORBIDDEN_CODE, message="forbidden")
    return ToolError("forbidden: the caller lacks the required app role")


def require(ctx: Context, role: str, tool: str) -> Principal:
    principal = decode_principal(ctx.headers)
    if principal is None:
        log.warning("tool=%s denied reason=no-principal", tool)
        raise forbidden()
    if role not in principal.roles:
        log.warning(
            "tool=%s denied principal=%s roles=%s", tool, principal.id_hash(), principal.roles
        )
        raise forbidden()
    log.info("tool=%s allowed principal=%s roles=%s", tool, principal.id_hash(), principal.roles)
    return principal


@mcp.tool(description="Return the identity of the caller as seen by the MCP server.")
def whoami(ctx: Context) -> dict[str, Any]:
    principal = decode_principal(ctx.headers)
    if principal is None:
        log.warning("tool=whoami no-principal")
        return {"authenticated": False}
    log.info("tool=whoami principal=%s roles=%s", principal.id_hash(), principal.roles)
    return {
        "authenticated": True,
        "auth_typ": principal.auth_typ,
        "principal_type": principal.principal_type,
        "object_id": principal.one("oid"),
        "app_id": principal.one("azp") or principal.one("appid"),
        "roles": principal.roles,
        "audience": principal.one("aud"),
        "issuer": principal.one("iss"),
        "token_version": principal.one("ver"),
        "tenant_id": principal.one("tid"),
        "claim_types": sorted(principal.claims),
        "raw_claim_types": principal.raw_claim_types,
        "name_typ": principal.name_typ,
        "role_typ": principal.role_typ,
        "server_uptime_s": round(time.time() - STARTED_AT, 1),
    }


@mcp.tool(description="Operations probe: succeeds only for callers with the Wiki.Operate role.")
def operate(ctx: Context) -> dict[str, Any]:
    principal = require(ctx, ROLE_OPERATE, "operate")
    return {"result": "ok", "roles": principal.roles}


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> Response:
    return JSONResponse({"status": "ok", "uptime_s": round(time.time() - STARTED_AT, 1)})


app = mcp.streamable_http_app(stateless_http=True, json_response=True, host="0.0.0.0")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), proxy_headers=True)
