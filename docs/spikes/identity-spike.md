# Identity spike: distinct agent principals for the MCP server

| | |
|---|---|
| Date | 2026-10-17 |
| Lane | identity-spike (throwaway Azure and Entra resources, deleted afterwards except an empty Foundry account, see section 9) |
| Decision | [ADR 0003](../adr/0003-mcp-agent-identity.md) |
| Result | **Per-agent Entra agent identity works.** The fallback (one Foundry project per agent with the project managed identity) was not needed and was not executed. |

## 1. Question

The Researcher (app role `Wiki.Read`) and the Librarian (`Wiki.Read` + `Wiki.Operate`) are Foundry
prompt agents that call the same remote MCP server on Azure Container Apps (ACA). Tool visibility
(`allowed_tools`) is not an authorization boundary (spec decision D9), so the server must see a
**distinct Entra principal per agent** and enforce the roles itself. Can Foundry give each prompt
agent its own principal for MCP calls, and what exact configuration does that need?

## 2. Answer

Yes. In the current Foundry agent object model every prompt agent receives its own Entra agent
identity blueprint and agent identity when it is created (`instance_identity` on the agent object).
An MCP tool whose project connection uses `category=RemoteTool`, `authType=AgenticIdentityToken`
and `audience=<MCP API application ID URI>` makes Agent Service request an app-only access token
**for the calling agent's own identity**. App roles assigned to each agent identity arrive in the
token, ACA built-in authentication (Easy Auth) validates the token and injects
`X-MS-CLIENT-PRINCIPAL`, and the server enforces `Wiki.Operate` from the role claims.

Measured: two different object IDs (each equal to the agent's `instance_identity.principal_id`),
Researcher `operate` → `forbidden`, Librarian `operate` → `ok`.

```
Researcher agent ──┐  Agent Service: token for the agent's own identity   ┌─ Easy Auth (ACA) ────────────┐
                   ├─ (connection RemoteTool / AgenticIdentityToken, ────▶│ issuer, audience,            │──▶ MCP server
Librarian agent ───┘   audience = api://<mcp-api-client-id>)              │ allowedApplications = agents │    roles per tool
                                                                          └──────────────────────────────┘
Entra: MCP API app registration (Wiki.Read, Wiki.Operate), appRoleAssignmentRequired = true
```

## 3. What was deployed

| Resource | Configuration |
|---|---|
| Resource group | `swedencentral`, tags `purpose=docwiki-identity-spike`, `owner=docwiki` |
| Foundry account + project | AIServices, custom subdomain, `disableLocalAuth: true`, `allowProjectManagement: true`, system-assigned identity, one project |
| Model deployment | `smart` = `gpt-5.4-mini` (2026-03-17), GlobalStandard, 10K TPM |
| Container registry | Basic, admin user disabled, image built remotely with `az acr build --platform linux/amd64` |
| User-assigned identity | `AcrPull` on the registry, used by the container app to pull its image |
| ACA environment | Consumption; logs to Log Analytics through a diagnostic setting (no workspace key) |
| ACA app | 0.25 vCPU / 0.5 GiB, min 0 / max 1 replicas, external ingress on port 8000, built-in auth |
| Entra app registration | MCP API with app roles `Wiki.Read` and `Wiki.Operate` (application members), `api://<client-id>`, v2 access tokens |
| Prompt agents | `spike-researcher`, `spike-librarian`, plus `spike-norole` for negative tests |

Versions: Azure CLI 2.86, Bicep 0.40, `azure-ai-projects` 2.9.0, `mcp` 2.3.0 (`MCPServer` API),
`uvicorn` 0.54. API versions: `Microsoft.CognitiveServices` 2025-06-01 (account, project,
deployment) and 2025-10-01-preview (connection), `Microsoft.App` 2024-03-01, Microsoft Graph v1.0,
Foundry data plane `api-version=v1`. The Easy Auth middleware reported module version 1.14.4.0.

The spike MCP server is [`identity-spike/spike_mcp_server.py`](identity-spike/spike_mcp_server.py):
stateless streamable HTTP at `/mcp`, `/healthz`, tools `whoami` and `operate`. Both agents were
given both tools so that the **server** is what blocks the Researcher.

## 4. Recipe (validated)

Placeholders: `<tenant-id>`, `<subscription-id>`, `<rg>`, `<account>`, `<project>`,
`<mcp-app-fqdn>`, `<mcp-api-client-id>`, `<mcp-api-app-object-id>`, `<mcp-api-sp-object-id>`,
`<agent-principal-id>`, `<role-id>`. Graph calls are shown with `az rest`; the spike sent the same
requests (see F9 for a token issue met on the way).

### 4.1 MCP API app registration

```bash
READ_ID=$(uuidgen); OPERATE_ID=$(uuidgen)
cat > mcp-api-app.json <<EOF
{
  "displayName": "<env>-docwiki-mcp-api",
  "signInAudience": "AzureADMyOrg",
  "api": { "requestedAccessTokenVersion": 2 },
  "appRoles": [
    { "id": "$READ_ID", "value": "Wiki.Read", "displayName": "Wiki.Read",
      "description": "Read the wiki through the MCP server",
      "allowedMemberTypes": ["Application"], "isEnabled": true },
    { "id": "$OPERATE_ID", "value": "Wiki.Operate", "displayName": "Wiki.Operate",
      "description": "Operate the wiki through the MCP server",
      "allowedMemberTypes": ["Application"], "isEnabled": true }
  ]
}
EOF
az rest --method POST --url https://graph.microsoft.com/v1.0/applications \
  --body @mcp-api-app.json --query "{objectId: id, clientId: appId}"
az rest --method PATCH \
  --url https://graph.microsoft.com/v1.0/applications/<mcp-api-app-object-id> \
  --body '{"identifierUris": ["api://<mcp-api-client-id>"]}'
az rest --method POST --url https://graph.microsoft.com/v1.0/servicePrincipals \
  --body '{"appId": "<mcp-api-client-id>"}' --query id
# Defense in depth: Entra refuses tokens to principals without an app role assignment.
az rest --method PATCH \
  --url https://graph.microsoft.com/v1.0/servicePrincipals/<mcp-api-sp-object-id> \
  --body '{"appRoleAssignmentRequired": true}'
```

No client secret, delegated scope or redirect URI is needed. (For negative tests only, the spike
temporarily exposed a delegated scope pre-authorized for Azure CLI to mint user tokens; that is
not part of the recipe.)

### 4.2 Built-in auth on the container app

Bicep: [`identity-spike/mcp-auth.bicep`](identity-spike/mcp-auth.bicep) (deployed as-is during the
spike).

| Setting | Value | Why |
|---|---|---|
| `registration.clientId` | MCP API client ID | Token validation; no `clientSecretSettingName` |
| `registration.openIdIssuer` | `https://login.microsoftonline.com/<tenant-id>/v2.0` | v2 access tokens |
| `validation.allowedAudiences` | `["api://<mcp-api-client-id>"]` | The client ID is accepted implicitly, and v2 tokens carry it as `aud` (verified) |
| `validation.defaultAuthorizationPolicy.allowedApplications` | the agents' `instance_identity.client_id` | **Required on ACA**: if empty, every other client gets 403 (F1) |
| `globalValidation.unauthenticatedClientAction` | `Return401` | APIs must not redirect |
| `globalValidation.excludedPaths` | `["/healthz"]` (optional) | Anonymous health probe |
| `login.tokenStore.enabled` | `false` | No token storage |

To change the allowlist without Bicep, `PUT` the full body to
`.../containerApps/<app>/authConfigs/current?api-version=2024-03-01` (PUT replaces the whole
configuration).

### 4.3 Project connection

Bicep: [`identity-spike/mcp-connection.bicep`](identity-spike/mcp-connection.bicep) (deployed and
used by the agents during the spike). ARM equivalent:

```bash
az rest --method PUT \
  --url "https://management.azure.com/subscriptions/<subscription-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<account>/projects/<project>/connections/docwiki-mcp?api-version=2025-10-01-preview" \
  --body '{"properties": {"category": "RemoteTool", "authType": "AgenticIdentityToken",
           "target": "https://<mcp-app-fqdn>/mcp", "audience": "api://<mcp-api-client-id>",
           "metadata": {"type": "generic_mcp"}}}'
```

### 4.4 Agents and their identities

Snippet: [`identity-spike/agents_with_identity.py`](identity-spike/agents_with_identity.py) (run
against the spike project). The essential calls:

```python
connection = project.connections.get("docwiki-mcp")
tool = MCPTool(
    server_label="docwiki",
    server_url="https://<mcp-app-fqdn>/mcp",
    require_approval="never",
    allowed_tools=["whoami", "operate"],
    project_connection_id=connection.id,
)
project.agents.create_version(
    agent_name="researcher",
    definition=PromptAgentDefinition(model="smart", instructions="...", tools=[tool]),
)
identity = project.agents.get("researcher")["instance_identity"]  # principal_id, client_id
```

REST equivalent: `GET {project-endpoint}/agents/{name}?api-version=v1` returns `instance_identity`
and `blueprint`. Observed for every agent: `principal_id == client_id`; Graph type
`#microsoft.graph.agentIdentity`; display names `<account>-<project>-<agent>-AgentIdentity` and
`<account>-<project>-<agent>-<hash>-AgentIdentityBlueprint`. The project also owns a shared agent
identity (`<account>-<project>-AgentIdentity`, visible in the project's `agentIdentity` ARM
property); it never reached the MCP server.

### 4.5 App role assignments and allowlist

```bash
# Role IDs by value.
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/servicePrincipals/<mcp-api-sp-object-id>?\$select=appRoles" \
  --query "appRoles[].{id: id, value: value}"
# One call per role: researcher -> Wiki.Read; librarian -> Wiki.Read and Wiki.Operate.
az rest --method POST \
  --url https://graph.microsoft.com/v1.0/servicePrincipals/<mcp-api-sp-object-id>/appRoleAssignedTo \
  --body '{"principalId": "<agent-principal-id>", "resourceId": "<mcp-api-sp-object-id>", "appRoleId": "<role-id>"}'
```

Then deploy `mcp-auth.bicep` with `allowedClientIds` set to the agents' `client_id` values. A
delegated Azure CLI Graph token was accepted for `appRoleAssignedTo` with an agent identity as
principal (the documented rejection of `Directory.AccessAsUser.All` concerns the Agent ID object
APIs, which Foundry calls for us).

### 4.6 Invoke

```python
openai = project.get_openai_client()
response = openai.responses.create(
    input="Call the whoami tool first, then call the operate tool.",
    extra_body={"agent_reference": {"name": "researcher", "type": "agent_reference"}},
)
```

### 4.7 What the MCP server receives

`X-MS-CLIENT-PRINCIPAL` is base64 JSON `{auth_typ, claims: [{typ, val}], name_typ, role_typ}` with
`auth_typ = "Bearer"` for these calls. Observed claim types for agent identity tokens:

| JWT claim | `typ` in the header | Observed value |
|---|---|---|
| `oid` | `http://schemas.microsoft.com/identity/claims/objectidentifier` | agent `instance_identity.principal_id` |
| `azp` | `azp` | agent `instance_identity.client_id` (same value) |
| `roles` | `http://schemas.microsoft.com/ws/2008/06/identity/claims/role`, one claim per role (this is the payload's `role_typ`) | `Wiki.Read` / `Wiki.Operate` |
| `aud` | `aud` | MCP API client ID (v2 token) |
| `iss` | `iss` | `https://login.microsoftonline.com/<tenant-id>/v2.0` |
| `ver` | `ver` | `2.0` |
| `tid` | `http://schemas.microsoft.com/identity/claims/tenantid` | tenant ID |
| `sub` | `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier` | (not used) |

Also present: `aio`, `azpacr`, `exp`, `iat`, `nbf`, `rh`, `uti`, `xms_ftd`. Absent: `scp`, `idtyp`
and any claim that marks the caller as an agent. `name_typ` is
`http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name`.

Server rules that held: trust the header only with `DOCWIKI_AUTH_MODE=easyauth`; select role
claims through `role_typ` (or the long role URI), not a literal `roles`; enforce the role per tool;
log a hash of `oid`, never the token.

## 5. Results (redacted)

| # | Check | Expected | Observed |
|---|---|---|---|
| 1 | `POST /mcp` without token | 401 | 401 with `WWW-Authenticate: Bearer realm="<fqdn>"` |
| 2 | Azure Resource Manager token (other audience) | 401 | 401 |
| 3 | Malformed bearer token | 401 | 401 |
| 4 | Forged `X-MS-CLIENT-PRINCIPAL`, no token | 401 | 401 |
| 5 | Valid MCP API token from a client not in `allowedApplications` (user via Azure CLI; both agents before allowlisting) | 403 | 403; Easy Auth log: "principal does not match any of the allowed applications", sub-status 76 |
| 6 | Valid user token, client allowlisted, no app role: `whoami`, `operate` | user without roles; forbidden | as expected |
| 7 | Same token plus forged `X-MS-CLIENT-PRINCIPAL` claiming `Wiki.Operate` | forgery ignored | `whoami` showed the real caller; `operate` forbidden |
| 8 | Researcher `whoami` | own principal, `Wiki.Read` | object ID = researcher `instance_identity`; roles `[Wiki.Read]`; `aud` = MCP API client ID; `ver` 2.0 |
| 9 | Librarian `whoami` | own principal, both roles | object ID = librarian `instance_identity` (differs from researcher); roles `[Wiki.Operate, Wiki.Read]` |
| 10 | Researcher `operate` | forbidden | server log `tool=operate denied`; Foundry returned HTTP 400 `tool_user_error` (F3) |
| 11 | Librarian `operate` | ok | `{"result": "ok"}` |
| 12 | Agent without assignment, `appRoleAssignmentRequired=true` | no token | Foundry 400 "Failed to fetch agentic identity access token" with `AADSTS501051` |
| 13 | Same agent after a `Wiki.Read` assignment | works | `whoami` ok, roles `[Wiki.Read]` |
| 14 | New version of an agent | same identity | `instance_identity` and blueprint unchanged |
| 15 | Delete and recreate an agent with the same name | new identity | new principal; old one in Entra deleted items; role and allowlist lost |
| 16 | Remove `Wiki.Operate` from the Librarian | effective at token refresh | `operate` still ok right after (cached token) |
| 17 | Remove the Librarian from `allowedApplications` | blocked | 403 on the next call, about one minute including the deployment |
| 18 | Shared project identity and project managed identity | never used | neither appeared at the server |

Server log excerpt (principal hashes replaced):

```
INFO spike tool=whoami principal=<researcher-hash> roles=['Wiki.Read']
WARNING spike tool=operate denied principal=<researcher-hash> roles=['Wiki.Read']
INFO spike tool=whoami principal=<librarian-hash> roles=['Wiki.Operate', 'Wiki.Read']
INFO spike tool=operate allowed principal=<librarian-hash> roles=['Wiki.Operate', 'Wiki.Read']
```

## 6. Findings and gotchas

- **F1 - ACA needs an explicit client allowlist.** With
  `defaultAuthorizationPolicy.allowedApplications` empty (the platform's default), Easy Auth on ACA
  rejected every valid token whose `azp` was not the MCP API itself: HTTP 403, sub-status 76,
  middleware warning "Access was denied for '...' because this principal does not match any of the
  allowed applications". List the agents' client IDs.
- **F2 - Audience.** With `requestedAccessTokenVersion: 2` the token `aud` is the client ID even
  when the connection asks for `api://<client-id>`. `allowedAudiences = ["api://<client-id>"]` was
  enough (the client ID is implicit). v1 tokens were not tested.
- **F3 - A failing MCP tool aborts the whole agent turn.** Both a JSON-RPC error
  (`McpProtocolException ... forbidden`) and an `isError: true` tool result
  (`An error occurred invoking 'operate' ...`) made the Responses call fail with HTTP 400
  `tool_user_error`; the model never saw the error. A forbidden call is therefore fail-closed but
  ends the conversation turn: keep each agent's `allowed_tools` aligned with its roles.
- **F4 - Identity lifecycle.** The identity belongs to the agent, not the version. Deleting an
  agent deletes its identity and blueprint (the identity service principal goes to Entra deleted
  items). Recreating an agent with the same name yields a new principal, so role assignments and
  the allowlist must be redone. Deploy scripts should only add versions.
- **F5 - `appRoleAssignmentRequired=true` works for agent identities.** An unassigned agent cannot
  obtain a token (`AADSTS501051`), which stops it before the network call.
- **F6 - Revocation lag.** Removing an app role does not affect a token Agent Service already
  cached; the change applies at the next token acquisition (lifetime not measured). The immediate
  kill switch is to remove the client ID from `allowedApplications`.
- **F7 - No agent marker in the token.** `idtyp` is absent and no claim says "agent". Authorize by
  roles (and the allowlist), never by guessing the caller type.
- **F8 - Header spoofing is blocked by Easy Auth.** A client-supplied `X-MS-CLIENT-PRINCIPAL` was
  replaced by the validated one, so the MCP tool `headers` option cannot forge an identity.
- **F9 - Continuous access evaluation.** Mid-spike, Microsoft Graph rejected the Azure CLI's cached
  token (`TokenCreatedWithOutdatedPolicies`, `InteractionRequired`) while Azure Resource Manager
  calls kept working. `az ad`/`az rest` Graph calls fail until `az login` runs again (or a client
  replays the claims challenge). Post-provision hooks should report this clearly.
- **F10 - Tooling gaps.** `azd ai connection create --auth-type agentic-identity` (azd 1.28
  extension) failed on a project without connections ("cannot discover ARM context"); ARM and Bicep
  work. Bicep 0.40 types lack `AgenticIdentityToken` (warning BCP036, suppressed in the snippet).
- **F11 - Look up role definition IDs.** A built-in role ID typed from memory failed deployment
  (`RoleDefinitionDoesNotExist`); resolve IDs with `az role definition list --name <role>`.
- **F12 - Diagnostics.** Easy Auth middleware events (401/403 reasons) appear in the
  `ContainerAppConsoleLogs` table next to the server logs.
- **F13 - Teardown deadlock on the Foundry account.** After the agents were deleted, Azure Resource
  Manager refused to delete the account while its project existed (`CannotDeleteResource`, "Cannot
  delete resource while nested resources exist"), and the resource provider refused to delete the
  project because it is the account's default project (`CannotDeleteDefaultProject`, "can only be
  deleted as part of deleting the account"). Two resource group deletions failed after 60 minutes
  each with the same project error. Not helping: account deletes with API versions from 2023-05-01
  to 2026-07-01, deleting the connections and the model deployment first, changing
  `defaultProject` or `allowProjectManagement` (accepted but ignored), creating and deleting a
  second project, deleting the project's shared agent identity. Root cause unknown; `teardown.py`
  must expect it, retry and then escalate to Azure support.

## 7. Cold start (min replicas 0)

| Measurement | Value |
|---|---|
| Idle time before the app scaled to zero | about 8.5 min after the last request |
| `GET /healthz` from zero (one request held by the activator) | 22.6 s, then 200 |
| Warm `GET /healthz` from the client | about 1.2 s |
| Librarian `whoami` + `operate`, cold | 38.8 s end to end |
| Same, warm | 8.0 s and 7.5 s |
| Platform timeline from zero | replica scheduled, about 15 s until the image pull starts, 57 MB pull in about 3 s, container start to uvicorn ready about 1.2 s, Easy Auth sidecar ready at the same time, first request served about 2 s later |
| Right after a new revision (seen once) | first request got 503 "upstream connect error"; not reproduced when scaling from zero |

A cold start adds about 30 s to an agent turn and stays well under the 100 s MCP tool timeout. For
demos, set `mcpMinReplicas=1` (already a spec parameter) or warm the app with `/healthz`.

## 8. Cost

Rough total below USD 1: resources lived about 1.5 hours (registry Basic prorated), three remote
image builds, ACA consumption inside the free grant, a few MB of Log Analytics ingestion and about
25 agent turns on `gpt-5.4-mini`. Foundry accounts have no idle charge.

## 9. Teardown

Order used: delete the agents (removes their identities and blueprints), purge the soft-deleted
agent identity service principals, delete the app registration and purge it from Entra deleted
items, then delete the resource group. Verified with Microsoft Graph: the app registration, its
service principal, every per-agent identity and every per-agent blueprint return 404, also in
deleted items.

The resource group deletion removed the container app, ACA environment, registry, Log Analytics
workspace and managed identity, but **not the Foundry account and its default project** (F13),
also on a second attempt. They remain empty (no model deployment, connection or agent) and cost
nothing. The project's shared agent identity and blueprint were then deleted and purged through
Microsoft Graph; only the account's and the project's system-assigned managed identities remain,
and they disappear with those resources once the account can be deleted.

## 10. Follow-ups for other lanes

- **infra** - Post-provision hook order: app registration + service principal
  (`appRoleAssignmentRequired=true`) -> connection -> agents (agents lane) -> read
  `instance_identity` -> app role assignments -> Easy Auth `allowedApplications`. Teardown: delete
  agents before the resource group, purge the Foundry account, delete and purge the app
  registration, and handle F13 (retry, then escalate). Record the agent principal IDs in the local
  state file used by `teardown.py`.
- **agents** - `deploy.py` creates versions only and outputs each agent's `instance_identity`;
  keep `allowed_tools` aligned with roles because of F3.
- **mcp** - Read roles through `role_typ`; trust the header only in `easyauth` mode; keep the
  `forbidden` error fail-closed; log principal hashes; expose `/healthz`.
- **spec** - Proposed clarifications: architecture section 6 can name the per-agent identities;
  infra section 2 should list `allowedApplications` and v2 tokens; MCP section 1 should mention the
  role claim type and F3.
