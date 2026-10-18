"""Microsoft Entra ID (Microsoft Graph) operations of the DocWiki hooks.

Creates or updates the app registrations used by Container Apps built-in auth, their service
principals and the app role assignments of the agent principals. Every function is
idempotent: re-running a hook converges on the same objects.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from azdlib import GRAPH, CommandError, HookError, Tools, info, retry, unique, warn

ROLE_READ = "Wiki.Read"
ROLE_OPERATE = "Wiki.Operate"

# App roles of the MCP API, granted to applications (agent principals), never to users.
MCP_APP_ROLES: dict[str, str] = {
    ROLE_READ: "Read the DocWiki wiki through the MCP read tools.",
    ROLE_OPERATE: "Operate the DocWiki pipeline through the MCP operations tools.",
}

# Roles per agent (docs/spec/architecture.md §6).
AGENT_ROLES: dict[str, tuple[str, ...]] = {
    "researcher": (ROLE_READ,),
    "librarian": (ROLE_READ, ROLE_OPERATE),
}

# App role ID used for "default access" assignments (no app role defined).
DEFAULT_ACCESS_ROLE_ID = str(uuid.UUID(int=0))

DOCWIKI_TAG = "docwiki"


def app_role_id(value: str) -> str:
    """Deterministic app role ID: the same role value always maps to the same GUID."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"urn:docwiki:app-role:{value}"))


@dataclass
class AppRegistration:
    """An app registration and its service principal."""

    object_id: str
    app_id: str
    display_name: str
    service_principal_id: str
    created: bool
    identifier_uri: str | None = None

    def to_state(self, previous: Mapping[str, Any] | None = None) -> dict[str, Any]:
        previous = previous or {}
        created_by_hook = bool(previous.get("created_by_hook")) or self.created
        if previous.get("app_id") not in (None, self.app_id):
            created_by_hook = self.created
        return {
            "app_id": self.app_id,
            "object_id": self.object_id,
            "display_name": self.display_name,
            "service_principal_id": self.service_principal_id,
            "identifier_uri": self.identifier_uri,
            "created_by_hook": created_by_hook,
        }


def _check_name(display_name: str) -> None:
    if not display_name or "'" in display_name:
        raise HookError(f"invalid app registration name {display_name!r}")


def get_application(tools: Tools, app_id: str) -> dict[str, Any] | None:
    return tools.rest("GET", f"{GRAPH}/applications(appId='{app_id}')", allow_not_found=True)


def find_tagged_applications(tools: Tools, display_name: str, tag: str) -> list[dict[str, Any]]:
    _check_name(display_name)
    data = tools.rest("GET", f"{GRAPH}/applications?$filter=displayName eq '{display_name}'")
    return [app for app in (data or {}).get("value", []) if tag in (app.get("tags") or [])]


def ensure_application(
    tools: Tools,
    *,
    display_name: str,
    tag: str,
    known_app_id: str | None,
    initial: Mapping[str, Any],
) -> tuple[dict[str, Any], bool]:
    """Find the app registration (state file first, then name + tag) or create it."""
    app: dict[str, Any] | None = None
    if known_app_id:
        app = get_application(tools, known_app_id)
        if app is None:
            warn(f"app registration {known_app_id} recorded in the state file no longer exists")
    if app is None:
        matches = find_tagged_applications(tools, display_name, tag)
        if len(matches) > 1:
            raise HookError(
                f"{len(matches)} app registrations named {display_name!r} carry the tag {tag!r}",
                "Delete the duplicates in Microsoft Entra ID, then re-run the hook.",
            )
        app = matches[0] if matches else None
    if app is not None:
        return app, False
    body = {
        "displayName": display_name,
        "signInAudience": "AzureADMyOrg",
        "tags": unique([tag, DOCWIKI_TAG]),
        **initial,
    }
    info(f"creating app registration {display_name}")
    created = tools.rest("POST", f"{GRAPH}/applications", body=body)
    if not isinstance(created, dict) or "appId" not in created:
        raise HookError("Microsoft Graph did not return the created application")
    return created, True


def merge_app_roles(
    existing: Iterable[Mapping[str, Any]],
    wanted: Mapping[str, str],
    member_types: Iterable[str] = ("Application",),
) -> list[dict[str, Any]]:
    """Existing app roles plus the wanted ones (IDs of existing roles are kept).

    The read-only ``origin`` property is dropped: Graph rejects it in POST and PATCH bodies.
    """
    merged: list[dict[str, Any]] = [
        {key: value for key, value in role.items() if key != "origin"} for role in existing
    ]
    by_value = {role.get("value"): role for role in merged}
    members = sorted(member_types)
    for value, description in wanted.items():
        role = by_value.get(value)
        desired = {
            "allowedMemberTypes": members,
            "description": description,
            "displayName": value,
            "isEnabled": True,
            "value": value,
        }
        if role is None:
            merged.append({"id": app_role_id(value), **desired})
        else:
            role.update(desired)
    return merged


def _roles_equal(left: Iterable[Mapping[str, Any]], right: Iterable[Mapping[str, Any]]) -> bool:
    def canon(roles: Iterable[Mapping[str, Any]]) -> list[tuple[Any, ...]]:
        return sorted(
            (
                str(role.get("id")),
                str(role.get("value")),
                str(role.get("description")),
                tuple(sorted(role.get("allowedMemberTypes") or [])),
                bool(role.get("isEnabled")),
            )
            for role in roles
        )

    return canon(left) == canon(right)


def ensure_service_principal(
    tools: Tools, app_id: str, *, assignment_required: bool
) -> dict[str, Any]:
    """Service principal of ``app_id`` with the wanted ``appRoleAssignmentRequired``."""
    sp = tools.rest("GET", f"{GRAPH}/servicePrincipals(appId='{app_id}')", allow_not_found=True)
    if sp is None:
        body = {
            "appId": app_id,
            "appRoleAssignmentRequired": assignment_required,
            "tags": ["WindowsAzureActiveDirectoryIntegratedApp", DOCWIKI_TAG],
        }
        # A new application can take a few seconds to replicate.
        sp = retry(
            lambda: tools.rest("POST", f"{GRAPH}/servicePrincipals", body=body),
            sleep=tools.sleep,
        )
        if not isinstance(sp, dict) or "id" not in sp:
            raise HookError("Microsoft Graph did not return the created service principal")
        return sp
    if bool(sp.get("appRoleAssignmentRequired")) != assignment_required:
        tools.rest(
            "PATCH",
            f"{GRAPH}/servicePrincipals/{sp['id']}",
            body={"appRoleAssignmentRequired": assignment_required},
        )
        sp["appRoleAssignmentRequired"] = assignment_required
    return sp


def ensure_owner(tools: Tools, service_principal_id: str, owner_object_id: str) -> None:
    """Make the deployer an owner of the service principal (needed to manage assignments)."""
    if not owner_object_id:
        return
    try:
        data = tools.rest("GET", f"{GRAPH}/servicePrincipals/{service_principal_id}/owners")
        if any(item.get("id") == owner_object_id for item in (data or {}).get("value", [])):
            return
        tools.rest(
            "POST",
            f"{GRAPH}/servicePrincipals/{service_principal_id}/owners/$ref",
            body={"@odata.id": f"{GRAPH}/directoryObjects/{owner_object_id}"},
        )
    except CommandError as exc:
        warn(f"could not add the deployer as owner of service principal: {exc}")


def ensure_mcp_api(
    tools: Tools,
    *,
    display_name: str,
    tag: str,
    known_app_id: str | None,
    owner_object_id: str = "",
) -> AppRegistration:
    """MCP API app registration: identifier URI, v2 tokens, app roles for applications."""
    app, created = ensure_application(
        tools,
        display_name=display_name,
        tag=tag,
        known_app_id=known_app_id,
        initial={
            "description": "DocWiki MCP API (Container Apps built-in auth audience).",
            "api": {"requestedAccessTokenVersion": 2},
            "appRoles": merge_app_roles([], MCP_APP_ROLES),
        },
    )
    app_id = str(app["appId"])
    identifier_uri = f"api://{app_id}"
    patch: dict[str, Any] = {}
    uris = list(app.get("identifierUris") or [])
    if identifier_uri not in uris:
        patch["identifierUris"] = unique([*uris, identifier_uri])
    api = dict(app.get("api") or {})
    if api.get("requestedAccessTokenVersion") != 2:
        api["requestedAccessTokenVersion"] = 2
        patch["api"] = api
    current_roles = list(app.get("appRoles") or [])
    roles = merge_app_roles(current_roles, MCP_APP_ROLES)
    if not _roles_equal(current_roles, roles):
        patch["appRoles"] = roles
    if patch:
        info(f"updating app registration {display_name}: {', '.join(sorted(patch))}")
        retry(
            lambda: tools.rest("PATCH", f"{GRAPH}/applications/{app['id']}", body=patch),
            sleep=tools.sleep,
        )
    sp = ensure_service_principal(tools, app_id, assignment_required=True)
    ensure_owner(tools, str(sp["id"]), owner_object_id)
    return AppRegistration(
        object_id=str(app["id"]),
        app_id=app_id,
        display_name=display_name,
        service_principal_id=str(sp["id"]),
        created=created,
        identifier_uri=identifier_uri,
    )


def ensure_portal_app(
    tools: Tools,
    *,
    display_name: str,
    tag: str,
    known_app_id: str | None,
    redirect_uri: str,
    owner_object_id: str = "",
) -> AppRegistration:
    """Portal sign-in app: web redirect URI and ID tokens only (no client secret)."""
    web = {
        "redirectUris": [redirect_uri],
        "implicitGrantSettings": {
            "enableIdTokenIssuance": True,
            "enableAccessTokenIssuance": False,
        },
    }
    app, created = ensure_application(
        tools,
        display_name=display_name,
        tag=tag,
        known_app_id=known_app_id,
        initial={"description": "DocWiki private portal sign-in.", "web": web},
    )
    current = app.get("web") or {}
    redirects = list(current.get("redirectUris") or [])
    implicit = current.get("implicitGrantSettings") or {}
    if (
        redirect_uri not in redirects
        or not implicit.get("enableIdTokenIssuance")
        or implicit.get("enableAccessTokenIssuance")
    ):
        body = {"web": {**web, "redirectUris": unique([*redirects, redirect_uri])}}
        info(f"updating app registration {display_name}: web")
        retry(
            lambda: tools.rest("PATCH", f"{GRAPH}/applications/{app['id']}", body=body),
            sleep=tools.sleep,
        )
    sp = ensure_service_principal(tools, str(app["appId"]), assignment_required=True)
    ensure_owner(tools, str(sp["id"]), owner_object_id)
    return AppRegistration(
        object_id=str(app["id"]),
        app_id=str(app["appId"]),
        display_name=display_name,
        service_principal_id=str(sp["id"]),
        created=created,
    )


def ensure_app_role_assignment(
    tools: Tools, *, resource_sp_id: str, principal_id: str, role_id: str
) -> dict[str, Any]:
    """Assign ``role_id`` of the resource service principal to ``principal_id`` once."""
    url = f"{GRAPH}/servicePrincipals/{resource_sp_id}/appRoleAssignedTo"
    data = tools.rest("GET", f"{url}?$top=999")
    for item in (data or {}).get("value", []):
        if item.get("principalId") == principal_id and item.get("appRoleId") == role_id:
            return dict(item)
    body = {"principalId": principal_id, "resourceId": resource_sp_id, "appRoleId": role_id}
    created = retry(lambda: tools.rest("POST", url, body=body), sleep=tools.sleep)
    return dict(created or body)


def remove_app_role_assignment(
    tools: Tools, *, resource_sp_id: str, principal_id: str, role_id: str
) -> bool:
    """Remove ``role_id`` of the resource service principal from ``principal_id``, if granted."""
    url = f"{GRAPH}/servicePrincipals/{resource_sp_id}/appRoleAssignedTo"
    data = tools.rest("GET", f"{url}?$top=999")
    removed = False
    for item in (data or {}).get("value", []):
        if item.get("principalId") == principal_id and item.get("appRoleId") == role_id:
            tools.rest("DELETE", f"{url}/{item['id']}", allow_not_found=True)
            removed = True
    return removed


def delete_application(tools: Tools, object_id: str) -> None:
    """Delete an app registration (its service principal and assignments go with it)."""
    tools.rest("DELETE", f"{GRAPH}/applications/{object_id}", allow_not_found=True)
