"""agents/deploy.py: payloads (both MCP auth strategies), dry run, idempotency, routine flag."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from agents_testkit import (
    AGENTS_DIR,
    CONNECTION,
    DEPLOY_ENV,
    MCP_URL,
    FakeProject,
    agent_version,
    connection,
    copy_agents,
    edit_file,
    http_error,
)
from azure.ai.projects.models import (
    AgentDetails,
    AgentVersionDetails,
    InvokeAgentResponsesApiRoutineAction,
    MCPTool,
    MCPToolRequireApproval,
    PromptAgentDefinition,
    Routine,
    ScheduleRoutineTrigger,
)

from docwiki import __version__
from docwiki.agents_client.definitions import (
    APPROVAL_REQUIRED_TOOLS,
    READ_TOOLS,
    load_agent,
    load_agents,
    load_routines,
)
from docwiki.agents_client.deploy import (
    McpBinding,
    build_agent_payload,
    build_routine_body,
    definition_hash,
    deploy_agent,
    main,
    verify_connection,
)
from docwiki.agents_client.errors import AgentConfigurationError

STRATEGIES = ["per-agent-identity", "project-managed-identity"]


def _agents_with_strategy(tmp_path: Path, strategy: str) -> Path:
    root = copy_agents(tmp_path)
    if strategy != "per-agent-identity":
        for key in ("researcher", "librarian"):
            path = root / key / "agent.yaml"
            edit_file(path, "strategy: per-agent-identity", f"strategy: {strategy}")
    return root


def _run(capsys: pytest.CaptureFixture[str], *argv: str, **kwargs: Any) -> tuple[int, str, str]:
    code = main(list(argv), **kwargs)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# ---------------------------------------------------------------------- payloads


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_researcher_payload_for_each_auth_strategy(tmp_path: Path, strategy: str) -> None:
    agent = load_agent(_agents_with_strategy(tmp_path, strategy) / "researcher")
    payload = build_agent_payload(agent, DEPLOY_ENV)
    assert payload.agent_name == "docwiki-researcher"
    assert payload.missing_env == ()
    assert payload.body == {
        "definition": {
            "kind": "prompt",
            "model": "smart-deployment",
            "instructions": agent.instructions,
            "tools": [
                {
                    "type": "mcp",
                    "server_label": "docwiki",
                    "server_url": MCP_URL,
                    "allowed_tools": list(READ_TOOLS),
                    "require_approval": {"never": {"tool_names": list(READ_TOOLS)}},
                    "project_connection_id": CONNECTION,
                }
            ],
        },
        "description": agent.definition.description,
        "metadata": {
            "docwiki_agent": "researcher",
            "docwiki_spec": "mcp-and-agents.md section 2",
            "docwiki_mcp_auth": strategy,
            "docwiki_mcp_roles": "Wiki.Read",
            "docwiki_definition_sha256": payload.definition_sha256,
            "docwiki_version": __version__,
        },
    }
    assert payload.bindings == (
        McpBinding(
            server_label="docwiki",
            server_url=MCP_URL,
            connection=CONNECTION,
            strategy=strategy,
            server_url_env="DOCWIKI_MCP_URL",
            connection_env="DOCWIKI_MCP_CONNECTION",
        ),
    )
    assert definition_hash(payload.agent_name, payload.body) == payload.definition_sha256


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_librarian_payload_requires_approval_for_mutations(tmp_path: Path, strategy: str) -> None:
    agent = load_agent(_agents_with_strategy(tmp_path, strategy) / "librarian")
    payload = build_agent_payload(agent, DEPLOY_ENV)
    (tool,) = payload.body["definition"]["tools"]
    assert tool["require_approval"]["always"] == {"tool_names": list(APPROVAL_REQUIRED_TOOLS)}
    assert set(tool["require_approval"]["never"]["tool_names"]) == set(tool["allowed_tools"]) - set(
        APPROVAL_REQUIRED_TOOLS
    )
    assert payload.body["metadata"]["docwiki_mcp_roles"] == "Wiki.Operate Wiki.Read"
    assert payload.body["metadata"]["docwiki_mcp_auth"] == strategy


def test_payload_matches_the_azure_ai_projects_models() -> None:
    for agent in load_agents(AGENTS_DIR).values():
        body = build_agent_payload(agent, DEPLOY_ENV).body
        definition = PromptAgentDefinition(body["definition"])
        assert definition.kind == "prompt"
        assert definition.model == "smart-deployment"
        (tool,) = definition.tools
        assert isinstance(tool, MCPTool)
        assert (tool.server_label, tool.server_url) == ("docwiki", MCP_URL)
        assert tool.project_connection_id == CONNECTION
        assert tool.allowed_tools == list(agent.definition.allowed_tools)
        assert isinstance(tool.require_approval, MCPToolRequireApproval)
        assert tool.require_approval.never.tool_names
        assert definition.as_dict() == body["definition"]


def test_definition_hash_tracks_the_resolved_definition(tmp_path: Path) -> None:
    root = copy_agents(tmp_path)
    agent = load_agent(root / "researcher")
    base = build_agent_payload(agent, DEPLOY_ENV).definition_sha256
    assert build_agent_payload(agent, dict(DEPLOY_ENV)).definition_sha256 == base
    for name, value in [
        ("DOCWIKI_SMART_DEPLOYMENT", "other-deployment"),
        ("DOCWIKI_MCP_URL", "https://other-mcp.example/mcp"),
        ("DOCWIKI_MCP_CONNECTION", "other-connection"),
    ]:
        assert build_agent_payload(agent, {**DEPLOY_ENV, name: value}).definition_sha256 != base
    instructions = root / "researcher" / "instructions.md"
    text = instructions.read_text(encoding="utf-8")
    instructions.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    assert (
        build_agent_payload(load_agent(root / "researcher"), DEPLOY_ENV).definition_sha256 == base
    )
    instructions.write_text(text + "\nOne more rule.\n", encoding="utf-8")
    assert (
        build_agent_payload(load_agent(root / "researcher"), DEPLOY_ENV).definition_sha256 != base
    )


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("DOCWIKI_SMART_DEPLOYMENT", "", "DOCWIKI_SMART_DEPLOYMENT is not set"),
        ("DOCWIKI_MCP_URL", "", "DOCWIKI_MCP_URL is not set"),
        ("DOCWIKI_MCP_CONNECTION", "  ", "DOCWIKI_MCP_CONNECTION is not set"),
        ("DOCWIKI_MCP_URL", "http://docwiki-mcp.example/mcp", "must be an https URL"),
        ("DOCWIKI_MCP_URL", "https://docwiki-mcp.example/mcp?code=x", "must not contain"),
    ],
)
def test_payload_needs_valid_environment(name: str, value: str, message: str) -> None:
    agent = load_agent(AGENTS_DIR / "researcher")
    with pytest.raises(AgentConfigurationError, match=message):
        build_agent_payload(agent, {**DEPLOY_ENV, name: value})


def test_routine_body_matches_the_azure_ai_projects_models() -> None:
    agents = load_agents(AGENTS_DIR)
    (routine,) = load_routines(agents, AGENTS_DIR)
    body = build_routine_body(routine, enabled=False)
    model = Routine({"name": routine.name, **body})
    assert model.enabled is False
    trigger = model.triggers["schedule"]
    assert isinstance(trigger, ScheduleRoutineTrigger)
    assert (trigger.cron_expression, trigger.time_zone) == ("0 6 * * *", "UTC")
    assert isinstance(model.action, InvokeAgentResponsesApiRoutineAction)
    assert model.action.agent_name == "docwiki-librarian"
    assert model.action.input == routine.definition.input
    assert body["authorization"] == {"identity": "agent"}
    assert build_routine_body(routine, enabled=True)["enabled"] is True


# ---------------------------------------------------------------------- dry run


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_dry_run_prints_the_exact_payloads(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], strategy: str
) -> None:
    root = _agents_with_strategy(tmp_path, strategy)
    code, out, err = _run(capsys, "--dry-run", "--agents-dir", str(root), env=DEPLOY_ENV)
    assert code == 0 and err == ""
    plan = json.loads(out)
    assert plan["dry_run"] is True and plan["missing_env"] == [] and plan["routines"] == []
    agents = load_agents(root)
    expected = {
        build_agent_payload(agent, DEPLOY_ENV).agent_name: build_agent_payload(agent, DEPLOY_ENV)
        for agent in agents.values()
    }
    assert {item["agent"] for item in plan["agents"]} == set(expected)
    for item in plan["agents"]:
        payload = expected[item["agent"]]
        assert item["operation"] == "agents.create_version"
        assert item["http"] == f"POST /agents/{payload.agent_name}/versions?api-version=v1"
        assert item["body"] == payload.body
        assert item["definition_sha256"] == payload.definition_sha256
        assert item["body"]["metadata"]["docwiki_mcp_auth"] == strategy


def test_dry_run_without_environment_uses_placeholders(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = _run(
        capsys, "--dry-run", "--agent", "researcher", "--routine", "enable", env={}
    )
    assert code == 0
    plan = json.loads(out)
    assert plan["missing_env"] == [
        "DOCWIKI_FOUNDRY_PROJECT_ENDPOINT",
        "DOCWIKI_SMART_DEPLOYMENT",
        "DOCWIKI_MCP_URL",
        "DOCWIKI_MCP_CONNECTION",
    ]
    (agent,) = plan["agents"]
    assert agent["body"]["definition"]["model"] == "${DOCWIKI_SMART_DEPLOYMENT}"
    assert agent["body"]["definition"]["tools"][0]["server_url"] == "${DOCWIKI_MCP_URL}"
    (routine,) = plan["routines"]
    assert routine["http"] == "PUT /routines/docwiki-librarian-daily-health?api-version=v1"
    assert routine["headers"] == {"Foundry-Features": "Routines=V2Preview"}
    assert routine["body"]["enabled"] is True
    assert "warning: unset environment variables" in err


def test_deploy_script_runs_as_a_file() -> None:
    env = {key: value for key, value in os.environ.items() if not key.startswith("DOCWIKI_")}
    env.update(DEPLOY_ENV)
    result = subprocess.run(
        [sys.executable, str(AGENTS_DIR / "deploy.py"), "--dry-run", "--agent", "researcher"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    assert [item["agent"] for item in plan["agents"]] == ["docwiki-researcher"]
    assert plan["agents"][0]["body"]["definition"]["instructions"].startswith(
        "# DocWiki Researcher"
    )


# ---------------------------------------------------------------------- deployment


def test_deploy_creates_a_version_only_when_the_definition_changes(tmp_path: Path) -> None:
    root = copy_agents(tmp_path)
    project = FakeProject()
    payload = build_agent_payload(load_agent(root / "researcher"), DEPLOY_ENV)

    first = asyncio.run(deploy_agent(project, payload))
    assert (first.status, first.version, first.previous_version) == ("created", "1", None)
    assert first.identity_principal_id == "principal-docwiki-researcher"
    assert first.identity_client_id == "client-docwiki-researcher"
    assert project.agents.created == [("docwiki-researcher", payload.body)]

    again = asyncio.run(deploy_agent(project, payload))
    assert (again.status, again.version) == ("unchanged", "1")
    assert (again.identity_principal_id, again.identity_client_id) == (
        "principal-docwiki-researcher",
        "client-docwiki-researcher",
    )
    assert len(project.agents.created) == 1

    edit_file(root / "researcher" / "instructions.md", "Be concise.", "Be brief.")
    changed = build_agent_payload(load_agent(root / "researcher"), DEPLOY_ENV)
    third = asyncio.run(deploy_agent(project, changed))
    assert (third.status, third.version, third.previous_version) == ("created", "2", "1")


def test_deploy_reads_real_sdk_models() -> None:
    payload = build_agent_payload(load_agent(AGENTS_DIR / "researcher"), DEPLOY_ENV)
    project = FakeProject()
    latest = agent_version("4", payload.definition_sha256)
    identity = {"principal_id": "agent-oid", "client_id": "agent-appid", "status": "active"}

    async def get(agent_name: str) -> AgentDetails:
        return AgentDetails(
            {
                "object": "agent",
                "id": "a",
                "name": agent_name,
                "versions": {"latest": latest},
                "instance_identity": identity,
            }
        )

    async def create_version(agent_name: str, body: dict[str, Any]) -> AgentVersionDetails:
        return AgentVersionDetails({**agent_version("5"), "metadata": body["metadata"]})

    project.agents.get = get  # type: ignore[method-assign]
    project.agents.create_version = create_version  # type: ignore[method-assign]
    unchanged = asyncio.run(deploy_agent(project, payload))
    assert unchanged.status == "unchanged"
    assert (unchanged.identity_principal_id, unchanged.identity_client_id) == (
        "agent-oid",
        "agent-appid",
    )
    latest["metadata"] = {"docwiki_definition_sha256": "older"}
    created = asyncio.run(deploy_agent(project, payload))
    assert (created.status, created.version, created.previous_version) == ("created", "5", "4")
    # The new version carries no identity: it is read from the agent object (ADR 0003).
    assert (created.identity_principal_id, created.identity_client_id) == (
        "agent-oid",
        "agent-appid",
    )


def test_identity_of_a_new_agent_comes_from_the_agent_object() -> None:
    project = FakeProject()
    project.agents.version_identity = False
    payload = build_agent_payload(load_agent(AGENTS_DIR / "librarian"), DEPLOY_ENV)
    result = asyncio.run(deploy_agent(project, payload))
    assert result.status == "created"
    assert (result.identity_principal_id, result.identity_client_id) == (
        "principal-docwiki-librarian",
        "client-docwiki-librarian",
    )
    assert project.agents.get_calls == ["docwiki-librarian", "docwiki-librarian"]


def test_main_deploys_both_agents_idempotently(capsys: pytest.CaptureFixture[str]) -> None:
    project = FakeProject()
    code, out, err = _run(capsys, env=DEPLOY_ENV, project_client=project)
    assert code == 0, err
    assert "docwiki-librarian: created version 1;" in out
    assert "docwiki-researcher: created version 1;" in out
    assert (
        "agent identity: principal principal-docwiki-researcher, client client-docwiki-researcher"
        in out
    )
    assert project.connections.calls == [CONNECTION, CONNECTION]
    assert project.beta.routines.calls == []

    code, out, _ = _run(capsys, "--json", env=DEPLOY_ENV, project_client=project)
    assert code == 0
    results = json.loads(out)
    assert [item["status"] for item in results["agents"]] == ["unchanged", "unchanged"]
    assert results["routines"] == []
    assert len(project.agents.created) == 2


def test_json_output_reports_agent_identities_for_the_infra_hook(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, out, err = _run(capsys, "--json", env=DEPLOY_ENV, project_client=FakeProject())
    assert code == 0, err
    agents = {item["key"]: item for item in json.loads(out)["agents"]}
    assert sorted(agents) == ["librarian", "researcher"]
    for key, item in agents.items():
        assert item["status"] == "created"
        assert item["agent_name"] == f"docwiki-{key}"
        assert item["identity_principal_id"] == f"principal-docwiki-{key}"
        assert item["identity_client_id"] == f"client-docwiki-{key}"


@pytest.mark.parametrize(("flag", "enabled"), [("enable", True), ("disable", False)])
def test_main_routine_flag(capsys: pytest.CaptureFixture[str], flag: str, enabled: bool) -> None:
    project = FakeProject()
    code, out, err = _run(capsys, "--routine", flag, env=DEPLOY_ENV, project_client=project)
    assert code == 0, err
    ((name, body),) = project.beta.routines.calls
    assert name == "docwiki-librarian-daily-health"
    assert body["enabled"] is enabled
    assert body["action"]["agent_name"] == "docwiki-librarian"
    state = "enabled" if enabled else "disabled"
    assert f"routine docwiki-librarian-daily-health: {state}" in out


def test_main_selects_agents_and_skips_connection_checks(
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = FakeProject(connections={})
    code, _, err = _run(
        capsys,
        "--agent",
        "researcher",
        "--skip-connection-check",
        env=DEPLOY_ENV,
        project_client=project,
    )
    assert code == 0, err
    assert [name for name, _ in project.agents.created] == ["docwiki-researcher"]
    assert project.connections.calls == []


@pytest.mark.parametrize(
    ("argv", "env", "message"),
    [
        (["--agent", "auditor"], DEPLOY_ENV, "unknown agent 'auditor'"),
        ([], {k: v for k, v in DEPLOY_ENV.items() if k != "DOCWIKI_MCP_URL"}, "DOCWIKI_MCP_URL"),
    ],
)
def test_main_returns_2_on_invalid_input(
    capsys: pytest.CaptureFixture[str], argv: list[str], env: dict[str, str], message: str
) -> None:
    project = FakeProject()
    code, _, err = _run(capsys, *argv, env=env, project_client=project)
    assert code == 2
    assert message in err
    assert project.agents.created == []


def test_main_requires_the_project_endpoint(capsys: pytest.CaptureFixture[str]) -> None:
    env = {k: v for k, v in DEPLOY_ENV.items() if k != "DOCWIKI_FOUNDRY_PROJECT_ENDPOINT"}
    code, _, err = _run(capsys, env=env)
    assert code == 2
    assert "DOCWIKI_FOUNDRY_PROJECT_ENDPOINT is not set" in err


def test_main_returns_1_on_azure_errors(capsys: pytest.CaptureFixture[str]) -> None:
    project = FakeProject()
    project.agents.create_error = http_error(403, "forbidden")
    code, _, err = _run(capsys, "--agent", "researcher", env=DEPLOY_ENV, project_client=project)
    assert code == 1
    assert "docwiki-researcher: HTTP 403: forbidden" in err


# ---------------------------------------------------------------------- MCP connection checks


def _binding(strategy: str) -> McpBinding:
    return McpBinding(
        server_label="docwiki",
        server_url=MCP_URL,
        connection=CONNECTION,
        strategy=strategy,
        server_url_env="DOCWIKI_MCP_URL",
        connection_env="DOCWIKI_MCP_CONNECTION",
    )


@pytest.mark.parametrize(
    ("strategy", "auth_type"),
    [
        ("per-agent-identity", "AgenticIdentityToken_Preview"),
        ("per-agent-identity", "AgenticIdentityToken"),
        ("project-managed-identity", "ProjectManagedIdentity"),
        ("project-managed-identity", "AAD"),
    ],
)
def test_connection_matches_the_strategy(strategy: str, auth_type: str) -> None:
    target = MCP_URL + "/"
    project = FakeProject(connections={CONNECTION: connection(auth_type=auth_type, target=target)})
    asyncio.run(verify_connection(project, _binding(strategy)))


@pytest.mark.parametrize(
    ("strategy", "auth_type"),
    [
        ("per-agent-identity", "AAD"),
        ("per-agent-identity", "ApiKey"),
        ("project-managed-identity", "AgenticIdentityToken_Preview"),
        ("project-managed-identity", "CustomKeys"),
        ("project-managed-identity", "None"),
    ],
)
def test_connection_with_another_auth_type_is_rejected(strategy: str, auth_type: str) -> None:
    project = FakeProject(connections={CONNECTION: connection(auth_type=auth_type)})
    with pytest.raises(AgentConfigurationError, match=f"the {strategy} strategy needs a"):
        asyncio.run(verify_connection(project, _binding(strategy)))


def test_connection_target_and_existence_are_checked() -> None:
    other = FakeProject(connections={CONNECTION: connection(target="https://other.example/mcp")})
    with pytest.raises(AgentConfigurationError, match="must be the same endpoint"):
        asyncio.run(verify_connection(other, _binding("per-agent-identity")))
    missing = FakeProject(connections={})
    with pytest.raises(AgentConfigurationError, match="does not exist"):
        asyncio.run(verify_connection(missing, _binding("per-agent-identity")))


def test_reasoning_effort_is_optional_and_part_of_the_hash(tmp_path: Path) -> None:
    root = copy_agents(tmp_path)
    default = build_agent_payload(load_agent(root / "researcher"), DEPLOY_ENV)
    path = root / "researcher" / "agent.yaml"
    edit_file(path, "instructions_file:", "reasoning_effort: low\ninstructions_file:")
    low = build_agent_payload(load_agent(root / "researcher"), DEPLOY_ENV)
    assert "reasoning" not in default.body["definition"]
    assert low.body["definition"]["reasoning"] == {"effort": "low"}
    assert low.definition_sha256 != default.definition_sha256
