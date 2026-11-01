#!/usr/bin/env python3
"""DocWiki preflight: verify the deployer machine, sign-in, subscription and region.

Runs as the azd ``preprovision`` hook (``scripts/hooks/preprovision.py``) and on its own:

    python scripts/preflight.py [--env NAME] [--json] [--strict] [--skip roles,entra]

Checks: Python/az/azd/Bicep/Node/uv versions, az and azd sign-in, subscription state, allowed
region, resource providers, model availability and lifecycle, model quota, deployer Azure
roles (Owner, or Contributor + User Access Administrator), permission to create Entra app
registrations, budget contacts and soft-deleted Foundry accounts that would block a redeploy.

It never changes anything and never switches the region or a model on its own: every failure
prints the exact command that fixes it. Exit code 1 when a check fails (``--strict``: also on
warnings).
"""

from __future__ import annotations

import sys

if sys.version_info < (3, 12):  # noqa: UP036 - must run (and explain) on older interpreters
    major, minor = sys.version_info[:2]
    sys.stderr.write(f"[docwiki] ERROR: Python 3.12+ is required (found {major}.{minor}).\n")
    raise SystemExit(1)

import argparse
import json
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent / "hooks"))

from azdlib import (
    ALLOWED_REGIONS,
    REPO_ROOT,
    CommandError,
    HookError,
    Runner,
    ToolMissingError,
    Tools,
    bicep_parameter_defaults,
    parse_version,
    tools_from_environment,
)

MIN_PYTHON = (3, 12)
MIN_AZ = (2, 67, 0)
MIN_AZD = (1, 23, 8)  # Container Apps jobs as `host: containerapp` services
MIN_BICEP = (0, 33, 0)
MIN_NODE = (22, 0, 0)
DEPRECATION_WARNING_DAYS = 90

REQUIRED_PROVIDERS = (
    "Microsoft.App",
    "Microsoft.CognitiveServices",
    "Microsoft.ContainerRegistry",
    "Microsoft.EventGrid",
    "Microsoft.Insights",
    "Microsoft.ManagedIdentity",
    "Microsoft.OperationalInsights",
    "Microsoft.Storage",
    "Microsoft.Consumption",
)

APP_REGISTRATION_ROLES = {
    "Application Developer",
    "Application Administrator",
    "Cloud Application Administrator",
    "Global Administrator",
}

QUOTA_REQUEST_URL = "https://aka.ms/oai/stuquotarequest"
EMAIL_PATTERN = re.compile(r"^[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+$")
SIGN_IN_AGAIN = "Sign in again (az logout; az login; azd auth login), then re-run the preflight."

OK, WARN, FAIL, SKIP = "ok", "warn", "fail", "skip"
_LABEL = {OK: "[ OK ]", WARN: "[WARN]", FAIL: "[FAIL]", SKIP: "[SKIP]"}


@dataclass
class Check:
    name: str
    status: str
    detail: str
    remediation: str | None = None


@dataclass
class ModelChoice:
    tier: str
    name: str
    version: str
    capacity: int
    env_prefix: str


@dataclass
class Settings:
    env_name: str | None
    subscription_id: str | None
    location: str
    resource_group: str | None
    foundry_account: str | None
    deployment_sku: str
    models: list[ModelChoice] = field(default_factory=list)
    budget_contacts: list[str] = field(default_factory=list)

    @classmethod
    def from_tools(cls, tools: Tools, defaults: dict[str, str]) -> Settings:
        def value(env_key: str, param: str) -> str:
            return tools.get(env_key, defaults.get(param, ""))

        def capacity(env_key: str, param: str) -> int:
            raw = value(env_key, param)
            try:
                return int(raw)
            except ValueError:
                raise HookError(f"{env_key} must be an integer, got {raw!r}") from None

        env_name = tools.get("AZURE_ENV_NAME") or None
        contacts = [item.strip() for item in tools.get("BUDGET_CONTACT_EMAILS").split(",")]
        embed = ModelChoice(
            "embed",
            value("DOCWIKI_EMBED_MODEL", "embedModel"),
            value("DOCWIKI_EMBED_MODEL_VERSION", "embedModelVersion"),
            capacity("DOCWIKI_EMBED_CAPACITY", "embedCapacity"),
            "DOCWIKI_EMBED",
        )
        return cls(
            env_name=env_name,
            subscription_id=tools.get("AZURE_SUBSCRIPTION_ID") or None,
            location=value("AZURE_LOCATION", "location"),
            resource_group=tools.get("AZURE_RESOURCE_GROUP")
            or (f"rg-{env_name}" if env_name else None),
            foundry_account=tools.get("DOCWIKI_FOUNDRY_ACCOUNT_NAME") or None,
            deployment_sku=value("DOCWIKI_DEPLOYMENT_SKU", "deploymentSku"),
            models=[
                ModelChoice(
                    "fast",
                    value("DOCWIKI_FAST_MODEL", "fastModel"),
                    value("DOCWIKI_FAST_MODEL_VERSION", "fastModelVersion"),
                    capacity("DOCWIKI_FAST_CAPACITY", "fastCapacity"),
                    "DOCWIKI_FAST",
                ),
                ModelChoice(
                    "smart",
                    value("DOCWIKI_SMART_MODEL", "smartModel"),
                    value("DOCWIKI_SMART_MODEL_VERSION", "smartModelVersion"),
                    capacity("DOCWIKI_SMART_CAPACITY", "smartCapacity"),
                    "DOCWIKI_SMART",
                ),
                # The embedding deployment is optional (capacity 0 = none, ADR 0014).
                *([embed] if embed.capacity > 0 else []),
            ],
            budget_contacts=[item for item in contacts if item],
        )


# ---------------------------------------------------------------------------
# Pure evaluation helpers (unit-tested without any command)
# ---------------------------------------------------------------------------


def first_line(exc: BaseException, limit: int = 200) -> str:
    """First line of an error, shortened (az errors embed request IDs and long JSON)."""
    text = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
    return text if len(text) <= limit else text[: limit - 3] + "..."


def version_check(
    name: str, found: str | None, minimum: tuple[int, ...], *, required: bool, remediation: str
) -> Check:
    if not found:
        return Check(name, FAIL if required else WARN, "not installed", remediation)
    try:
        version = parse_version(found)
    except ValueError:
        return Check(name, WARN, f"unrecognised version output {found.strip()[:60]!r}")
    wanted = ".".join(str(part) for part in minimum)
    shown = ".".join(str(part) for part in version)
    if version < minimum:
        return Check(name, FAIL if required else WARN, f"{shown} < {wanted}", remediation)
    return Check(name, OK, shown)


def evaluate_region(location: str) -> Check:
    if location in ALLOWED_REGIONS:
        return Check("region", OK, location)
    shown = location or "<unset>"
    return Check(
        "region",
        FAIL,
        f"{shown} is not an allowed region ({', '.join(ALLOWED_REGIONS)})",
        "azd env set AZURE_LOCATION swedencentral   # or eastus2 / westeurope",
    )


def evaluate_providers(providers: Iterable[dict[str, Any]], subscription: str) -> Check:
    states = {str(item.get("namespace", "")).lower(): item.get("state") for item in providers}
    missing = [ns for ns in REQUIRED_PROVIDERS if states.get(ns.lower()) != "Registered"]
    if not missing:
        return Check("resource-providers", OK, f"{len(REQUIRED_PROVIDERS)} registered")
    commands = "; ".join(
        f"az provider register --namespace {ns} --subscription {subscription}" for ns in missing
    )
    return Check("resource-providers", FAIL, "not registered: " + ", ".join(missing), commands)


def _model_entries(models: Iterable[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    entries = []
    for item in models:
        model = item.get("model") or {}
        if model.get("format") == "OpenAI" and model.get("name") == name:
            entries.append(model)
    return entries


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for candidate in (value, value.replace("Z", "+00:00")):
        try:
            return datetime.fromisoformat(candidate).date()
        except ValueError:
            continue
    match = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", value)
    if match:
        month, day, year = (int(group) for group in match.groups())
        return date(year, month, day)
    return None


def evaluate_model(
    models: Sequence[dict[str, Any]], choice: ModelChoice, sku: str, location: str, today: date
) -> Check:
    name = f"model-{choice.tier}"
    entries = _model_entries(models, choice.name)
    if not entries:
        offered = sorted(
            {
                str((item.get("model") or {}).get("name"))
                for item in models
                if (item.get("model") or {}).get("format") == "OpenAI"
                and (item.get("model") or {}).get("lifecycleStatus") == "GenerallyAvailable"
                and any(s.get("name") == sku for s in (item.get("model") or {}).get("skus") or [])
            }
        )
        return Check(
            name,
            FAIL,
            f"{choice.name} is not offered in {location}",
            f"azd env set {choice.env_prefix}_MODEL <model> and {choice.env_prefix}_MODEL_VERSION "
            f"<version>; GA models with {sku} here: {', '.join(offered[:12]) or 'none'}",
        )
    match = next((entry for entry in entries if entry.get("version") == choice.version), None)
    if match is None:
        versions = sorted({str(entry.get("version")) for entry in entries})
        return Check(
            name,
            FAIL,
            f"{choice.name} version {choice.version} is not offered in {location}",
            f"azd env set {choice.env_prefix}_MODEL_VERSION <version>   # offered: "
            + ", ".join(versions),
        )
    skus = {str(item.get("name")): item for item in match.get("skus") or []}
    if sku not in skus:
        return Check(
            name,
            FAIL,
            f"{choice.name} {choice.version} has no {sku} deployment type in {location}",
            "azd env set DOCWIKI_DEPLOYMENT_SKU <type>   # offered: "
            + ", ".join(sorted(s for s in skus if "Standard" in s)),
        )
    lifecycle = str(match.get("lifecycleStatus") or "unknown")
    retires = _parse_date(skus[sku].get("deprecationDate")) or _parse_date(
        (match.get("deprecation") or {}).get("inference")
    )
    detail = f"{choice.name} {choice.version} ({sku}) {lifecycle}"
    if retires:
        detail += f", retires {retires.isoformat()}"
    if lifecycle != "GenerallyAvailable":
        return Check(
            name,
            WARN,
            detail,
            f"Prefer a GenerallyAvailable model: azd env set {choice.env_prefix}_MODEL <model>",
        )
    if retires and retires - today < timedelta(days=DEPRECATION_WARNING_DAYS):
        return Check(
            name,
            WARN,
            detail + " (retirement within 90 days)",
            f"Plan a newer version: azd env set {choice.env_prefix}_MODEL_VERSION <version>",
        )
    return Check(name, OK, detail)


def usage_name(models: Sequence[dict[str, Any]], choice: ModelChoice, sku: str) -> str:
    for entry in _model_entries(models, choice.name):
        if entry.get("version") != choice.version:
            continue
        for item in entry.get("skus") or []:
            if item.get("name") == sku and item.get("usageName"):
                return str(item["usageName"])
    return f"OpenAI.{sku}.{choice.name}"


def evaluate_quota(
    usages: Sequence[dict[str, Any]],
    needs: dict[str, int],
    credits: dict[str, int],
    location: str,
) -> list[Check]:
    by_name = {str((item.get("name") or {}).get("value")): item for item in usages}
    checks: list[Check] = []
    for name, needed in sorted(needs.items()):
        entry = by_name.get(name)
        if entry is None:
            checks.append(
                Check(f"quota:{name}", WARN, f"no quota entry in {location}", QUOTA_REQUEST_URL)
            )
            continue
        limit = int(float(entry.get("limit") or 0))
        current = int(float(entry.get("currentValue") or 0))
        available = limit - current + credits.get(name, 0)
        detail = f"need {needed}, available {available} (limit {limit}, used {current}"
        detail += f", {credits[name]} by this environment)" if credits.get(name) else ")"
        if available < needed:
            checks.append(
                Check(
                    f"quota:{name}",
                    FAIL,
                    detail,
                    "Lower the capacity (azd env set DOCWIKI_FAST_CAPACITY, "
                    "DOCWIKI_SMART_CAPACITY or DOCWIKI_EMBED_CAPACITY "
                    f"<units>), free quota in {location}, or request more at {QUOTA_REQUEST_URL}",
                )
            )
        else:
            checks.append(Check(f"quota:{name}", OK, detail))
    return checks


def evaluate_roles(assignments: Iterable[dict[str, Any]], subscription: str) -> Check:
    """Owner, or Contributor + an access administrator role."""
    names = {str(item.get("roleDefinitionName")) for item in assignments}
    if "Owner" in names:
        return Check("deployer-roles", OK, "Owner")
    admin = names & {"User Access Administrator", "Role Based Access Control Administrator"}
    if "Contributor" in names and admin:
        return Check("deployer-roles", OK, "Contributor + " + sorted(admin)[0])
    shown = ", ".join(sorted(names)) or "none"
    return Check(
        "deployer-roles",
        FAIL,
        f"subscription roles: {shown}",
        "Ask for Owner (or Contributor + User Access Administrator) on subscription "
        f"{subscription}; activate eligible PIM roles first.",
    )


def evaluate_budget_contacts(contacts: Sequence[str]) -> Check:
    if not contacts:
        return Check(
            "budget-contacts",
            WARN,
            "BUDGET_CONTACT_EMAILS is empty: no budget or cost alerts will be created",
            'azd env set BUDGET_CONTACT_EMAILS "<address>[,<address>]"',
        )
    invalid = [item for item in contacts if not EMAIL_PATTERN.match(item)]
    if invalid:
        return Check(
            "budget-contacts",
            FAIL,
            f"{len(invalid)} of {len(contacts)} addresses are not valid e-mail addresses",
            'azd env set BUDGET_CONTACT_EMAILS "<address>[,<address>]"',
        )
    return Check("budget-contacts", OK, f"{len(contacts)} address(es)")


def evaluate_deleted_accounts(
    deleted: Iterable[dict[str, Any]], resource_group: str, location: str, subscription: str
) -> Check:
    conflicts = []
    for item in deleted:
        resource_id = str(item.get("id", ""))
        match = re.search(r"/resourceGroups/([^/]+)/", resource_id, re.I)
        same_rg = bool(match) and match.group(1).lower() == resource_group.lower()
        if same_rg and str(item.get("location", "")).lower() == location.lower():
            conflicts.append(str(item.get("name")))
    if not conflicts:
        return Check("foundry-soft-delete", OK, "no soft-deleted account blocks this environment")
    commands = "; ".join(
        f"az cognitiveservices account purge --location {location} --resource-group "
        f"{resource_group} --name {name} --subscription {subscription}"
        for name in conflicts
    )
    return Check(
        "foundry-soft-delete",
        FAIL,
        f"soft-deleted Foundry account(s) in {resource_group}: {', '.join(conflicts)}",
        commands,
    )


# ---------------------------------------------------------------------------
# Preflight run
# ---------------------------------------------------------------------------


class Preflight:
    def __init__(
        self,
        tools: Tools,
        settings: Settings,
        *,
        skip: Iterable[str] = (),
        today: date | None = None,
    ) -> None:
        self.tools = tools
        self.settings = settings
        self.skip = {item.strip() for item in skip if item.strip()}
        self.today = today or datetime.now(UTC).date()
        self.checks: list[Check] = []
        self.subscription: str | None = None
        self.principal: tuple[str, str] | None = None

    # -- helpers -----------------------------------------------------------------

    def add(self, check: Check) -> Check:
        self.checks.append(check)
        return check

    def skipped(self, name: str) -> bool:
        if name in self.skip:
            self.add(Check(name, SKIP, "skipped on request"))
            return True
        return False

    def tool_output(self, args: Sequence[str]) -> str | None:
        try:
            result = self.tools.run(args, check=False)
        except ToolMissingError:
            return None
        return (result.stdout + "\n" + result.stderr) if result.ok else None

    # -- checks --------------------------------------------------------------------

    def check_local_tools(self) -> None:
        shown = ".".join(str(part) for part in sys.version_info[:3])
        self.add(Check("python", OK, shown))
        try:
            az_data = self.tools.az_json("version", check=False)
        except ToolMissingError:
            az_data = None
        az_version = az_data.get("azure-cli") if isinstance(az_data, dict) else None
        self.add(
            version_check(
                "az",
                az_version,
                MIN_AZ,
                required=True,
                remediation="Install or upgrade the Azure CLI: az upgrade",
            )
        )
        self.add(
            version_check(
                "azd",
                self.tool_output(["azd", "version"]),
                MIN_AZD,
                required=True,
                remediation="Install or upgrade azd (winget upgrade Microsoft.Azd)",
            )
        )
        self.add(
            version_check(
                "bicep",
                self.tool_output(["az", "bicep", "version"]),
                MIN_BICEP,
                required=False,
                remediation="az bicep install   # or: az bicep upgrade",
            )
        )
        self.add(
            version_check(
                "node",
                self.tool_output(["node", "--version"]),
                MIN_NODE,
                required=False,
                remediation="Install Node 22+ (only needed for local site builds)",
            )
        )
        self.add(
            version_check(
                "uv",
                self.tool_output(["uv", "--version"]),
                (0, 4, 0),
                required=False,
                remediation="Install uv (needed to deploy the agents with agents/deploy.py)",
            )
        )

    def check_sign_in(self) -> bool:
        try:
            account = self.tools.account()
        except (HookError, CommandError) as exc:
            self.add(Check("az-login", FAIL, str(exc), "az login   # then: azd auth login"))
            return False
        user = account.get("user") or {}
        self.add(Check("az-login", OK, f"{user.get('type', 'user')} signed in"))
        azd_status = self.tool_output(["azd", "auth", "login", "--check-status"])
        if azd_status is None:
            self.add(Check("azd-login", FAIL, "azd is not signed in", "azd auth login"))
        else:
            self.add(Check("azd-login", OK, "signed in"))
        target = self.settings.subscription_id or str(account.get("id", ""))
        details = self.tools.az_json("account", "show", "--subscription", target, check=False)
        if not isinstance(details, dict):
            self.add(
                Check(
                    "subscription",
                    FAIL,
                    "subscription not accessible with this sign-in",
                    "az account list --output table; then azd env set AZURE_SUBSCRIPTION_ID <id>",
                )
            )
            return False
        if details.get("state") != "Enabled":
            self.add(
                Check(
                    "subscription",
                    FAIL,
                    f"state is {details.get('state')}",
                    "Use an enabled subscription (azd env set AZURE_SUBSCRIPTION_ID <id>)",
                )
            )
            return False
        source = "AZURE_SUBSCRIPTION_ID" if self.settings.subscription_id else "az default"
        note = ""
        if self.settings.subscription_id and account.get("id") != self.settings.subscription_id:
            note = "; differs from the az default, hooks pass --subscription explicitly"
        self.add(Check("subscription", OK, f"enabled ({source}{note})"))
        self.subscription = target
        return True

    def check_region(self) -> None:
        self.add(evaluate_region(self.settings.location))

    def check_providers(self) -> None:
        if self.skipped("resource-providers") or not self.subscription:
            return
        data = self.tools.az_json(
            "provider",
            "list",
            "--subscription",
            self.subscription,
            "--query",
            "[].{namespace:namespace, state:registrationState}",
            check=False,
        )
        if not isinstance(data, list):
            self.add(Check("resource-providers", WARN, "could not list resource providers"))
            return
        self.add(evaluate_providers(data, self.subscription))

    def check_models_and_quota(self) -> None:
        if self.settings.location not in ALLOWED_REGIONS or not self.subscription:
            return
        location = self.settings.location
        sku = self.settings.deployment_sku
        models = self.tools.az_json(
            "cognitiveservices",
            "model",
            "list",
            "--location",
            location,
            "--subscription",
            self.subscription,
            check=False,
        )
        if not isinstance(models, list):
            self.add(
                Check(
                    "models",
                    FAIL,
                    f"could not list models in {location}",
                    "az provider register --namespace Microsoft.CognitiveServices",
                )
            )
            return
        for choice in self.settings.models:
            self.add(evaluate_model(models, choice, sku, location, self.today))
        if self.skipped("quota"):
            return
        needs: dict[str, int] = {}
        for choice in self.settings.models:
            key = usage_name(models, choice, sku)
            needs[key] = needs.get(key, 0) + choice.capacity
        usages = self.tools.az_json(
            "cognitiveservices",
            "usage",
            "list",
            "--location",
            location,
            "--subscription",
            self.subscription,
            check=False,
        )
        if not isinstance(usages, list):
            self.add(Check("quota", WARN, "could not read model quota", QUOTA_REQUEST_URL))
            return
        for check in evaluate_quota(usages, needs, self.existing_deployment_credit(), location):
            self.add(check)

    def existing_deployment_credit(self) -> dict[str, int]:
        """Capacity already held by this environment's deployments (re-provision)."""
        account, group = self.settings.foundry_account, self.settings.resource_group
        if not (account and group and self.subscription):
            return {}
        data = self.tools.az_json(
            "cognitiveservices",
            "account",
            "deployment",
            "list",
            "--name",
            account,
            "--resource-group",
            group,
            "--subscription",
            self.subscription,
            check=False,
        )
        credit: dict[str, int] = {}
        for item in data if isinstance(data, list) else []:
            sku = item.get("sku") or {}
            model = ((item.get("properties") or {}).get("model") or {}).get("name")
            if model and sku.get("name"):
                key = f"OpenAI.{sku['name']}.{model}"
                credit[key] = credit.get(key, 0) + int(sku.get("capacity") or 0)
        return credit

    def check_deployer_roles(self) -> None:
        if self.skipped("roles") or not self.subscription:
            return
        try:
            self.principal = self.tools.signed_in_object_id()
        except (HookError, CommandError) as exc:
            self.add(
                Check(
                    "deployer-roles",
                    WARN,
                    f"could not resolve the signed-in principal: {first_line(exc)}",
                    SIGN_IN_AGAIN,
                )
            )
            return
        object_id = self.principal[0]
        scope = f"/subscriptions/{self.subscription}"
        base = [
            "role",
            "assignment",
            "list",
            "--assignee",
            object_id,
            "--scope",
            scope,
            "--include-inherited",
        ]
        data = self.tools.az_json(*base, "--include-groups", check=False)
        if not isinstance(data, list):
            data = self.tools.az_json(*base, check=False)
        if not isinstance(data, list):
            self.add(
                Check("deployer-roles", WARN, "could not list role assignments", SIGN_IN_AGAIN)
            )
            return
        self.add(evaluate_roles(data, self.subscription))

    def check_entra(self) -> None:
        if self.skipped("entra"):
            return
        principal = self.principal
        if principal is None:
            try:
                principal = self.tools.signed_in_object_id()
            except (HookError, CommandError):
                principal = ("", "User")
        if principal[1] == "ServicePrincipal":
            self.add(
                Check(
                    "entra-app-registration",
                    WARN,
                    "signed in as a service principal: it needs Application.ReadWrite.OwnedBy",
                    "Grant the Graph application permission Application.ReadWrite.OwnedBy",
                )
            )
            return
        try:
            roles = self.tools.rest(
                "GET",
                "https://graph.microsoft.com/v1.0/me/memberOf/microsoft.graph.directoryRole"
                "?$select=displayName",
            )
            names = {str(item.get("displayName")) for item in (roles or {}).get("value", [])}
            if names & APP_REGISTRATION_ROLES:
                self.add(
                    Check("entra-app-registration", OK, sorted(names & APP_REGISTRATION_ROLES)[0])
                )
                return
            policy = self.tools.rest(
                "GET", "https://graph.microsoft.com/v1.0/policies/authorizationPolicy"
            )
        except CommandError as exc:
            self.add(
                Check(
                    "entra-app-registration",
                    WARN,
                    f"could not verify with Microsoft Graph: {first_line(exc)}",
                    SIGN_IN_AGAIN,
                )
            )
            return
        except HookError as exc:
            # Microsoft Graph refused the cached CLI token (continuous access evaluation, spike
            # F9): the postprovision hook would fail after the resources are created.
            self.add(
                Check(
                    "entra-app-registration",
                    FAIL,
                    f"Microsoft Graph: {first_line(exc)}",
                    SIGN_IN_AGAIN,
                )
            )
            return
        permissions = (policy or {}).get("defaultUserRolePermissions") or {}
        if permissions.get("allowedToCreateApps"):
            self.add(Check("entra-app-registration", OK, "tenant lets users register applications"))
            return
        self.add(
            Check(
                "entra-app-registration",
                FAIL,
                "no Application Developer role and users may not register applications",
                "Ask a tenant administrator for the Entra Application Developer role.",
            )
        )

    def check_budget(self) -> None:
        self.add(evaluate_budget_contacts(self.settings.budget_contacts))

    def check_soft_deleted_foundry(self) -> None:
        group = self.settings.resource_group
        if self.skipped("foundry-soft-delete") or not (self.subscription and group):
            return
        if self.settings.foundry_account:
            live = self.tools.az_json(
                "cognitiveservices",
                "account",
                "show",
                "--name",
                self.settings.foundry_account,
                "--resource-group",
                group,
                "--subscription",
                self.subscription,
                check=False,
            )
            if isinstance(live, dict):
                self.add(Check("foundry-soft-delete", OK, "Foundry account exists"))
                return
        deleted = self.tools.az_json(
            "cognitiveservices",
            "account",
            "list-deleted",
            "--subscription",
            self.subscription,
            check=False,
        )
        if not isinstance(deleted, list):
            self.add(Check("foundry-soft-delete", WARN, "could not list soft-deleted accounts"))
            return
        self.add(
            evaluate_deleted_accounts(deleted, group, self.settings.location, self.subscription)
        )

    def run(self) -> list[Check]:
        self.check_local_tools()
        self.check_region()
        if self.check_sign_in():
            self.check_providers()
            self.check_models_and_quota()
            self.check_deployer_roles()
            self.check_entra()
            self.check_soft_deleted_foundry()
        self.check_budget()
        return self.checks


def render(checks: Sequence[Check]) -> str:
    lines = []
    for check in checks:
        lines.append(f"{_LABEL[check.status]} {check.name}: {check.detail}")
        if check.remediation and check.status in (WARN, FAIL):
            lines.append(f"       fix: {check.remediation}")
    failed = sum(check.status == FAIL for check in checks)
    warned = sum(check.status == WARN for check in checks)
    lines.append(f"preflight: {failed} failed, {warned} warning(s), {len(checks)} checks")
    return "\n".join(lines)


def exit_code(checks: Sequence[Check], *, strict: bool) -> int:
    if any(check.status == FAIL for check in checks):
        return 1
    if strict and any(check.status == WARN for check in checks):
        return 1
    return 0


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--env", help="azd environment name (default: AZURE_ENV_NAME or default env)"
    )
    parser.add_argument("--json", action="store_true", help="print machine-readable results")
    parser.add_argument("--strict", action="store_true", help="fail on warnings too")
    parser.add_argument(
        "--skip",
        default="",
        help="comma-separated checks to skip: resource-providers, quota, roles, entra, "
        "foundry-soft-delete",
    )
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    *,
    runner: Runner | None = None,
    environ: dict[str, str] | None = None,
    root: Path = REPO_ROOT,
    today: date | None = None,
    output: Callable[[str], None] = print,
) -> int:
    args = parse_args(argv)
    tools = tools_from_environment(environ, root=root, runner=runner, env_name=args.env)
    skip = [*args.skip.split(","), *tools.get("DOCWIKI_PREFLIGHT_SKIP").split(",")]
    try:
        settings = Settings.from_tools(
            tools, bicep_parameter_defaults(root / "infra" / "main.bicep")
        )
    except HookError as exc:
        output(f"[FAIL] settings: {exc}")
        return 1
    checks = Preflight(tools, settings, skip=skip, today=today).run()
    if args.json:
        output(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        output(render(checks))
    return exit_code(checks, strict=args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
