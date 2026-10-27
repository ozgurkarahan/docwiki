"""Schema validation of agents/*/agent.yaml and agents/librarian/routine.yaml."""

from __future__ import annotations

from pathlib import Path

import pytest
from agents_testkit import AGENTS_DIR, copy_agents, edit_file

from docwiki.agents_client.definitions import (
    APPROVAL_REQUIRED_TOOLS,
    AUTH_STRATEGIES,
    DEFAULT_CONNECTION_ENV,
    OPS_TOOLS,
    READ_TOOLS,
    ROUTINE_TOOLS,
    foundry_agent_name,
    load_agent,
    load_agents,
    load_routine,
    load_routines,
)
from docwiki.agents_client.errors import AgentDefinitionError


@pytest.fixture(scope="module")
def agents():
    return load_agents(AGENTS_DIR)


def test_both_agents_are_defined_with_the_naming_convention(agents) -> None:
    assert sorted(agents) == ["librarian", "researcher"]
    for key, agent in agents.items():
        assert agent.name == f"docwiki-{key}" == foundry_agent_name(key)
        assert agent.definition.metadata["docwiki_agent"] == key
        assert agent.definition.model_env == "DOCWIKI_SMART_DEPLOYMENT"
        assert agent.instructions and "\r" not in agent.instructions
        (tool,) = agent.definition.tools
        assert tool.type == "mcp"
        assert tool.server_label == "docwiki"
        assert tool.server_url_env == "DOCWIKI_MCP_URL"
        assert tool.auth.strategy in AUTH_STRATEGIES
        assert tool.auth.connection_env == DEFAULT_CONNECTION_ENV


def test_researcher_only_has_read_tools_without_approval(agents) -> None:
    (tool,) = agents["researcher"].definition.tools
    assert tool.allowed_tools == READ_TOOLS
    assert tool.require_approval.always == ()
    assert tool.require_approval.never == READ_TOOLS
    assert tool.auth.app_roles == ("Wiki.Read",)
    assert not set(tool.allowed_tools) & set(OPS_TOOLS)


def test_librarian_has_read_and_ops_tools_with_approval_for_mutations(agents) -> None:
    (tool,) = agents["librarian"].definition.tools
    assert tool.allowed_tools == READ_TOOLS + OPS_TOOLS
    assert tool.require_approval.always == APPROVAL_REQUIRED_TOOLS
    assert set(tool.require_approval.never) == set(READ_TOOLS + OPS_TOOLS) - set(
        APPROVAL_REQUIRED_TOOLS
    )
    assert set(tool.auth.app_roles) == {"Wiki.Read", "Wiki.Operate"}
    assert tool.require_approval.payload() == {
        "always": {"tool_names": ["ingest_start", "recompile", "decide_proposal"]},
        "never": {"tool_names": list(tool.require_approval.never)},
    }


def test_routine_is_daily_at_six_utc_disabled_and_uses_only_safe_tools(agents) -> None:
    (routine,) = load_routines(agents, AGENTS_DIR)
    definition = routine.definition
    assert routine.name == "docwiki-librarian-daily-health"
    assert definition.enabled is False
    assert definition.agent == "docwiki-librarian" == routine.agent.name
    assert definition.trigger.type == "schedule"
    assert definition.trigger.cron == "0 6 * * *"
    assert definition.trigger.time_zone == "UTC"
    assert definition.tools == ROUTINE_TOOLS
    assert definition.authorization.identity == "agent"
    assert not set(definition.tools) & set(APPROVAL_REQUIRED_TOOLS)
    assert definition.input == definition.input.strip()


def test_foundry_agent_names() -> None:
    assert foundry_agent_name("researcher") == "docwiki-researcher"
    assert foundry_agent_name("librarian") == "docwiki-librarian"
    assert foundry_agent_name("my-agent-2") == "my-agent-2"
    with pytest.raises(AgentDefinitionError):
        foundry_agent_name("-not valid")


# ---------------------------------------------------------------------- invalid agent.yaml


@pytest.fixture
def agents_copy(tmp_path: Path) -> Path:
    return copy_agents(tmp_path)


def _expect_error(path: Path, old: str, new: str, message: str) -> None:
    edit_file(path, old, new)
    with pytest.raises(AgentDefinitionError, match=message):
        load_agent(path)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("metadata:\n", "temperature: 0.2\nmetadata:\n", "Extra inputs are not permitted"),
        (
            "      - recent_changes\n    require",
            "      - recent_changes\n      - delete_all\n    require",
            "unknown DocWiki MCP tools",
        ),
        ("        - recent_changes\n    auth", "    auth", "explicit approval policy"),
        ("  - type: mcp", "  - type: openapi", "Input should be 'mcp'"),
        ("server_label: docwiki", "server_label: DocWiki", "should match pattern"),
        ("server_url_env: DOCWIKI_MCP_URL", "server_url_env: MCP_URL", "should match pattern"),
        ("connection_env: DOCWIKI_MCP_CONNECTION", "connection_env: mcp", "should match pattern"),
        ("strategy: per-agent-identity", "strategy: api-key", "per-agent-identity"),
        ("app_roles: [Wiki.Read]", "app_roles: [Wiki.Read, Wiki.Operate]", "least privilege"),
        ("app_roles: [Wiki.Read]", "app_roles: []", "at least 1 item"),
        ("model: ${DOCWIKI_SMART_DEPLOYMENT}", "model: ${SMART}", "model must be"),
        ("model: ${DOCWIKI_SMART_DEPLOYMENT}", "model: smart model", "model must be"),
        ("instructions_file: instructions.md", "instructions_file: ../x.md", "relative POSIX"),
        ("instructions_file: instructions.md", "instructions_file: missing.md", "cannot read"),
        ("name: docwiki-researcher", "name: -researcher", "should match pattern"),
        ("docwiki_agent: researcher", "docwiki_definition_sha256: x", "written by the deploy"),
        ("docwiki_agent: researcher", "Docwiki-Agent: researcher", "must match"),
        ("docwiki_agent: researcher", "docwiki_agent: 3", "valid string"),
    ],
)
def test_invalid_researcher_definitions_are_rejected(
    agents_copy: Path, old: str, new: str, message: str
) -> None:
    _expect_error(agents_copy / "researcher" / "agent.yaml", old, new, message)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        (
            "      always:\n        - ingest_start\n",
            "      always:\n",
            "explicit approval policy",
        ),
        (
            "      never:\n        - answer_context\n",
            "      never:\n        - ingest_start\n        - answer_context\n",
            "both require_approval.always and .never",
        ),
        (
            "      always:\n        - ingest_start\n        - recompile\n",
            "      always:\n        - ingest_start\n",
            "explicit approval policy",
        ),
        (
            "        - write_health_report\n    auth",
            "        - write_health_report\n        - recompile\n    auth",
            "both",
        ),
        ("app_roles: [Wiki.Read, Wiki.Operate]", "app_roles: [Wiki.Read]", "need app roles"),
        (
            "app_roles: [Wiki.Read, Wiki.Operate]",
            "app_roles: [Wiki.Read, Wiki.Read, Wiki.Operate]",
            "more than once",
        ),
    ],
)
def test_invalid_librarian_definitions_are_rejected(
    agents_copy: Path, old: str, new: str, message: str
) -> None:
    _expect_error(agents_copy / "librarian" / "agent.yaml", old, new, message)


def test_mutating_tools_can_never_skip_approval(agents_copy: Path) -> None:
    path = agents_copy / "librarian" / "agent.yaml"
    edit_file(path, "      always:\n        - ingest_start\n", "      always:\n")
    edit_file(path, "      never:\n", "      never:\n        - ingest_start\n")
    with pytest.raises(AgentDefinitionError, match="mutating tools must always require approval"):
        load_agent(path)


def test_policy_for_a_tool_that_is_not_allowed_is_rejected(agents_copy: Path) -> None:
    path = agents_copy / "researcher" / "agent.yaml"
    edit_file(path, "    always: []", "    always: [ingest_start]")
    with pytest.raises(AgentDefinitionError, match="not allowed"):
        load_agent(path)


def test_too_many_metadata_entries_are_rejected(agents_copy: Path) -> None:
    path = agents_copy / "researcher" / "agent.yaml"
    extra = "".join(f"  key{index}: value\n" for index in range(12))
    edit_file(path, "metadata:\n", "metadata:\n" + extra)
    with pytest.raises(AgentDefinitionError, match="at most 12 metadata entries"):
        load_agent(path)


def test_non_mapping_yaml_and_empty_instructions_are_rejected(agents_copy: Path) -> None:
    path = agents_copy / "researcher" / "agent.yaml"
    (agents_copy / "researcher" / "instructions.md").write_text("  \n\n", encoding="utf-8")
    with pytest.raises(AgentDefinitionError, match="instructions are empty"):
        load_agent(path)
    path.write_text("- just\n- a list\n", encoding="utf-8")
    with pytest.raises(AgentDefinitionError, match="mapping"):
        load_agent(path)
    path.write_text("name: [unclosed\n", encoding="utf-8")
    with pytest.raises(AgentDefinitionError, match="invalid YAML"):
        load_agent(path)


def test_duplicate_agent_names_are_rejected(agents_copy: Path) -> None:
    librarian = agents_copy / "librarian" / "agent.yaml"
    edit_file(librarian, "name: docwiki-librarian", "name: docwiki-researcher")
    with pytest.raises(AgentDefinitionError, match="defined in"):
        load_agents(agents_copy)


def test_crlf_instructions_are_normalised(agents_copy: Path) -> None:
    path = agents_copy / "researcher" / "instructions.md"
    text = path.read_text(encoding="utf-8")
    path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    assert (
        load_agent(agents_copy / "researcher").instructions
        == load_agent(AGENTS_DIR / "researcher").instructions
    )


# ---------------------------------------------------------------------- invalid routine.yaml


@pytest.mark.parametrize(
    ("edits", "message"),
    [
        (
            [("  - write_health_report\n", "  - write_health_report\n  - ingest_start\n")],
            "without approval",
        ),
        ([("  - write_health_report\n", "")], "include write_health_report"),
        ([("  - run_status\n", "  - run_status\n  - run_status\n")], "more than once"),
        ([("summary.", "summary. Then call recompile.")], "must not mention approval tools"),
        ([("summary.", "summary. Use explain_source if needed.")], "outside routine.tools"),
        (
            [
                ("these tools: run_status, quality_report", "these tools: quality_report"),
                ("1. Call run_status for the last run.", "1. Check the last run."),
            ],
            "name every tool",
        ),
        ([('cron: "0 6 * * *"', 'cron: "0 6 * *"')], "5-field cron"),
        ([("identity: agent", "identity: creator")], "Input should be 'agent'"),
        ([("type: schedule", "type: timer")], "Input should be 'schedule'"),
        ([("enabled: false", "enabled: maybe")], "valid boolean"),
        ([("agent: docwiki-librarian", "agent: docwiki-unknown")], "is not defined"),
    ],
)
def test_invalid_routines_are_rejected(
    agents_copy: Path, edits: list[tuple[str, str]], message: str
) -> None:
    agents = load_agents(agents_copy)
    path = agents_copy / "librarian" / "routine.yaml"
    for old, new in edits:
        edit_file(path, old, new)
    with pytest.raises(AgentDefinitionError, match=message):
        load_routine(path, agents)


def test_routine_tools_must_not_require_approval_for_the_agent(agents_copy: Path) -> None:
    librarian = agents_copy / "librarian" / "agent.yaml"
    edit_file(librarian, "      always:\n", "      always:\n        - run_status\n")
    edit_file(librarian, "        - run_status\n        - list_sources", "        - list_sources")
    agents = load_agents(agents_copy)
    with pytest.raises(AgentDefinitionError, match="require approval"):
        load_routine(agents_copy / "librarian" / "routine.yaml", agents)


def test_routine_tools_must_be_allowed_for_the_agent(agents_copy: Path) -> None:
    routine = agents_copy / "librarian" / "routine.yaml"
    edit_file(routine, "agent: docwiki-librarian", "agent: docwiki-researcher")
    with pytest.raises(AgentDefinitionError, match="not allowed to use"):
        load_routine(routine, load_agents(agents_copy))
