#!/usr/bin/env python3
"""Delete a DocWiki environment: agents, resource group, Foundry account, app registrations.

    python scripts/teardown.py [--env NAME] [--yes] [--dry-run]
                               [--entra-only | --keep-entra | --agents-only] [--no-purge]

Order (ADR 0003, docs/spikes/identity-spike.md section 9):

* Deletes the Foundry agents recorded in ``.azure/<env>/docwiki-state.json`` first: deleting an
  agent deletes its Entra agent identity and blueprint, which a resource group deletion leaves
  behind. ``azd down`` runs ``--agents-only --yes`` as its ``predown`` hook.
* Deletes the resource group ``AZURE_RESOURCE_GROUP`` (every Azure resource, role assignment
  and Event Grid subscription of the environment). Known issue F13: the Foundry account can stay
  blocked by its default project; the script reports it and can be re-run later.
* Purges the soft-deleted Foundry account so that the environment can be redeployed under
  the same name (``--no-purge`` keeps it recoverable for 48 hours).
* Deletes the Entra app registrations recorded as created by the hooks (their service
  principals and app role assignments go with them) and purges them from the deleted items
  (``--no-purge`` keeps them restorable for 30 days). Registrations that existed before the
  hooks ran are never deleted.

Without ``--yes`` the script asks to type the environment name; non-interactive runs must
pass ``--yes``. ``azd down`` runs ``--entra-only --yes`` as its ``postdown`` hook.
"""

from __future__ import annotations

import sys

if sys.version_info < (3, 12):  # noqa: UP036 - must run (and explain) on older interpreters
    major, minor = sys.version_info[:2]
    sys.stderr.write(f"[docwiki] ERROR: Python 3.12+ is required (found {major}.{minor}).\n")
    raise SystemExit(1)

import argparse
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "hooks"))

import entra
from azdlib import (
    GRAPH,
    REPO_ROOT,
    CommandError,
    HookError,
    Runner,
    Tools,
    error,
    info,
    is_not_found,
    load_state,
    save_state,
    state_path,
    tools_from_environment,
    utc_now,
    warn,
)

# "studio_app": the sign-in registration of the standalone Studio, removed in v1.6 (ADR 0009).
# Nothing creates it any more; an older docwiki-state.json may still record it.
ENTRA_KEYS = ("mcp_api", "portal_app", "studio_app")
# Foundry data plane (project endpoint): token audience and API version of the agents API.
FOUNDRY_DATA_PLANE = "https://ai.azure.com"
AGENTS_API = "v1"
# Spike finding F13: the default project blocks the account deletion.
FOUNDRY_BLOCKED = re.compile(
    r"CannotDeleteDefaultProject|nested resources exist|CannotDeleteResource", re.IGNORECASE
)


class FoundryAccountBlocked(HookError):
    """The resource group deletion stopped at the Foundry account (spike finding F13)."""


@dataclass
class Plan:
    env_name: str
    subscription: str | None
    resource_group: str | None
    location: str | None
    foundry_account: str | None
    agents: list[tuple[str, dict[str, str]]]
    applications: list[tuple[str, dict[str, str]]]
    delete_group: bool
    purge: bool

    def describe(self) -> list[str]:
        lines = [f"environment: {self.env_name}"]
        for key, agent in self.agents:
            lines.append(f"delete agent ({key}): {agent.get('agent_name')}")
        if self.delete_group:
            lines.append(f"delete resource group: {self.resource_group or '<unknown>'}")
        if self.delete_group and self.purge and self.foundry_account:
            lines.append(f"purge soft-deleted Foundry account: {self.foundry_account}")
        for key, app in self.applications:
            purge = " (then purge)" if self.purge else ""
            lines.append(f"delete app registration ({key}): {app.get('display_name')}{purge}")
        if len(lines) == 1:
            lines.append("nothing to delete")
        return lines


def recorded_agents(state: Mapping[str, object]) -> list[tuple[str, dict[str, str]]]:
    agents = state.get("agents")
    if not isinstance(agents, dict):
        return []
    return [
        (str(key), {k: str(v) for k, v in entry.items() if v is not None})
        for key, entry in agents.items()
        if isinstance(entry, dict)
        and entry.get("agent_name")
        and entry.get("project_endpoint")
        and not entry.get("deleted_at")
    ]


def build_plan(tools: Tools, state: Mapping[str, object], args: argparse.Namespace) -> Plan:
    applications: list[tuple[str, dict[str, str]]] = []
    if not (args.keep_entra or args.agents_only):
        for key in ENTRA_KEYS:
            entry = state.get(key)
            if not isinstance(entry, dict) or entry.get("deleted_at"):
                continue
            if entry.get("created_by_hook") and entry.get("object_id"):
                applications.append((key, {k: str(v) for k, v in entry.items()}))
            elif entry.get("object_id"):
                warn(f"{key}: {entry.get('display_name')} was not created by the hooks; kept")
    return Plan(
        env_name=tools.env_name,
        subscription=tools.get("AZURE_SUBSCRIPTION_ID") or None,
        resource_group=tools.get("AZURE_RESOURCE_GROUP") or None,
        location=tools.get("AZURE_LOCATION") or None,
        foundry_account=tools.get("DOCWIKI_FOUNDRY_ACCOUNT_NAME") or None,
        agents=[] if args.entra_only else recorded_agents(state),
        applications=applications,
        delete_group=not (args.entra_only or args.agents_only),
        purge=not args.no_purge,
    )


def confirm(plan: Plan, *, assume_yes: bool, ask: Callable[[str], str] | None) -> bool:
    if assume_yes:
        return True
    if ask is None:
        if not sys.stdin.isatty():
            error("refusing to delete without confirmation", "Re-run with --yes.")
            return False
        ask = input
    answer = ask(f"Type the environment name ({plan.env_name}) to confirm: ")
    return answer.strip() == plan.env_name


def delete_agents(tools: Tools, plan: Plan, state: dict[str, object], path: Path) -> None:
    """Delete the recorded agents (and with them their Entra agent identities)."""
    agents = state.get("agents")
    for key, agent in plan.agents:
        name = agent["agent_name"]
        url = f"{agent['project_endpoint'].rstrip('/')}/agents/{name}?api-version={AGENTS_API}"
        info(f"deleting agent {name} (its Entra agent identity and blueprint go with it)")
        try:
            tools.rest("DELETE", url, resource=FOUNDRY_DATA_PLANE, allow_not_found=True)
        except CommandError as exc:
            warn(
                f"could not delete agent {name}: {str(exc)[:200]}. Delete it in the Foundry "
                "portal (Agents) before the resource group, or its agent identity stays in Entra."
            )
            continue
        if isinstance(agents, dict) and isinstance(agents.get(key), dict):
            agents[key]["deleted_at"] = utc_now()
            save_state(path, state)


def delete_resource_group(tools: Tools, plan: Plan) -> None:
    if not (plan.subscription and plan.resource_group):
        raise HookError(
            "AZURE_SUBSCRIPTION_ID / AZURE_RESOURCE_GROUP unknown for this environment",
            "Run `azd env refresh`, or delete the resource group in the portal.",
        )
    exists = tools.az(
        "group", "exists", "--name", plan.resource_group, "--subscription", plan.subscription
    )
    if exists.stdout.strip().lower() != "true":
        info(f"resource group {plan.resource_group} does not exist")
        return
    info(f"deleting resource group {plan.resource_group} (this takes several minutes)")
    args = [
        "group", "delete", "--name", plan.resource_group,
        "--subscription", plan.subscription, "--yes",
    ]  # fmt: skip
    result = tools.az(*args, check=False)
    if result.ok:
        return
    if FOUNDRY_BLOCKED.search(f"{result.stderr}\n{result.stdout}"):
        raise FoundryAccountBlocked(
            f"resource group {plan.resource_group} was not fully deleted: the Foundry account "
            f"{plan.foundry_account or ''} is blocked by its default project (known issue F13 in "
            "docs/spikes/identity-spike.md)",
            "Everything else is deleted and the empty account has no idle cost. Re-run "
            "`python scripts/teardown.py --yes` later; if it keeps failing, open an Azure "
            "support request for the Foundry account.",
        )
    raise CommandError(["az", *args], result)


def purge_application(tools: Tools, object_id: str, display_name: str) -> None:
    """Remove a deleted app registration from the Entra deleted items (best effort)."""
    try:
        tools.rest("DELETE", f"{GRAPH}/directory/deletedItems/{object_id}")
    except CommandError as exc:
        if is_not_found(exc.result):
            info(f"{display_name} is not in the deleted items yet; Entra purges it after 30 days")
        else:
            warn(f"could not purge {display_name}: {str(exc)[:200]}")
        return
    info(f"purged {display_name} from the deleted items")


def purge_foundry_account(tools: Tools, plan: Plan) -> None:
    if not (plan.foundry_account and plan.location and plan.resource_group and plan.subscription):
        return
    info(f"purging soft-deleted Foundry account {plan.foundry_account}")
    result = tools.az(
        "cognitiveservices", "account", "purge",
        "--location", plan.location,
        "--resource-group", plan.resource_group,
        "--name", plan.foundry_account,
        "--subscription", plan.subscription,
        check=False,
    )  # fmt: skip
    if not result.ok:
        warn(f"purge skipped: {(result.stderr or result.stdout).strip()[:200]}")


def main(
    argv: Sequence[str] | None = None,
    *,
    runner: Runner | None = None,
    environ: Mapping[str, str] | None = None,
    root: Path = REPO_ROOT,
    ask: Callable[[str], str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(description="Delete a DocWiki environment")
    parser.add_argument("--env", help="azd environment name (default: AZURE_ENV_NAME or default)")
    parser.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    parser.add_argument("--dry-run", action="store_true", help="print the plan only")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--entra-only", action="store_true", help="only the app registrations")
    scope.add_argument("--keep-entra", action="store_true", help="keep the app registrations")
    scope.add_argument("--agents-only", action="store_true", help="only the Foundry agents")
    parser.add_argument(
        "--no-purge",
        action="store_true",
        help="keep the Foundry account and app registrations recoverable (no purge)",
    )
    args = parser.parse_args(argv)

    tools = tools_from_environment(environ, root=root, runner=runner, env_name=args.env)
    try:
        path = state_path(tools.env_name, root)
        state = load_state(path)
        plan = build_plan(tools, state, args)
        for line in plan.describe():
            info(line)
        if args.dry_run:
            return 0
        if not confirm(plan, assume_yes=args.yes, ask=ask):
            error("cancelled")
            return 2
        if plan.agents:
            delete_agents(tools, plan, state, path)
        blocked: FoundryAccountBlocked | None = None
        if plan.delete_group:
            try:
                delete_resource_group(tools, plan)
            except FoundryAccountBlocked as exc:
                blocked = exc  # finish the Entra cleanup, then report it
            else:
                if plan.purge:
                    purge_foundry_account(tools, plan)
        for key, app in plan.applications:
            info(f"deleting app registration {app.get('display_name')}")
            entra.delete_application(tools, app["object_id"])
            entry = dict(state.get(key) or {})
            entry["deleted_at"] = utc_now()
            state[key] = entry
            save_state(path, state)
            if plan.purge:
                purge_application(tools, app["object_id"], str(app.get("display_name")))
        if plan.applications:
            state["app_role_assignments"] = []
            save_state(path, state)
        if blocked is not None:
            raise blocked
    except HookError as exc:
        error(str(exc), exc.remediation)
        return 1
    info("teardown complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
