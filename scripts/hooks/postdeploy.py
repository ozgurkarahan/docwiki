#!/usr/bin/env python3
"""azd ``postdeploy`` hook for DocWiki (also a standalone MCP smoke test).

1. The ``reconcile`` job runs the same image as the ``ingest`` job (the azd ``job`` service):
   after ``azd deploy`` its image is synchronised and its arguments set to ``reconcile``.
2. Smoke check of the MCP endpoint: built-in auth must be enabled on the MCP app
   (``az containerapp auth show``: ``platform.enabled`` and ``Return401``); ``/mcp`` must answer
   401 without a token, with a token for another audience (Azure Resource Manager) and to a forged
   ``X-MS-CLIENT-PRINCIPAL`` header claiming every app role; ``/healthz`` (excluded from auth)
   answers 200 once a release is published and 503 before. A 401 alone does not prove that
   built-in auth is on (the server answers 401 by itself), hence the explicit check. Any success
   without a valid token, or auth that is not enabled, fails the hook.

    python scripts/hooks/postdeploy.py [--smoke-only | --skip-smoke]
"""

from __future__ import annotations

import sys

if sys.version_info < (3, 12):  # noqa: UP036 - must run (and explain) on older interpreters
    major, minor = sys.version_info[:2]
    sys.stderr.write(f"[docwiki] ERROR: Python 3.12+ is required (found {major}.{minor}).\n")
    raise SystemExit(1)

import argparse
import base64
import json
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from azdlib import (
    ARM,
    REPO_ROOT,
    HookError,
    Runner,
    Tools,
    error,
    info,
    tools_from_environment,
    warn,
)

CONTAINER_APPS_API = "2025-01-01"
PLACEHOLDER_PREFIX = "mcr.microsoft.com/"
RECONCILE_ARGS = ["reconcile"]
PRINCIPAL_HEADER = "X-MS-CLIENT-PRINCIPAL"
ROLE_CLAIM = "http://schemas.microsoft.com/ws/2008/06/identity/claims/role"
OBJECT_ID_CLAIM = "http://schemas.microsoft.com/identity/claims/objectidentifier"

Probe = Callable[[str, str | None, Mapping[str, str] | None], int | None]
"""``probe(url, bearer_token, extra_headers) -> HTTP status`` (None when unreachable)."""


def http_status(
    url: str,
    bearer: str | None = None,
    extra_headers: Mapping[str, str] | None = None,
    timeout_s: float = 30.0,
) -> int | None:
    """HTTP status of a GET, optionally with a bearer token (never logged) and extra headers."""
    headers = {"User-Agent": "docwiki-hook", **(extra_headers or {})}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    request = urllib.request.Request(url, method="GET", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def forged_principal() -> str:
    """An ``X-MS-CLIENT-PRINCIPAL`` value claiming both app roles, as an attacker would send it."""
    claims = [{"typ": OBJECT_ID_CLAIM, "val": "docwiki-smoke-test-forgery"}]
    claims += [{"typ": ROLE_CLAIM, "val": role} for role in ("Wiki.Read", "Wiki.Operate")]
    payload = {"auth_typ": "Bearer", "claims": claims, "role_typ": ROLE_CLAIM}
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")


def job_url(tools: Tools, name: str) -> str:
    values = tools.require("AZURE_SUBSCRIPTION_ID", "AZURE_RESOURCE_GROUP")
    return (
        f"{ARM}/subscriptions/{values['AZURE_SUBSCRIPTION_ID']}/resourceGroups/"
        f"{values['AZURE_RESOURCE_GROUP']}/providers/Microsoft.App/jobs/{name}"
        f"?api-version={CONTAINER_APPS_API}"
    )


def first_container(resource: Mapping[str, Any] | None) -> dict[str, Any]:
    template = ((resource or {}).get("properties") or {}).get("template") or {}
    containers = template.get("containers") or [{}]
    return dict(containers[0])


def sync_reconcile_job(tools: Tools) -> bool:
    """Give the reconcile job the ingest job's image; True when an update was made."""
    values = tools.require(
        "AZURE_SUBSCRIPTION_ID",
        "AZURE_RESOURCE_GROUP",
        "DOCWIKI_INGEST_JOB_NAME",
        "DOCWIKI_RECONCILE_JOB_NAME",
    )
    image = tools.get("SERVICE_JOB_IMAGE_NAME")
    if not image:
        ingest = tools.rest("GET", job_url(tools, values["DOCWIKI_INGEST_JOB_NAME"]))
        image = str(first_container(ingest).get("image") or "")
    if not image or image.startswith(PLACEHOLDER_PREFIX):
        warn("the job image has not been deployed yet: reconcile job left unchanged")
        return False
    reconcile_name = values["DOCWIKI_RECONCILE_JOB_NAME"]
    current = first_container(tools.rest("GET", job_url(tools, reconcile_name)))
    if current.get("image") == image and list(current.get("args") or []) == RECONCILE_ARGS:
        info(f"{reconcile_name} already runs {image}")
        return False
    info(f"updating {reconcile_name} to {image} (args: {' '.join(RECONCILE_ARGS)})")
    tools.az(
        "containerapp", "job", "update",
        "--name", reconcile_name,
        "--resource-group", values["AZURE_RESOURCE_GROUP"],
        "--subscription", values["AZURE_SUBSCRIPTION_ID"],
        "--image", image,
        "--args", *RECONCILE_ARGS,
        "--output", "none",
    )  # fmt: skip
    return True


def verify_builtin_auth(tools: Tools) -> None:
    """Built-in auth must be enabled on the MCP app and answer unauthenticated calls with 401.

    HTTP probes cannot tell: without built-in auth the server itself answers 401.
    """
    values = tools.require("AZURE_SUBSCRIPTION_ID", "AZURE_RESOURCE_GROUP", "DOCWIKI_MCP_APP_NAME")
    app_name = values["DOCWIKI_MCP_APP_NAME"]
    shown = tools.az_json(
        "containerapp", "auth", "show",
        "--name", app_name,
        "--resource-group", values["AZURE_RESOURCE_GROUP"],
        "--subscription", values["AZURE_SUBSCRIPTION_ID"],
    )  # fmt: skip
    data = shown if isinstance(shown, dict) else {}
    properties = data.get("properties") if isinstance(data.get("properties"), dict) else data
    enabled = (properties.get("platform") or {}).get("enabled")
    action = (properties.get("globalValidation") or {}).get("unauthenticatedClientAction")
    remediation = (
        "Run `azd hooks run postprovision` (it applies and verifies built-in auth before it "
        "enables external ingress), then `python scripts/hooks/postdeploy.py --smoke-only`. "
        f"To stop traffic meanwhile: az containerapp ingress disable --name {app_name} "
        f"--resource-group {values['AZURE_RESOURCE_GROUP']}"
    )
    if enabled is not True:
        raise HookError(
            f"built-in auth is not enabled on {app_name} (platform.enabled: {enabled!r})",
            remediation,
        )
    if action != "Return401":
        raise HookError(
            f"built-in auth on {app_name} answers unauthenticated calls with {action!r} "
            "(expected Return401)",
            remediation,
        )
    info("MCP built-in auth is enabled (Return401)")


def first_answer(
    tools: Tools,
    probe: Probe,
    url: str,
    bearer: str | None = None,
    headers: Mapping[str, str] | None = None,
    *,
    attempts: int,
    delay_s: float,
) -> int | None:
    """The first status below 500, retrying cold starts (None or 5xx after ``attempts``)."""
    status: int | None = None
    for attempt in range(1, attempts + 1):
        status = probe(url, bearer, headers)
        if status is not None and status < 500:
            break
        if attempt < attempts:
            tools.sleep(delay_s)
    return status


def verify_mcp(tools: Tools, probe: Probe, *, attempts: int = 6, delay_s: float = 10.0) -> None:
    """Fail when built-in auth is off or the MCP endpoint answers without a valid token; warn
    when the endpoint is unreachable."""
    verify_builtin_auth(tools)
    fqdn = tools.get("DOCWIKI_MCP_FQDN")
    if not fqdn:
        warn("DOCWIKI_MCP_FQDN is unknown: MCP smoke check skipped")
        return
    url = f"https://{fqdn}/mcp"
    status = first_answer(tools, probe, url, attempts=attempts, delay_s=delay_s)
    if status is None or status >= 500:
        warn(f"MCP endpoint not reachable yet (status {status}); scale-to-zero cold start?")
        return
    if status < 400:
        raise HookError(
            f"{url} answered {status} without a token: built-in auth is not active",
            "Run `azd hooks run postprovision` and check `az containerapp auth show`.",
        )
    if status != 401:
        warn(f"{url} answered {status} without a token (expected 401)")
    else:
        info("MCP endpoint rejects unauthenticated calls (401)")
    # A forged principal header without a token must never get through: built-in auth replaces
    # the header, and the server requires a valid bearer token (DOCWIKI_MCP_TOKEN_VALIDATION).
    forged = first_answer(
        tools,
        probe,
        url,
        headers={PRINCIPAL_HEADER: forged_principal()},
        attempts=3,
        delay_s=delay_s,
    )
    if forged != 401:
        raise HookError(
            f"{url} answered {forged} to a forged {PRINCIPAL_HEADER} header without a token "
            "(expected 401)",
            "Stop traffic (az containerapp ingress disable --name "
            f"{tools.get('DOCWIKI_MCP_APP_NAME', '<mcp app>')} --resource-group "
            f"{tools.get('AZURE_RESOURCE_GROUP', '<resource group>')}), run `azd hooks run "
            "postprovision`, check `az containerapp auth show` and that "
            "DOCWIKI_MCP_TOKEN_VALIDATION is not off.",
        )
    info("MCP endpoint rejects a forged principal header without a token (401)")
    # A valid token for another audience must be rejected too (audience validation).
    token = tools.az_json("account", "get-access-token", check=False)
    bearer = str((token or {}).get("accessToken") or "")
    if bearer:
        wrong = probe(url, bearer, None)
        if wrong is not None and wrong < 400:
            raise HookError(
                f"{url} accepted a token issued for Azure Resource Manager ({wrong})",
                "Check the allowed audiences: az containerapp auth show --name "
                f"{tools.get('DOCWIKI_MCP_APP_NAME', '<mcp app>')}",
            )
        info(f"MCP endpoint rejects a token for another audience ({wrong})")
    health = probe(f"https://{fqdn}/healthz", None, None)
    if health == 200:
        info("MCP /healthz answers 200")
    elif health == 503:
        info(
            "MCP /healthz answers 503: no release published yet (expected before the first ingest)"
        )
    else:
        warn(f"MCP /healthz answered {health} (expected 200, or 503 before the first release)")


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DocWiki postdeploy hook and MCP smoke test")
    parser.add_argument("--env", help="azd environment name (default: AZURE_ENV_NAME)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--skip-smoke", action="store_true", help="skip the MCP smoke check")
    mode.add_argument("--smoke-only", action="store_true", help="only run the MCP smoke check")
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    *,
    runner: Runner | None = None,
    environ: Mapping[str, str] | None = None,
    root: Path = REPO_ROOT,
    probe: Probe = http_status,
) -> int:
    args = parse_args(argv)
    tools = tools_from_environment(environ, root=root, runner=runner, env_name=args.env)
    try:
        if not args.smoke_only:
            sync_reconcile_job(tools)
        if not args.skip_smoke:
            verify_mcp(tools, probe)
    except HookError as exc:
        error(str(exc), exc.remediation)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
