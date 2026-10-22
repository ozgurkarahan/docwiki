#!/usr/bin/env python3
"""azd ``postprovision`` hook for DocWiki (idempotent; safe to re-run).

Implements the recipe of ADR 0003 (``docs/adr/0003-mcp-agent-identity.md``): each Foundry
agent calls the MCP server with its own Entra agent identity. Steps (``--only``/``--skip``
select them by name):

1. ``mcp-api``         MCP API app registration: identifier URI ``api://<appId>``, v2 access
                       tokens, app roles ``Wiki.Read`` and ``Wiki.Operate`` for applications;
                       service principal with app role assignment required.
2. ``mcp-auth``        Container Apps built-in auth on the ``mcp`` app (v2 issuer, audience
                       ``api://<appId>``, ``Return401``, ``/healthz`` excluded, token store off,
                       no client secret, ``allowedApplications`` from
                       ``DOCWIKI_MCP_ALLOWED_CLIENT_IDS``) via ``infra/modules/app-auth.bicep``;
                       then, in this order: verify it with ``az containerapp auth show``, set the
                       server's token settings (``DOCWIKI_MCP_TENANT_ID``,
                       ``DOCWIKI_MCP_AUDIENCE``, ``DOCWIKI_MCP_ALLOWED_CLIENT_IDS``,
                       ``DOCWIKI_MCP_TOKEN_VALIDATION``) and only then enable external ingress.
3. ``portal``          Only with ``DOCWIKI_ENABLE_PORTAL=true``: sign-in app registration (ID
                       tokens, no client secret), built-in auth with ``RedirectToLoginPage``.
                       With ``DOCWIKI_PORTAL_ACCESS=public`` (public-audience builds only) Bicep
                       gives the portal its ingress and every page stays anonymous; the owner's
                       sign-in (ADR 0009, unless ``DOCWIKI_PORTAL_OWNER_SIGN_IN=false``, deployer
                       must be a user): registration (assignment required, the deployer
                       assigned, redirect URIs of the default host and the custom domain), the
                       deployer's object ID as ``DOCWIKI_PORTAL_OWNERS`` unless already set,
                       built-in auth with ``AllowAnonymous`` (``/api/ask``, ``/healthz`` and
                       ``/livez`` excluded); then, in this order: verify it and only then give
                       the running container ``DOCWIKI_PORTAL_OWNERS``. The owner's upload
                       right on ``raw/`` follows on the next ``azd provision``.
4. ``studio``          Only with ``DOCWIKI_ENABLE_STUDIO=true`` and a deployer who is a user (the
                       Studio signs in its owner): sign-in app registration (ID tokens, no client
                       secret, assignment required, the deployer assigned), the deployer's object
                       ID as ``DOCWIKI_STUDIO_ALLOWED_PRINCIPALS`` unless already set, built-in
                       auth on the ``studio`` app (``RedirectToLoginPage``, ``/healthz`` and
                       ``/livez`` excluded); then, in this order: verify it with
                       ``az containerapp auth show``, give the running container
                       ``DOCWIKI_STUDIO_ALLOWED_PRINCIPALS`` (the app refuses everyone without
                       it) and only then enable external ingress.
5. ``mcp-connection``  Foundry project connection of the agents' MCP tool: ``RemoteTool``,
                       ``AgenticIdentityToken``, target ``DOCWIKI_MCP_URL``, audience
                       ``api://<appId>`` (ARM, same properties as
                       ``infra/modules/mcp-connection.bicep``).
6. ``agents``          ``agents/deploy.py --json`` (``--routine enable`` when
                       ``DOCWIKI_ENABLE_ROUTINE=true``); records each agent's identity.
7. ``agent-roles``     App roles for the agent identities: Researcher ``Wiki.Read``, Librarian
                       ``Wiki.Read`` + ``Wiki.Operate``.
8. ``mcp-allowlist``   Built-in auth ``allowedApplications`` = the agents' client IDs (except
                       ``DOCWIKI_MCP_BLOCKED_AGENTS``); an empty list means 403 for every agent.
                       Verified again, and the server's caller allowlist follows.
9. ``content-understanding``  Only with ``DOCWIKI_CU_DEFAULTS=true``: Content Understanding
                       model defaults.

``DOCWIKI_SKIP_AGENTS=true`` skips steps 5 and 6. Created Entra objects, agents and
assignments are recorded in ``.azure/<env>/docwiki-state.json`` (git-ignored), which
``scripts/teardown.py`` uses to delete them.

Microsoft Graph calls go through ``az rest``. When continuous access evaluation refuses the
Azure CLI's token, ``DOCWIKI_GRAPH_TOKEN_SOURCE=azd`` lets them use the azd sign-in instead, after
checking that it is the same account and tenant (``azdlib.Tools.rest``).
"""

from __future__ import annotations

import sys

if sys.version_info < (3, 12):  # noqa: UP036 - must run (and explain) on older interpreters
    major, minor = sys.version_info[:2]
    sys.stderr.write(f"[docwiki] ERROR: Python 3.12+ is required (found {major}.{minor}).\n")
    raise SystemExit(1)

import argparse
import json
import os
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

import entra
from azdlib import (
    ARM,
    COGNITIVE_SERVICES_RESOURCE,
    REPO_ROOT,
    CommandError,
    HookError,
    Runner,
    Tools,
    error,
    info,
    is_true,
    load_state,
    save_state,
    state_path,
    tools_from_environment,
    unique,
    utc_now,
    warn,
)

CONTAINER_APPS_API = "2025-01-01"
# AgenticIdentityToken connections are only accepted by preview API versions (ADR 0003).
CONNECTIONS_API = "2025-10-01-preview"
CONTENT_UNDERSTANDING_API = "2025-11-01"
ADR_0003 = "docs/adr/0003-mcp-agent-identity.md"
TOKEN_VALIDATION_MODES = ("required", "off")

DEFAULT_MCP_CONNECTION = "docwiki-mcp"
# Object IDs allowed into the Studio: read by the app (an empty list refuses everyone) and
# written to the azd environment (-> Bicep parameter studioAllowedPrincipals) by the studio step.
STUDIO_PRINCIPALS_SETTING = "DOCWIKI_STUDIO_ALLOWED_PRINCIPALS"
# The owners of the public portal (ADR 0009): read by the app (it accepts an owner call only from
# one of them) and written to the azd environment (-> Bicep parameter portalOwners).
PORTAL_OWNERS_SETTING = "DOCWIKI_PORTAL_OWNERS"
# Built-in auth refuses every browser POST that carries its session cookie: the public ask is
# excluded, the owner's routes use GET and PUT only.
PORTAL_OWNER_EXCLUDED_PATHS = ("/api/ask", "/healthz", "/livez")
CONNECTION_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,32}$")
# `auth.strategy` the agent definitions declare; agents/deploy.py checks the connection with it.
AGENT_AUTH_STRATEGY = "per-agent-identity"
AGENT_FILE = "agent.yaml"
_STRATEGY_LINE = re.compile(r"^\s*strategy:\s*([A-Za-z0-9_-]+)", re.MULTILINE)


@dataclass(frozen=True)
class AuthSpec:
    """Desired built-in auth configuration of one container app."""

    client_id: str
    audiences: tuple[str, ...]
    action: str
    excluded_paths: tuple[str, ...] = ()
    allowed_applications: tuple[str, ...] = ()


@dataclass
class Context:
    tools: Tools
    state: dict[str, Any]
    state_file: Path
    _principal: tuple[str, str] | None = field(default=None, repr=False)

    def save(self) -> None:
        save_state(self.state_file, self.state)

    def principal(self) -> tuple[str, str]:
        """Object ID and type of the signed-in deployer (cached)."""
        if self._principal is None:
            self._principal = self.tools.signed_in_object_id()
        return self._principal

    def names(self) -> tuple[str, str]:
        values = self.tools.require("AZURE_ENV_NAME", "DOCWIKI_RESOURCE_TOKEN")
        suffix = f"{values['AZURE_ENV_NAME']}-{values['DOCWIKI_RESOURCE_TOKEN']}"
        return suffix, f"docwiki-env:{suffix}"


# ---------------------------------------------------------------------------
# Built-in auth (shared by the mcp and portal apps)
# ---------------------------------------------------------------------------


def auth_config_url(tools: Tools, app_name: str) -> str:
    values = tools.require("AZURE_SUBSCRIPTION_ID", "AZURE_RESOURCE_GROUP")
    return (
        f"{ARM}/subscriptions/{values['AZURE_SUBSCRIPTION_ID']}/resourceGroups/"
        f"{values['AZURE_RESOURCE_GROUP']}/providers/Microsoft.App/containerApps/{app_name}"
        f"/authConfigs/current?api-version={CONTAINER_APPS_API}"
    )


def auth_problems(config: Mapping[str, Any] | None, spec: AuthSpec) -> list[str]:
    """Differences between a built-in auth configuration and ``spec`` (empty when it matches).

    ``config`` is the ARM resource (``{"properties": {...}}``) or the properties alone, as
    printed by ``az containerapp auth show``.
    """
    data = config or {}
    properties = data.get("properties") if isinstance(data.get("properties"), dict) else data
    platform = properties.get("platform") or {}
    validation = properties.get("globalValidation") or {}
    provider = (properties.get("identityProviders") or {}).get("azureActiveDirectory") or {}
    registration = provider.get("registration") or {}
    token_validation = provider.get("validation") or {}
    policy = token_validation.get("defaultAuthorizationPolicy") or {}
    token_store = (properties.get("login") or {}).get("tokenStore") or {}
    checks = (
        (platform.get("enabled") is True, "built-in auth is not enabled (platform.enabled)"),
        (
            validation.get("unauthenticatedClientAction") == spec.action,
            f"unauthenticated requests are not answered with {spec.action}",
        ),
        (
            set(validation.get("excludedPaths") or []) == set(spec.excluded_paths),
            "the excluded paths differ",
        ),
        (provider.get("enabled", True) is not False, "the Microsoft Entra provider is disabled"),
        (registration.get("clientId") == spec.client_id, "the client ID differs"),
        (
            str(registration.get("openIdIssuer") or "").endswith("/v2.0"),
            "the issuer is not the tenant's v2 issuer",
        ),
        (not registration.get("clientSecretSettingName"), "a client secret is configured"),
        (
            set(token_validation.get("allowedAudiences") or []) == set(spec.audiences),
            "the allowed audiences differ",
        ),
        (
            set(policy.get("allowedApplications") or []) == set(spec.allowed_applications),
            "the allowed applications differ",
        ),
        (not token_store.get("enabled"), "the token store is enabled"),
    )
    return [problem for ok, problem in checks if not ok]


def auth_matches(config: Mapping[str, Any] | None, spec: AuthSpec) -> bool:
    return not auth_problems(config, spec)


def apply_auth(tools: Tools, app_name: str, spec: AuthSpec, *, deployment_name: str) -> bool:
    """Deploy infra/modules/app-auth.bicep unless the app already matches; then verify.

    Returns True when a deployment was made.
    """
    url = auth_config_url(tools, app_name)
    if auth_matches(tools.rest("GET", url, allow_not_found=True), spec):
        info(f"built-in auth on {app_name} already configured ({spec.action})")
        return False
    values = tools.require("AZURE_SUBSCRIPTION_ID", "AZURE_RESOURCE_GROUP")
    parameters = {
        "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
        "contentVersion": "1.0.0.0",
        "parameters": {
            "containerAppName": {"value": app_name},
            "clientId": {"value": spec.client_id},
            "allowedAudiences": {"value": list(spec.audiences)},
            "unauthenticatedClientAction": {"value": spec.action},
            "excludedPaths": {"value": list(spec.excluded_paths)},
            "allowedApplications": {"value": list(spec.allowed_applications)},
        },
    }
    parameters_file = tools.write_scratch("auth-parameters", parameters)
    info(f"configuring built-in auth on {app_name} ({spec.action})")
    try:
        tools.az(
            "deployment", "group", "create",
            "--subscription", values["AZURE_SUBSCRIPTION_ID"],
            "--resource-group", values["AZURE_RESOURCE_GROUP"],
            "--name", deployment_name,
            "--template-file", str(tools.root / "infra" / "modules" / "app-auth.bicep"),
            "--parameters", f"@{parameters_file}",
            "--output", "none",
        )  # fmt: skip
    finally:
        parameters_file.unlink(missing_ok=True)
    if not auth_matches(tools.rest("GET", url, allow_not_found=True), spec):
        raise HookError(
            f"built-in auth on {app_name} does not match the expected configuration",
            f"Inspect it with: az containerapp auth show --name {app_name} "
            f"--resource-group {values['AZURE_RESOURCE_GROUP']}",
        )
    return True


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


def step_mcp_api(ctx: Context) -> None:
    tools = ctx.tools
    suffix, tag = ctx.names()
    previous = ctx.state.get("mcp_api") or {}
    owner, _ = ctx.principal()
    registration = entra.ensure_mcp_api(
        tools,
        display_name=f"docwiki-mcp-api-{suffix}",
        tag=tag,
        known_app_id=previous.get("app_id") or tools.get("DOCWIKI_MCP_API_CLIENT_ID") or None,
        owner_object_id=owner,
    )
    ctx.state["mcp_api"] = registration.to_state(previous)
    ctx.save()
    tools.azd_env_set("DOCWIKI_MCP_API_CLIENT_ID", registration.app_id)
    tools.azd_env_set("DOCWIKI_MCP_API_AUDIENCE", registration.identifier_uri or "")
    tools.azd_env_set("DOCWIKI_MCP_API_SERVICE_PRINCIPAL_ID", registration.service_principal_id)
    info(f"MCP API app registration ready ({registration.display_name})")


def split_ids(value: str) -> tuple[str, ...]:
    return tuple(unique(item.strip() for item in value.split(",") if item.strip()))


def mcp_auth_spec(tools: Tools, allowed: Sequence[str] | None = None) -> AuthSpec:
    """Built-in auth of the MCP app (ADR 0003); ``allowed`` defaults to the recorded allowlist."""
    client_id = tools.require("DOCWIKI_MCP_API_CLIENT_ID")["DOCWIKI_MCP_API_CLIENT_ID"]
    if allowed is None:
        allowed = split_ids(tools.get("DOCWIKI_MCP_ALLOWED_CLIENT_IDS"))
    return AuthSpec(
        client_id=client_id,
        # v2 access tokens carry the client ID as `aud`, which is accepted implicitly.
        audiences=(f"api://{client_id}",),
        action="Return401",
        excluded_paths=("/healthz",),
        allowed_applications=tuple(allowed),
    )


def step_mcp_auth(ctx: Context) -> None:
    tools = ctx.tools
    app_name = tools.require("DOCWIKI_MCP_APP_NAME")["DOCWIKI_MCP_APP_NAME"]
    spec = mcp_auth_spec(tools)
    try:
        apply_auth(tools, app_name, spec, deployment_name="docwiki-mcp-auth")
    except CommandError as exc:
        raise HookError(
            f"built-in auth could not be applied to {app_name}; this run does not enable "
            f"external ingress: {exc}",
            "Fix the cause shown above, or run `azd provision` (the MCP API app registration now "
            "exists, so Bicep declares the built-in auth with the app), then "
            "`azd hooks run postprovision`.",
        ) from exc
    if not spec.allowed_applications:
        info("no agent allowed through the MCP app's built-in auth yet (mcp-allowlist step)")
    secure_mcp_app(tools, app_name, spec)
    ctx.state["mcp_auth"] = {"app": app_name, "verified_at": utc_now()}
    ctx.save()


# ---------------------------------------------------------------------------
# MCP app exposure: verified built-in auth -> server token settings -> external ingress
# ---------------------------------------------------------------------------


def container_app_url(tools: Tools, app_name: str) -> str:
    values = tools.require("AZURE_SUBSCRIPTION_ID", "AZURE_RESOURCE_GROUP")
    return (
        f"{ARM}/subscriptions/{values['AZURE_SUBSCRIPTION_ID']}/resourceGroups/"
        f"{values['AZURE_RESOURCE_GROUP']}/providers/Microsoft.App/containerApps/{app_name}"
        f"?api-version={CONTAINER_APPS_API}"
    )


def verify_auth_enabled(tools: Tools, app_name: str, spec: AuthSpec) -> None:
    """``az containerapp auth show`` must report the expected configuration, enabled."""
    values = tools.require("AZURE_SUBSCRIPTION_ID", "AZURE_RESOURCE_GROUP")
    shown = tools.az_json(
        "containerapp", "auth", "show",
        "--name", app_name,
        "--resource-group", values["AZURE_RESOURCE_GROUP"],
        "--subscription", values["AZURE_SUBSCRIPTION_ID"],
    )  # fmt: skip
    problems = auth_problems(shown if isinstance(shown, dict) else None, spec)
    if problems:
        raise HookError(
            f"built-in auth on {app_name} is not verified ({'; '.join(problems)}): external "
            "ingress stays disabled",
            f"Inspect it with: az containerapp auth show --name {app_name} --resource-group "
            f"{values['AZURE_RESOURCE_GROUP']}; then re-run: azd hooks run postprovision",
        )
    info(
        f"built-in auth on {app_name} verified: enabled, {spec.action}, audience, "
        f"{len(spec.allowed_applications)} allowed application(s)"
    )


def mcp_server_settings(tools: Tools, spec: AuthSpec) -> dict[str, str]:
    """Token settings of the MCP server (same values as ``infra/main.bicep``); empty = unset."""
    tenant = tools.require("AZURE_TENANT_ID")["AZURE_TENANT_ID"]
    validation = tools.get("DOCWIKI_MCP_TOKEN_VALIDATION", "required").strip().lower()
    if validation not in TOKEN_VALIDATION_MODES:
        raise HookError(
            f"invalid DOCWIKI_MCP_TOKEN_VALIDATION {validation!r}",
            "azd env set DOCWIKI_MCP_TOKEN_VALIDATION required",
        )
    if validation == "off":
        warn(
            "DOCWIKI_MCP_TOKEN_VALIDATION=off: the MCP server trusts the principal header of "
            "built-in auth without validating the bearer token (src/docwiki/mcp/README.md)"
        )
    return {
        "DOCWIKI_MCP_TENANT_ID": tenant,
        "DOCWIKI_MCP_AUDIENCE": ",".join((f"api://{spec.client_id}", spec.client_id)),
        "DOCWIKI_MCP_ALLOWED_CLIENT_IDS": ",".join(spec.allowed_applications),
        "DOCWIKI_MCP_TOKEN_VALIDATION": validation,
    }


def container_env(app: Mapping[str, Any] | None) -> tuple[str, dict[str, str]]:
    """Name and plain environment values of the app's first container."""
    template = ((app or {}).get("properties") or {}).get("template") or {}
    containers = template.get("containers") or [{}]
    first = containers[0] if isinstance(containers[0], dict) else {}
    env = {
        str(item["name"]): str(item.get("value") or "")
        for item in first.get("env") or []
        if isinstance(item, dict) and item.get("name")
    }
    return str(first.get("name") or ""), env


def ensure_container_settings(
    tools: Tools,
    app_name: str,
    app: Mapping[str, Any] | None,
    settings: Mapping[str, str],
    *,
    label: str = "MCP server token settings",
) -> bool:
    """Set (or remove, for empty values) environment variables of the app's container.

    Returns True when the app was updated (a new revision).
    """
    container, current = container_env(app)
    changed = {key: value for key, value in settings.items() if value and current.get(key) != value}
    removed = [key for key, value in settings.items() if not value and key in current]
    if not changed and not removed:
        info(f"{label} already up to date on {app_name}")
        return False
    values = tools.require("AZURE_SUBSCRIPTION_ID", "AZURE_RESOURCE_GROUP")
    command = [
        "containerapp", "update",
        "--name", app_name,
        "--resource-group", values["AZURE_RESOURCE_GROUP"],
        "--subscription", values["AZURE_SUBSCRIPTION_ID"],
    ]  # fmt: skip
    if container:
        command += ["--container-name", container]
    if changed:
        info(f"setting {', '.join(changed)} on {app_name}")
        pairs = [f"{key}={value}" for key, value in changed.items()]
        tools.az(*command, "--set-env-vars", *pairs, "--output", "none")
    if removed:
        info(f"removing {', '.join(removed)} from {app_name}")
        tools.az(*command, "--remove-env-vars", *removed, "--output", "none")
    return True


def secure_mcp_app(tools: Tools, app_name: str, spec: AuthSpec) -> None:
    """Expose the MCP app only behind verified built-in auth, with the server's token settings.

    Order matters (fail closed): verify built-in auth, then set the token settings, then enable
    external ingress. Any failure leaves the app without external ingress.
    """
    verify_auth_enabled(tools, app_name, spec)
    app = tools.rest("GET", container_app_url(tools, app_name)) or {}
    ensure_container_settings(tools, app_name, app, mcp_server_settings(tools, spec))
    fqdn = ensure_external_ingress(tools, app_name, app=app)
    expected = tools.get("DOCWIKI_MCP_FQDN")
    if fqdn and expected and fqdn.lower() != expected.lower():
        warn(
            f"{app_name} answers at {fqdn}, not at DOCWIKI_MCP_FQDN ({expected}): the agents' "
            "connection targets DOCWIKI_MCP_URL; run `azd provision` and report the difference"
        )


def ensure_external_ingress(
    tools: Tools,
    app_name: str,
    target_port: int = 8080,
    *,
    app: Mapping[str, Any] | None = None,
) -> str:
    """Enable external ingress unless the app already has it; returns the app's FQDN."""
    values = tools.require("AZURE_SUBSCRIPTION_ID", "AZURE_RESOURCE_GROUP")
    if app is None:
        app = tools.rest("GET", container_app_url(tools, app_name)) or {}
    ingress = ((app.get("properties") or {}).get("configuration") or {}).get("ingress") or {}
    if ingress.get("external") is True:
        return str(ingress.get("fqdn") or "")
    info(f"enabling external ingress on {app_name}")
    enabled = tools.az_json(
        "containerapp", "ingress", "enable",
        "--name", app_name,
        "--resource-group", values["AZURE_RESOURCE_GROUP"],
        "--subscription", values["AZURE_SUBSCRIPTION_ID"],
        "--type", "external",
        "--target-port", str(target_port),
        "--transport", "auto",
    )  # fmt: skip
    return str(enabled.get("fqdn") or "") if isinstance(enabled, dict) else ""


def step_portal(ctx: Context) -> None:
    tools = ctx.tools
    if not is_true(tools.get("DOCWIKI_ENABLE_PORTAL")):
        info("portal disabled (DOCWIKI_ENABLE_PORTAL=false): skipped")
        return
    values = tools.require("DOCWIKI_PORTAL_APP_NAME", "DOCWIKI_CONTAINER_APPS_DEFAULT_DOMAIN")
    app_name = values["DOCWIKI_PORTAL_APP_NAME"]
    host = f"{app_name}.{values['DOCWIKI_CONTAINER_APPS_DEFAULT_DOMAIN']}"
    if (tools.get("DOCWIKI_PORTAL_ACCESS") or "entra").strip().lower() == "public":
        # Bicep gives the portal its ingress itself, and only for a public-audience build.
        if is_true(tools.get("DOCWIKI_PORTAL_ANONYMOUS")):
            info(f"portal ready at https://{host}/ (public: every page without sign-in)")
            secure_portal_owner(ctx, app_name, host)
        else:
            warn(
                "DOCWIKI_PORTAL_ACCESS=public needs DOCWIKI_AUDIENCE=public: the portal stays "
                "without ingress (set DOCWIKI_PORTAL_ACCESS=entra for a signed-in portal)"
            )
        return
    suffix, tag = ctx.names()
    previous = ctx.state.get("portal_app") or {}
    owner, owner_type = ctx.principal()
    registration = entra.ensure_portal_app(
        tools,
        display_name=f"docwiki-portal-{suffix}",
        tag=tag,
        known_app_id=previous.get("app_id") or tools.get("DOCWIKI_PORTAL_CLIENT_ID") or None,
        redirect_uri=f"https://{host}/.auth/login/aad/callback",
        owner_object_id=owner,
    )
    ctx.state["portal_app"] = registration.to_state(previous)
    ctx.save()
    tools.azd_env_set("DOCWIKI_PORTAL_CLIENT_ID", registration.app_id)
    if owner and owner_type == "User":
        # Sign-in requires an assignment: grant the deployer; add readers in Entra ID.
        entra.ensure_app_role_assignment(
            tools,
            resource_sp_id=registration.service_principal_id,
            principal_id=owner,
            role_id=entra.DEFAULT_ACCESS_ROLE_ID,
        )
    spec = AuthSpec(
        client_id=registration.app_id,
        audiences=(registration.app_id,),
        action="RedirectToLoginPage",
    )
    apply_auth(tools, app_name, spec, deployment_name="docwiki-portal-auth")
    ensure_external_ingress(tools, app_name)
    info(f"portal ready at https://{host}/ (Entra sign-in)")


def secure_portal_owner(ctx: Context, app_name: str, host: str) -> None:
    """The owner's sign-in on the public portal (ADR 0009), fail closed: the container gets its
    owners only once built-in auth (AllowAnonymous) is verified in front of it, since without it
    any client could send the principal header itself."""
    tools = ctx.tools
    if not is_true(tools.get("DOCWIKI_PORTAL_OWNER_SIGN_IN"), default=True):
        info("owner sign-in on the portal disabled (DOCWIKI_PORTAL_OWNER_SIGN_IN=false): skipped")
        return
    owner, owner_type = ctx.principal()
    if owner_type != "User":
        warn(
            f"the portal signs in its owner and the deployer is a {owner_type}, not a user: "
            "no sign-in and no uploads (run the hook signed in as the user who owns it)"
        )
        return
    suffix, tag = ctx.names()
    previous = ctx.state.get("portal_app") or {}
    custom_domain = (tools.get("DOCWIKI_PORTAL_CUSTOM_DOMAIN") or "").strip()
    registration = entra.ensure_portal_app(
        tools,
        display_name=f"docwiki-portal-{suffix}",
        tag=tag,
        known_app_id=previous.get("app_id") or tools.get("DOCWIKI_PORTAL_CLIENT_ID") or None,
        redirect_uri=f"https://{host}/.auth/login/aad/callback",
        extra_redirect_uris=(
            (f"https://{custom_domain}/.auth/login/aad/callback",) if custom_domain else ()
        ),
        owner_object_id=owner,
        description="DocWiki portal: the owner's sign-in (uploads).",
    )
    ctx.state["portal_app"] = registration.to_state(previous)
    ctx.save()
    tools.azd_env_set("DOCWIKI_PORTAL_CLIENT_ID", registration.app_id)
    # Sign-in requires an assignment: grant the deployer; nobody else signs in.
    entra.ensure_app_role_assignment(
        tools,
        resource_sp_id=registration.service_principal_id,
        principal_id=owner,
        role_id=entra.DEFAULT_ACCESS_ROLE_ID,
    )
    owners = tools.get(PORTAL_OWNERS_SETTING)
    if not owners:
        tools.azd_env_set(PORTAL_OWNERS_SETTING, owner)
        owners = owner
    spec = AuthSpec(
        client_id=registration.app_id,
        audiences=(registration.app_id,),
        action="AllowAnonymous",
        excluded_paths=PORTAL_OWNER_EXCLUDED_PATHS,
    )
    apply_auth(tools, app_name, spec, deployment_name="docwiki-portal-auth")
    verify_auth_enabled(tools, app_name, spec)
    app = tools.rest("GET", container_app_url(tools, app_name)) or {}
    ensure_container_settings(
        tools, app_name, app, {PORTAL_OWNERS_SETTING: owners}, label="portal owners"
    )
    info(f"owner sign-in ready at https://{custom_domain or host}/how-it-works")


def secure_studio_app(tools: Tools, app_name: str, spec: AuthSpec, allowed_principals: str) -> None:
    """Expose the Studio only behind verified built-in auth, with its owner allowlist.

    Same order as the MCP app (fail closed): verify built-in auth, make sure the running
    container has the allowlist (on the first provision Bicep ran before the hook set it, and the
    app refuses everyone without it), then enable external ingress.
    """
    verify_auth_enabled(tools, app_name, spec)
    app = tools.rest("GET", container_app_url(tools, app_name)) or {}
    ensure_container_settings(
        tools,
        app_name,
        app,
        {STUDIO_PRINCIPALS_SETTING: allowed_principals},
        label="Studio owner allowlist",
    )
    ensure_external_ingress(tools, app_name, app=app)


def step_studio(ctx: Context) -> None:
    tools = ctx.tools
    if not is_true(tools.get("DOCWIKI_ENABLE_STUDIO")):
        info("studio disabled (DOCWIKI_ENABLE_STUDIO=false): skipped")
        return
    values = tools.require("DOCWIKI_STUDIO_APP_NAME", "DOCWIKI_CONTAINER_APPS_DEFAULT_DOMAIN")
    app_name = values["DOCWIKI_STUDIO_APP_NAME"]
    host = f"{app_name}.{values['DOCWIKI_CONTAINER_APPS_DEFAULT_DOMAIN']}"
    owner, owner_type = ctx.principal()
    if owner_type != "User":
        warn(
            f"the Studio signs in its owner and the deployer is a {owner_type}, not a user: "
            "the Studio stays without ingress (run the hook signed in as the user who owns it)"
        )
        return
    suffix, tag = ctx.names()
    previous = ctx.state.get("studio_app") or {}
    registration = entra.ensure_portal_app(
        tools,
        display_name=f"docwiki-studio-{suffix}",
        tag=tag,
        known_app_id=previous.get("app_id") or tools.get("DOCWIKI_STUDIO_CLIENT_ID") or None,
        redirect_uri=f"https://{host}/.auth/login/aad/callback",
        owner_object_id=owner,
        description="DocWiki Studio sign-in (owner only).",
    )
    ctx.state["studio_app"] = registration.to_state(previous)
    ctx.save()
    tools.azd_env_set("DOCWIKI_STUDIO_CLIENT_ID", registration.app_id)
    # Sign-in requires an assignment: grant the deployer; the Studio has no other user.
    entra.ensure_app_role_assignment(
        tools,
        resource_sp_id=registration.service_principal_id,
        principal_id=owner,
        role_id=entra.DEFAULT_ACCESS_ROLE_ID,
    )
    allowed = tools.get(STUDIO_PRINCIPALS_SETTING)
    if not allowed:
        tools.azd_env_set(STUDIO_PRINCIPALS_SETTING, owner)
        allowed = owner
    spec = AuthSpec(
        client_id=registration.app_id,
        audiences=(registration.app_id,),
        action="RedirectToLoginPage",
        excluded_paths=("/healthz", "/livez"),
    )
    apply_auth(tools, app_name, spec, deployment_name="docwiki-studio-auth")
    secure_studio_app(tools, app_name, spec, allowed)
    info(f"studio ready at https://{host}/ (Entra sign-in, owner only)")


# ---------------------------------------------------------------------------
# Agents (ADR 0003: docs/adr/0003-mcp-agent-identity.md)
# ---------------------------------------------------------------------------


def agents_available(tools: Tools) -> bool:
    """Whether the agent steps run (agents lane present and not skipped on request)."""
    if is_true(tools.get("DOCWIKI_SKIP_AGENTS")):
        info("DOCWIKI_SKIP_AGENTS is set: agents skipped")
        return False
    if not (tools.root / "agents" / "deploy.py").is_file():
        info("agents/deploy.py not found: agents skipped (agents lane)")
        return False
    return True


def mcp_connection_name(tools: Tools) -> str:
    name = tools.get("DOCWIKI_MCP_CONNECTION", DEFAULT_MCP_CONNECTION)
    if not CONNECTION_NAME.match(name):
        raise HookError(
            f"invalid DOCWIKI_MCP_CONNECTION {name!r} (3-33 letters, digits, '-' or '_')",
            f"azd env set DOCWIKI_MCP_CONNECTION {DEFAULT_MCP_CONNECTION}",
        )
    return name


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}{parts.path.rstrip('/')}"


def connection_url(tools: Tools, name: str) -> str:
    values = tools.require(
        "AZURE_SUBSCRIPTION_ID",
        "AZURE_RESOURCE_GROUP",
        "DOCWIKI_FOUNDRY_ACCOUNT_NAME",
        "DOCWIKI_FOUNDRY_PROJECT_NAME",
    )
    return (
        f"{ARM}/subscriptions/{values['AZURE_SUBSCRIPTION_ID']}/resourceGroups/"
        f"{values['AZURE_RESOURCE_GROUP']}/providers/Microsoft.CognitiveServices/accounts/"
        f"{values['DOCWIKI_FOUNDRY_ACCOUNT_NAME']}/projects/"
        f"{values['DOCWIKI_FOUNDRY_PROJECT_NAME']}/connections/{name}"
        f"?api-version={CONNECTIONS_API}"
    )


def connection_body(target: str, audience: str) -> dict[str, Any]:
    """Same properties as ``infra/modules/mcp-connection.bicep``."""
    return {
        "properties": {
            "category": "RemoteTool",
            "authType": "AgenticIdentityToken",
            "target": target,
            "audience": audience,
            "metadata": {"type": "generic_mcp"},
        }
    }


def connection_matches(current: Mapping[str, Any] | None, *, target: str, audience: str) -> bool:
    """Whether the connection read from ARM already has the wanted properties.

    A property the service does not echo counts as a mismatch: the PUT is idempotent.
    """
    properties = (current or {}).get("properties") or {}
    return (
        str(properties.get("category") or "").casefold() == "remotetool"
        and str(properties.get("authType") or "").casefold() == "agenticidentitytoken"
        and normalize_url(str(properties.get("target") or "")) == normalize_url(target)
        and properties.get("audience") == audience
    )


def step_mcp_connection(ctx: Context) -> None:
    """RemoteTool connection with AgenticIdentityToken, created through ARM
    (`azd ai connection` fails on a project without connections, spike finding F10)."""
    tools = ctx.tools
    if not agents_available(tools):
        return
    values = tools.require("DOCWIKI_MCP_URL", "DOCWIKI_MCP_API_CLIENT_ID")
    target = values["DOCWIKI_MCP_URL"]
    audience = f"api://{values['DOCWIKI_MCP_API_CLIENT_ID']}"
    name = mcp_connection_name(tools)
    url = connection_url(tools, name)
    current = tools.rest("GET", url, allow_not_found=True)
    if connection_matches(current, target=target, audience=audience):
        info(f"MCP connection {name} already configured (AgenticIdentityToken)")
    else:
        action = "updating" if current else "creating"
        info(f"{action} MCP connection {name} (AgenticIdentityToken, audience {audience})")
        tools.rest("PUT", url, body=connection_body(target, audience))
    tools.azd_env_set("DOCWIKI_MCP_CONNECTION", name)
    ctx.state["mcp_connection"] = {
        "name": name,
        "target": target,
        "audience": audience,
        "auth_type": "AgenticIdentityToken",
        "verified_at": utc_now(),
    }
    ctx.save()


def declared_strategies(agents_dir: Path) -> dict[str, set[str]]:
    """``auth.strategy`` values declared by ``agents/<key>/agent.yaml`` (text scan, no YAML)."""
    declared: dict[str, set[str]] = {}
    for path in sorted(agents_dir.glob(f"*/{AGENT_FILE}")):
        found = set(_STRATEGY_LINE.findall(path.read_text(encoding="utf-8")))
        if found:
            declared[path.parent.name] = found
    return declared


def check_agent_definitions(agents_dir: Path) -> None:
    """agents/deploy.py checks the connection against each agent's ``auth.strategy``."""
    mismatched = {
        agent: sorted(found)
        for agent, found in declared_strategies(agents_dir).items()
        if found != {AGENT_AUTH_STRATEGY}
    }
    if mismatched:
        shown = "; ".join(f"{agent}: {', '.join(found)}" for agent, found in mismatched.items())
        raise HookError(
            "the MCP connection authenticates each agent with its own identity, but "
            f"agents/<agent>/{AGENT_FILE} declares {shown}",
            f"Set `auth.strategy: {AGENT_AUTH_STRATEGY}` in the agent definitions ({ADR_0003}).",
        )


def routine_option(ctx: Context) -> str | None:
    """``--routine`` of agents/deploy.py: enable on request, disable a routine enabled before."""
    if is_true(ctx.tools.get("DOCWIKI_ENABLE_ROUTINE")):
        return "enable"
    if ctx.state.get("routine_enabled"):
        return "disable"
    return None


def deploy_command(tools: Tools, script: Path) -> list[str]:
    if tools.which("uv"):
        return [
            "uv",
            "run",
            "--project",
            str(tools.root),
            "--extra",
            "azure",
            "python",
            str(script),
        ]
    return [sys.executable, str(script)]


def parse_deploy_output(text: str) -> dict[str, Any]:
    """The JSON document printed by ``agents/deploy.py --json`` (tolerates surrounding noise)."""
    start = text.find("{")
    if start >= 0:
        try:
            data, _ = json.JSONDecoder().raw_decode(text[start:])
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            return data
    raise HookError(
        "agents/deploy.py --json did not print a JSON document",
        "Run it by hand to see why: uv run --extra azure python agents/deploy.py --json",
    )


def step_agents(ctx: Context) -> None:
    tools = ctx.tools
    if not agents_available(tools):
        return
    agents_dir = tools.root / "agents"
    check_agent_definitions(agents_dir)
    values = tools.require(
        "DOCWIKI_FOUNDRY_PROJECT_ENDPOINT", "DOCWIKI_MCP_URL", "DOCWIKI_SMART_DEPLOYMENT"
    )
    routine = routine_option(ctx)
    command = [*deploy_command(tools, agents_dir / "deploy.py"), "--json"]
    if routine:
        command += ["--routine", routine]
    environment = {
        **os.environ,
        **tools.env,
        "DOCWIKI_MCP_CONNECTION": mcp_connection_name(tools),
    }
    info("deploying the Foundry agents with agents/deploy.py (a new version only on change)")
    result = tools.run(command, env=environment, check=False)
    if not result.ok:
        detail = (result.stderr or result.stdout).strip().splitlines()[-5:]
        raise HookError(
            f"agents/deploy.py failed (exit code {result.returncode}): " + " | ".join(detail),
            "Check the MCP connection and DOCWIKI_* values (agents/README.md), then: "
            "azd hooks run postprovision",
        )
    report = parse_deploy_output(result.stdout)
    deployed: dict[str, Any] = dict(ctx.state.get("agents") or {})
    for item in report.get("agents") or []:
        if not isinstance(item, dict) or not item.get("key"):
            continue
        key = str(item["key"])
        principal = str(item.get("identity_principal_id") or "")
        previous = deployed.get(key)
        before = previous.get("principal_id") if isinstance(previous, dict) else None
        if principal and before and before != principal:
            # A recreated agent gets a new identity (spike finding F4): access is re-applied.
            warn(f"{key}: new agent identity (agent recreated?); MCP roles and allowlist follow")
        deployed[key] = {
            "agent_name": item.get("agent_name"),
            "status": item.get("status"),
            "version": item.get("version"),
            "principal_id": principal,
            # Agent identities use one value for both IDs (spike report section 4.4).
            "client_id": str(item.get("identity_client_id") or principal),
            "project_endpoint": values["DOCWIKI_FOUNDRY_PROJECT_ENDPOINT"],
        }
        info(f"{item.get('agent_name')}: {item.get('status')} (version {item.get('version')})")
    ctx.state["agents"] = deployed
    if routine:
        routines = [item for item in report.get("routines") or [] if isinstance(item, dict)]
        ctx.state["routines"] = routines
        ctx.state["routine_enabled"] = routine == "enable"
    ctx.state["agents_deployed_at"] = utc_now()
    ctx.save()


def _agent_value(ctx: Context, agent: str, key: str) -> str:
    """``DOCWIKI_<AGENT>_<KEY>`` override, else the value reported by agents/deploy.py."""
    reported = ctx.state.get("agents") or {}
    entry = reported.get(agent) if isinstance(reported, dict) else None
    value = entry.get(key) if isinstance(entry, dict) else None
    return ctx.tools.get(f"DOCWIKI_{agent.upper()}_{key.upper()}") or str(value or "")


def resolve_agent_principals(ctx: Context) -> dict[str, str]:
    """Object IDs of the agent identities (``instance_identity.principal_id``) per agent key."""
    return {agent: _agent_value(ctx, agent, "principal_id") for agent in entra.AGENT_ROLES}


def resolve_agent_client_ids(ctx: Context) -> dict[str, str]:
    """Client IDs of the agent identities (``instance_identity.client_id``) per agent key."""
    return {
        agent: _agent_value(ctx, agent, "client_id") or _agent_value(ctx, agent, "principal_id")
        for agent in entra.AGENT_ROLES
    }


def shared_principals(principals: Mapping[str, str]) -> set[str]:
    """Principals reported for more than one agent (never expected, ADR 0003)."""
    counts: dict[str, int] = {}
    for principal in principals.values():
        if principal:
            counts[principal] = counts.get(principal, 0) + 1
    return {principal for principal, count in counts.items() if count > 1}


def step_agent_roles(ctx: Context) -> None:
    tools = ctx.tools
    mcp_api = ctx.state.get("mcp_api") or {}
    resource_sp = mcp_api.get("service_principal_id") or tools.get(
        "DOCWIKI_MCP_API_SERVICE_PRINCIPAL_ID"
    )
    if not resource_sp:
        raise HookError("the MCP API service principal is unknown", "Run the mcp-api step first.")
    principals = resolve_agent_principals(ctx)
    shared = shared_principals(principals)
    recorded: list[dict[str, Any]] = list(ctx.state.get("app_role_assignments") or [])
    for agent, roles in entra.AGENT_ROLES.items():
        principal = principals.get(agent)
        if not principal:
            warn(
                f"no agent identity for the {agent} agent: MCP roles not assigned. Deploy the "
                f"agents (or set DOCWIKI_{agent.upper()}_PRINCIPAL_ID), then re-run "
                f"`azd hooks run postprovision` ({ADR_0003})."
            )
            continue
        granted = roles
        if principal in shared:
            # Least privilege: a principal shared with the read-only Researcher never operates.
            granted = tuple(role for role in roles if role == entra.ROLE_READ)
            withheld = [role for role in roles if role not in granted]
            for role in withheld:
                warn(
                    f"{agent} reports the same identity as another agent: {role} withheld "
                    f"(each agent should have its own identity, {ADR_0003})."
                )
                if entra.remove_app_role_assignment(
                    tools,
                    resource_sp_id=resource_sp,
                    principal_id=principal,
                    role_id=entra.app_role_id(role),
                ):
                    warn(f"{role} revoked from the shared principal (effective at token refresh)")
                recorded = [
                    item
                    for item in recorded
                    if not (item.get("principal_id") == principal and item.get("role") == role)
                ]
        for role in granted:
            assignment = entra.ensure_app_role_assignment(
                tools,
                resource_sp_id=resource_sp,
                principal_id=principal,
                role_id=entra.app_role_id(role),
            )
            entry = {
                "agent": agent,
                "role": role,
                "principal_id": principal,
                "assignment_id": assignment.get("id"),
            }
            recorded = [
                item
                for item in recorded
                if not (item.get("principal_id") == principal and item.get("role") == role)
            ]
            recorded.append(entry)
            info(f"{agent}: {role} granted")
    ctx.state["app_role_assignments"] = recorded
    ctx.save()


def blocked_agents(tools: Tools) -> set[str]:
    """Agents removed from the MCP allowlist on purpose (``DOCWIKI_MCP_BLOCKED_AGENTS``)."""
    blocked = {item.strip() for item in tools.get("DOCWIKI_MCP_BLOCKED_AGENTS").split(",")}
    blocked.discard("")
    unknown = blocked - set(entra.AGENT_ROLES)
    if unknown:
        raise HookError(
            f"unknown agents in DOCWIKI_MCP_BLOCKED_AGENTS: {', '.join(sorted(unknown))}",
            "Use agent keys: " + ", ".join(entra.AGENT_ROLES),
        )
    return blocked


def step_mcp_allowlist(ctx: Context) -> None:
    """Easy Auth ``allowedApplications`` = the agents' client IDs (empty: every agent gets 403)."""
    tools = ctx.tools
    blocked = blocked_agents(tools)
    allowed: dict[str, str] = {}
    for agent, client_id in resolve_agent_client_ids(ctx).items():
        if agent in blocked:
            warn(f"{agent} is blocked (DOCWIKI_MCP_BLOCKED_AGENTS): the MCP app answers 403 to it")
        elif not client_id:
            warn(f"no agent identity for the {agent} agent yet: the MCP app answers 403 to it")
        else:
            allowed[agent] = client_id
    client_ids = unique(allowed.values())
    value = ",".join(client_ids)
    if tools.get("DOCWIKI_MCP_ALLOWED_CLIENT_IDS") != value:
        tools.azd_env_set("DOCWIKI_MCP_ALLOWED_CLIENT_IDS", value)
    app_name = tools.require("DOCWIKI_MCP_APP_NAME")["DOCWIKI_MCP_APP_NAME"]
    spec = mcp_auth_spec(tools, client_ids)
    apply_auth(tools, app_name, spec, deployment_name="docwiki-mcp-auth")
    # The server's own caller allowlist (DOCWIKI_MCP_ALLOWED_CLIENT_IDS) follows the new list.
    secure_mcp_app(tools, app_name, spec)
    ctx.state["mcp_allowed_applications"] = allowed
    ctx.save()
    info(f"MCP built-in auth allows: {', '.join(allowed) or 'no agent'}")


def step_content_understanding(ctx: Context) -> None:
    tools = ctx.tools
    if not is_true(tools.get("DOCWIKI_CU_DEFAULTS")):
        info("Content Understanding defaults not requested (DOCWIKI_CU_DEFAULTS): skipped")
        return
    endpoint = tools.require("DOCWIKI_FOUNDRY_ACCOUNT_ENDPOINT")["DOCWIKI_FOUNDRY_ACCOUNT_ENDPOINT"]
    deployments = {
        "prebuilt-analyzer-completion": tools.get(
            "DOCWIKI_CU_COMPLETION_DEPLOYMENT", tools.get("DOCWIKI_SMART_DEPLOYMENT", "smart")
        ),
        "prebuilt-analyzer-completion-mini": tools.get(
            "DOCWIKI_CU_COMPLETION_MINI_DEPLOYMENT", tools.get("DOCWIKI_FAST_DEPLOYMENT", "fast")
        ),
    }
    embedding = tools.get("DOCWIKI_CU_EMBEDDING_DEPLOYMENT")
    if embedding:
        deployments["prebuilt-analyzer-embedding"] = embedding
    url = (
        f"{endpoint.rstrip('/')}/contentunderstanding/defaults"
        f"?api-version={CONTENT_UNDERSTANDING_API}"
    )
    tools.rest(
        "PATCH", url, body={"modelDeployments": deployments}, resource=COGNITIVE_SERVICES_RESOURCE
    )
    ctx.state["content_understanding_defaults"] = deployments
    ctx.save()
    info("Content Understanding model defaults set")


STEPS: tuple[tuple[str, Callable[[Context], None]], ...] = (
    ("mcp-api", step_mcp_api),
    ("mcp-auth", step_mcp_auth),
    ("portal", step_portal),
    ("studio", step_studio),
    ("mcp-connection", step_mcp_connection),
    ("agents", step_agents),
    ("agent-roles", step_agent_roles),
    ("mcp-allowlist", step_mcp_allowlist),
    ("content-understanding", step_content_understanding),
)


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    names = ", ".join(name for name, _ in STEPS)
    parser = argparse.ArgumentParser(description="DocWiki postprovision hook")
    parser.add_argument("--env", help="azd environment name (default: AZURE_ENV_NAME)")
    parser.add_argument("--only", default="", help=f"comma-separated steps to run ({names})")
    parser.add_argument("--skip", default="", help="comma-separated steps to skip")
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    *,
    runner: Runner | None = None,
    environ: Mapping[str, str] | None = None,
    root: Path = REPO_ROOT,
) -> int:
    args = parse_args(argv)
    only = {item.strip() for item in args.only.split(",") if item.strip()}
    skip = {item.strip() for item in args.skip.split(",") if item.strip()}
    unknown = (only | skip) - {name for name, _ in STEPS}
    if unknown:
        error("unknown steps: " + ", ".join(sorted(unknown)))
        return 2
    tools = tools_from_environment(environ, root=root, runner=runner, env_name=args.env)
    try:
        path = state_path(tools.env_name, root)
        ctx = Context(tools=tools, state=load_state(path), state_file=path)
        ctx.state.setdefault("environment", tools.env_name)
        for name, step in STEPS:
            if (only and name not in only) or name in skip:
                continue
            info(f"step {name}")
            step(ctx)
    except HookError as exc:
        error(str(exc), exc.remediation)
        return 1
    info(f"postprovision complete; state in {path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
