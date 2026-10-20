# BOOTSTRAP — deploy DocWiki to Azure (agent-executable runbook)

This runbook deploys DocWiki into **one resource group per azd environment** and verifies it end
to end. It is written for a coding agent or an operator: every step has a **GOAL**, a
**COMMAND**, a **VERIFY** condition that must hold before the next step, and an **ON_FAIL**
procedure. Design: [`docs/spec/infra-ops-security.md`](docs/spec/infra-ops-security.md) and
[`docs/spec/architecture.md`](docs/spec/architecture.md). Day-2 operations:
[`docs/operations.md`](docs/operations.md).

Rules for whoever runs it:

- Run the commands from the repository root, in PowerShell 7 (`pwsh`) or bash. They are
  identical in both shells (`$(...)` substitution works in both).
- Never commit or paste `.azure/` content, `azd env get-values` output, subscription, tenant,
  object or client IDs, e-mail addresses or tokens. `.azure/` is git-ignored.
- Never change the region, a model or a deployment type on your own: when a check fails, apply
  the printed fix only if the owner of the subscription agreed.
- Stop at the first VERIFY that does not hold and follow its ON_FAIL.
- Costs: Foundry models are pay-per-token, Content Understanding is billed per page, the
  Container Apps scale to zero; the registry (Basic) and Log Analytics ingestion have small
  fixed or usage costs. Run Step 14 when you no longer need the environment.

What gets deployed (`infra/main.bicep`):

| Resource | Name pattern | Notes |
|---|---|---|
| Resource group | `rg-<env>` | Tag `azd-env-name` |
| Microsoft Foundry account + project | `aif-<token>`, project `docwiki` | AIServices, local auth disabled; deployments `fast` and `smart`; App Insights tracing connection |
| Storage account | `st<token>` | Shared key disabled, versioning + soft delete; containers `raw`, `work`, `releases`; queues `ingest`, `ingest-poison` |
| Network security perimeter (optional) | `nsp-docwiki-<token>` | Only with `DOCWIKI_NETWORK_PERIMETER=true`: storage reachable only by managed identities of the subscription and `DOCWIKI_ALLOWED_IP_RANGES` |
| Event Grid system topic | `evgt-<token>` | `raw/` BlobCreated/BlobDeleted and `work/inbox/queries/` BlobCreated (filed answers) → queue `ingest` (managed identity delivery) |
| Container registry | `cr<token>` | Basic, admin user disabled; images built remotely by azd |
| Container Apps environment | `cae-<token>` | Consumption profile; logs to Log Analytics through Azure Monitor |
| Jobs | `caj-ingest-<token>`, `caj-reconcile-<token>` | Queue-triggered (KEDA, one execution) and scheduled reconcile |
| Apps | `ca-mcp-<token>`, `ca-portal-<token>`, `ca-studio-<token>` | MCP server behind built-in auth (`/healthz` excluded; external ingress only once that auth is verified; the server validates the forwarded bearer token too); portal and Studio private unless enabled |
| Managed identities | `id-docwiki-<token>`, `id-docwiki-mcp-<token>`, `id-docwiki-portal-<token>`, `id-docwiki-studio-<token>` | One per workload: pipeline jobs, MCP app, portal, Studio (least privilege) |
| Log Analytics + Application Insights | `log-<token>`, `appi-<token>` | 30-day retention |
| Budget + action group | `budget-docwiki-<token>` | 50/80/100 % alerts (when contacts are set) |
| Entra app registrations (hooks) | `docwiki-mcp-api-<env>-<token>` (+ `docwiki-portal-…`, `docwiki-studio-…`) | MCP API audience and app roles `Wiki.Read`, `Wiki.Operate`; sign-in of the portal and the Studio |
| Foundry project connection | `docwiki-mcp` | MCP tool of the agents: `RemoteTool` / `AgenticIdentityToken`, target `DOCWIKI_MCP_URL`, audience = MCP API identifier URI |
| Foundry agents (hooks) | `docwiki-researcher`, `docwiki-librarian` | Each with its own Entra agent identity (ADR 0003); app roles and MCP allowlist set by the hooks |

---

## Step 1 — Prerequisites

GOAL: The machine has the tools used by azd, the hooks and the verification steps.

COMMAND:

```bash
az version --output table
azd version
az bicep version
python --version
uv --version
git --version
```

VERIFY: Azure CLI ≥ 2.67, azd ≥ 1.23.8 (Container Apps jobs as azd services), Bicep ≥ 0.33,
Python ≥ 3.12 (on Linux/macOS the hooks call `python3`), uv installed. Docker is **not**
required: images are built in the registry. Node 22+ is only needed for local site builds.

ON_FAIL: Install or upgrade the missing tool: `az upgrade`, `az bicep install` (or
`az bicep upgrade`), azd from <https://aka.ms/azd-install>, Python 3.12 from python.org, uv
from <https://docs.astral.sh/uv/>. Re-run the commands.

## Step 2 — Sign in and choose the subscription

GOAL: az and azd are signed in to the tenant and the subscription that will host DocWiki.

COMMAND:

```bash
az login
azd auth login
az account list --query "[].{name:name, state:state, default:isDefault}" --output table
az account set --subscription "<subscription name or id>"
```

VERIFY: `az account show --query "{name:name, state:state}" --output table` shows the chosen
subscription with state `Enabled`, and `azd auth login --check-status` reports a signed-in
account.

ON_FAIL: For multi-tenant accounts use `az login --tenant <tenant>` and
`azd auth login --tenant-id <tenant>`. If conditional access requires a fresh sign-in
(`InteractionRequired`), run `az logout` then `az login` again.

## Step 3 — Create the azd environment

GOAL: A new azd environment pinned to the subscription and an allowed region.

COMMAND:

```bash
azd env new <env-name> --subscription "<subscription id>" --location swedencentral
azd env select <env-name>
```

Allowed regions: `swedencentral` (default), `eastus2`, `westeurope` — regions where Foundry
models, agents and Content Understanding are available.

VERIFY: `azd env list` marks `<env-name>` as default, and
`azd env get-value AZURE_LOCATION` prints an allowed region.

ON_FAIL: Pick another environment name if it already exists (`azd env list`). Fix the region
with `azd env set AZURE_LOCATION swedencentral`.

## Step 4 — Set the deployment parameters

GOAL: The environment holds every value that differs from the defaults of `infra/main.bicep`.
Values are read by `infra/main.parameters.json`; unset values use the template defaults.

COMMAND (budget contacts are required for cost alerts; the rest is optional):

```bash
azd env set BUDGET_CONTACT_EMAILS "<address>[,<address>]"
azd env set DOCWIKI_BUDGET_AMOUNT 50
azd env set DOCWIKI_MCP_MIN_REPLICAS 0
```

| Variable | Default | Meaning |
|---|---|---|
| `AZURE_LOCATION` | `swedencentral` | Region (allowed: `swedencentral`, `eastus2`, `westeurope`) |
| `DOCWIKI_FAST_MODEL` / `DOCWIKI_FAST_MODEL_VERSION` / `DOCWIKI_FAST_CAPACITY` | `gpt-5.4-mini` / `2026-03-17` / `100` | `fast` deployment (capacity in 1,000 tokens per minute) |
| `DOCWIKI_SMART_MODEL` / `DOCWIKI_SMART_MODEL_VERSION` / `DOCWIKI_SMART_CAPACITY` | `gpt-5.5` / `2026-04-24` / `100` | `smart` deployment (pipeline compilation and both agents) |
| `DOCWIKI_DEPLOYMENT_SKU` | `GlobalStandard` | Or `DataZoneStandard` to keep model processing in the EU or US data zone (smaller quota, about 10 % higher list price) |
| `DOCWIKI_MCP_MIN_REPLICAS` | `0` | `1` keeps the MCP server warm for demos (from zero, a cold start adds about 30 s to an agent turn) |
| `DOCWIKI_ENABLE_PORTAL` | `false` | Portal Container App serving the current release's site (Entra sign-in by default) |
| `DOCWIKI_PORTAL_ACCESS` | `entra` | `public` serves the portal without sign-in; honoured only with `DOCWIKI_AUDIENCE=public`, otherwise the portal gets no ingress |
| `DOCWIKI_ENABLE_STUDIO` | `false` | DocWiki Studio ([docs/studio.md](docs/studio.md)): owner-only web app to upload documents, follow runs and ask the agents; always behind Entra sign-in |
| `DOCWIKI_STUDIO_MIN_REPLICAS` | `1` | `0` lets the Studio scale to zero (questions in flight are then lost when it does) |
| `DOCWIKI_ENABLE_EVENT_TRIGGER` | `true` | `false` makes the ingest job manual |
| `DOCWIKI_RECONCILE_CRON` | `0 */6 * * *` | Reconcile schedule (UTC) |
| `DOCWIKI_AUDIENCE` | `internal` | Build audience (`public`, `internal`, `restricted`) |
| `DOCWIKI_DOMAIN` | `batiment` | Domain pack |
| `DOCWIKI_CONTENT_UNDERSTANDING` | `true` | Extract with Content Understanding (`prebuilt-layout`) |
| `DOCWIKI_ENABLE_ROUTINE` | `false` | `true` deploys the Librarian routine enabled (`agents/deploy.py --routine enable`); back to `false` disables it |
| `DOCWIKI_ENABLE_FOUNDRY_SKILLS_PREVIEW` | `false` | Opt-in Foundry skills preview for the agents |
| `DOCWIKI_MCP_CONNECTION` | `docwiki-mcp` | Name of the agents' MCP project connection |
| `DOCWIKI_MCP_BLOCKED_AGENTS` | unset | Agent keys (`researcher`, `librarian`) kept out of the MCP app's allowlist (kill switch) |
| `DOCWIKI_MCP_TOKEN_VALIDATION` | `required` | The MCP server validates the bearer token forwarded by built-in auth; `off` only after Step 12 showed that the platform does not forward it |
| `DOCWIKI_SKIP_AGENTS` | unset | `true` skips the MCP connection and agent deployment in the `postprovision` hook |
| `DOCWIKI_BUDGET_AMOUNT` / `BUDGET_CONTACT_EMAILS` | `50` / empty | Monthly budget; no budget is created without contacts |
| `DOCWIKI_CU_DEFAULTS` | unset | `true` sets Content Understanding model defaults (not needed for `prebuilt-layout`) |
| `DOCWIKI_NETWORK_PERIMETER` | `false` | `true` secures the storage account with a network security perimeter (`publicNetworkAccess` `SecuredByPerimeter`: managed identities of the subscription and `DOCWIKI_ALLOWED_IP_RANGES` only) instead of open public access; required where a policy turns public network access off on storage accounts (Step 8). Event Grid cannot create its subscription inside the perimeter: provision once without the perimeter (the subscription then keeps delivering), or rely on the reconcile schedule, a manual job start or an ingest message |
| `DOCWIKI_ALLOWED_IP_RANGES` | unset | With the perimeter: comma-separated public CIDR ranges allowed to reach storage (the workstation that uploads to `raw/`; the address Azure sees is `SourceIpAddress` in the `NSPAccessLogs` table); never commit them |

After the first `azd provision` the deployed model settings are written back to the
environment, so a newer template default never changes the models of an existing
environment silently.

VERIFY: `azd env get-value BUDGET_CONTACT_EMAILS` is set (do not print it in shared logs) and
every variable you changed reads back with `azd env get-value <NAME>`.

ON_FAIL: Re-run `azd env set` with the corrected value. To return to a template default,
delete the line from `.azure/<env>/.env` (local file, never committed).

## Step 5 — Preflight

GOAL: Detect every blocker before resources are created. The same checks run automatically
as the azd `preprovision` hook.

COMMAND:

```bash
python scripts/preflight.py
```

(`--json` for machine-readable output, `--strict` to fail on warnings,
`--skip roles,entra` only when the owner accepted the risk.)

VERIFY: The last line reads `preflight: 0 failed`. Checks: tool versions, az/azd sign-in,
subscription state, allowed region, resource providers, both models offered in the region
with the chosen deployment type and GA lifecycle, model quota, deployer roles (Owner, or
Contributor + User Access Administrator; both include
`Microsoft.Authorization/roleDefinitions/write`, which the Studio's custom role on `work` needs),
permission to register Entra applications, budget contacts, no soft-deleted Foundry account
blocking the name.

ON_FAIL: Apply the `fix:` line printed under each failed check. Typical fixes:

- `quota:*` — lower `DOCWIKI_FAST_CAPACITY` / `DOCWIKI_SMART_CAPACITY`, choose
  `DOCWIKI_DEPLOYMENT_SKU GlobalStandard` (with the owner's agreement), or request quota.
- `model-*` — pick a model and version listed by the check (with the owner's agreement).
- `resource-providers` — run the printed `az provider register` commands and wait until
  `az provider show --namespace <ns> --query registrationState` is `Registered`.
- `deployer-roles` / `entra-app-registration` — ask an administrator; activate PIM roles.
- `foundry-soft-delete` — run the printed `az cognitiveservices account purge` command.

## Step 6 — Provision and deploy

GOAL: All resources exist, images are built remotely and deployed, the MCP API app
registration and built-in auth are configured, the reconcile job runs the pipeline image.

COMMAND:

```bash
azd up --no-prompt
```

`azd up` runs: `preprovision` hook (preflight) → Bicep deployment → `postprovision` hook (MCP
API app registration with app roles `Wiki.Read`/`Wiki.Operate`, built-in auth `Return401` on
the MCP app — verified with `az containerapp auth show` before the server's token settings
`DOCWIKI_MCP_*` are set and only then external ingress is enabled —, optional portal sign-in, the
agents' MCP project connection, `agents/deploy.py --json` when present, app roles for the agent
identities, the built-in auth allowlist of the agents (also the server's own caller allowlist),
optional Content Understanding defaults) → remote image builds in the registry for the `job`,
`mcp` and `portal` services → `postdeploy` hook (reconcile job image, MCP smoke test). Expect
15–30 minutes on the first run. On the first provision the MCP app has no external ingress
(Bicep declares it only once the MCP API app registration exists): if the hook fails, the app
stays unreachable until `azd hooks run postprovision` succeeds.

VERIFY:

```bash
azd show
azd env get-value DOCWIKI_MCP_URL
azd env get-value DOCWIKI_MCP_API_AUDIENCE
```

`azd show` lists the three services; the MCP URL ends with `/mcp`; the audience has the form
`api://<client id>`. The `postprovision` output contains `built-in auth on ca-mcp-… verified`
before `enabling external ingress on ca-mcp-…` (first run). The `postdeploy` output contains
`MCP built-in auth is enabled (Return401)`, `MCP endpoint rejects unauthenticated calls (401)`
and `MCP endpoint rejects a forged principal header without a token (401)`.

ON_FAIL:

- Event Grid subscription creation fails with `Managed identity for event subscription does not
  have authorization to deliver to the endpoint` right after the role assignment: role
  propagation; wait 2 minutes and run `azd provision`. If it persists, check that the system
  topic's identity holds Storage Queue Data Message Sender **on the storage account** (Event Grid
  validates the account scope; a queue-scoped assignment is not enough).
- `ACR Tasks` / remote build refused (some free or sponsored subscriptions): use a
  subscription with ACR Tasks enabled; there is no local-build fallback without Docker.
- Base image pull throttled (`toomanyrequests`): retry later or mirror the base images (see
  [`docs/operations.md`](docs/operations.md#images-and-updates)).
- Hook failures print an `ERROR` and a `remediation`; fix and re-run only the hook:
  `azd hooks run postprovision` or `azd hooks run postdeploy`. `the signed-in session needs a
  fresh sign-in` means continuous access evaluation revoked the cached Microsoft Graph token:
  `az logout`, `az login`, `azd auth login`, then re-run the hook (or, with the owner's
  agreement, set `DOCWIKI_GRAPH_TOKEN_SOURCE=azd` so the hooks use the azd sign-in for Graph
  after checking it is the same account).
- Model deployment errors (`InsufficientQuota`, `DeploymentModelNotSupported`): go back to
  Step 5.
- Budget creation refused (subscription types without Cost Management budgets): with the
  owner's agreement run `azd env set DOCWIKI_BUDGET_AMOUNT 0` and `azd provision`, and set the
  alerts on the billing account instead.

## Step 7 — Verify resources, security settings and RBAC

GOAL: The deployment matches the zero-secret design and the access model of
`docs/spec/architecture.md` §6.

COMMAND:

```bash
az resource list --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) --query "[].{type:type, name:name}" --output table
az storage account show --name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --query "{sharedKey:allowSharedKeyAccess, publicBlob:allowBlobPublicAccess, tls:minimumTlsVersion}"
az cognitiveservices account show --name $(azd env get-value DOCWIKI_FOUNDRY_ACCOUNT_NAME) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) --query "{localAuth:properties.disableLocalAuth, projects:properties.allowProjectManagement}"
az cognitiveservices account deployment list --name $(azd env get-value DOCWIKI_FOUNDRY_ACCOUNT_NAME) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) --query "[].{name:name, model:properties.model.name, version:properties.model.version, sku:sku.name, capacity:sku.capacity}" --output table
az acr show --name $(azd env get-value AZURE_CONTAINER_REGISTRY_NAME) --query "{admin:adminUserEnabled}"
az role assignment list --assignee $(azd env get-value DOCWIKI_RUNTIME_IDENTITY_PRINCIPAL_ID) --all --query "[].{role:roleDefinitionName, scope:scope}" --output table
az role assignment list --assignee $(azd env get-value DOCWIKI_MCP_IDENTITY_PRINCIPAL_ID) --all --query "[].{role:roleDefinitionName, scope:scope, condition:condition}" --output json
az role assignment list --assignee $(azd env get-value DOCWIKI_PORTAL_IDENTITY_PRINCIPAL_ID) --all --query "[].{role:roleDefinitionName, scope:scope}" --output table
az eventgrid system-topic event-subscription show --name raw-to-ingest --system-topic-name $(azd env get-value DOCWIKI_EVENT_GRID_SYSTEM_TOPIC) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) --query "{state:provisioningState, subject:filter.subjectBeginsWith, types:filter.includedEventTypes}"
az eventgrid system-topic event-subscription show --name inbox-to-ingest --system-topic-name $(azd env get-value DOCWIKI_EVENT_GRID_SYSTEM_TOPIC) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) --query "{state:provisioningState, subject:filter.subjectBeginsWith, types:filter.includedEventTypes}"
az containerapp job show --name $(azd env get-value DOCWIKI_INGEST_JOB_NAME) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) --query "properties.configuration.{trigger:triggerType, timeout:replicaTimeout, retries:replicaRetryLimit, scale:eventTriggerConfig.scale}"
az containerapp auth show --name $(azd env get-value DOCWIKI_MCP_APP_NAME) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) --query "{enabled:platform.enabled, action:globalValidation.unauthenticatedClientAction, excluded:globalValidation.excludedPaths, issuer:identityProviders.azureActiveDirectory.registration.openIdIssuer, audiences:identityProviders.azureActiveDirectory.validation.allowedAudiences, allowed:identityProviders.azureActiveDirectory.validation.defaultAuthorizationPolicy.allowedApplications}"
az containerapp show --name $(azd env get-value DOCWIKI_MCP_APP_NAME) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) --query "{external:properties.configuration.ingress.external, settings:properties.template.containers[0].env[?starts_with(name, 'DOCWIKI_MCP_')].name, validation:properties.template.containers[0].env[?name=='DOCWIKI_MCP_TOKEN_VALIDATION'].value | [0]}"
az rest --method GET --url "https://management.azure.com/subscriptions/$(azd env get-value AZURE_SUBSCRIPTION_ID)/resourceGroups/$(azd env get-value AZURE_RESOURCE_GROUP)/providers/Microsoft.CognitiveServices/accounts/$(azd env get-value DOCWIKI_FOUNDRY_ACCOUNT_NAME)/projects/$(azd env get-value DOCWIKI_FOUNDRY_PROJECT_NAME)/connections/$(azd env get-value DOCWIKI_MCP_CONNECTION)?api-version=2025-10-01-preview" --query "properties.{category:category, auth:authType, target:target, audience:audience}"
```

VERIFY:

- Storage `sharedKey` and `publicBlob` are `false`; Foundry `localAuth` is `true`; registry
  `admin` is `false`.
- Deployments `fast` and `smart` show the expected model, version, type and capacity.
- The jobs identity (`DOCWIKI_RUNTIME_IDENTITY_*`) holds: Storage Blob Data Reader on
  `.../containers/raw`; Storage Blob Data Contributor on `work` and `releases`; Storage Queue
  Data Contributor on `.../queues/ingest` (needed to renew message visibility during long runs);
  Message Sender on `ingest-poison`;
  Cognitive Services User and Azure AI User on the Foundry account; AcrPull on the registry;
  Monitoring Metrics Publisher on Application Insights.
- The MCP identity (`DOCWIKI_MCP_IDENTITY_*`) holds: Storage Blob Data Reader on `releases`;
  Storage Blob Data Contributor on `work` **with a condition** (its `condition` limits writes
  to `reports/`, `proposals/` and `state/overlay.yaml`); Storage Queue Data Message Sender on
  `ingest`; AcrPull; Monitoring Metrics Publisher. Nothing on `raw` or on Foundry.
- The portal identity (`DOCWIKI_PORTAL_IDENTITY_*`) holds: Storage Blob Data Reader on
  `releases`; AcrPull; Monitoring Metrics Publisher.
- The Event Grid subscription `raw-to-ingest` is `Succeeded`, filtered on `/blobServices/default/containers/raw/blobs/`
  with `Microsoft.Storage.BlobCreated` and `Microsoft.Storage.BlobDeleted`, and `inbox-to-ingest`
  is `Succeeded`, filtered on `/blobServices/default/containers/work/blobs/inbox/queries/` with
  `Microsoft.Storage.BlobCreated`; the system topic's
  identity holds Storage Queue Data Message Sender on the storage account. (With
  `DOCWIKI_NETWORK_PERIMETER=true` the subscription is no longer declared: Event Grid cannot
  create or update it inside the perimeter, but one created by an earlier provision keeps
  delivering.)
- The ingest job is `Event`-triggered, timeout 3600, 1 retry, `maxExecutions` 1, polling 30 s.
- MCP auth (ADR 0003): enabled, `Return401`, `excluded` is `["/healthz"]`, the issuer ends with
  `/v2.0`, the only audience is `api://<client id>` (v2 tokens carry the client ID, which is
  accepted implicitly), and `allowed` lists the client IDs of the two agent identities
  (`azd env get-value DOCWIKI_MCP_ALLOWED_CLIENT_IDS`; empty before the agents are deployed,
  which means 403 for every agent).
- MCP app: `external` is `true` (only ever after the auth above is verified); `settings` lists
  `DOCWIKI_MCP_TENANT_ID`, `DOCWIKI_MCP_TOKEN_VALIDATION`, `DOCWIKI_MCP_AUDIENCE` and, once the
  agents exist, `DOCWIKI_MCP_ALLOWED_CLIENT_IDS`; `validation` is `required` (the server validates
  the bearer token forwarded by built-in auth; `off` only after the explicit opt-out of Step 12).
- The MCP connection is `RemoteTool` / `AgenticIdentityToken`, targets `DOCWIKI_MCP_URL` and
  has the audience `DOCWIKI_MCP_API_AUDIENCE`.

ON_FAIL: Re-run `azd provision` (idempotent). If auth is missing, run
`azd hooks run postprovision` and check its output. Report any persistent difference as an
infrastructure bug; do not fix it by hand in the portal.

## Step 8 — Upload the sample corpus to `raw/`

GOAL: Sample documents land in `raw/`; Event Grid queues a wake-up message per blob.

COMMAND (Entra sign-in, no keys; the deployer received Storage Blob Data Contributor on
`raw` during provisioning):

```bash
az storage blob upload-batch --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --destination raw --source samples/corpus/full --auth-mode login
```

`samples/corpus/full` holds the 12 public documents and, under `restricted/`, the restricted
internal price study. Every document is fictional, and the two site photos are AI-generated images
(model and prompts in `samples/generators/assets/photos/PROVENANCE.md`). Upload the restricted
study too: its sensitivity rule keeps it out of any build below the `restricted` audience
(gate G07), so a `public` or `internal` deployment never serves it. Do not upload
`samples/corpus/held-back/`: it is the document of the live upload demo
([`docs/studio.md`](docs/studio.md#time-travel-optional)). With azcopy: `azcopy login` then
`azcopy copy "samples/corpus/full/*" "https://<account>.blob.core.windows.net/raw/" --recursive`.

VERIFY:

```bash
az storage blob list --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --container-name raw --auth-mode login --num-results "*" --query "length(@)"
az storage message peek --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --queue-name ingest --auth-mode login --num-messages 5 --query "length(@)"
```

The blob count matches the uploaded files (13: the 12 public documents and the restricted one); the
queue shows messages (or is already empty because the job consumed them — Step 9 tells).

ON_FAIL: `AuthorizationPermissionMismatch`: role assignments take up to 10 minutes to apply;
retry. If `AZURE_PRINCIPAL_ID` was empty during provisioning, run `azd provision` again while
signed in with azd. If no messages appear, check the Event Grid subscription (Step 7) and its
delivery metrics: `az monitor metrics list --resource <system topic id> --metric DeliverySuccessCount`.
`AuthorizationFailure` ("The request may be blocked by network rules"): run
`az storage account show --name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --query publicNetworkAccess`.
`Disabled` although the template sets `Enabled` means a policy of the tenant turned public
network access off (look for a Modify policy in `az policy state list --resource <account id>`);
the jobs, the MCP app, the queue scaler and Event Grid are cut off as well. Do not work around
the policy: switch to the perimeter with `azd env set DOCWIKI_NETWORK_PERIMETER true` and
`azd env set DOCWIKI_ALLOWED_IP_RANGES <public address of this workstation>/32`, then
`azd provision` and retry the upload (update the range when the address changes; a request
still denied by the perimeter is logged in `NSPAccessLogs` with the `SourceIpAddress` Azure
saw). With the perimeter, the event subscription must exist from a provision without it
(Step 7): Event Grid cannot create or re-create it inside the perimeter, so turn the perimeter
off temporarily to re-create it; otherwise start the reconcile job after the upload (Step 9,
ON_FAIL).

## Step 9 — Watch the job execution

GOAL: The ingest job wakes up from the queue, compiles the corpus and succeeds.

COMMAND:

```bash
az containerapp job execution list --name $(azd env get-value DOCWIKI_INGEST_JOB_NAME) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) --query "[].{name:name, status:properties.status, start:properties.startTime, end:properties.endTime}" --output table
az monitor log-analytics query --workspace $(azd env get-value DOCWIKI_LOG_ANALYTICS_WORKSPACE_ID) --analytics-query "ContainerAppConsoleLogs | where ContainerAppName startswith 'caj-ingest' or JobName startswith 'caj-ingest' | project TimeGenerated, Log | top 50 by TimeGenerated" --output table
```

VERIFY: An execution appears within about a minute of the upload (polling 30 s + debounce
30 s) and ends `Succeeded`. Only one execution runs at a time. Logs carry `run_id`, `stage`
and `source_id`.

ON_FAIL:

- No execution: check KEDA events with
  `ContainerAppSystemLogs | where JobName startswith 'caj-ingest' | top 50 by TimeGenerated`;
  `Unauthorized` on the queue means the jobs identity lacks Storage Queue Data Contributor on
  `ingest` (re-run `azd provision`). Start a run by hand:
  `az containerapp job start --name $(azd env get-value DOCWIKI_RECONCILE_JOB_NAME) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP)`.
- `Failed`: read the logs, then the run report (`work/runs/<run_id>/report.json`, see
  [`docs/operations.md`](docs/operations.md#runs-reports-and-receipts)). A failing blocking
  gate keeps the previous release current by design. Systemic failures (models, Content
  Understanding, storage, queue, lost lease) keep their messages and are retried; deterministic
  ones (blocking gates, final validation, invalid domain pack) acknowledge them, so the
  execution may end `Succeeded` while the report says `failed` with
  `deterministic failure: not retried …`: fix the cause, then upload or recompile. A report
  stuck in `running` after `az containerapp job stop` or a timeout is closed as
  `abandoned: the execution ended before finishing` by the next execution.
- The job still runs the placeholder image (`quickstart-jobs`): run `azd deploy job`.

## Step 10 — Check the release pointer

GOAL: A validated release was published and `releases/current.json` points at it.

COMMAND (`.local/` is git-ignored):

```bash
python -c "import pathlib; pathlib.Path('.local').mkdir(exist_ok=True)"
az storage blob download --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --container-name releases --name current.json --file .local/current.json --auth-mode login --output none
python -c "import json; p = json.load(open('.local/current.json', encoding='utf-8')); print(p['release_id'], p['audience'], p['created_at'])"
```

VERIFY: `release_id` has the form `YYYYMMDDTHHMMSSZ-xxxxxxxx`, `audience` is the
`DOCWIKI_AUDIENCE` value, and
`az storage blob list --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --container-name releases --prefix <release_id>/manifest.json --auth-mode login --num-results "*" --query "length(@)"`
returns `1`.

ON_FAIL: No `current.json` means no release was published yet: go back to Step 9 and read the
gate results in the run report.

## Step 11 — Call the MCP endpoint

GOAL: The MCP server is reachable only with a valid token for its audience, behind enabled
built-in auth.

COMMAND:

```bash
python scripts/hooks/postdeploy.py --smoke-only
```

VERIFY: The output contains `MCP built-in auth is enabled (Return401)`,
`MCP endpoint rejects unauthenticated calls (401)`,
`MCP endpoint rejects a forged principal header without a token (401)`,
`MCP endpoint rejects a token for another audience (401)` and `MCP /healthz answers 200`
(before the first release: `MCP /healthz answers 503: no release published yet`, which is
expected — `/healthz` is excluded from built-in auth and reports whether a release is served).
The script exits 0. It never prints tokens. A 401 without a token alone proves nothing (the
server answers it by itself); the auth check and the forged-header probe are what show that both
built-in auth and the server's token validation are in place.

ON_FAIL: A 2xx without a valid token, or any answer other than 401 to the forged header, is a
security failure: stop traffic with `az containerapp ingress disable --name $(azd env get-value DOCWIKI_MCP_APP_NAME) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP)`,
run `azd hooks run postprovision` (it re-enables ingress only after verifying built-in auth),
check `az containerapp auth show` (Step 7) and do not continue until the smoke test passes.
`built-in auth is not enabled on …` means the auth config is missing or switched off: run
`azd hooks run postprovision`. With `DOCWIKI_MCP_MIN_REPLICAS=0` the app scales to zero after
about 8.5 minutes idle and the first request takes about 20–25 s (measured: 22.6 s cold versus
1.2 s warm); re-run before investigating. `/healthz` other than 200 or 503 means the server
image is missing or crashing: `azd deploy mcp`, then read `ContainerAppConsoleLogs` for
`ca-mcp-*` (built-in auth decisions are logged there too; a server that stops at start with
`DOCWIKI_AUTH_MODE=easyauth validates the bearer token …` lacks its token settings: run
`azd hooks run postprovision`). A 503 after Step 10 succeeded means the server cannot read
`releases/` (check the MCP identity, Step 7).

## Step 12 — Deploy and smoke-test the agents

GOAL: The Researcher and Librarian Foundry agents exist and reach the MCP server each with its
own Entra agent identity and the roles of `docs/spec/mcp-and-agents.md`
([ADR 0003](docs/adr/0003-mcp-agent-identity.md)).

COMMAND:

```bash
python scripts/hooks/postprovision.py --only mcp-connection,agents,agent-roles,mcp-allowlist
uv run --extra azure docwiki ask "Which revision of quote DEV-2026-014 is current, and which revision did it replace?" --agent researcher
uv run --extra azure docwiki ask "What is the status of the last run?" --agent librarian
```

`azd up` already ran these steps; re-running them is idempotent. The hook:

1. creates or updates the project connection `DOCWIKI_MCP_CONNECTION` (default `docwiki-mcp`)
   through Azure Resource Manager: category `RemoteTool`, auth type `AgenticIdentityToken`,
   target `DOCWIKI_MCP_URL`, audience `DOCWIKI_MCP_API_AUDIENCE` (`api://<client id>`), API
   version `2025-10-01-preview` (same properties as `infra/modules/mcp-connection.bicep`, which
   later provisions keep in place);
2. runs `agents/deploy.py --json` with `DOCWIKI_FOUNDRY_PROJECT_ENDPOINT`,
   `DOCWIKI_SMART_DEPLOYMENT`, `DOCWIKI_MCP_URL` and `DOCWIKI_MCP_CONNECTION`, adding
   `--routine enable` when `DOCWIKI_ENABLE_ROUTINE` is `true` (`--routine disable` when it was
   enabled before), and records each agent's identity (`instance_identity`: principal ID and
   client ID) in `.azure/<env>/docwiki-state.json`;
3. assigns the MCP API app roles to the agent identities: Researcher `Wiki.Read`, Librarian
   `Wiki.Read` and `Wiki.Operate`;
4. sets the built-in auth allowlist (`allowedApplications`) of the MCP app to the agents'
   client IDs and records them in `DOCWIKI_MCP_ALLOWED_CLIENT_IDS` (later provisions keep it);
   once `az containerapp auth show` confirms it, the same list becomes the MCP server's own
   caller allowlist (`DOCWIKI_MCP_ALLOWED_CLIENT_IDS` on the `mcp` app).

VERIFY: The hook prints `MCP connection docwiki-mcp` (`creating` or `already configured`), one
line per agent (`docwiki-researcher: created (version …)` or `unchanged`), then
`researcher: Wiki.Read granted`, `librarian: Wiki.Read granted`,
`librarian: Wiki.Operate granted` and `MCP built-in auth allows: researcher, librarian`. The
Researcher answers with numbered citations that point to evidence sidecars; the Librarian
reports the last run with `run_status`. Operations tools are not even listed for the
Researcher, and a direct call is answered with the result
`{"ok": false, "error": {"code": "forbidden", …}}` (the agent turn continues). A cold MCP app
adds about 30 s to an agent turn (38.8 s cold versus about 8 s warm in the identity spike); set
`DOCWIKI_MCP_MIN_REPLICAS=1` and `azd provision` for demos.

The agent answers also verify a platform behaviour the documentation leaves implicit: built-in
auth passes the caller's `Authorization` header on to the container, where the MCP server
validates the token again ([`src/docwiki/mcp/README.md`](src/docwiki/mcp/README.md#bearer-token-validation)).
Confirm that the server saw no request without it since the agents ran (expect `0`):

```bash
az monitor log-analytics query --workspace $(azd env get-value DOCWIKI_LOG_ANALYTICS_WORKSPACE_ID) --analytics-query "ContainerAppConsoleLogs | where ContainerAppName startswith 'ca-mcp' and Log has 'without a valid bearer token header but with' | where TimeGenerated > ago(1h) | count" --output table
```

ON_FAIL:

- `agents/deploy.py failed`: the last lines of its error are printed (unset `DOCWIKI_*` value,
  connection missing or with another target or auth type); fix and re-run.
- `the MCP connection authenticates each agent with its own identity, but … declares …`: set
  `auth.strategy: per-agent-identity` in `agents/<agent>/agent.yaml` (ADR 0003).
- `no agent identity for the … agent`: `agents/deploy.py` did not report it; re-run the agents
  step, or set `DOCWIKI_RESEARCHER_PRINCIPAL_ID` / `DOCWIKI_LIBRARIAN_PRINCIPAL_ID` (and the
  matching `_CLIENT_ID`) by hand, then re-run.
- `reports the same identity as another agent … Wiki.Operate withheld`: both agents reported one
  principal, so only `Wiki.Read` is granted (least privilege); check the agents in the Foundry
  portal (each must have its own agent identity) and re-run.
- 403 from the MCP tool: the agent's client ID is missing from the allowlist (an agent that was
  deleted and recreated gets a new identity); re-run the command above. 401: wrong audience
  or token; compare the connection audience with `DOCWIKI_MCP_API_AUDIENCE`, and the
  `DOCWIKI_MCP_AUDIENCE` / `DOCWIKI_MCP_ALLOWED_CLIENT_IDS` settings of the `mcp` app (Step 7)
  with its built-in auth (the server logs `rejected request: bearer token …` with the reason).
  Foundry error `Failed to fetch agentic identity access token` (`AADSTS501051`): the agent has
  no app role yet. Agent traces are in the Foundry portal (Agents → Traces) and in Application
  Insights.
- Every agent call gets 401 and the query above returns more than `0`: the platform did not pass
  the `Authorization` header on to the container, so the server cannot validate the token.
  Record it, then opt out explicitly: `azd env set DOCWIKI_MCP_TOKEN_VALIDATION off`,
  `azd provision` (the server trusts the principal header of built-in auth again and logs a
  warning at start-up), re-run Step 11 and this step, and report the platform behaviour.

## Step 13 — Cost check

GOAL: Spending is visible and bounded.

COMMAND:

```bash
az consumption budget list --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) --query "[].{name:name, amount:amount, spent:currentSpend.amount}" --output table
az storage blob list --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --container-name work --prefix runs/ --auth-mode login --query "[].name" --output tsv
```

VERIFY: The budget exists with the configured amount (only when `BUDGET_CONTACT_EMAILS` is
set). Each run report (`work/runs/<run_id>/report.json`) carries a cost receipt (tokens ×
price table, Content Understanding pages, duration); see
[`docs/operations.md`](docs/operations.md#budgets-and-cost). The Cost analysis blade of the
resource group shows month-to-date spend. Expect one-time costs: the first full ingest compiles
every document (see [`docs/cost.md`](docs/cost.md)), so a 50 budget alert can fire during the first
days of experimentation; an idle environment costs close to nothing.

ON_FAIL: No budget: set `BUDGET_CONTACT_EMAILS` and run `azd provision`. Unexpected spend:
check for repeated job executions (poison loops), `DOCWIKI_MCP_MIN_REPLICAS` above 0, and
large re-ingests; the price table of the receipts is a placeholder until verified
(`src/docwiki/llm/README.md`).

## Step 14 — Teardown

GOAL: Nothing of the environment remains: Foundry agents (and their Entra agent identities),
resource group, soft-deleted Foundry account and the Entra app registrations created by the
hooks.

COMMAND:

```bash
azd down --purge --force
```

`azd down` first runs the `predown` hook (`python scripts/teardown.py --agents-only --yes`):
deleting each agent deletes its Entra agent identity and blueprint, which a resource group
deletion would leave behind. azd then deletes the resource group and purges soft-deleted
resources; its `postdown` hook runs `python scripts/teardown.py --entra-only --yes`, which
deletes the app registrations recorded in `.azure/<env>/docwiki-state.json` and purges them
from the Entra deleted items. Without azd: `python scripts/teardown.py --yes` does the same in
the same order (`--dry-run` shows the plan, `--no-purge` keeps things recoverable).

VERIFY:

```bash
az group exists --name $(azd env get-value AZURE_RESOURCE_GROUP)
python scripts/teardown.py --dry-run
```

`az group exists` prints `false` and the dry run reports `nothing to delete`.

ON_FAIL:

- The group deletion fails or times out on the Foundry account with `CannotDeleteDefaultProject`
  or "nested resources exist" (a known Foundry issue, F13 in
  [`docs/spikes/identity-spike.md`](docs/spikes/identity-spike.md)): everything else is
  deleted and the empty account has no idle cost; `teardown.py` still removes the app
  registrations and reports the block. Re-run `python scripts/teardown.py --yes` later; if it
  keeps failing, open an Azure support request for the Foundry account.
- The group deletion was interrupted: re-run `azd down --purge --force` or
  `python scripts/teardown.py --yes`.
- `could not delete agent …`: delete the agent in the Foundry portal (Agents) while the project
  still exists; otherwise its agent identity remains in Entra ID (deleted items).
- App registrations that existed before the hooks ran are never deleted; remove them in
  Microsoft Entra ID if they are no longer needed. Without purge, deleted app registrations
  stay restorable for 30 days.

---

One maintenance procedure follows. It is not part of a first deployment.

## Reset the sample data

Replace everything an environment holds (documents, state and releases) with another corpus, for
example after the sample corpus or its domain pack changed. It destroys data: **run it only with
the explicit approval of the environment's owner**, and never skip the backup (R2).

Preconditions: you are signed in and pointed at the right azd environment (Steps 2 and 3); the
deployer holds Storage Blob Data Contributor on `raw`, `work` and `releases` and Storage Queue
Data Contributor on `ingest` and `ingest-poison` (Bicep grants them when
`grantDeployerDataAccess` is on); nobody is uploading through the Studio. `<backup>` is a new, empty
folder outside the repository, written without a trailing slash (never commit it). Delete
**blobs, never containers**: the role assignments, the Event Grid subscription and the queue
scaler are tied to them.

### R1 — Record the settings, update the pack and the job image, pause the writers

GOAL: Nothing writes to the environment while you back it up and reset it, and both jobs are
ready to compile the new corpus: pack `batiment`, new job image.

COMMAND:

```bash
azd env get-value DOCWIKI_ENABLE_EVENT_TRIGGER
azd env get-value DOCWIKI_RECONCILE_CRON
azd env get-value SERVICE_JOB_IMAGE_NAME
azd env set DOCWIKI_ENABLE_EVENT_TRIGGER false
azd env set DOCWIKI_RECONCILE_CRON "0 0 1 1 *"
azd env set DOCWIKI_DOMAIN batiment
azd provision
azd deploy job
```

Write down the values printed by the first three commands (an error means the template default
applies, `true` and `0 */6 * * *`, or, for the image, that none has been deployed yet); R5 restores
the first two and the VERIFY compares the third with the new image.

Two things do not follow the repository by themselves in an existing environment:

- **The pack.** After the first `azd provision`, azd saves the Bicep outputs, `DOCWIKI_DOMAIN`
  included, in `.azure/<env>/.env`, and `infra/main.parameters.json` feeds that value back into
  every later provision (Step 4 says the same of the models). The template default, `batiment`,
  therefore never applies to an environment provisioned with another pack: set it explicitly (a
  no-op when the environment already uses it).
- **The job image.** `domains/` is bundled in the job image, and `azd provision` never replaces a
  deployed image ([`docs/operations.md`](docs/operations.md#images-and-updates)), so an older image
  does not hold the pack. `azd deploy job` (or `azd deploy` for every service) builds a new one
  remotely, and its `postdeploy` hook copies it to the reconcile job
  ([`docs/domain-packs.md`](docs/domain-packs.md#workflow-for-a-new-pack)). Do it now, before any
  data is deleted: a failed build then costs nothing, and the job started in R4 finds its pack.

VERIFY (repeat it right before R3):

```bash
az containerapp job show --name $(azd env get-value DOCWIKI_INGEST_JOB_NAME) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) --query "properties.configuration.triggerType"
az containerapp job show --name $(azd env get-value DOCWIKI_RECONCILE_JOB_NAME) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) --query "properties.configuration.scheduleTriggerConfig.cronExpression"
az containerapp job execution list --name $(azd env get-value DOCWIKI_INGEST_JOB_NAME) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) --query "[?properties.status=='Running'].name" --output tsv
az containerapp job execution list --name $(azd env get-value DOCWIKI_RECONCILE_JOB_NAME) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) --query "[?properties.status=='Running'].name" --output tsv
az storage blob show --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --container-name work --name state/lease --auth-mode login --query "properties.lease.status"
azd env get-value SERVICE_JOB_IMAGE_NAME
az containerapp job show --name $(azd env get-value DOCWIKI_INGEST_JOB_NAME) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) --query "{pack: properties.template.containers[0].env[?name=='DOCWIKI_DOMAIN'].value | [0], image: properties.template.containers[0].image}"
az containerapp job show --name $(azd env get-value DOCWIKI_RECONCILE_JOB_NAME) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) --query "{pack: properties.template.containers[0].env[?name=='DOCWIKI_DOMAIN'].value | [0], image: properties.template.containers[0].image}"
```

The ingest job reads `"Manual"`, the reconcile job `"0 0 1 1 *"`, both execution lists are empty,
and the run lease reads `"unlocked"` (or the blob does not exist because no run ever took it).
Both jobs report the pack `batiment` and the same image, the one `SERVICE_JOB_IMAGE_NAME` names,
whose tag differs from the one you wrote down.

ON_FAIL: An execution is still running: let it finish (stopping it leaves an `abandoned`
report). `azd provision` refuses to change the trigger of the existing job: stop and report it;
do not delete the job by hand. `azd deploy job` fails, or a job still reports the old pack or
image: Step 6 ON_FAIL (remote build, hooks), then repeat the command; do not go on without the new
image.

### R2 — Back up

GOAL: A complete copy of the data exists outside the environment.

COMMAND (`download-batch` writes into **existing** folders, so create them first):

```bash
python -c "import pathlib; [pathlib.Path(r'<backup>', name).mkdir(parents=True, exist_ok=True) for name in ('raw', 'work', 'releases')]"
az storage blob download-batch --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --source raw --destination "<backup>/raw" --auth-mode login
az storage blob download-batch --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --source work --destination "<backup>/work" --auth-mode login
az storage blob download-batch --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --source releases --destination "<backup>/releases" --auth-mode login
```

VERIFY: Each backup folder holds as many files as its container has blobs. Count the blobs
(`--num-results "*"` lists them all; the default stops at 5,000), then the local files, and
compare the three pairs:

```bash
az storage blob list --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --container-name raw --auth-mode login --num-results "*" --query "length(@)"
az storage blob list --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --container-name work --auth-mode login --num-results "*" --query "length(@)"
az storage blob list --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --container-name releases --auth-mode login --num-results "*" --query "length(@)"
python -c "import pathlib; [print(name, sum(p.is_file() for p in pathlib.Path(r'<backup>', name).rglob('*'))) for name in ('raw', 'work', 'releases')]"
```

The last command prints `raw <n>`, `work <n>` and `releases <n>`: each number equals the blob
count of its container. **Do not start R3 unless all three pairs match.**

ON_FAIL: A download fails with `AuthorizationPermissionMismatch`: a data role is missing or still
propagating (up to 10 minutes, Step 8). In an older environment, grant the missing role
temporarily with the owner's agreement and remove it in R5. A count differs, or a download
stopped half-way: repeat that download with `--overwrite true` (by default existing files are
kept as they are), then count again. Do not continue without a complete backup.

### R3 — Delete the data

GOAL: `raw`, `work` and `releases` hold no blob, and both queues hold no message.

Start only when the VERIFY of R2 matched for the three containers: once the blobs are deleted, the
backup is the only copy. Then run the VERIFY of R1 again: no execution may be running, and both
jobs still report the new image and the pack `batiment`.

COMMAND:

```bash
az storage blob delete-batch --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --source raw --auth-mode login
az storage blob delete-batch --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --source work --auth-mode login
az storage blob delete-batch --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --source releases --auth-mode login
```

Event Grid turns every deleted `raw` blob into a message on `ingest`: wait a minute, then clear
both queues:

```bash
az storage message clear --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --queue-name ingest --auth-mode login
az storage message clear --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --queue-name ingest-poison --auth-mode login
```

VERIFY: Each command prints `0`:

```bash
az storage blob list --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --container-name raw --auth-mode login --num-results "*" --query "length(@)"
az storage blob list --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --container-name work --auth-mode login --num-results "*" --query "length(@)"
az storage blob list --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --container-name releases --auth-mode login --num-results "*" --query "length(@)"
az storage message peek --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --queue-name ingest --auth-mode login --num-messages 5 --query "length(@)"
az storage message peek --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --queue-name ingest-poison --auth-mode login --num-messages 5 --query "length(@)"
```

ON_FAIL: A late event refilled `ingest`: clear it again. Versioning and soft delete keep the
deleted blobs recoverable for a few days (see
[`docs/operations.md`](docs/operations.md#rotate-and-retain-releases)), but they do not replace the
backup. Until the first new release is published, the MCP server and the portal keep what they
cached or report that no release is available.

### R4 — Upload the corpus and compile by hand

GOAL: The new corpus is compiled into the first release of the clean environment.

Both jobs must already report the pack `batiment` and the new image (the end of the R1 VERIFY):
check it before the start.

COMMAND:

```bash
az storage blob upload-batch --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --destination raw --source samples/corpus/full --auth-mode login
az containerapp job start --name $(azd env get-value DOCWIKI_INGEST_JOB_NAME) --resource-group $(azd env get-value AZURE_RESOURCE_GROUP)
```

VERIFY: Follow the execution to its end as in Step 9. It ends `Succeeded`, the newest run report
(`work/runs/<run_id>/report.json`) says `succeeded` (a deterministic failure also ends
`Succeeded`: read the report), and Step 10 finds a new `current.json` with the expected audience.
A cold compile calls the models for every document: expect the cost described in Step 13.

ON_FAIL: Step 9. The writers stay paused, so nothing else changes while you fix forward. Restore
the backup only when the old data must be served again: empty the containers as in R3, then
upload `<backup>/releases` (release folders first, `current.json` last), then `work`, then `raw`.

### R5 — Re-enable the triggers and test the automatic ingest

GOAL: The environment ingests on its own again, with its original settings.

COMMAND:

```bash
az storage message clear --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --queue-name ingest --auth-mode login
az storage message clear --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --queue-name ingest-poison --auth-mode login
azd env set DOCWIKI_ENABLE_EVENT_TRIGGER <value recorded in R1>
azd env set DOCWIKI_RECONCILE_CRON "<value recorded in R1>"
azd provision
az storage blob upload --account-name $(azd env get-value DOCWIKI_STORAGE_ACCOUNT) --container-name raw --name <folder>/<file> --file samples/corpus/full/<folder>/<file> --overwrite --auth-mode login
```

The last command re-uploads one public document with identical bytes.

VERIFY: The first two `az containerapp job show` commands of the R1 VERIFY (trigger and cron) read
`"Event"` (when the trigger is on) and the original cron. Within about a minute an ingest execution
starts by itself and ends `Succeeded`; its report shows no change, `current.json` still names the
release compiled in R4, and the served sources are the same.

ON_FAIL: No execution: Step 9 ON_FAIL (Event Grid delivery, KEDA, queue roles). Remove any
temporary role you granted for the reset, and delete `<backup>` once the owner agrees. Then run
Steps 10 to 12 for the new release.
