"""azure.yaml: services, remote builds and hooks exist and point at real files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from infra_testkit import REPO_ROOT

SERVICES = {
    "job": "docker/job.Dockerfile",
    "mcp": "docker/mcp.Dockerfile",
    "portal": "docker/portal.Dockerfile",
}
HOOKS = ("preprovision", "postprovision", "postdeploy", "predown", "postdown")


@pytest.fixture(scope="module")
def azure_yaml() -> dict[str, Any]:
    return yaml.safe_load((REPO_ROOT / "azure.yaml").read_text(encoding="utf-8"))


def test_project_and_infra(azure_yaml: dict[str, Any]) -> None:
    assert azure_yaml["name"] == "docwiki"
    infra = azure_yaml["infra"]
    assert infra["provider"] == "bicep"
    assert (REPO_ROOT / infra["path"] / f"{infra['module']}.bicep").is_file()
    assert (REPO_ROOT / infra["path"] / f"{infra['module']}.parameters.json").is_file()


def test_required_azd_version_supports_container_app_jobs(azure_yaml: dict[str, Any]) -> None:
    constraint = azure_yaml["requiredVersions"]["azd"]
    match = re.fullmatch(r">=\s*(\d+)\.(\d+)\.(\d+)", constraint)
    assert match, constraint
    assert tuple(int(part) for part in match.groups()) >= (1, 23, 8)


def test_down_deletes_agents_before_and_entra_after(azure_yaml: dict[str, Any]) -> None:
    """ADR 0003: agents (and their identities) go before the resource group."""
    hooks = azure_yaml["hooks"]
    assert hooks["predown"]["posix"]["run"].endswith("teardown.py --agents-only --yes")
    assert hooks["postdown"]["posix"]["run"].endswith("teardown.py --entra-only --yes")


@pytest.mark.parametrize(("service", "dockerfile"), sorted(SERVICES.items()))
def test_services_build_remotely(azure_yaml: dict[str, Any], service: str, dockerfile: str) -> None:
    config = azure_yaml["services"][service]
    assert config["host"] == "containerapp"
    assert config["language"] == "docker"
    docker = config["docker"]
    assert docker["remoteBuild"] is True
    assert docker["path"] == dockerfile
    assert docker["context"] == "."
    project = REPO_ROOT / config["project"]
    assert (project / dockerfile).is_file()
    ignore = (project / f"{dockerfile}.dockerignore").read_text(encoding="utf-8").splitlines()
    rules = [line.strip() for line in ignore if line.strip() and not line.startswith("#")]
    assert rules[0] == "*", "the build context must be an allowlist"
    assert "!src" in rules and "!pyproject.toml" in rules


def test_services_match_bicep_tags(azure_yaml: dict[str, Any]) -> None:
    bicep = (REPO_ROOT / "infra" / "main.bicep").read_text(encoding="utf-8")
    tagged = set(re.findall(r"'azd-service-name': '([a-z-]+)'", bicep))
    assert tagged == set(azure_yaml["services"])


@pytest.mark.parametrize("hook", HOOKS)
def test_hooks_are_cross_platform_and_exist(azure_yaml: dict[str, Any], hook: str) -> None:
    config = azure_yaml["hooks"][hook]
    assert set(config) == {"windows", "posix"}
    assert config["windows"]["shell"] == "pwsh"
    assert config["posix"]["shell"] == "sh"
    for platform in ("windows", "posix"):
        command = config[platform]["run"].split()
        assert command[0] in {"python", "python3"}
        script = REPO_ROOT / Path(command[1])
        assert script.is_file(), script
        assert config[platform]["continueOnError"] is False
    assert config["windows"]["run"].split()[1:] == config["posix"]["run"].split()[1:]


def test_hooks_never_persist_the_foundry_user_agent() -> None:
    text = (REPO_ROOT / "azure.yaml").read_text(encoding="utf-8")
    assert "AZURE_DEV_USER_AGENT" not in text
