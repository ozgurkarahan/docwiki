"""scripts/teardown.py: confirmation, plan and deletions (fake az)."""

from __future__ import annotations

import json
from pathlib import Path

import azdlib
import pytest
import teardown
from azdlib import Result
from infra_testkit import FakeRunner, not_found

ENV = "demo"
PROJECT = "https://aif-tok.services.ai.azure.com/api/projects/docwiki"


def environ() -> dict[str, str]:
    return {
        "AZURE_ENV_NAME": ENV,
        "AZURE_SUBSCRIPTION_ID": "sub-test",
        "AZURE_RESOURCE_GROUP": "rg-demo",
        "AZURE_LOCATION": "swedencentral",
        "DOCWIKI_FOUNDRY_ACCOUNT_NAME": "aif-tok",
    }


@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    path = azdlib.state_path(ENV, tmp_path)
    azdlib.save_state(
        path,
        {
            "mcp_api": {
                "object_id": "obj-1",
                "display_name": "docwiki-mcp-api-demo",
                "created_by_hook": True,
            },
            "portal_app": {
                "object_id": "obj-2",
                "display_name": "pre-existing",
                "created_by_hook": False,
            },
            "agents": {
                key: {
                    "agent_name": f"docwiki-{key}",
                    "principal_id": f"{key}-id",
                    "project_endpoint": PROJECT,
                }
                for key in ("researcher", "librarian")
            },
            "app_role_assignments": [{"agent": "researcher", "role": "Wiki.Read"}],
        },
    )
    return path


def azure(runner: FakeRunner) -> FakeRunner:
    runner.on(r"DELETE .*/agents/docwiki-", None)
    runner.on(r"^az group exists", "true")
    runner.on(r"^az group delete", None)
    runner.on(r"^az cognitiveservices account purge", None)
    runner.on(r"DELETE .*/applications/obj-1", None)
    runner.on(r"DELETE .*/directory/deletedItems/obj-1", None)
    return runner


def test_requires_confirmation_when_not_interactive(
    runner: FakeRunner, tmp_path: Path, state_file: Path
) -> None:
    code = teardown.main([], runner=azure(runner), environ=environ(), root=tmp_path)
    assert code == 2
    assert not runner.calls


def test_wrong_confirmation_cancels(runner: FakeRunner, tmp_path: Path, state_file: Path) -> None:
    code = teardown.main(
        [], runner=azure(runner), environ=environ(), root=tmp_path, ask=lambda _: "other"
    )
    assert code == 2
    assert not runner.calls


def test_dry_run_changes_nothing(runner: FakeRunner, tmp_path: Path, state_file: Path) -> None:
    assert teardown.main(["--dry-run"], runner=runner, environ=environ(), root=tmp_path) == 0
    assert not runner.calls


def test_full_teardown(runner: FakeRunner, tmp_path: Path, state_file: Path) -> None:
    code = teardown.main(
        [], runner=azure(runner), environ=environ(), root=tmp_path, ask=lambda _: ENV
    )
    assert code == 0
    commands = [" ".join(call) for call in runner.calls]
    group_delete = next(
        i
        for i, line in enumerate(commands)
        if line.startswith("az group delete --name rg-demo --subscription sub-test --yes")
    )
    agents = [i for i, line in enumerate(commands) if "/agents/docwiki-" in line]
    assert len(agents) == 2 and max(agents) < group_delete, "agents before the resource group"
    researcher = f"--url {PROJECT}/agents/docwiki-researcher?api-version=v1"
    assert any(researcher in commands[i] for i in agents)
    assert all("--resource https://ai.azure.com" in commands[i] for i in agents)
    assert runner.commands(
        r"account purge --location swedencentral --resource-group rg-demo "
        r"--name aif-tok"
    )
    assert runner.commands(r"DELETE .*/applications/obj-1")
    assert runner.commands(r"DELETE .*/directory/deletedItems/obj-1"), "purged"
    assert not runner.commands(r"obj-2"), "registrations not created by the hooks are kept"
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["mcp_api"]["deleted_at"]
    assert "deleted_at" not in state["portal_app"]
    assert all(agent["deleted_at"] for agent in state["agents"].values())
    assert state["app_role_assignments"] == []


def test_agents_only_for_azd_predown(runner: FakeRunner, tmp_path: Path, state_file: Path) -> None:
    code = teardown.main(
        ["--agents-only", "--yes"], runner=azure(runner), environ=environ(), root=tmp_path
    )
    assert code == 0
    assert len(runner.commands(r"DELETE .*/agents/docwiki-")) == 2
    assert not runner.commands(r"group delete|account purge|applications|deletedItems")


def test_entra_only_for_azd_down(runner: FakeRunner, tmp_path: Path, state_file: Path) -> None:
    code = teardown.main(
        ["--entra-only", "--yes"], runner=azure(runner), environ=environ(), root=tmp_path
    )
    assert code == 0
    assert not runner.commands(r"group delete|account purge|/agents/")
    assert runner.commands(r"DELETE .*/applications/obj-1")


def test_blocked_foundry_account_is_reported_after_the_entra_cleanup(
    runner: FakeRunner, tmp_path: Path, state_file: Path
) -> None:
    blocked = Result(
        1, "", "ERROR: (CannotDeleteDefaultProject) can only be deleted with the account"
    )
    runner.on(r"^az group delete", blocked)
    code = teardown.main(["--yes"], runner=azure(runner), environ=environ(), root=tmp_path)
    assert code == 1
    assert not runner.commands(r"account purge"), "nothing to purge while the account exists"
    assert runner.commands(r"DELETE .*/applications/obj-1"), "Entra cleanup still done"


def test_agent_deletion_failure_does_not_stop_the_teardown(
    runner: FakeRunner, tmp_path: Path, state_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runner.on(r"DELETE .*/agents/docwiki-", Result(1, "", "ERROR: connection refused"))
    code = teardown.main(["--yes"], runner=azure(runner), environ=environ(), root=tmp_path)
    assert code == 0
    assert runner.commands(r"^az group delete")
    assert "could not delete agent docwiki-researcher" in capsys.readouterr().out


def test_missing_group_and_deleted_registration_are_tolerated(
    runner: FakeRunner, tmp_path: Path, state_file: Path
) -> None:
    runner.on(r"DELETE .*/agents/", not_found())
    runner.on(r"^az group exists", "false")
    runner.on(r"^az cognitiveservices account purge", not_found())
    runner.on(r"DELETE .*/applications/obj-1", not_found())
    runner.on(r"DELETE .*/directory/deletedItems/obj-1", not_found())
    code = teardown.main(["--yes"], runner=runner, environ=environ(), root=tmp_path)
    assert code == 0
    assert not runner.commands(r"group delete")
    assert runner.commands(r"account purge"), "a soft-deleted account is purged after azd down"


def test_second_run_has_nothing_left_to_delete(
    runner: FakeRunner, tmp_path: Path, state_file: Path
) -> None:
    assert (
        teardown.main(
            ["--entra-only", "--yes"], runner=azure(runner), environ=environ(), root=tmp_path
        )
        == 0
    )
    again = FakeRunner()
    assert (
        teardown.main(["--entra-only", "--yes"], runner=again, environ=environ(), root=tmp_path)
        == 0
    )
    assert not again.calls


def with_studio(state_file: Path, *, created_by_hook: bool = True) -> None:
    """The sign-in registration of the standalone Studio (removed in v1.6, ADR 0009), as an
    older postprovision hook recorded it: teardown still deletes it."""
    state = azdlib.load_state(state_file)
    state["studio_app"] = {
        "object_id": "obj-3",
        "display_name": "docwiki-studio-demo",
        "created_by_hook": created_by_hook,
    }
    azdlib.save_state(state_file, state)


def test_studio_registration_is_deleted_like_the_portal_one(
    runner: FakeRunner, tmp_path: Path, state_file: Path
) -> None:
    assert "studio_app" in teardown.ENTRA_KEYS
    with_studio(state_file)
    azure(runner).on(r"DELETE .*/applications/obj-3", None).on(
        r"DELETE .*/directory/deletedItems/obj-3", None
    )
    code = teardown.main(["--entra-only", "--yes"], runner=runner, environ=environ(), root=tmp_path)
    assert code == 0
    assert runner.commands(r"DELETE .*/applications/obj-3")
    assert runner.commands(r"DELETE .*/directory/deletedItems/obj-3"), "purged"
    assert runner.commands(r"DELETE .*/applications/obj-1"), "the MCP API one goes too"
    assert not runner.commands(r"obj-2"), "a registration the hooks did not create is kept"
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["studio_app"]["deleted_at"]
    again = FakeRunner()
    teardown.main(["--entra-only", "--yes"], runner=again, environ=environ(), root=tmp_path)
    assert not again.calls, "deleted once"


def test_studio_registration_that_pre_existed_is_kept(
    runner: FakeRunner, tmp_path: Path, state_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with_studio(state_file, created_by_hook=False)
    code = teardown.main(
        ["--entra-only", "--yes"], runner=azure(runner), environ=environ(), root=tmp_path
    )
    assert code == 0
    assert not runner.commands(r"obj-3")
    assert "studio_app: docwiki-studio-demo was not created by the hooks; kept" in (
        capsys.readouterr().out
    )


def test_dry_run_lists_the_studio_registration(
    runner: FakeRunner, tmp_path: Path, state_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with_studio(state_file)
    assert teardown.main(["--dry-run"], runner=runner, environ=environ(), root=tmp_path) == 0
    assert "delete app registration (studio_app): docwiki-studio-demo (then purge)" in (
        capsys.readouterr().out
    )
    assert not runner.calls
