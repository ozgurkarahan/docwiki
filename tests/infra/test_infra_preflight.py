"""scripts/preflight.py: evaluation rules and an end-to-end run with a fake az/azd."""

from __future__ import annotations

import base64
import json
from datetime import date
from pathlib import Path
from typing import Any

import preflight
import pytest
from azdlib import Result, bicep_parameter_defaults
from infra_testkit import REPO_ROOT, FakeRunner
from preflight import FAIL, OK, WARN, ModelChoice

TODAY = date(2026, 10, 17)
SUBSCRIPTION = "sub-test"


def model_entry(
    name: str,
    version: str,
    skus: tuple[str, ...] = ("GlobalStandard", "DataZoneStandard"),
    lifecycle: str = "GenerallyAvailable",
    retires: str = "2027-09-21T02:00:00+02:00",
) -> dict[str, Any]:
    return {
        "kind": "OpenAI",
        "model": {
            "format": "OpenAI",
            "name": name,
            "version": version,
            "lifecycleStatus": lifecycle,
            "skus": [
                {"name": sku, "usageName": f"OpenAI.{sku}.{name}", "deprecationDate": retires}
                for sku in skus
            ],
        },
    }


MODELS = [
    model_entry("gpt-5.4-mini", "2026-03-17"),
    model_entry("gpt-5.5", "2026-04-24", retires="2027-10-26T02:00:00+02:00"),
    model_entry("gpt-5.5", "2026-04-24"),  # the CLI lists some models twice
    model_entry("gpt-4o-mini", "2024-07-18", lifecycle="Deprecating"),
    model_entry("gpt-5-pro", "2025-10-06", skus=("GlobalStandard",)),
]


def fast(
    name: str = "gpt-5.4-mini", version: str = "2026-03-17", capacity: int = 100
) -> ModelChoice:
    return ModelChoice("fast", name, version, capacity, "DOCWIKI_FAST")


def usage(name: str, current: int, limit: int) -> dict[str, Any]:
    return {"name": {"value": name}, "currentValue": current, "limit": limit, "unit": "Count"}


# ---------------------------------------------------------------------------
# Pure rules
# ---------------------------------------------------------------------------


def test_region_rule() -> None:
    assert preflight.evaluate_region("swedencentral").status == OK
    check = preflight.evaluate_region("northeurope")
    assert check.status == FAIL
    assert "azd env set AZURE_LOCATION" in (check.remediation or "")


def test_version_rule() -> None:
    assert (
        preflight.version_check(
            "azd", "azd version 1.28.1 (commit x)", (1, 23, 8), required=True, remediation="r"
        ).status
        == OK
    )
    assert (
        preflight.version_check(
            "azd", "azd version 1.20.0", (1, 23, 8), required=True, remediation="r"
        ).status
        == FAIL
    )
    assert (
        preflight.version_check(
            "node", "v20.1.0", (22, 0, 0), required=False, remediation="r"
        ).status
        == WARN
    )
    assert (
        preflight.version_check("uv", None, (0, 4, 0), required=False, remediation="r").status
        == WARN
    )


def test_model_available_and_ga() -> None:
    check = preflight.evaluate_model(MODELS, fast(), "DataZoneStandard", "swedencentral", TODAY)
    assert check.status == OK
    assert "retires 2027-09-21" in check.detail


def test_model_version_missing_lists_offered_versions() -> None:
    check = preflight.evaluate_model(
        MODELS, fast(version="2025-01-01"), "DataZoneStandard", "swedencentral", TODAY
    )
    assert check.status == FAIL
    assert "2026-03-17" in (check.remediation or "")
    assert "DOCWIKI_FAST_MODEL_VERSION" in (check.remediation or "")


def test_model_without_the_deployment_type_is_not_switched_silently() -> None:
    check = preflight.evaluate_model(
        MODELS, fast("gpt-5-pro", "2025-10-06"), "DataZoneStandard", "swedencentral", TODAY
    )
    assert check.status == FAIL
    assert "DOCWIKI_DEPLOYMENT_SKU" in (check.remediation or "")
    assert "GlobalStandard" in (check.remediation or "")


def test_unknown_model_lists_alternatives() -> None:
    check = preflight.evaluate_model(
        MODELS, fast("gpt-0", "1"), "DataZoneStandard", "swedencentral", TODAY
    )
    assert check.status == FAIL
    assert "gpt-5.4-mini" in (check.remediation or "")
    assert "gpt-4o-mini" not in (check.remediation or ""), "only GA models are suggested"


def test_deprecating_or_retiring_models_warn() -> None:
    check = preflight.evaluate_model(
        MODELS, fast("gpt-4o-mini", "2024-07-18"), "DataZoneStandard", "swedencentral", TODAY
    )
    assert check.status == WARN
    soon = [model_entry("gpt-5.4-mini", "2026-03-17", retires="2026-11-01T00:00:00Z")]
    check = preflight.evaluate_model(soon, fast(), "DataZoneStandard", "swedencentral", TODAY)
    assert check.status == WARN
    assert "90 days" in check.detail


def test_quota_rules() -> None:
    needs = {"OpenAI.DataZoneStandard.gpt-5.5": 100}
    enough = preflight.evaluate_quota(
        [usage("OpenAI.DataZoneStandard.gpt-5.5", 0, 333)], needs, {}, "swedencentral"
    )
    assert [check.status for check in enough] == [OK]
    short = preflight.evaluate_quota(
        [usage("OpenAI.DataZoneStandard.gpt-5.5", 300, 333)], needs, {}, "swedencentral"
    )
    assert short[0].status == FAIL
    assert "DOCWIKI_SMART_CAPACITY" in (short[0].remediation or "")
    credited = preflight.evaluate_quota(
        [usage("OpenAI.DataZoneStandard.gpt-5.5", 300, 333)],
        needs,
        {"OpenAI.DataZoneStandard.gpt-5.5": 100},
        "swedencentral",
    )
    assert credited[0].status == OK, "capacity held by this environment is re-usable"
    missing = preflight.evaluate_quota([], needs, {}, "swedencentral")
    assert missing[0].status == WARN


def test_usage_name_comes_from_the_model_list() -> None:
    assert preflight.usage_name(MODELS, fast(), "DataZoneStandard") == (
        "OpenAI.DataZoneStandard.gpt-5.4-mini"
    )


def test_role_rules() -> None:
    def roles(*names: str) -> list[dict[str, str]]:
        return [{"roleDefinitionName": name} for name in names]

    assert preflight.evaluate_roles(roles("Owner"), SUBSCRIPTION).status == OK
    assert preflight.evaluate_roles(roles("Contributor"), SUBSCRIPTION).status == FAIL
    assert (
        preflight.evaluate_roles(
            roles("Contributor", "User Access Administrator"), SUBSCRIPTION
        ).status
        == OK
    )
    assert (
        preflight.evaluate_roles(
            roles("Contributor", "Role Based Access Control Administrator"), SUBSCRIPTION
        ).status
        == OK
    )
    assert preflight.evaluate_roles([], SUBSCRIPTION).status == FAIL


def test_budget_contacts_are_never_echoed() -> None:
    address = "budget-alerts" + "@" + "example.org"
    assert preflight.evaluate_budget_contacts([]).status == WARN
    ok = preflight.evaluate_budget_contacts([address])
    assert ok.status == OK and address not in ok.detail
    bad = preflight.evaluate_budget_contacts(["not-an-address"])
    assert bad.status == FAIL and "not-an-address" not in bad.detail


def test_soft_deleted_account_in_the_same_group_blocks() -> None:
    deleted = [
        {
            "name": "aif-abc",
            "location": "swedencentral",
            "id": "/subscriptions/x/providers/Microsoft.CognitiveServices/locations/swedencentral"
            "/resourceGroups/rg-demo/deletedAccounts/aif-abc",
        }
    ]
    check = preflight.evaluate_deleted_accounts(deleted, "rg-demo", "swedencentral", SUBSCRIPTION)
    assert check.status == FAIL
    assert "az cognitiveservices account purge" in (check.remediation or "")
    other = preflight.evaluate_deleted_accounts(deleted, "rg-other", "swedencentral", SUBSCRIPTION)
    assert other.status == OK


def test_settings_default_to_the_bicep_parameters() -> None:
    defaults = bicep_parameter_defaults(REPO_ROOT / "infra" / "main.bicep")
    assert defaults["fastModel"] == "gpt-5.4-mini"
    assert defaults["smartModel"] == "gpt-5.5"
    assert defaults["location"] == "swedencentral"
    assert defaults["deploymentSku"] == "GlobalStandard"
    assert "budgetStartDate" not in defaults, "expressions are not literal defaults"


# ---------------------------------------------------------------------------
# End-to-end with a fake az / azd
# ---------------------------------------------------------------------------


def fake_token(claims: dict[str, str]) -> str:
    def part(data: dict[str, str]) -> str:
        raw = json.dumps(data).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    return ".".join([part({"alg": "none"}), part(claims), "signature"])


def healthy(runner: FakeRunner, *, roles: tuple[str, ...] = ("Owner",)) -> FakeRunner:
    account = {"id": SUBSCRIPTION, "name": "Test", "state": "Enabled", "user": {"type": "user"}}
    runner.on(r"^az version", {"azure-cli": "2.86.0"})
    runner.on(r"^azd version", "azd version 1.28.1 (commit abc)")
    runner.on(r"^az bicep version", Result(0, "", "Bicep CLI version 0.40.2 (abc)"))
    runner.on(r"^node --version", "v22.12.0")
    runner.on(r"^uv --version", "uv 0.11.2")
    runner.on(r"^azd auth login --check-status", "Logged in to Azure")
    runner.on(r"^az account show", account)
    runner.on(r"^az account get-access-token", {"accessToken": fake_token({"oid": "oid-1"})})
    providers = [{"namespace": ns, "state": "Registered"} for ns in preflight.REQUIRED_PROVIDERS]
    runner.on(r"^az provider list", providers)
    runner.on(r"^az cognitiveservices model list", MODELS)
    runner.on(
        r"^az cognitiveservices usage list",
        [
            usage("OpenAI.GlobalStandard.gpt-5.4-mini", 0, 1000),
            usage("OpenAI.GlobalStandard.gpt-5.5", 0, 1000),
            usage("OpenAI.DataZoneStandard.gpt-5.4-mini", 0, 1000),
            usage("OpenAI.DataZoneStandard.gpt-5.5", 0, 333),
        ],
    )
    runner.on(r"^az role assignment list", [{"roleDefinitionName": role} for role in roles])
    runner.on(r"memberOf/microsoft.graph.directoryRole", {"value": []})
    runner.on(
        r"policies/authorizationPolicy",
        {"defaultUserRolePermissions": {"allowedToCreateApps": True}},
    )
    runner.on(r"^az cognitiveservices account list-deleted", [])
    return runner


def environ(**extra: str) -> dict[str, str]:
    values = {
        "AZURE_ENV_NAME": "demo",
        "AZURE_SUBSCRIPTION_ID": SUBSCRIPTION,
        "AZURE_LOCATION": "swedencentral",
        "BUDGET_CONTACT_EMAILS": "budget-alerts" + "@" + "example.org",
    }
    values.update(extra)
    return values


def run(runner: FakeRunner, tmp_path: Path, *args: str, **env: str) -> tuple[int, str]:
    lines: list[str] = []
    root = tmp_path / "repo"
    (root / "infra").mkdir(parents=True, exist_ok=True)
    (root / "infra" / "main.bicep").write_text(
        (REPO_ROOT / "infra" / "main.bicep").read_text(encoding="utf-8"), encoding="utf-8"
    )
    code = preflight.main(
        list(args),
        runner=runner,
        environ=environ(**env),
        root=root,
        today=TODAY,
        output=lines.append,
    )
    return code, "\n".join(lines)


def test_healthy_environment_passes(runner: FakeRunner, tmp_path: Path) -> None:
    code, text = run(healthy(runner), tmp_path)
    assert code == 0, text
    assert "0 failed" in text
    assert runner.commands(r"--subscription sub-test"), "every az call targets the subscription"
    assert not runner.commands(
        r"^az (?!version|bicep|account|provider|cognitiveservices|role|rest)"
    )


def test_json_output_and_quota_capacity(runner: FakeRunner, tmp_path: Path) -> None:
    code, text = run(
        healthy(runner),
        tmp_path,
        "--json",
        DOCWIKI_SMART_CAPACITY="400",
        DOCWIKI_DEPLOYMENT_SKU="DataZoneStandard",
    )
    assert code == 1
    checks = {item["name"]: item for item in json.loads(text)}
    assert checks["quota:OpenAI.DataZoneStandard.gpt-5.5"]["status"] == FAIL
    assert checks["model-smart"]["status"] == OK


def test_disallowed_region_fails_without_model_lookup(runner: FakeRunner, tmp_path: Path) -> None:
    code, text = run(healthy(runner), tmp_path, AZURE_LOCATION="northeurope")
    assert code == 1
    assert "[FAIL] region" in text
    assert not runner.commands(r"cognitiveservices model list")


def test_insufficient_roles_fail(runner: FakeRunner, tmp_path: Path) -> None:
    code, text = run(healthy(runner, roles=("Contributor",)), tmp_path)
    assert code == 1
    assert "[FAIL] deployer-roles" in text


def test_strict_mode_fails_on_warnings(runner: FakeRunner, tmp_path: Path) -> None:
    code, _ = run(healthy(runner), tmp_path, "--strict", BUDGET_CONTACT_EMAILS="")
    assert code == 1
    code, _ = run(healthy(FakeRunner()), tmp_path, BUDGET_CONTACT_EMAILS="")
    assert code == 0


def test_skipped_checks_are_reported(runner: FakeRunner, tmp_path: Path) -> None:
    code, text = run(healthy(runner), tmp_path, "--skip", "roles,entra")
    assert code == 0
    assert "[SKIP] roles" in text and "[SKIP] entra" in text
    assert not runner.commands(r"role assignment list")


def test_not_signed_in(tmp_path: Path) -> None:
    runner = FakeRunner()
    runner.on(r"^az version", {"azure-cli": "2.86.0"})
    runner.on(r"^azd version", "azd version 1.28.1")
    runner.on(r"^az bicep version", "Bicep CLI version 0.40.2")
    runner.on(r"^node --version", "v22.12.0")
    runner.on(r"^uv --version", "uv 0.11.2")
    runner.on(r"^az account show", Result(1, "", "Please run 'az login' to setup account."))
    code, text = run(runner, tmp_path)
    assert code == 1
    assert "[FAIL] az-login" in text and "az login" in text


def test_graph_requiring_a_fresh_sign_in_fails_instead_of_crashing(
    runner: FakeRunner, tmp_path: Path
) -> None:
    refused = Result(
        1,
        "",
        "ERROR: Unauthorized: Continuous access evaluation resulted in challenge with result: "
        "InteractionRequired and code: TokenCreatedWithOutdatedPolicies",
    )
    runner.on(r"memberOf/microsoft.graph.directoryRole", refused)  # first matching rule wins
    code, text = run(healthy(runner), tmp_path)
    assert code == 1
    assert "[FAIL] entra-app-registration" in text
    assert "az logout" in text
    assert "foundry-soft-delete" in text, "the remaining checks still run"


def test_secrets_never_reach_the_output(runner: FakeRunner, tmp_path: Path) -> None:
    code, text = run(healthy(runner), tmp_path, "--json")
    assert code == 0
    assert "accessToken" not in text and "signature" not in text
    assert "example.org" not in text


@pytest.mark.parametrize("value", ["abc", "1.5"])
def test_invalid_capacity_is_reported(runner: FakeRunner, tmp_path: Path, value: str) -> None:
    code, text = run(healthy(runner), tmp_path, DOCWIKI_FAST_CAPACITY=value)
    assert code == 1
    assert "DOCWIKI_FAST_CAPACITY" in text
