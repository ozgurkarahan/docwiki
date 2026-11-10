"""Evaluation variants: agents/variants.yaml, deploy.py --variant and the stack helpers."""

from __future__ import annotations

import base64
import json
import uuid
from pathlib import Path
from typing import Any

import pytest
from agents_testkit import (
    AGENTS_DIR,
    CONNECTION,
    DEPLOY_ENV,
    FakeAgents,
    FakeProject,
    connection,
    copy_agents,
)

from docwiki.agents_client import evalstack
from docwiki.agents_client.definitions import load_agents
from docwiki.agents_client.deploy import build_agent_payload, delete_agent, main
from docwiki.agents_client.errors import AgentConfigurationError, AgentDefinitionError
from docwiki.agents_client.variants import (
    AgentVariant,
    VariantsFile,
    build_variant_agent,
    encode_mcp_variants,
    load_variants,
    resolve_mcp_variants,
    variant_environment,
)

REPO_ROOT = AGENTS_DIR.parent
URL_TEMPLATE = "https://{name}.variants.example/mcp"
CONN_TEMPLATE = "docwiki-mcp-{name}"
MCP_NAMES = ("wiki", "raw", "wiki2", "raw2")
V2_TEXT = "# DocWiki Researcher v2\n\nPlan sub-questions, search each, join.\n"
API_CLIENT_ID = str(uuid.UUID(int=0xA1))
READ_ROLE_ID = str(uuid.UUID(int=0xB1))
API_SP_ID = str(uuid.UUID(int=0xC1))


def _out() -> str:
    return json.dumps(
        {
            name: {
                "url": URL_TEMPLATE.format(name=name),
                "connection": CONN_TEMPLATE.format(name=name),
            }
            for name in MCP_NAMES
        }
    )


ENV: dict[str, str] = {
    **DEPLOY_ENV,
    "DOCWIKI_EVAL_SMART_DEPLOYMENT": "smart-eval",
    "DOCWIKI_EVAL_MCP_VARIANTS_OUT": _out(),
    "DOCWIKI_EVAL_MCP_VECTORS": "vectors-2026-11",
    "DOCWIKI_MCP_API_CLIENT_ID": API_CLIENT_ID,
}


def _agents_dir(tmp_path: Path, *, v2: bool = True) -> Path:
    agents_dir = copy_agents(tmp_path)
    path = agents_dir / "variants" / "v2" / "instructions.md"
    if v2:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(V2_TEXT, encoding="utf-8")
    else:
        path.unlink(missing_ok=True)
    return agents_dir


def _project(*names: str) -> FakeProject:
    connections = {
        CONN_TEMPLATE.format(name=name): {
            **connection(target=URL_TEMPLATE.format(name=name)),
            "name": CONN_TEMPLATE.format(name=name),
        }
        for name in names or MCP_NAMES
    }
    return FakeProject(connections={CONNECTION: connection(), **connections})


def _run(
    capsys: pytest.CaptureFixture[str], agents_dir: Path, *argv: str, **kwargs: Any
) -> tuple[int, str, str]:
    code = main([*argv], agents_dir=agents_dir, **kwargs)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# ---------------------------------------------------------------- the declaration


def test_committed_variants_match_the_study_arms() -> None:
    declared = load_variants(AGENTS_DIR / "variants.yaml")
    arms = {
        agent.name: (agent.mcp_variant, agent.instructions, agent.reasoning_effort)
        for agent in declared.agents
    }
    v2 = "agents/variants/v2/instructions.md"
    assert arms == {
        "w1": ("wiki", None, None),
        "r1": ("raw", None, None),
        "w2": ("wiki2", v2, None),
        "r2": ("raw2", v2, None),
        "w2high": ("wiki2", v2, "high"),
    }
    assert [agent.name for agent in declared.agents] == ["w1", "r1", "w2", "r2", "w2high"]
    assert all(agent.base == "researcher" for agent in declared.agents)
    assert all(agent.model_env == "DOCWIKI_EVAL_SMART_DEPLOYMENT" for agent in declared.agents)
    assert declared.mcp_variants == {
        "wiki": {},
        "raw": {"DOCWIKI_MCP_WIKI_ABLATION": "raw"},
        "wiki2": {
            "DOCWIKI_MCP_DENSE": "on",
            "DOCWIKI_MCP_SUPERSESSION_COMPANIONS": "on",
            "DOCWIKI_MCP_VECTORS": "${DOCWIKI_EVAL_MCP_VECTORS}",
        },
        "raw2": {
            "DOCWIKI_MCP_WIKI_ABLATION": "raw",
            "DOCWIKI_MCP_DENSE": "on",
            "DOCWIKI_MCP_VECTORS": "${DOCWIKI_EVAL_MCP_VECTORS}",
        },
    }


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"name": "toolongname"}, "name"),
        ({"name": "Bad-Name"}, "name"),
        ({"mcp_variant": "nope"}, "undeclared mcp_variants"),
        ({"instructions": "../secret.md"}, "relative POSIX path"),
        ({"instructions": "agents/x.txt"}, "relative POSIX path"),
        ({"reasoning_effort": "extreme"}, "reasoning_effort"),
        ({"base": "librarian"}, "base"),
        ({"model_env": "smart"}, "model_env"),
    ],
)
def test_invalid_agent_variants_are_rejected(change: dict[str, Any], message: str) -> None:
    agent = {"name": "w9", "base": "researcher", "mcp_variant": "wiki", **change}
    with pytest.raises(ValueError, match=message):
        VariantsFile.model_validate({"mcp_variants": {"wiki": {}}, "agents": [agent]})


def test_mcp_variant_env_rules() -> None:
    def make(env: dict[str, Any]) -> VariantsFile:
        return VariantsFile.model_validate({"mcp_variants": {"wiki": env}, "agents": []})

    assert make({"DOCWIKI_MCP_DENSE": "on"}).mcp_variants["wiki"] == {"DOCWIKI_MCP_DENSE": "on"}
    with pytest.raises(ValueError, match="authentication settings"):
        make({"DOCWIKI_MCP_AUDIENCE": "x"})
    with pytest.raises(ValueError, match="DOCWIKI_MCP_"):
        make({"DOCWIKI_FAST_DEPLOYMENT": "x"})
    with pytest.raises(ValueError, match="string"):
        make({"DOCWIKI_MCP_DENSE": True})  # unquoted YAML `on`
    with pytest.raises(ValueError, match="duplicate"):
        VariantsFile.model_validate(
            {
                "mcp_variants": {"wiki": {}},
                "agents": [{"name": "a", "mcp_variant": "wiki"}] * 2,
            }
        )


def test_variants_file_errors_name_the_file(tmp_path: Path) -> None:
    path = tmp_path / "variants.yaml"
    path.write_text("mcp_variants: {}\nagents: [{name: A, mcp_variant: x}]\n", encoding="utf-8")
    with pytest.raises(AgentDefinitionError, match=r"variants\.yaml"):
        load_variants(path)


def test_ordinary_loading_ignores_the_variants() -> None:
    assert sorted(load_agents(AGENTS_DIR)) == ["librarian", "researcher"]


# ---------------------------------------------------------------- the variant agent


def test_variant_payload_equals_production_except_name_model_endpoint_and_metadata() -> None:
    base = load_agents(AGENTS_DIR)["researcher"]
    declared = load_variants(AGENTS_DIR / "variants.yaml")
    w1 = next(a for a in declared.agents if a.name == "w1")
    env = variant_environment(ENV, [w1], strict=True)
    prod = build_agent_payload(base, ENV)
    payload = build_agent_payload(build_variant_agent(w1, base, REPO_ROOT), env)
    assert payload.agent_name == "docwiki-researcher-w1"
    (tool,) = payload.body["definition"]["tools"]
    assert tool["server_url"] == URL_TEMPLATE.format(name="wiki")
    assert tool["project_connection_id"] == CONN_TEMPLATE.format(name="wiki")
    assert payload.body["definition"]["model"] == "smart-eval"
    assert "reasoning" not in payload.body["definition"]
    expected = json.loads(json.dumps(prod.body))
    expected["definition"]["model"] = "smart-eval"
    expected["definition"]["tools"][0].update(
        server_url=tool["server_url"], project_connection_id=tool["project_connection_id"]
    )
    expected["metadata"].update(docwiki_variant="w1", docwiki_mcp_variant="wiki")
    for body in (expected, payload.body):
        body["metadata"].pop("docwiki_definition_sha256")
    assert payload.body == expected
    assert payload.body["definition"]["instructions"] == base.instructions
    assert payload.definition_sha256 != prod.definition_sha256


def test_v2_variants_use_their_instructions_and_effort(tmp_path: Path) -> None:
    agents_dir = _agents_dir(tmp_path)
    base = load_agents(agents_dir)["researcher"]
    declared = load_variants(agents_dir / "variants.yaml")
    bodies = {
        agent.name: build_agent_payload(
            build_variant_agent(agent, base, tmp_path),
            variant_environment(ENV, [agent], strict=True),
        ).body
        for agent in declared.agents
    }
    assert bodies["w2"]["definition"]["instructions"] == V2_TEXT.strip()
    assert bodies["w1"]["definition"]["instructions"] == base.instructions
    assert bodies["w2high"]["definition"]["reasoning"] == {"effort": "high"}
    assert "reasoning" not in bodies["w2"]["definition"]
    assert bodies["w2"]["definition"]["tools"][0]["server_url"] == URL_TEMPLATE.format(name="wiki2")
    assert bodies["r2"]["definition"]["tools"][0]["server_url"] == URL_TEMPLATE.format(name="raw2")


def test_missing_instructions_file_is_a_clear_deploy_time_error(tmp_path: Path) -> None:
    agents_dir = _agents_dir(tmp_path, v2=False)
    base = load_agents(agents_dir)["researcher"]
    w2 = next(a for a in load_variants(agents_dir / "variants.yaml").agents if a.name == "w2")
    with pytest.raises(AgentConfigurationError, match=r"agents/variants/v2/instructions\.md"):
        build_variant_agent(w2, base, tmp_path)
    # Variants without a file of their own do not need it.
    w1 = next(a for a in load_variants(agents_dir / "variants.yaml").agents if a.name == "w1")
    assert build_variant_agent(w1, base, tmp_path).instructions == base.instructions


def test_variant_environment_reads_the_bicep_output() -> None:
    raw = AgentVariant(name="r1", mcp_variant="raw")
    env = variant_environment(ENV, [raw], strict=True)
    assert env["DOCWIKI_EVAL_MCP_URL_R1"] == URL_TEMPLATE.format(name="raw")
    assert env["DOCWIKI_EVAL_MCP_CONNECTION_R1"] == CONN_TEMPLATE.format(name="raw")
    unknown = AgentVariant(name="x1", mcp_variant="absent")
    with pytest.raises(AgentConfigurationError, match="'absent' is not in"):
        variant_environment(ENV, [unknown], strict=True)
    assert "DOCWIKI_EVAL_MCP_URL_X1" not in variant_environment(ENV, [unknown], strict=False)
    without = {k: v for k, v in ENV.items() if k != "DOCWIKI_EVAL_MCP_VARIANTS_OUT"}
    with pytest.raises(AgentConfigurationError, match="DOCWIKI_EVAL_MCP_VARIANTS_OUT"):
        variant_environment(without, [raw], strict=True)
    assert variant_environment(without, [raw], strict=False) == without
    bad = {**ENV, "DOCWIKI_EVAL_MCP_VARIANTS_OUT": "{not json"}
    with pytest.raises(AgentConfigurationError, match="not valid JSON"):
        variant_environment(bad, [raw], strict=True)
    bad = {
        **ENV,
        "DOCWIKI_EVAL_MCP_VARIANTS_OUT": '{"raw": {"url": "https://raw.variants.example/mcp"}}',
    }
    with pytest.raises(AgentConfigurationError, match="url and a connection"):
        variant_environment(bad, [raw], strict=True)


# ---------------------------------------------------------------- agents/deploy.py --variant


def test_deploy_selected_variants_only(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    agents_dir = _agents_dir(tmp_path)
    project = _project()
    argv = ("--variant", "w1", "--variant", "r1", "--json")
    code, out, err = _run(capsys, agents_dir, *argv, env=ENV, project_client=project)
    assert code == 0, err
    assert [name for name, _ in project.agents.created] == [
        "docwiki-researcher-w1",
        "docwiki-researcher-r1",
    ]
    assert sorted(project.agents.versions) == ["docwiki-researcher-r1", "docwiki-researcher-w1"]
    assert project.connections.calls == [CONN_TEMPLATE.format(name=n) for n in ("wiki", "raw")]
    results = json.loads(out)["agents"]
    assert [r["identity_client_id"] for r in results] == [
        "client-docwiki-researcher-w1",
        "client-docwiki-researcher-r1",
    ]
    code, out, err = _run(capsys, agents_dir, "--variant", "w1", env=ENV, project_client=project)
    assert code == 0, err
    assert "docwiki-researcher-w1: unchanged at version 1" in out
    assert len(project.agents.created) == 2


def test_deploy_all_variants(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    agents_dir = _agents_dir(tmp_path)
    project = _project()
    code, _, err = _run(capsys, agents_dir, "--variant", "all", env=ENV, project_client=project)
    assert code == 0, err
    assert [name for name, _ in project.agents.created] == [
        f"docwiki-researcher-{n}" for n in ("w1", "r1", "w2", "r2", "w2high")
    ]
    efforts = {name: body["definition"].get("reasoning") for name, body in project.agents.created}
    assert efforts["docwiki-researcher-w2high"] == {"effort": "high"}
    assert efforts["docwiki-researcher-w2"] is None


def test_ordinary_deploy_never_touches_variants(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    agents_dir = _agents_dir(tmp_path)
    project = FakeProject()
    code, _, err = _run(capsys, agents_dir, env=ENV, project_client=project)
    assert code == 0, err
    assert sorted(name for name, _ in project.agents.created) == [
        "docwiki-librarian",
        "docwiki-researcher",
    ]


def test_deploy_variant_without_provisioned_apps_fails_clearly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    agents_dir = _agents_dir(tmp_path)
    project = _project()
    env = {k: v for k, v in ENV.items() if k != "DOCWIKI_EVAL_MCP_VARIANTS_OUT"}
    code, _, err = _run(capsys, agents_dir, "--variant", "w1", env=env, project_client=project)
    assert code == 2 and "DOCWIKI_EVAL_MCP_VARIANTS_OUT" in err
    assert project.agents.created == []
    only = {
        **ENV,
        "DOCWIKI_EVAL_MCP_VARIANTS_OUT": json.dumps({"wiki": json.loads(_out())["wiki"]}),
    }
    code, _, err = _run(capsys, agents_dir, "--variant", "r1", env=only, project_client=project)
    assert code == 2 and "'raw' is not in" in err


def test_deploy_variant_with_a_missing_instructions_file_fails_before_azure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    agents_dir = _agents_dir(tmp_path, v2=False)
    project = _project()
    code, _, err = _run(capsys, agents_dir, "--variant", "all", env=ENV, project_client=project)
    assert code == 2
    assert "agents/variants/v2/instructions.md" in err and "does not exist" in err
    assert project.agents.created == []


def test_variant_dry_run_prints_the_resolved_bodies(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    agents_dir = _agents_dir(tmp_path)
    code, out, _ = _run(capsys, agents_dir, "--variant", "w2high", "--dry-run", env=ENV)
    assert code == 0
    plan = json.loads(out)
    (agent,) = plan["agents"]
    assert agent["agent"] == "docwiki-researcher-w2high"
    definition = agent["body"]["definition"]
    assert definition["model"] == "smart-eval"
    assert definition["reasoning"] == {"effort": "high"}
    assert definition["instructions"] == V2_TEXT.strip()
    assert definition["tools"][0]["server_url"] == URL_TEMPLATE.format(name="wiki2")
    assert agent["body"]["metadata"]["docwiki_variant"] == "w2high"
    assert plan["missing_env"] == []
    # Before the apps exist the dry run still works and lists what is missing.
    code, out, err = _run(capsys, agents_dir, "--variant", "w1", "--dry-run", env={})
    assert code == 0 and "DOCWIKI_EVAL_MCP_URL_W1" in err
    assert json.loads(out)["missing_env"] == [
        "DOCWIKI_FOUNDRY_PROJECT_ENDPOINT",
        "DOCWIKI_EVAL_SMART_DEPLOYMENT",
        "DOCWIKI_EVAL_MCP_URL_W1",
        "DOCWIKI_EVAL_MCP_CONNECTION_W1",
    ]


def test_variant_delete_only_removes_declared_variants(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    agents_dir = _agents_dir(tmp_path)
    project = _project()
    assert _run(capsys, agents_dir, env=ENV, project_client=project)[0] == 0
    assert _run(capsys, agents_dir, "--variant", "w1", env=ENV, project_client=project)[0] == 0
    code, out, err = _run(
        capsys, agents_dir, "--variant", "w1", "--delete", env=ENV, project_client=project
    )
    assert code == 0, err
    assert "docwiki-researcher-w1: deleted" in out
    assert project.agents.deleted == ["docwiki-researcher-w1"]
    assert sorted(project.agents.versions) == ["docwiki-librarian", "docwiki-researcher"]
    code, out, _ = _run(
        capsys, agents_dir, "--variant", "w1", "--delete", "--json", env=ENV, project_client=project
    )
    assert code == 0
    assert json.loads(out) == {"deleted": [], "absent": ["docwiki-researcher-w1"]}
    code, out, _ = _run(capsys, agents_dir, "--variant", "all", "--delete", "--dry-run", env={})
    assert code == 0
    assert [item["http"] for item in json.loads(out)["delete"]] == [
        f"DELETE /agents/docwiki-researcher-{n}" for n in ("w1", "r1", "w2", "r2", "w2high")
    ]


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["--variant", "researcher", "--delete"], "unknown variant"),
        (["--variant", "nope"], "unknown variant"),
        (["--delete"], "--delete only removes evaluation agents"),
        (["--variant", "w1", "--agent", "researcher"], "drop --eval, --agent and --routine"),
        (["--variant", "w1", "--routine", "enable"], "drop --eval, --agent and --routine"),
        (["--variant", "w1", "--eval"], "drop --eval, --agent and --routine"),
    ],
)
def test_variant_refusal_rules(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], argv: list[str], message: str
) -> None:
    agents_dir = _agents_dir(tmp_path)
    project = _project()
    code, _, err = _run(capsys, agents_dir, *argv, env=ENV, project_client=project)
    assert code == 2 and message in err
    assert project.agents.created == [] and project.agents.deleted == []


@pytest.mark.asyncio
async def test_delete_agent_refuses_names_outside_the_allowed_set() -> None:
    project = FakeProject(versions={"docwiki-researcher": [{"version": "1"}]})
    with pytest.raises(AgentConfigurationError, match="not a declared evaluation variant"):
        await delete_agent(project, "docwiki-researcher", allowed=["docwiki-researcher-w1"])
    with pytest.raises(AgentConfigurationError, match="not an evaluation agent"):
        await delete_agent(project, "docwiki-researcher")
    assert project.agents.deleted == []


def test_eval_flag_still_works_with_a_deprecation_note(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, out, err = _run(capsys, AGENTS_DIR, "--eval", "--dry-run", env={})
    assert code == 0
    assert "--eval is deprecated" in err
    assert json.loads(out)["agents"][0]["agent"] == "docwiki-researcher-eval"


# ---------------------------------------------------------------- the operator helpers


def test_encode_resolves_placeholders_and_survives_the_parameters_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    declared = load_variants(AGENTS_DIR / "variants.yaml")
    resolved = resolve_mcp_variants(declared, ENV)
    assert [item["name"] for item in resolved] == ["wiki", "raw", "wiki2", "raw2"]
    assert resolved[2]["env"]["DOCWIKI_MCP_VECTORS"] == "vectors-2026-11"
    encoded = encode_mcp_variants(resolved)
    assert encoded.isascii() and '"' not in encoded and "$" not in encoded
    assert json.loads(base64.b64decode(encoded)) == resolved
    assert [i["name"] for i in resolve_mcp_variants(declared, ENV, ["raw"])] == ["raw"]
    with pytest.raises(AgentConfigurationError, match="DOCWIKI_EVAL_MCP_VECTORS"):
        resolve_mcp_variants(declared, {})
    with pytest.raises(AgentConfigurationError, match="unknown mcp variant"):
        resolve_mcp_variants(declared, ENV, ["nope"])
    assert evalstack.main(["encode"], agents_dir=AGENTS_DIR, env=ENV) == 0
    assert json.loads(base64.b64decode(capsys.readouterr().out.strip())) == resolved
    assert evalstack.main(["encode"], agents_dir=AGENTS_DIR, env={}) == 2
    assert "DOCWIKI_EVAL_MCP_VECTORS" in capsys.readouterr().err


class FakeGraph:
    def __init__(self, *, existing: set[tuple[str, str]] | None = None, role: bool = True) -> None:
        self.assignments = set(existing or ())
        self.role = role
        self.posts: list[dict[str, Any]] = []
        self.pages = 2

    def __call__(self, method: str, url: str, body: dict[str, Any] | None) -> dict[str, Any] | None:
        if method == "GET" and "servicePrincipals(appId=" in url:
            assert API_CLIENT_ID in url
            roles = [{"id": READ_ROLE_ID, "value": "Wiki.Read"}] if self.role else []
            return {"id": API_SP_ID, "appRoles": roles}
        if method == "GET" and url.endswith("/appRoleAssignedTo?$top=999"):
            items = [{"principalId": p, "appRoleId": r} for p, r in sorted(self.assignments)]
            return {"value": items[:1], "@odata.nextLink": f"{url}&page=2"}
        if method == "GET" and url.endswith("&page=2"):
            items = [{"principalId": p, "appRoleId": r} for p, r in sorted(self.assignments)]
            return {"value": items[1:]}
        if method == "POST":
            assert body is not None
            self.posts.append(body)
            self.assignments.add((body["principalId"], body["appRoleId"]))
            return {"id": "assignment", **body}
        raise AssertionError(f"unexpected Graph call {method} {url}")


def _deployed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> tuple[Path, FakeProject]:
    agents_dir = _agents_dir(tmp_path)
    project = _project()
    assert _run(capsys, agents_dir, "--variant", "all", env=ENV, project_client=project)[0] == 0
    return agents_dir, project


def test_identities_print_the_allowlist(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    agents_dir, project = _deployed(tmp_path, capsys)
    argv = ["identities", "--json"]
    code = evalstack.main(argv, agents_dir=agents_dir, env=ENV, project_client=project)
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    ids = [f"client-docwiki-researcher-{n}" for n in ("w1", "r1", "w2", "r2", "w2high")]
    assert [item["client_id"] for item in data["agents"]] == ids
    assert data["DOCWIKI_EVAL_MCP_ALLOWED_CLIENT_IDS"] == ",".join(sorted(ids))
    code = evalstack.main(
        ["identities", "--variant", "w1"], agents_dir=agents_dir, env=ENV, project_client=project
    )
    out = capsys.readouterr().out
    assert code == 0
    assert out.strip().splitlines()[-1] == (
        "DOCWIKI_EVAL_MCP_ALLOWED_CLIENT_IDS=client-docwiki-researcher-w1"
    )


def test_identities_fail_for_agents_that_are_not_deployed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    agents_dir = _agents_dir(tmp_path)
    code = evalstack.main(
        ["identities"], agents_dir=agents_dir, env=ENV, project_client=FakeProject()
    )
    assert code == 2 and "does not exist: deploy it first" in capsys.readouterr().err


def _identities() -> list[evalstack.AgentIdentity]:
    return [
        evalstack.AgentIdentity(
            f"docwiki-researcher-{name}",
            f"00000000-0000-4000-8000-00000000010{i}",
            f"00000000-0000-4000-8000-00000000020{i}",
        )
        for i, name in enumerate(("w1", "r1"))
    ]


def test_grant_is_idempotent_and_dry_run_changes_nothing() -> None:
    identities = _identities()
    graph = FakeGraph(existing={(identities[0].principal_id or "", READ_ROLE_ID)})
    kwargs = {"mcp_api_client_id": API_CLIENT_ID, "identities": identities}
    dry = evalstack.grant_wiki_read(graph, dry_run=True, **kwargs)
    assert [(r.agent_name, r.status) for r in dry] == [
        ("docwiki-researcher-w1", "exists"),
        ("docwiki-researcher-r1", "would-grant"),
    ]
    assert graph.posts == []
    done = evalstack.grant_wiki_read(graph, dry_run=False, **kwargs)
    assert [r.status for r in done] == ["exists", "granted"]
    assert graph.posts == [
        {
            "principalId": identities[1].principal_id,
            "resourceId": API_SP_ID,
            "appRoleId": READ_ROLE_ID,
        }
    ]
    again = evalstack.grant_wiki_read(graph, dry_run=False, **kwargs)
    assert [r.status for r in again] == ["exists", "exists"]
    assert len(graph.posts) == 1


def test_grant_refuses_bad_input() -> None:
    identities = _identities()
    with pytest.raises(AgentConfigurationError, match=r"does not define the Wiki\.Read"):
        evalstack.grant_wiki_read(
            FakeGraph(role=False),
            mcp_api_client_id=API_CLIENT_ID,
            identities=identities,
            dry_run=False,
        )
    with pytest.raises(AgentConfigurationError, match="must be a GUID"):
        evalstack.grant_wiki_read(
            FakeGraph(), mcp_api_client_id="x' or 1=1", identities=identities, dry_run=True
        )
    with pytest.raises(AgentConfigurationError, match="without an identity principal"):
        evalstack.grant_wiki_read(
            FakeGraph(),
            mcp_api_client_id=API_CLIENT_ID,
            identities=[evalstack.AgentIdentity("a", None, "c")],
            dry_run=True,
        )


def test_grant_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    agents_dir, project = _deployed(tmp_path, capsys)
    # FakeAgents identities are not GUIDs: the command validates them before calling Graph.
    graph = FakeGraph()
    code = evalstack.main(
        ["grant", "--dry-run"],
        agents_dir=agents_dir,
        env=ENV,
        project_client=project,
        graph=graph,
    )
    assert code == 2 and "must be a GUID" in capsys.readouterr().err
    assert graph.posts == []
    no_api = {k: v for k, v in ENV.items() if k != "DOCWIKI_MCP_API_CLIENT_ID"}
    code = evalstack.main(
        ["grant"], agents_dir=agents_dir, env=no_api, project_client=project, graph=graph
    )
    assert code == 2 and "DOCWIKI_MCP_API_CLIENT_ID" in capsys.readouterr().err


def test_grant_command_end_to_end(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def guid_identity(agent_name: str) -> dict[str, str]:
        number = sum(map(ord, agent_name))
        return {
            "principal_id": f"00000000-0000-4000-8000-{number:012d}",
            "client_id": f"00000000-0000-4000-9000-{number:012d}",
        }

    monkeypatch.setattr(FakeAgents, "identity", staticmethod(guid_identity))
    agents_dir, project = _deployed(tmp_path, capsys)
    graph = FakeGraph()
    common = {"agents_dir": agents_dir, "env": ENV, "project_client": project, "graph": graph}
    assert evalstack.main(["grant", "--dry-run", "--json"], **common) == 0
    assert {r["status"] for r in json.loads(capsys.readouterr().out)} == {"would-grant"}
    assert graph.posts == []
    assert evalstack.main(["grant", "--variant", "w1", "--variant", "r1"], **common) == 0
    out = capsys.readouterr().out
    assert out.count("Wiki.Read granted") == 2 and len(graph.posts) == 2
    assert evalstack.main(["grant", "--json"], **common) == 0
    statuses = [r["status"] for r in json.loads(capsys.readouterr().out)]
    assert statuses == ["exists", "exists", "granted", "granted", "granted"]
