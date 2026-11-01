# DocWiki agents

Two Microsoft Foundry **prompt agents** use the DocWiki MCP server (spec:
[`docs/spec/mcp-and-agents.md`](../docs/spec/mcp-and-agents.md) §2). They are defined as code in
this folder, deployed with [`deploy.py`](deploy.py), and called by `docwiki ask` and the evaluation
runner through [`docwiki.agents_client`](../src/docwiki/agents_client/).

| Agent | Foundry name | What it does | MCP tools | MCP app roles |
|---|---|---|---|---|
| Researcher | `docwiki-researcher` | Answers questions with `[n]` citations to evidence sidecars, prefers current over superseded information, surfaces contradictions, abstains ("Not found in the wiki.") instead of guessing | read tools only: `answer_context`, `search`, `read_page`, `get_index`, `get_links`, `glossary`, `get_evidence`, `query_table`, `get_skill`, `list_skills`, `recent_changes` (no approval) | `Wiki.Read` |
| Librarian | `docwiki-librarian` | Starts ingests, watches runs, diagnoses failed or quarantined sources, proposes recompiles with precise hints, reviews proposals, writes health reports | read tools + `run_status`, `list_sources`, `quality_report`, `explain_source`, `list_proposals`, `write_health_report` (no approval) + `ingest_start`, `recompile`, `decide_proposal` (**human approval on every call**) | `Wiki.Read`, `Wiki.Operate` |

Both use the `smart` model deployment and one MCP tool (`server_label: docwiki`). Tool visibility
is not authorization: the MCP server enforces the app roles of the calling principal (D9).

```text
agents/
  researcher/agent.yaml        # definition (schema below)
  researcher/instructions.md   # the prompt
  librarian/agent.yaml
  librarian/instructions.md
  librarian/routine.yaml       # optional daily health report (disabled by default)
  deploy.py                    # idempotent deployment (docwiki.agents_client.deploy)
```

## Definition schema

`agent.yaml` is validated by `docwiki.agents_client.definitions.AgentDefinition` (unknown fields
are errors):

| Field | Meaning |
|---|---|
| `name` | Foundry agent name (`docwiki-<folder>`) |
| `description` | Human description (≤ 512 characters) |
| `model` | Deployment name, or `${DOCWIKI_SMART_DEPLOYMENT}` resolved from the environment at deploy time |
| `instructions_file` | Prompt file next to the YAML (line endings normalised to LF before hashing) |
| `tools[]` | `type: mcp`, `server_label`, `server_url_env` (environment variable holding the MCP URL), `allowed_tools`, `require_approval: {always: [...], never: [...]}`, `auth: {strategy, connection_env, app_roles}` |
| `metadata` | String key/values copied to the agent version (Foundry allows 16 entries; 4 are written by the deploy script) |

Rules enforced in code (and by `tests/agents`): every allowed tool has an explicit approval
policy; `ingest_start`, `recompile` and `decide_proposal` are always in `always`; tool names are the
MCP tools of the spec; `auth.app_roles` lists exactly the roles the allowed tools need (least
privilege); a routine only uses tools that never need approval.

## MCP authentication

Agent Service authenticates to the MCP server through a **project connection** (kind
`remote-tool`, target = the MCP URL, audience = the MCP API application ID URI). The MCP tool
references it with `project_connection_id` = the connection name from `DOCWIKI_MCP_CONNECTION`.
`auth.strategy` says which kind of connection is expected:

| `auth.strategy` | Connection auth type | Calling principal | Consequence |
|---|---|---|---|
| `per-agent-identity` (**ADR 0003, used by both agents**) | `agentic-identity` (`AgenticIdentityToken`) | The agent's own Entra agent identity (`instance_identity`, kept across versions) | Distinct principals per agent, so the server can deny `Wiki.Operate` to the Researcher. |
| `project-managed-identity` (supported, not adopted) | `project-managed-identity` | The Foundry project's managed identity | One principal for every agent of the project: keeping the Researcher read-only would need one project per agent. |

Equivalent CLI for the connection (the infrastructure hook creates it through ARM; shown for
reference):
`azd ai connection create <name> --kind remote-tool --target <mcp-url> --auth-type agentic-identity --audience <app-id-uri>`.

`deploy.py` reads the connection before deploying and fails when its target differs from
`DOCWIKI_MCP_URL` (the connection target wins at run time) or its auth type does not match the
strategy (`--skip-connection-check` skips this). The decision and its evidence are in
[`docs/adr/0003-mcp-agent-identity.md`](../docs/adr/0003-mcp-agent-identity.md).

## Deploy (after the infrastructure exists)

Prerequisites: the Foundry project and its `smart` deployment, the `mcp` app with built-in auth,
the MCP API app registration with the `Wiki.Read` / `Wiki.Operate` roles, the project connection
above, and a deployer with the Foundry User (formerly Azure AI User) role on the project.
Authentication uses `DefaultAzureCredential` (no keys).

| Variable | Meaning |
|---|---|
| `DOCWIKI_FOUNDRY_PROJECT_ENDPOINT` | `https://<account>.services.ai.azure.com/api/projects/<project>` |
| `DOCWIKI_SMART_DEPLOYMENT` | Model deployment used by both agents |
| `DOCWIKI_MCP_URL` | MCP endpoint, `https://<mcp-app-host>/mcp` |
| `DOCWIKI_MCP_CONNECTION` | Name of the project connection to the MCP server |

```powershell
uv run python agents/deploy.py --dry-run           # exact request bodies, no Azure call
uv run python agents/deploy.py                     # create a version only when the definition changed
uv run python agents/deploy.py --json              # machine-readable results (post-provision hook)
uv run python agents/deploy.py --agent researcher  # one agent
```

- `--dry-run` prints the exact `POST /agents/{name}/versions` bodies (unset variables appear as
  `${NAME}` and are listed in `missing_env`).
- Idempotent: each version stores `docwiki_definition_sha256`, the SHA-256 of the resolved body
  (model, instructions, tools, metadata after environment substitution). When the latest version
  has the same hash the agent is reported `unchanged`; otherwise a new version is created. Other
  metadata: `docwiki_mcp_auth`, `docwiki_mcp_roles`, `docwiki_version`.
- Each result reports the agent's Entra agent identity when the service returns it:
  `identity_principal_id` and `identity_client_id` in `--json` (read from the agent object's
  `instance_identity`). The post-provision hook assigns the MCP app roles to the principal and adds
  the client ID to the Container Apps `allowedApplications` list (ADR 0003).
- Exit codes: 0 success, 1 Azure error, 2 invalid definition or configuration.

SDK calls (`azure-ai-projects` 2.9, async): `agents.get`, `agents.create_version(name, body)`,
`connections.get`, `beta.routines.create_or_update`.

## Evaluation agent (optional)

The optional evaluation environment (`enableEvalMcp`,
[`docs/spec/infra-ops-security.md`](../docs/spec/infra-ops-security.md) §1) adds a second MCP app
with the feature under evaluation switched on. `--eval` deploys an evaluation Researcher
`docwiki-researcher-eval` that is identical to the production one (same instructions file, model,
tools, approvals and auth strategy) except its name and its MCP endpoint: it reads
`DOCWIKI_EVAL_MCP_URL` and `DOCWIKI_EVAL_MCP_CONNECTION` (the `azd` outputs of the evaluation
environment) instead of `DOCWIKI_MCP_URL` and `DOCWIKI_MCP_CONNECTION`, never falling back to the
production ones. The production agents are not touched.

```powershell
azd env set DOCWIKI_ENABLE_EVAL_MCP true; azd provision    # the evaluation app and connection
uv run python agents/deploy.py --eval --dry-run            # exact body of docwiki-researcher-eval
uv run python agents/deploy.py --eval --json               # deploy it; note identity_client_id
azd env set DOCWIKI_EVAL_MCP_ALLOWED_CLIENT_IDS <identity_client_id>; azd provision
# then grant Wiki.Read on the MCP API to that identity (the hook does it for production agents only)
uv run python evals/run.py --system docwiki-researcher --agent docwiki-researcher-eval `
    --questions evals/golden/dev.jsonl --catalog <release folder or its catalog.json>
```

The evaluation agent has its own Entra agent identity: the evaluation MCP app accepts it in
addition to the production agents, the production app does not. After the gates, remove it with
`uv run python agents/deploy.py --eval --delete` (`--dry-run` shows the `DELETE` it would send; it
only deletes names ending in `-eval`), delete the evaluation app and connection (a provision with
the flag off leaves them in place), and set `DOCWIKI_ENABLE_EVAL_MCP` back to `false`.

## Invoke

```powershell
docwiki ask "What is the total contract amount including amendment no. 1?"
docwiki ask "Write today's health report" --agent librarian
uv run python -m docwiki.agents_client "<question>" [--agent librarian] [--json]   # same client
```

`docwiki ask` (in `src/docwiki/cli.py`) delegates to `docwiki.agents_client.ask`. In Python, keep
one client open for many questions (the evaluation runner does):

```python
from docwiki.agents_client import AgentClient

async with AgentClient() as client:  # DOCWIKI_FOUNDRY_PROJECT_ENDPOINT + DefaultAzureCredential
    answer = await client.ask("What is the total contract amount including amendment no. 1?")
print(answer.text, answer.sources, answer.tool_calls, answer.usage, answer.version)
```

- The client resolves and pins the latest agent version, then calls the project's Responses API
  (`AIProjectClient.get_openai_client()`, `responses.create(input=..., extra_body={"agent_reference":
  {"type": "agent_reference", "name": ..., "version": ...}})`; `conversation_id` continues a
  conversation).
- MCP approvals: every `mcp_approval_request` goes to the `approve` callback (sync or async, must
  return `True`); without a callback every call is **denied**. The client then continues with
  `previous_response_id` and `mcp_approval_response` items. In a terminal, `docwiki ask` asks on
  the console.
- `AgentAnswer` holds `text`, `sources` (`[{n, title, locator_label, provenance, path, source_id,
  locator_key}]`, from `parse_answer`), `tool_calls` (`{name, arguments, status, error, output}`,
  denied approvals have `status: denied`), `approvals`, `usage` (tokens summed over every call),
  `agent`, `version`, `definition_sha256`, `latency_s` (approval waits excluded), `response_id`
  and `conversation_id`.
- Tool failures: the MCP server returns them as normal results
  `{"ok": false, "tool": ..., "error": {"code", "message", "retryable"}}`, because any MCP error
  makes Foundry end the whole turn (HTTP 400 `tool_user_error`). Both agents' instructions check
  `ok`, follow the error message, repeat a call only when `retryable` is true and never retry
  `forbidden`. The client reports such calls with `status: failed` and `error: "<code>:
  <message>"`.
- Errors surface as `AgentInvocationError` (`AgentAuthError` for 401/403, `AgentNotFoundError` when
  the agent is not deployed); the client never retries an agent run on its own.
  `DOCWIKI_AGENT_TIMEOUT_SECONDS` (default 600) bounds one Responses call.

The citation format (Researcher rule 4) is
`[n] <source title> — <locator label> (<provenance>) — <sidecar path>` under a `Sources:` line;
`docwiki.agents_client.parse_answer` parses it and tolerates common drift (other dashes, Markdown
bullets and links, wiki footnote badges, `../` prefixes).

## Routine (optional)

`librarian/routine.yaml` defines `docwiki-librarian-daily-health`: a schedule trigger at 06:00 UTC
(`0 6 * * *`) that invokes the Librarian through its Responses API with a fixed prompt using only
`run_status`, `quality_report`, `list_sources`, `list_proposals` and `write_health_report` — nobody
is there to approve a call. It is **disabled by default** and only deployed on request:

```powershell
uv run python agents/deploy.py --routine enable    # create or update it, enabled
uv run python agents/deploy.py --routine disable   # keep it, disabled
```

Chosen way: the Foundry routines REST API through `azure-ai-projects` 2.9
(`AIProjectClient.beta.routines.create_or_update` = `PUT /routines/{name}` with the preview header
`Foundry-Features: Routines=V2Preview`), with the same credential as the agents and no extra CLI
extension. The routine is a named project resource, so `azd ai routine` (extension
`azure.ai.routines`) can also show, enable, disable, dispatch it and list its runs. The
post-provision hook maps `DOCWIKI_ENABLE_ROUTINE=true` (`enableRoutine`) to `--routine enable`, and
back to `--routine disable` for a routine it enabled before.

## Tests

`uv run pytest tests/agents` runs offline: schema validation, the instruction requirement
checklist (including the `ok`/error rules, cross-checked against `docwiki.mcp` tool names and error
codes), payloads for both auth strategies, the dry run, idempotent deployment and agent identities
against fakes, `ask()` with mocked clients (answer, approval approved and denied, tool failures,
errors) and through the real SDK clients over a mocked HTTP transport, `docwiki ask` end to end
(CLI, client and SDK with only the Azure boundary mocked), and the citation parser.
