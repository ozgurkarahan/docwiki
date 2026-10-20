# DocWiki MCP server

`docwiki.mcp` serves **one immutable wiki release at a time** to agents through the
[Model Context Protocol](https://modelcontextprotocol.io/): the two Foundry prompt agents
(Researcher: read tools; Librarian: read and operations tools) over stateless streamable HTTP,
and local agents (GitHub Copilot in VS Code, Copilot CLI, Claude Code) over stdio.
It implements `docs/spec/mcp-and-agents.md` §1 on top of the frozen contracts
(`docwiki.release.ReleaseReader`, `docwiki.search`, `docwiki.contracts`).

Built with the Python MCP SDK **2.x** (`mcp.server.mcpserver.MCPServer`, the successor of
FastMCP), stateless JSON responses at `/mcp`, a guarded tool class that checks roles and
arguments, and SDK server middleware that hides tools and logs calls.

## Tools

Every result is one compact JSON object (a single text content block) whose first key is `ok`
(see [Results and errors](#results-and-errors)); read results carry the `release_id` they were
answered from. Results are bounded to `DOCWIKI_MCP_MAX_CHARS` (default 12,000 characters): long
texts are paged by character `offset` and lists by item `offset`, with `truncated` and
`next_offset` in the result. Document text is never returned without its locator and
provenance; compiled wiki text comes with the citations it carries.

### Read tools (app role `Wiki.Read`)

| Tool | Parameters | Returns |
|---|---|---|
| `search` | `query`, `kinds?` (`page-section`, `source-block`), `types?`, `entity?`, `topic?`, `limit=10`, `offset=0` | Ranked hits `{kind, origin, page_id, path, title, section, anchor, snippet, score, status?, source_id?, locator_key?, locator_label?, evidence_path?, provenance?}` and the synonym-expanded terms |
| `read_page` | `page` (id or path, `#anchor` allowed), `section?`, `offset=0` | Frontmatter, Markdown (whole page or one section with its subsections), section list, outgoing page links and one citation per footnote in the returned text `{source_title, locator_label, source_id, locator_key, evidence_path, badge, provenance}` |
| `get_index` | `scope="home"` (`home`, `sources`, `entities`, `entities/<type>`, `topics`, `queries`, `glossary`, `log`), `offset=0` | Index Markdown |
| `get_links` | `page`, `offset=0` | `outgoing` and `backlinks` with edge kinds (`mentions`, `supersedes`, `topic-of`, `cites`, `related`) |
| `glossary` | `term?`, `offset=0` | Matching terms (exact, partial, synonym) with definition, synonyms per language and related pages |
| `get_evidence` | `source_id`, `locator_key`, `offset=0` | Verbatim sidecar content with locator, label, provenance, badge, sidecar path, published original, source page and status |
| `query_table` | `source_id`, `sql` | One read-only DuckDB `SELECT` over tables `t01`… (≤ 200 rows) with `row_id`, plus the table schema and locators |
| `get_skill` | `name`, `offset=0` | `SKILL.md` of a wiki skill |
| `list_skills` | — | Skill names, descriptions and paths |
| `recent_changes` | `since?` (date), `limit=20`, `offset=0` | Log entries, newest first, with the pages concerned |

### Operations tools (app role `Wiki.Operate`)

| Tool | Parameters | Effect | Approval in Foundry |
|---|---|---|---|
| `ingest_start` | `reason`, `scope?: {source_ids?, prefix?}` | Enqueues a `docwiki.ingest/v1` message (`kind=ingest`, `requested_by=librarian`, deterministic idempotency key; identical requests within ~10 minutes are not queued twice) | required |
| `run_status` | `run_id?` | Latest or selected run report summary, and whether its release is the one served | none |
| `list_sources` | `status?`, `limit=50`, `offset=0` | Per-source state (status, stage, last error, sensitivity, presence in the release), problems first | none |
| `quality_report` | `release?` | Gate results G01–G15 of the served or of another release | none |
| `explain_source` | `source_id` | Stage errors, extraction warnings, sample blocks (with locators and injection flags), related proposals, whether a quarantine is retried automatically, next steps | none |
| `recompile` | `source_ids`, `hints` | Enqueues `kind=recompile` with `hints.operator_notes` (text addressed to an AI system is refused) | required |
| `list_proposals` | `status?`, `limit=20`, `offset=0` | Proposals with summary, payload, evidence and decision | none |
| `decide_proposal` | `id`, `decision` (`accept`/`reject`), `note` | Records the decision (ETag-guarded); accepted entity/glossary/topic proposals are merged into `work/state/overlay.yaml`, accepted recompile proposals are enqueued. Accepting is refused (`invalid_argument`, nothing recorded) when the domain pack recorded by the last ingest run (`work/state/domain-pack.json`) could not apply the proposal, e.g. an entity type the pack does not define (`unavailable` before the first run) | required |
| `write_health_report` | `markdown` (≤ 20,000 characters) | Sanitised report written to `work/reports/health-<yyyy-mm-dd>.md` | none (routine-safe) |

Tool annotations mark the read tools and the read-only operations tools `readOnlyHint`; the
four mutating tools are not read-only. Tool descriptions and the server instructions live in
`descriptions.py`: they are part of agent quality, keep them precise when tools change.

## Results and errors

Microsoft Foundry aborts the whole agent turn (HTTP 400 `tool_user_error`) when an MCP tool
answers with a JSON-RPC error **or** with an `isError: true` result, and the model never sees
why (`docs/adr/0003-mcp-agent-identity.md`, spike finding F3). So the server never uses either
for tool failures: every `tools/call` returns a normal result, and its JSON says whether the call
worked.

```json
{"ok": true, "release_id": "...", "...": "..."}
{"ok": false, "tool": "read_page",
 "error": {"code": "not_found", "message": "unknown page 'topic:x'. Did you mean: ...?",
           "retryable": false, "details": {"suggestions": ["topic:quotes-contract-and-amendment"]}}}
```

| `error.code` | Meaning | What the agent should do |
|---|---|---|
| `invalid_argument` | Arguments fail the input schema or a check (bad id or locator key, non-`SELECT` or multi-statement SQL, wrong tool for an evidence path, operator notes addressed to an AI system) | Fix the arguments using the message |
| `not_found` | Unknown page, section, source, sidecar, table, skill, run, proposal, release, index scope or tool (`details` lists suggestions or valid values when known) | Search or browse an index |
| `forbidden` | The caller lacks the app role of the tool (`details.required_role`); checked before arguments | Do not retry; report that the action is not permitted |
| `conflict` | Concurrent change, or a proposal decision is already final | Re-read, then retry or stop |
| `too_large` | An input exceeds its size limit, or a result cannot fit the output budget | Shorten or narrow the request |
| `unavailable` | No release is served yet, or storage or the queue failed (`retryable: true`) | Retry later or report |
| `timeout` | An upstream call timed out (`retryable: true`) | Retry later or report |
| `internal` | Unexpected server error; details are only in the server log | Report the failure |

Messages never contain tokens, claims, machine paths or upstream error text. Protocol-level
problems that are not tool failures (malformed JSON-RPC, unknown methods) keep their JSON-RPC
errors, and transport authentication failures stay HTTP 401 (503 while the token signing keys
cannot be fetched).

## Authorization

| Mode | Who | Behaviour |
|---|---|---|
| `DOCWIKI_AUTH_MODE=easyauth` (HTTP) | Callers authenticated by Container Apps built-in authentication | Every request needs the caller's bearer token (`Authorization: Bearer <jwt>`, passed on by built-in authentication), which the server validates itself (see [Bearer-token validation](#bearer-token-validation)): missing or invalid → HTTP 401 with the generic body `{"error": "unauthorized", "message": "authentication required"}`. The caller's object id and app roles come from the validated token. An `X-MS-CLIENT-PRINCIPAL` header, when present, must be unique and well formed (else 401) and never adds roles: roles it claims beyond the token's are ignored and logged. Read tools need a read role, operations tools an operate role (no implication between levels). A missing role → result `{"ok": false, "error": {"code": "forbidden", "details": {"required_role": ...}}}`, checked before argument validation, so the agent turn continues. `tools/list` shows every tool to a caller holding any DocWiki role (none to a caller without): Agent Service caches the tool list of a project connection across the agents that share it, so a list filtered by the Researcher's roles hid the Librarian's operations tools; each agent's `allowed_tools` scopes what its model sees. |
| `DOCWIKI_AUTH_MODE=easyauth` with `DOCWIKI_MCP_TOKEN_VALIDATION=off` | Explicit opt-out, logged as a warning at start-up | The header alone is trusted (the behaviour before token validation): `X-MS-CLIENT-PRINCIPAL` is decoded on every request; missing, duplicated or malformed → HTTP 401. App roles come from the claim types of `DOCWIKI_ROLE_CLAIM` and from the payload's `role_typ` (Container Apps sends one long-form role claim per role). Only safe while built-in authentication is verifiably on. |
| `DOCWIKI_AUTH_MODE=none` | stdio, or HTTP bound to a loopback address only (refused otherwise) | Read tools; operations tools only with `--allow-ops` (development). The principal header is ignored. |

The header is trusted **only** in `easyauth` mode, so that mode must only run behind Container
Apps authentication (`Return401`, allowed audience = the MCP API app registration). Logs carry a
hash of the principal id (`principal:<16 hex>`), never tokens or claims. `/healthz` needs no
principal.

Agent principals are per-agent Entra agent identities (`docs/adr/0003-mcp-agent-identity.md`):
the Researcher holds `Wiki.Read`, the Librarian `Wiki.Read` and `Wiki.Operate`. The caller is
identified by its object id (`oid`; `objectidentifier` in the principal header), logged as a
hash. The mapping is configurable:

| Variable | Default | Meaning |
|---|---|---|
| `DOCWIKI_ROLE_CLAIM` | `roles,http://schemas.microsoft.com/ws/2008/06/identity/claims/role` | Comma-separated claim types carrying app roles; the token's `roles` claim and the principal payload's `role_typ` are always honoured too |
| `DOCWIKI_READ_ROLE` | `Wiki.Read` | Comma-separated roles granting the read tools |
| `DOCWIKI_OPERATE_ROLE` | `Wiki.Operate` | Comma-separated roles granting the operations tools |

### Bearer-token validation

Built-in authentication validates the caller's token, drops client-supplied `X-MS-*` headers and
adds its own principal header (identity spike, finding F8). When the platform's authentication
is missing — a post-provision hook that failed before configuring it, followed by `azd deploy`,
or authentication disabled while troubleshooting — nothing removes a forged header any more. So
the server never relies on the header alone: it validates the forwarded bearer token too
(`tokens.py`, PyJWT), and a forged header without a valid token gets 401. The infrastructure adds
two guards: the `mcp` app gets external ingress only after built-in authentication is applied and
verified, and the post-deploy smoke test sends a forged header (it must get 401) and checks that
built-in authentication is enabled (`docs/operations.md`, `BOOTSTRAP.md` steps 6 and 11).

| Check | Rule |
|---|---|
| Signature | RS256 only, with a key of the tenant's v2 signing keys (`https://login.microsoftonline.com/<tenant>/discovery/v2.0/keys`, read with PyJWT's `PyJWKClient`): cached for an hour, fetched again when a token names an unknown key (key rotation) but at most once a minute, and kept for up to a day when a fetch fails; no key at all → HTTP 503 |
| Issuer | `https://login.microsoftonline.com/<tenant>/v2.0` (the MCP API issues v2 tokens, ADR 0003); `tid`, when present, must be the tenant |
| Audience | One of `DOCWIKI_MCP_AUDIENCE` (v2 tokens carry the client ID; the application ID URI is accepted too) |
| Lifetime | `exp` and `nbf` required, 60 s clock-skew leeway |
| Caller | `azp` (v2 tokens) or `appid` (v1) in `DOCWIKI_MCP_ALLOWED_CLIENT_IDS`, when that list is set |
| Identity and roles | Object id from `oid` (else `sub`); app roles from `roles` and the claim types of `DOCWIKI_ROLE_CLAIM` |

| Variable | Default | Meaning |
|---|---|---|
| `DOCWIKI_MCP_TOKEN_VALIDATION` | `required` | `required` or `off` (explicit opt-out, logged as a warning); used in `easyauth` mode only |
| `DOCWIKI_MCP_TENANT_ID` | — | Tenant ID (a GUID) of the MCP API app registration; required with validation |
| `DOCWIKI_MCP_AUDIENCE` | — | Comma-separated accepted audiences, `api://<client id>,<client id>`; required with validation |
| `DOCWIKI_MCP_ALLOWED_CLIENT_IDS` | empty (any caller with a valid token) | Comma-separated client IDs of the agent identities: the same list as the built-in auth allowlist |

In `easyauth` mode with validation required, the server refuses to start (exit code 2) and names
the missing variable when the tenant or the audience is not set. `infra/main.bicep` sets the
four variables on the `mcp` app; the post-provision hook sets them on the first run and refreshes
the allowlist whenever the agents change.

**Platform behaviour to verify on each new deployment.** App Service documents that built-in
authentication passes the validated bearer token on to the application: in
[Tutorial: Authenticate and authorize users end-to-end in Azure App Service](https://learn.microsoft.com/azure/app-service/tutorial-auth-aad)
the back end reads it from the `Authorization` header after the platform rejected invalid
requests. [Authentication and authorization in Azure Container Apps](https://learn.microsoft.com/azure/container-apps/authentication)
states that Container Apps uses the same authentication system as App Service, but it does not
say explicitly that the `Authorization` header reaches the container, and the identity spike did
not record it. `BOOTSTRAP.md` step 12 checks it: agent calls must succeed, and the MCP log must
not show `rejected request without a valid bearer token header but with a x-ms-client-principal
header`. If the platform does not forward the header, every agent call gets 401 (fail closed);
then, and only then, opt out with `azd env set DOCWIKI_MCP_TOKEN_VALIDATION off` and
`azd provision`, keep the ingress gate and the smoke test, and report it.

## Run modes

```powershell
uv sync --all-extras --no-extra evals                 # once

# Local agents (stdio): read tools on a release folder
uv run python -m docwiki.mcp.server --stdio --release samples/fixtures/mock-release

# Local HTTP for development (loopback only without authentication)
uv run python -m docwiki.mcp.server --http 127.0.0.1:8765 --release samples/fixtures/mock-release

# Local operations tools on a work folder (development)
uv run python -m docwiki.mcp.server --stdio --allow-ops --work-dir .local

# Azure Container Apps (container command)
python -m docwiki.mcp.server --http :8080 --storage blob
```

`--release` accepts a **portable wiki folder** (the content namespace as a plain folder with
its machine files in `.docwiki/`, CONTRACT.md §19), a
release folder, a `releases/` folder with `current.json`, or a folder that contains
`releases/current.json`. Without `--release`, local mode serves `<work-dir>/releases` and
`--storage blob` serves the `releases` container: the release is downloaded into `--cache-dir`
(default: a folder in the system temporary directory) with every hash verified against the
manifest. The pointer (`current.json`, or the manifest of a portable or release folder) is
re-checked at most every `DOCWIKI_MCP_POINTER_TTL_SECONDS` (30 s) and the served release is
swapped atomically; a release that fails to load or verify never replaces the working one.
`search.db` is verified and loaded into memory, so no release file stays open: a portable folder
can be re-exported in place (`docwiki.release.export_portable`) while the server runs. The server
never writes to the release it serves.

| Variable | Default | Used for |
|---|---|---|
| `DOCWIKI_AUTH_MODE` | `none` | `none` or `easyauth` (which also needs the [bearer-token settings](#bearer-token-validation)) |
| `DOCWIKI_MODE` | `local` | `azure` = Blob storage + Storage queue (same as `--storage blob`) |
| `DOCWIKI_STORAGE_ACCOUNT` | — | Storage account name (Blob and queue, Microsoft Entra ID through `DefaultAzureCredential`) |
| `DOCWIKI_RELEASES_CONTAINER`, `DOCWIKI_WORK_CONTAINER` | `releases`, `work` | Container names |
| `DOCWIKI_QUEUE_NAME` | `ingest` | Queue of `ingest_start` and `recompile` in Azure mode |
| `DOCWIKI_WORK_DIR` | `.local` | Local work folder (`work/…`, folder queue `work/queue/*.json`) |
| `DOCWIKI_RELEASE` | — | Default for `--release` |
| `DOCWIKI_MCP_MAX_CHARS` | `12000` | Output budget per tool result (minimum 2000) |
| `DOCWIKI_MCP_POINTER_TTL_SECONDS` | `30` | Pointer re-check interval |
| `DOCWIKI_QUERY_TABLE_MAX_ROWS` | `200` | Row cap of `query_table` (at most 200) |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | — | HTTP mode exports traces and `docwiki` logs to Application Insights |

HTTP endpoints: `POST /mcp` (stateless streamable HTTP, JSON responses; no trailing slash) and
`GET /healthz` (`{"status": "ok", "release_id": …}` or 503 while no release can be served).
`create_app(...)` returns the ASGI application for other hosts and for tests.

## Local agents

The repository ships two project configurations that launch the server over stdio on the
current release of your own deployment (`--storage blob`; set `DOCWIKI_STORAGE_ACCOUNT`):

- `.vscode/mcp.json` — GitHub Copilot in VS Code (agent mode).
- `.mcp.json` — Claude Code (project-scoped servers; approve it when Claude Code asks).

GitHub Copilot CLI reads its servers from the user configuration (`~/.copilot/mcp-config.json`,
or `/mcp add` inside the CLI). Run the CLI from the repository root and add:

```json
{
  "mcpServers": {
    "docwiki": {
      "type": "local",
      "command": "uv",
      "args": ["run", "--extra", "mcp", "python", "-m", "docwiki.mcp.server", "--stdio",
               "--release", "samples/fixtures/mock-release"],
      "tools": ["*"]
    }
  }
}
```

A wiki also ships its skills for each client (`.agents/skills`, `.claude/skills`,
`.github/skills`); `list_skills` and `get_skill` expose the same skills through MCP.

## Foundry agents

Both prompt agents use an MCP tool pointing at the `mcp` Container App:

```json
{
  "type": "mcp",
  "server_label": "docwiki",
  "server_url": "https://<mcp-app-fqdn>/mcp",
  "allowed_tools": ["search", "read_page", "get_index", "get_links", "glossary",
                    "get_evidence", "query_table", "get_skill", "list_skills", "recent_changes"],
  "require_approval": "never"
}
```

The Librarian adds the operations tools and requires approval for `ingest_start`, `recompile`
and `decide_proposal`. Each agent's own Entra agent identity obtains a token for the MCP API app
registration (project connection with `AgenticIdentityToken`); Container Apps authentication
validates it and forwards the principal; the server validates the token again and enforces
`Wiki.Read` / `Wiki.Operate` from its app-role claims, so tool visibility in the agent is not the
authorization boundary. The server lists every tool to any caller with a DocWiki role (Agent
Service shares a connection's cached tool list between the agents), so each agent's
`allowed_tools` is what keeps the operations tools out of the Researcher's model; keep it
aligned with each agent's roles: a forbidden call is answered as a `forbidden` result, but it
still costs a tool call. Agent definitions and deployment live in `agents/`.

## Tests

```powershell
uv run pytest tests/mcp
```

The suite runs against `samples/fixtures/mock-release`: every tool, output bounds and paging,
SQL guards, every error code as an `ok: false` result (never `isError` or a JSON-RPC error), the
HTTP app (401 without a valid bearer token, with a forged principal header or with a token for
another audience, issuer, client or key; header roles never added to the token's; Researcher's
operations calls answered `forbidden`, Librarian allowed; the `off` opt-out; loopback-only `none`
mode), bearer tokens signed with locally generated RSA keys and checked against an in-memory key
set (rotation, throttled refreshes, outages; no network), role claims shaped like the identity
spike's, a spawned
stdio server, pointer swaps, the Blob cache and adapter (with an in-memory fake), and SDK client
round trips (in-process and HTTP). A portable export of the mock release is served over HTTP
and over a spawned stdio server with every read tool, and re-exported in place to check the
reload. Spawned stdio servers get a 300 s request timeout and up to three start attempts, because
starting a Python process that imports the MCP SDK can be slow on a busy machine.

## Known limitations

- `query_table` relies on the contract's locked-down DuckDB connection (no files, network or
  configuration changes; single `SELECT`); it has no execution timeout yet.
- The Blob adapter (`blob.py`) implements the subset of the storage protocol the server needs
  (no leases); it can be replaced by the engine's Blob storage once available.
