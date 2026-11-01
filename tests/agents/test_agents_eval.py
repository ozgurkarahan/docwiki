"""agents/deploy.py --eval: the evaluation Researcher equals production except name and MCP."""

from __future__ import annotations

import json
from typing import Any

import pytest
from agents_testkit import CONNECTION, DEPLOY_ENV, FakeProject, connection

from docwiki.agents_client.definitions import load_agents
from docwiki.agents_client.deploy import (
    build_agent_payload,
    definition_hash,
    eval_agent,
    eval_env_name,
    main,
)
from docwiki.agents_client.errors import AgentConfigurationError

EVAL_MCP_URL = "https://docwiki-mcp-eval.example/mcp"
EVAL_CONNECTION = "docwiki-mcp-eval"
EVAL_ENV: dict[str, str] = {
    **DEPLOY_ENV,
    "DOCWIKI_EVAL_MCP_URL": EVAL_MCP_URL,
    "DOCWIKI_EVAL_MCP_CONNECTION": EVAL_CONNECTION,
}


def _run(capsys: pytest.CaptureFixture[str], *argv: str, **kwargs: Any) -> tuple[int, str, str]:
    code = main(list(argv), **kwargs)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _project() -> FakeProject:
    return FakeProject(
        connections={
            CONNECTION: connection(),
            EVAL_CONNECTION: {**connection(target=EVAL_MCP_URL), "name": EVAL_CONNECTION},
        }
    )


def test_eval_env_names() -> None:
    assert eval_env_name("DOCWIKI_MCP_URL") == "DOCWIKI_EVAL_MCP_URL"
    assert eval_env_name("DOCWIKI_MCP_CONNECTION") == "DOCWIKI_EVAL_MCP_CONNECTION"


@pytest.mark.parametrize("key", ["researcher", "librarian"])
def test_eval_definition_differs_only_by_name_and_mcp_variables(key: str) -> None:
    agent = load_agents()[key]
    variant = eval_agent(agent)
    assert variant.key == agent.key
    assert variant.instructions == agent.instructions
    assert variant.name == f"docwiki-{key}-eval"
    prod, evaluated = agent.definition.model_dump(), variant.definition.model_dump()
    assert evaluated.pop("name") == f"docwiki-{key}-eval"
    prod.pop("name")
    for prod_tool, eval_tool in zip(prod["tools"], evaluated["tools"], strict=True):
        assert eval_tool.pop("server_url_env") == "DOCWIKI_EVAL_MCP_URL"
        assert prod_tool.pop("server_url_env") == "DOCWIKI_MCP_URL"
        assert eval_tool["auth"].pop("connection_env") == "DOCWIKI_EVAL_MCP_CONNECTION"
        assert prod_tool["auth"].pop("connection_env") == "DOCWIKI_MCP_CONNECTION"
    assert evaluated == prod


def test_eval_payload_equals_production_except_name_url_and_connection() -> None:
    agent = load_agents()["researcher"]
    prod = build_agent_payload(agent, EVAL_ENV)
    evaluated = build_agent_payload(eval_agent(agent), EVAL_ENV)
    assert prod.agent_name == "docwiki-researcher"
    assert evaluated.agent_name == "docwiki-researcher-eval"
    (eval_tool,) = evaluated.body["definition"]["tools"]
    assert eval_tool["server_url"] == EVAL_MCP_URL
    assert eval_tool["project_connection_id"] == EVAL_CONNECTION
    expected = json.loads(json.dumps(prod.body))
    expected["definition"]["tools"][0]["server_url"] = EVAL_MCP_URL
    expected["definition"]["tools"][0]["project_connection_id"] = EVAL_CONNECTION
    for body in (expected, evaluated.body):
        body["metadata"].pop("docwiki_definition_sha256")
    assert evaluated.body == expected
    assert evaluated.body["definition"]["instructions"] == agent.instructions
    assert evaluated.definition_sha256 == definition_hash(evaluated.agent_name, evaluated.body)
    assert evaluated.definition_sha256 != prod.definition_sha256
    (binding,) = evaluated.bindings
    assert (binding.server_url_env, binding.connection_env) == (
        "DOCWIKI_EVAL_MCP_URL",
        "DOCWIKI_EVAL_MCP_CONNECTION",
    )


def test_eval_payload_never_falls_back_to_the_production_mcp() -> None:
    with pytest.raises(AgentConfigurationError, match="DOCWIKI_EVAL_MCP_URL"):
        build_agent_payload(eval_agent(load_agents()["researcher"]), DEPLOY_ENV)


def test_main_eval_deploys_only_the_eval_researcher(capsys: pytest.CaptureFixture[str]) -> None:
    project = _project()
    code, out, err = _run(capsys, "--eval", "--json", env=EVAL_ENV, project_client=project)
    assert code == 0, err
    ((name, body),) = project.agents.created
    assert name == "docwiki-researcher-eval"
    assert body["definition"]["tools"][0]["server_url"] == EVAL_MCP_URL
    assert body["definition"]["tools"][0]["project_connection_id"] == EVAL_CONNECTION
    assert project.connections.calls == [EVAL_CONNECTION]
    (result,) = json.loads(out)["agents"]
    assert result["agent_name"] == "docwiki-researcher-eval"
    assert result["identity_client_id"] == "client-docwiki-researcher-eval"

    code, out, err = _run(capsys, "--eval", env=EVAL_ENV, project_client=project)
    assert code == 0, err
    assert "docwiki-researcher-eval: unchanged at version 1" in out
    assert len(project.agents.created) == 1


def test_main_eval_dry_run_lists_the_eval_variables(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(capsys, "--eval", "--dry-run", env=DEPLOY_ENV)
    assert code == 0
    plan = json.loads(out)
    assert [item["agent"] for item in plan["agents"]] == ["docwiki-researcher-eval"]
    assert plan["missing_env"] == ["DOCWIKI_EVAL_MCP_URL", "DOCWIKI_EVAL_MCP_CONNECTION"]
    assert plan["routines"] == []


def test_main_eval_delete_removes_only_eval_agents(capsys: pytest.CaptureFixture[str]) -> None:
    project = _project()
    assert _run(capsys, env=EVAL_ENV, project_client=project)[0] == 0
    assert _run(capsys, "--eval", env=EVAL_ENV, project_client=project)[0] == 0
    code, out, err = _run(capsys, "--eval", "--delete", env=EVAL_ENV, project_client=project)
    assert code == 0, err
    assert "docwiki-researcher-eval: deleted" in out
    assert project.agents.deleted == ["docwiki-researcher-eval"]
    assert sorted(project.agents.versions) == ["docwiki-librarian", "docwiki-researcher"]

    code, out, err = _run(
        capsys, "--eval", "--delete", "--json", env=EVAL_ENV, project_client=project
    )
    assert code == 0, err
    assert json.loads(out) == {"deleted": [], "absent": ["docwiki-researcher-eval"]}


def test_main_eval_delete_dry_run(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(capsys, "--eval", "--delete", "--dry-run", env={})
    assert code == 0
    assert json.loads(out)["delete"][0]["http"] == "DELETE /agents/docwiki-researcher-eval"


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["--delete"], "--delete only removes evaluation agents"),
        (["--eval", "--routine", "enable"], "--eval deploys agents only"),
    ],
)
def test_main_eval_refuses_production_changes(
    capsys: pytest.CaptureFixture[str], argv: list[str], message: str
) -> None:
    project = _project()
    code, _, err = _run(capsys, *argv, env=EVAL_ENV, project_client=project)
    assert code == 2
    assert message in err
    assert project.agents.created == [] and project.agents.deleted == []
    assert project.beta.routines.calls == []
