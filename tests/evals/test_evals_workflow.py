"""The live evaluation workflow stays manual, credential-free and private-safe."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml


@pytest.fixture(scope="module")
def workflow_text(repo_root: Path) -> str:
    return (repo_root / ".github" / "workflows" / "evals.yml").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def workflow(workflow_text: str) -> dict[Any, Any]:
    return yaml.safe_load(workflow_text)


def test_manual_trigger_only(workflow: dict[Any, Any]) -> None:
    triggers = workflow.get("on", workflow.get(True))
    assert list(triggers) == ["workflow_dispatch"]
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert set(inputs["system"]["options"]) == {
        "all",
        "docwiki-researcher",
        "baseline-rag",
        "baseline-long-context",
    }


def test_linux_least_privilege_and_no_active_login(
    workflow: dict[Any, Any], workflow_text: str
) -> None:
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["evaluate"]
    assert job["runs-on"] == "ubuntu-latest"
    uses = [step.get("uses", "") for step in job["steps"]]
    assert not any(action.startswith("azure/login") for action in uses)
    assert "#   uses: azure/login@v2" in workflow_text
    assert "# id-token: write" in workflow_text
    installs = [step["run"] for step in job["steps"] if "uv sync" in step.get("run", "")]
    assert installs and "--extra evals" in installs[0]


def test_settings_come_from_secrets_and_variables(workflow: dict[Any, Any]) -> None:
    env = workflow["jobs"]["evaluate"]["env"]
    assert (
        env["DOCWIKI_FOUNDRY_PROJECT_ENDPOINT"] == "${{ secrets.DOCWIKI_FOUNDRY_PROJECT_ENDPOINT }}"
    )
    assert env["DOCWIKI_SMART_DEPLOYMENT"] == "${{ vars.DOCWIKI_SMART_DEPLOYMENT }}"


def test_inputs_never_expand_inside_scripts(workflow: dict[Any, Any]) -> None:
    for step in workflow["jobs"]["evaluate"]["steps"]:
        assert not re.search(r"\$\{\{\s*(inputs|github\.event)\.", step.get("run", "")), step


def test_only_public_outputs_are_uploaded(workflow: dict[Any, Any]) -> None:
    steps = workflow["jobs"]["evaluate"]["steps"]
    upload = next(
        step for step in steps if step.get("uses", "").startswith("actions/upload-artifact")
    )
    paths = upload["with"]["path"].split()
    assert paths == ["evals/results/", "evals/SCOREBOARD.md"]
    assert not any("RUNNER_TEMP" in path or "private" in path for path in paths)
    run = next(step["run"] for step in steps if "evals/run.py" in step.get("run", ""))
    assert '--private-out "$RUNNER_TEMP/private"' in run
