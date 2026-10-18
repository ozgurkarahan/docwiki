# Operations (day 2)

Day-2 tasks for a DocWiki environment deployed with [`BOOTSTRAP.md`](../BOOTSTRAP.md). Design
references: [`docs/spec/architecture.md`](spec/architecture.md) (run control §4, identities §6,
observability §7, cost §8) and [`docs/spec/infra-ops-security.md`](spec/infra-ops-security.md).

Every command runs from the repository root in PowerShell 7 or bash and reads resource names
from the azd environment (`azd env get-value <NAME>`), so nothing environment-specific is
written down. Never paste the values (IDs, addresses, tokens) into issues or commits.

## Names at a glance

| Value | `azd env get-value …` |
|---|---|
| Resource group | `AZURE_RESOURCE_GROUP` |
| Storage account (containers `raw`, `work`, `releases`; queues `ingest`, `ingest-poison`) | `DOCWIKI_STORAGE_ACCOUNT` |
| Ingest job / reconcile job | `DOCWIKI_INGEST_JOB_NAME` / `DOCWIKI_RECONCILE_JOB_NAME` |
| MCP app / URL / API audience | `DOCWIKI_MCP_APP_NAME` / `DOCWIKI_MCP_URL` / `DOCWIKI_MCP_API_AUDIENCE` |
| Agents' MCP project connection | `DOCWIKI_MCP_CONNECTION` |
| Foundry account / project endpoint | `DOCWIKI_FOUNDRY_ACCOUNT_NAME` / `DOCWIKI_FOUNDRY_PROJECT_ENDPOINT` |
| Log Analytics workspace (for queries) | `DOCWIKI_LOG_ANALYTICS_WORKSPACE_ID` |
| Managed identities: jobs / MCP app / portal | `DOCWIKI_RUNTIME_IDENTITY_NAME` / `DOCWIKI_MCP_IDENTITY_NAME` / `DOCWIKI_PORTAL_IDENTITY_NAME` |

The hooks keep a local record of the Entra objects they created in
`.azure/<env>/docwiki-state.json` (git-ignored); `scripts/teardown.py` relies on it.

## Ingest new or changed documents

1. Upload, replace or delete files under `raw/` (Storage Explorer, `azcopy` after
   `azcopy login`, or `az storage blob upload-batch … --auth-mode login`). Paths become source
   IDs, so keep a stable folder layout; replacing a file with the same path is a new revision
   of the same source.
2. Event Grid turns every BlobCreated/BlobDeleted under `raw/` into a message on `ingest`.
   KEDA polls the queue every 30 s and starts one execution of the ingest job (never more than
   one). The job takes the blob lease `work/state/lease`, waits 30 s to batch bursts, diffs
   `raw/` against the state shards, compiles only what changed and publishes a new release.
3. Deleting a blob creates a tombstone: dependent pages are rebuilt or removed in the next
   release.

Ask the Librarian to start an ingest (`ingest_start`, approval required), or start a full
level-triggered pass by hand with the reconcile job:

```bash
az containerapp job start --name $(azd env get-value DOCWIKI_RECONCILE_JOB_NAME) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP)
```

The reconcile job also runs on its schedule (`DOCWIKI_RECONCILE_CRON`, default every 6 hours)
and catches lost wake-ups. Starting the ingest job by hand is equivalent when
`DOCWIKI_ENABLE_EVENT_TRIGGER=false` (the ingest job is then a manual job).

## Recompile sources with hints

Use the Librarian: `explain_source` to diagnose, then `recompile` with precise operator notes
(approval required). The tool enqueues a `docwiki.ingest/v1` message with `kind=recompile`,
`scope.source_ids` and `hints.operator_notes`.

Without the Librarian, enqueue the same message with the operator's Entra identity (the
deployer holds Storage Queue Data Contributor on both queues). Save the message as
`.local/recompile.json` (git-ignored), for example:

```json
{"schema": "docwiki.ingest/v1", "kind": "recompile",
 "scope": {"source_ids": ["src-0123456789ab"], "prefix": null},
 "hints": {"operator_notes": "Table 3 is continued on the next page."},
 "requested_by": "cli", "idempotency_key": "recompile-1",
 "created_at": "2026-01-01T00:00:00Z"}
```

then send it with the SDK installed by `uv sync --extra azure` (the command is identical in
PowerShell and bash):

```bash
uv run --extra azure python -c "import json, os; from azure.identity import DefaultAzureCredential; from azure.storage.queue import QueueClient; body = json.dumps(json.load(open('.local/recompile.json', encoding='utf-8'))); url = 'https://' + os.environ['ACCOUNT'] + '.queue.core.windows.net'; QueueClient(url, 'ingest', credential=DefaultAzureCredential()).send_message(body); print('queued')"
```

with `ACCOUNT` set to `$(azd env get-value DOCWIKI_STORAGE_ACCOUNT)` in the shell
(`$env:ACCOUNT = …` in PowerShell, `export ACCOUNT=…` in bash). The parser accepts plain and
base64 message bodies.

## Runs, reports and receipts

```bash
az containerapp job execution list --name $(azd env get-value DOCWIKI_INGEST_JOB_NAME) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) --query "[].{name:name, status:properties.status, start:properties.startTime}" --output table
az storage blob list --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --container-name work --prefix runs/ --auth-mode login --query "[].{name:name, modified:properties.lastModified}" --output table
```

Each run writes `work/runs/<run_id>/report.json`: status, counts, per-stage results, gate
results, model deployments and versions, and the **cost receipt** (tokens per tier × price
table, Content Understanding pages, duration). The next release also contains a readable
summary page `_meta/runs/<run_id>.md`, and the Librarian reads it with `run_status`. Download
a report with `az storage blob download --container-name work --name runs/<run_id>/report.json
--file .local/report.json --auth-mode login --account-name …`.

A failing **blocking** gate stops the publish; the previous release stays current. Fix the
cause (often a source to recompile or a proposal to decide) and run again.

**Which failures are retried.** Systemic failures — model rate limits, authentication,
timeouts or service errors, Content Understanding throttling, outages or authorization,
storage or queue errors, a lost lease, and any unexpected error — keep the run's queue
messages: they become visible again and the run is retried (five deliveries at most, then
`ingest-poison`). Deterministic failures — a blocking gate or the final release validation
fails, or the domain pack or `work/state/overlay.yaml` is invalid — would fail the same way
again: the run deletes (acknowledges) its messages, its report says `failed` with the reason
and the gate results plus the line `deterministic failure: not retried …`, and the execution
exits 0 so Container Apps does not retry the replica. A new upload, a Librarian `recompile`
or the reconcile schedule starts the next run.

**Stale `running` reports.** Stopping an execution (`az containerapp job stop`, the replica
timeout, a crash) leaves its `report.json` in status `running`. The next execution that takes
the run lease marks every earlier report still `running` as `failed` with the error
`abandoned: the execution ended before finishing` and `finished_at` set: no lease holder can
be running them. Until then, a `running` report older than the one-hour replica timeout is
abandoned, not in progress.

### Poison messages

A message dequeued more than five times moves to `ingest-poison`. Inspect and, after fixing the
cause, re-drive (the operator holds Storage Queue Data Contributor):

```bash
az storage message peek --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --queue-name ingest-poison --num-messages 32 --auth-mode login --output json
az storage message clear --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --queue-name ingest-poison --auth-mode login
```

Re-drive means enqueueing a fresh `ingest` or `recompile` message (see above) or starting the
reconcile job; the job is level-triggered, so the content of a lost message never matters.

## Roll back the current release

Releases are immutable; `releases/current.json` is the only pointer readers follow (the MCP
server re-checks it at most every 30 s). To roll back, point it at an earlier complete
release:

```bash
az storage blob list --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --container-name releases --delimiter / --auth-mode login --query "[].name" --output tsv
uv run --extra azure docwiki release rollback <release_id>
```

`docwiki release rollback` (pipeline CLI; arguments in its `--help`) calls
`docwiki.release.publish.rollback`: it reads the target manifest, writes a new pointer
(`release_id`, `audience`, `manifest_sha256`, new `created_at`) with an ETag precondition and
never touches the release folders. The next successful run publishes a newer release and moves
the pointer forward again; pause the triggers first if that is not wanted
(`az containerapp job stop` for a running execution, `DOCWIKI_ENABLE_EVENT_TRIGGER=false` plus
`azd provision` to stop wake-ups).

## Rotate and retain releases

- The publish stage keeps the last 10 releases plus the one referenced by `current.json`
  (`DOCWIKI_RELEASE_RETENTION`) and deletes older release folders.
- Blob versioning keeps every overwritten blob (state shards, pointer). A lifecycle rule
  deletes previous versions after 30 days; soft-deleted blobs and containers are recoverable
  for 7 days (`az storage blob undelete`, `az storage container restore`).
- To free space immediately, delete old `releases/<release_id>/` folders that are not current
  (`az storage blob delete-batch --source releases --pattern "<release_id>/*" --auth-mode login --account-name …`).

## Budgets and cost

- The monthly budget on the resource group (`DOCWIKI_BUDGET_AMOUNT`, default 50 in the billing
  currency) notifies the action group at 50, 80 and 100 % of actual cost. Contacts come from
  `BUDGET_CONTACT_EMAILS`; without contacts no budget is created. Change either with
  `azd env set …` and `azd provision`.
- Expect one-time costs while experimenting: a full ingest of the 38-document sample cost about
  USD 19 in the first live run (gpt-5.5 / gpt-5.4-mini, Data Zone list prices from the
  unverified price table), so the 50 alert can fire in the first days of tests and re-ingests.
  An idle environment costs close to nothing.
- Cost drivers: tokens on `fast` and `smart` (pay-per-token), Content Understanding pages, Log
  Analytics ingestion, the Basic registry, storage. Everything else scales to zero (the disabled
  portal app is kept at zero replicas by a `dormant` cron scale rule that is never active); keep
  `DOCWIKI_MCP_MIN_REPLICAS=0` outside demos. Measured in the identity spike: the MCP app scales
  to zero after about 8.5 minutes idle; from zero, `/healthz` took 22.6 s (1.2 s warm) and an
  agent turn 38.8 s (about 8 s warm). For a demo, `azd env set DOCWIKI_MCP_MIN_REPLICAS 1` and
  `azd provision` (or warm the app with a call to `/healthz` a minute before).
- Run receipts price tokens with `src/docwiki/llm/prices.yaml`, a placeholder table
  (`verified: false`): copy it, verify the prices for your region and deployment type, and
  point `DOCWIKI_LLM_PRICE_TABLE` at the copy before relying on receipts.
- Bounded work: per-document page limit, map-reduce chunk limits and at most 12 research tool
  calls per question (see `SETTINGS_DEFAULTS` in `src/docwiki/contracts/settings.py`). A per-run
  token budget (`DOCWIKI_MAX_TOKENS_PER_RUN`) is reserved in the settings but not enforced yet.

## Change models, capacity or settings

```bash
python scripts/preflight.py
azd env set DOCWIKI_SMART_CAPACITY 150
azd provision
```

The deployed model name, version, capacity and deployment type are written back to the azd
environment after each provision, so they only change when you set them. Always run the
preflight first: it verifies the model, version, deployment type and quota in the region and
never picks an alternative on its own. Container settings (`DOCWIKI_*`) are applied by
`azd provision`; client-side rate limits follow the capacity (1,000 tokens and 1 request per
minute per capacity unit).

## Images and updates

- `azd deploy` rebuilds and deploys all images remotely in the registry; `azd deploy job`,
  `azd deploy mcp` or `azd deploy portal` deploy one service. The `postdeploy` hook copies the
  job image to the reconcile job and smoke-tests the MCP endpoint: built-in auth enabled
  (`Return401`), and 401 without a token, to a forged principal header and to a token for
  another audience (`python scripts/hooks/postdeploy.py --smoke-only` repeats the test).
- `azd provision` never resets a deployed image (it reuses `SERVICE_<NAME>_IMAGE_NAME` or the
  image currently running).
- Base images come from public registries (`python:3.12-slim-bookworm`, `node:22-bookworm-slim`,
  `ghcr.io/astral-sh/uv`). If pulls are throttled, mirror them (for example with an ACR cache
  rule) and change the `ARG …_IMAGE` defaults in `docker/*.Dockerfile`.
- Quartz is pinned by `site/QUARTZ_VERSION` (the `QUARTZ_VERSION` build argument is only a
  fallback when that file is missing) and pre-fetched at build time: the job image mirrors a
  source checkout under `/opt/docwiki` (the package installed in editable mode from
  `/opt/docwiki/src`, next to `site/`, `domains/` and `skills/`), so the engine finds its domain
  packs, skill templates and site overlay there, and the installed Quartz in
  `/opt/docwiki/.cache/quartz/<tag>` (owned by the runtime user, never cloned at run time).
  Runs use `DOCWIKI_WORK_DIR=/var/lib/docwiki/work` for local scratch (raw downloads, release
  staging); in Azure mode the engine builds the site during publish unless
  `DOCWIKI_SITE_BUILD=false`. Rebuild the site of a release by hand with
  `python -m docwiki.site <release> --out <dir> --base-url <url>` (Node 22 and git needed
  locally).
- The portal image serves the current release's site and keeps the application's security
  headers; its Content Security Policy allows `'unsafe-eval'` because the Quartz explorer and
  graph need it. Do not strip or override these headers in front of the app.

## Identities and access

- One managed identity per workload (least privilege, `docs/spec/architecture.md` §6):
  - jobs (`DOCWIKI_RUNTIME_IDENTITY_*`): pipeline storage access, ingest queue processing,
    Foundry models and Content Understanding;
  - MCP app (`DOCWIKI_MCP_IDENTITY_*`): reads `releases/` and `work/`, writes only
    `work/reports/`, `work/proposals/` and `work/state/overlay.yaml` (Blob Data Contributor
    with an attribute-based condition), enqueues on `ingest`; no `raw/`, no Foundry;
  - portal (`DOCWIKI_PORTAL_IDENTITY_*`): reads `releases/`.

  List them with
  `az role assignment list --assignee $(azd env get-value DOCWIKI_MCP_IDENTITY_PRINCIPAL_ID) --all --output table`
  (same for `DOCWIKI_RUNTIME_IDENTITY_PRINCIPAL_ID` and `DOCWIKI_PORTAL_IDENTITY_PRINCIPAL_ID`).
  There are no keys, connection strings or SAS tokens to rotate; the Application Insights
  connection string is an ingestion endpoint, not a credential.
- MCP API and agents ([ADR 0003](adr/0003-mcp-agent-identity.md)): each Foundry agent calls the
  MCP server with its own Entra agent identity (`instance_identity`, kept across agent
  versions). Four layers protect the server: Entra issues tokens only to principals with an
  app role (`appRoleAssignmentRequired`), built-in auth accepts only the audience
  `api://<client id>` from the allowlisted client IDs (`allowedApplications`), the server
  validates the forwarded bearer token again (signature, issuer, audience, lifetime and the same
  client allowlist, `DOCWIKI_MCP_*` settings in
  [`src/docwiki/mcp/README.md`](../src/docwiki/mcp/README.md#bearer-token-validation)), and it
  checks the role of every tool (`Wiki.Read` for read tools, `Wiki.Operate` for operations
  tools; the long role claim type is accepted by default, `DOCWIKI_ROLE_CLAIM`). The MCP app
  gets external ingress only once built-in auth is applied and verified: Bicep declares it only
  when the MCP API app registration is known, and on the first run the postprovision hook
  enables it after `az containerapp auth show` confirms the configuration and the server's token
  settings are set.
  - After deploying or recreating agents, re-run
    `python scripts/hooks/postprovision.py --only mcp-connection,agents,agent-roles,mcp-allowlist`:
    a deleted and recreated agent gets a **new** identity and loses its roles and allowlist entry
    until this runs. `agents/deploy.py` only adds versions, which keep the identity.
  - **Revoking an agent immediately**: removing an app role is not immediate (Agent Service
    keeps using its cached token until it expires). Use the allowlist instead:
    `azd env set DOCWIKI_MCP_BLOCKED_AGENTS librarian` then
    `python scripts/hooks/postprovision.py --only mcp-allowlist`; the agent gets 403 within
    about a minute, the server's own allowlist drops it too (`DOCWIKI_MCP_ALLOWED_CLIENT_IDS` on
    the `mcp` app, a new revision), and later provisions keep it out. Clear the variable and
    re-run the step to restore it.
  - If both agents ever report the same principal, the hook grants it `Wiki.Read` only and
    revokes `Wiki.Operate` (effective at token refresh). Other unwanted assignments are removed
    in Microsoft Entra ID (Enterprise applications → the MCP API → Users and groups).
- Agents' MCP connection (`DOCWIKI_MCP_CONNECTION`, default `docwiki-mcp`): project connection
  `RemoteTool` / `AgenticIdentityToken`, target `DOCWIKI_MCP_URL`, audience
  `DOCWIKI_MCP_API_AUDIENCE`. The first provision creates it from the hook through Azure
  Resource Manager (API `2025-10-01-preview`; `azd ai connection create` fails on a project
  without connections); later provisions declare it in Bicep
  (`infra/modules/mcp-connection.bicep`). Both rewrite it only when it differs.
- Librarian routine: `azd env set DOCWIKI_ENABLE_ROUTINE true` then
  `python scripts/hooks/postprovision.py --only agents` deploys it enabled
  (`agents/deploy.py --routine enable`); setting it back to `false` and re-running disables it.
- Portal (when `DOCWIKI_ENABLE_PORTAL=true`): users sign in with Entra ID; only users or
  groups assigned to the portal enterprise application get in. The hook assigns the deployer;
  add readers under Enterprise applications → `docwiki-portal-<env>-<token>` → Users and
  groups. No client secret exists (ID-token sign-in).
- Public portal (`DOCWIKI_PORTAL_ACCESS=public`, only with `DOCWIKI_AUDIENCE=public`): no sign-in
  and no app registration; Bicep gives the portal its ingress, so anyone with the URL can read the
  public build. A portal that already had Entra sign-in keeps it until you run
  `az containerapp auth update --name <portal app> --resource-group <rg> --enabled false`.
- The hooks call Microsoft Graph with the Azure CLI sign-in. When continuous access evaluation
  revokes it, they stop with `the signed-in session needs a fresh sign-in`: run `az logout`,
  `az login` and `azd auth login`, then re-run the hook.

## Storage network perimeter (optional)

`DOCWIKI_NETWORK_PERIMETER=true` (then `azd provision`) secures the storage account with a
network security perimeter: only managed identities of the subscription and the CIDR ranges in
`DOCWIKI_ALLOWED_IP_RANGES` (operator uploads; kept in the azd environment, never committed)
get through. Event Grid cannot create or re-create its `raw-to-ingest` subscription inside the
perimeter: create it first with a provision without the perimeter (it keeps delivering
afterwards), or temporarily turn the perimeter off to re-create it. Without the subscription,
uploads are picked up by the reconcile schedule, a manual job start or an ingest message.

## Logs and queries

Container logs reach Log Analytics through an Azure Monitor diagnostic setting (tables
`ContainerAppConsoleLogs` and `ContainerAppSystemLogs`, no `_CL` suffix); application
telemetry (OpenTelemetry) is in the workspace-based Application Insights tables (`AppTraces`,
`AppRequests`, `AppDependencies`, `AppExceptions`). Retention is 30 days. Run a query with:

```bash
az monitor log-analytics query --workspace $(azd env get-value DOCWIKI_LOG_ANALYTICS_WORKSPACE_ID) --analytics-query "<KQL>" --output table
```

Useful queries:

```kusto
// Ingest and reconcile job output, newest first
ContainerAppConsoleLogs
| where ContainerAppName startswith "caj-" or JobName startswith "caj-"
| project TimeGenerated, ContainerAppName, JobName, Log
| top 200 by TimeGenerated

// Job and scaler events (KEDA, image pulls, replica failures)
ContainerAppSystemLogs
| where JobName startswith "caj-ingest" or ContainerAppName startswith "caj-ingest"
| project TimeGenerated, Reason, Log
| top 100 by TimeGenerated

// Errors by pipeline stage (structured logs carry run_id, source_id, stage)
AppTraces
| where SeverityLevel >= 3
| extend run_id = tostring(Properties.run_id), stage = tostring(Properties.stage)
| summarize errors = count() by run_id, stage
| order by errors desc

// LLM calls per tier: count, tokens, estimated cost, latency (spans docwiki.llm.structured)
AppDependencies
| where Name == "docwiki.llm.structured"
| extend tier = tostring(Properties["docwiki.llm.tier"]),
         tokens_in = toint(Properties["docwiki.llm.input_tokens"]),
         tokens_out = toint(Properties["docwiki.llm.output_tokens"]),
         cost_usd = todouble(Properties["docwiki.llm.estimated_cost_usd"])
| summarize calls = count(), tokens_in = sum(tokens_in), tokens_out = sum(tokens_out),
            cost_usd = sum(cost_usd), p95_ms = percentile(DurationMs, 95)
            by tier, bin(TimeGenerated, 1h)

// MCP traffic: requests, rejected calls and latency
AppRequests
| where AppRoleName endswith "docwiki-mcp"
| summarize requests = count(), rejected = countif(ResultCode in ("401", "403")),
            p95_ms = percentile(DurationMs, 95) by bin(TimeGenerated, 1h)
```

The MCP server, jobs and portal report as `docwiki-mcp`, `docwiki-ingest`,
`docwiki-reconcile` and `docwiki-portal` (`OTEL_SERVICE_NAME`; Application Insights shows the
role names with the `docwiki.` service namespace, for example `docwiki.docwiki-mcp`). The jobs
export their stage and LLM spans and their warnings; their console output keeps warnings and
the run summary only. Foundry agent traces appear in
the Foundry portal (Agents → Traces) through the project's Application Insights connection.

## Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| No job execution after an upload | Event Grid delivery, queue role, KEDA auth | Check the event subscription metrics, `ContainerAppSystemLogs`; re-run `azd provision` |
| Several executions in a row, all failing | A poison source or a crash loop | Read the logs and `report.json`; messages end in `ingest-poison` after five attempts |
| An execution ends within seconds without work | Another execution holds the run lease | Expected; the running execution picks up the change (level-triggered) |
| MCP answers 401 to an agent | Wrong audience or token | Compare `DOCWIKI_MCP_API_AUDIENCE` with the connection's audience; `python scripts/hooks/postprovision.py --only mcp-connection` |
| MCP answers 403 to an agent (HTTP, before any tool runs) | Agent client ID not in `allowedApplications` (new or recreated agent, or blocked on purpose) | `python scripts/hooks/postprovision.py --only agents,agent-roles,mcp-allowlist`; check `DOCWIKI_MCP_BLOCKED_AGENTS` |
| Foundry: `Failed to fetch agentic identity access token` (`AADSTS501051`) | The agent identity has no MCP app role | `python scripts/hooks/postprovision.py --only agent-roles` |
| A tool result `{"ok": false, "error": {"code": "forbidden", …}}` | The calling agent lacks the tool's app role (for example the Researcher calling an operations tool) | Expected; keep each agent's `allowed_tools` aligned with its roles, or check its app roles |
| MCP `/healthz` answers 503 | No release published yet, or the MCP identity cannot read `releases/` | Expected before the first ingest; afterwards check the MCP identity's roles |
| `the MCP connection authenticates each agent with its own identity, but …` | An agent definition declares another `auth.strategy` | Set `auth.strategy: per-agent-identity` in `agents/*/agent.yaml` (ADR 0003) |
| `the signed-in session needs a fresh sign-in` from a hook | Continuous access evaluation revoked the CLI token | `az logout`, `az login`, `azd auth login`; re-run the hook |
| MCP answers 403 when writing a proposal or report | Write outside the paths allowed by the MCP identity's condition | Expected for any other `work/` path; check the key the server writes |
| A request with a forged `X-MS-CLIENT-PRINCIPAL` header and no token succeeds; the smoke test fails with `answered 200 to a forged X-MS-CLIENT-PRINCIPAL header` | Built-in auth is off (a hook that failed before configuring it, or auth disabled while troubleshooting) **and** the server's token validation is off (`DOCWIKI_MCP_TOKEN_VALIDATION=off`). A request without any header still gets 401 from the server itself, so a 401 does not prove that built-in auth is on | Stop traffic: `az containerapp ingress disable --name $(azd env get-value DOCWIKI_MCP_APP_NAME) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP)`; `azd hooks run postprovision` (re-enables ingress only after verifying built-in auth); `python scripts/hooks/postdeploy.py --smoke-only` |
| Smoke test: `built-in auth is not enabled on ca-mcp-…`, or `az containerapp auth show` reports `enabled: false` | Built-in auth missing or switched off; the server's token validation still answers 401 to unauthenticated and forged calls, but one layer is gone | `azd hooks run postprovision`; check with `az containerapp auth show --name $(azd env get-value DOCWIKI_MCP_APP_NAME) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) --query "{enabled:platform.enabled, action:globalValidation.unauthenticatedClientAction}"` |
| Every agent call gets 401 from the MCP server, whose log shows `rejected request without a valid bearer token header but with a x-ms-client-principal header` | The platform did not pass the `Authorization` header on to the container ([platform behaviour to verify](../src/docwiki/mcp/README.md#bearer-token-validation)) | Confirm in `ContainerAppConsoleLogs`; then opt out explicitly: `azd env set DOCWIKI_MCP_TOKEN_VALIDATION off` and `azd provision` (the server trusts the principal header again; keep the smoke test); report it |
| MCP log: `rejected request: bearer token …` (expired, another audience, issuer or tenant, signature, client not allowed) | The token settings of the `mcp` app differ from its built-in auth (audience, allowlist), or a caller bypassed built-in auth | Compare `DOCWIKI_MCP_AUDIENCE` and `DOCWIKI_MCP_ALLOWED_CLIENT_IDS` on the app with `az containerapp auth show`; `python scripts/hooks/postprovision.py --only mcp-auth,mcp-allowlist` |
| The MCP container stops at start: `DOCWIKI_AUTH_MODE=easyauth validates the bearer token …: set DOCWIKI_MCP_AUDIENCE …` | The token settings are missing (the MCP API app registration did not exist yet when the app was provisioned) | `azd hooks run postprovision` (sets them before it enables ingress) or `azd provision` |
| MCP answers 503 `authentication is temporarily unavailable` | The server cannot fetch the tenant's token signing keys (outbound HTTPS to `login.microsoftonline.com`) | Check the environment's egress; the server retries on its own and keeps cached keys for up to a day |
| 429 from the models | Capacity too low for the run | Raise `DOCWIKI_*_CAPACITY` after the preflight quota check |
| `AuthorizationPermissionMismatch` from storage | Role propagation or missing deployer role | Wait 10 minutes; re-run `azd provision` signed in as the operator |
| `AuthorizationFailure` from storage (jobs, MCP app, uploads); `publicNetworkAccess` reads `Disabled` | A tenant policy turned public network access off on the storage account | `azd env set DOCWIKI_NETWORK_PERIMETER true` (and `DOCWIKI_ALLOWED_IP_RANGES` for uploads), `azd provision`; see BOOTSTRAP Step 8 |
| Redeploy fails on the Foundry account name | Soft-deleted account | `python scripts/preflight.py` prints the purge command |

## Teardown

`azd down --purge --force` (or `python scripts/teardown.py --yes`): see Step 14 of
[`BOOTSTRAP.md`](../BOOTSTRAP.md#step-14--teardown). The agents are deleted first (their Entra
agent identities go with them), then the resource group, then the app registrations. If the
Foundry account stays behind with `CannotDeleteDefaultProject` (spike finding F13), the rest is
gone and the empty account costs nothing: re-run `python scripts/teardown.py --yes` later and
escalate to Azure support if it persists.
