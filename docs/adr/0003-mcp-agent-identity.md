# ADR 0003: Per-agent Entra agent identities for MCP authorization

- **Status:** Accepted (2026-10-17)
- **Amended:** v1.1 — defense in depth: the server also validates the bearer token forwarded by
  built-in auth, and the MCP app gets external ingress only after built-in auth is verified
  ([spec changelog](../spec/CHANGELOG.md), Security; `src/docwiki/mcp/README.md`)
- **Evidence:** [identity spike report](../spikes/identity-spike.md) (throwaway Azure and Entra
  resources; teardown status in section 9 of the report)
- **Related spec:** D9 in `docs/spec/README.md`; `docs/spec/mcp-and-agents.md` section 1
  (Authorization); `docs/spec/architecture.md` section 6; `docs/spec/infra-ops-security.md` section 2

## Context

DocWiki exposes its wiki through one remote MCP server hosted on Azure Container Apps (ACA) behind
built-in authentication (Easy Auth). Two Microsoft Foundry prompt agents use it:

- the **Researcher** may only read (app role `Wiki.Read`);
- the **Librarian** may also operate the wiki (`Wiki.Read` + `Wiki.Operate`).

Tool visibility (`allowed_tools`, approvals) is not an authorization boundary (D9): a prompt
injection, a misconfigured agent version or a direct call must not let the Researcher run
operations tools. The server therefore has to see a **distinct principal per agent** and enforce
the roles itself. The architecture left the concrete principals open: per-agent identity, or one
Foundry project per agent using the project managed identity as a fallback.

Foundry offers three Entra-based ways to authenticate an MCP tool through a project connection:
the agent identity (`AgenticIdentityToken`), the project managed identity
(`ProjectManagedIdentity`) and the signed-in user (OAuth identity passthrough / user Entra token).
In the current agent object model each new agent gets its own Entra agent identity blueprint and
agent identity; older material describes a shared project identity until an agent is published.
The spike had to establish which principal actually reaches the server.

## Decision

1. **Principals.** Each prompt agent authenticates to the MCP server with **its own Entra agent
   identity**: the `instance_identity` of the Foundry agent object, created with the agent and kept
   across agent versions. No secrets, keys or shared identities.
2. **Token acquisition.** Both agents use one project connection for the MCP tool:
   `category: RemoteTool`, `authType: AgenticIdentityToken`, `target` = the MCP endpoint,
   `audience` = the MCP API application ID URI (`api://<client-id>`). Agent Service obtains an
   app-only token for the calling agent's identity.
3. **MCP API app registration.** App roles `Wiki.Read` and `Wiki.Operate` (member type
   Application), identifier URI `api://<client-id>`, v2 access tokens
   (`requestedAccessTokenVersion: 2`), and a service principal with
   `appRoleAssignmentRequired: true`. Assignments: Researcher identity -> `Wiki.Read`; Librarian
   identity -> `Wiki.Read` and `Wiki.Operate`.
4. **Edge validation (Easy Auth).** Microsoft provider with the v2 issuer of the tenant, allowed
   audience = the application ID URI (the client ID is accepted implicitly),
   `defaultAuthorizationPolicy.allowedApplications` = the two agents' client IDs,
   `unauthenticatedClientAction: Return401`, token store disabled, no client secret.
   `/healthz` may be excluded from authentication.
5. **Server enforcement.** The MCP server trusts `X-MS-CLIENT-PRINCIPAL` only when
   `DOCWIKI_AUTH_MODE=easyauth`, reads the role claims (claim type given by the payload's
   `role_typ`), requires `Wiki.Read` for read tools and `Wiki.Operate` for operations tools, answers
   `forbidden` otherwise and logs a hash of the principal object ID, never the token.
6. **Lifecycle.** Agents change only by adding versions. Creating, deleting or recreating an agent is
   a provisioning event: the post-provision hook (infra lane) reads each agent's
   `instance_identity`, (re)applies the app role assignments and updates `allowedApplications`.
   Teardown deletes the agents before the resource group and deletes the app registration.

The fallback (one Foundry project per agent with `ProjectManagedIdentity`) is not adopted.

## Consequences

Positive:

- The server sees one principal per agent and enforces least privilege itself; every call is
  attributable to a named agent identity (token object ID, hashed in the server log).
- Three independent layers: Entra refuses tokens to unassigned principals, Easy Auth accepts only
  the right audience from allowlisted clients and strips forged principal headers, and the server
  checks roles per tool.
- One Foundry project, one connection and no secrets to rotate.
- Removing a client ID from `allowedApplications` is an immediate kill switch for one agent.

Negative and risks:

- Preview surfaces: the `AgenticIdentityToken` connection type is only accepted by preview ARM API
  versions (2025-10-01-preview was used) and Bicep types lag behind (warning BCP036); agent
  identities rely on Microsoft Entra Agent ID. Re-validate when these APIs change.
- Coupling: the role assignments and the Easy Auth allowlist depend on agent principal IDs that only
  exist after the agents are created, so provisioning has an ordering constraint and a recreated
  agent silently loses access until the hook runs again.
- On ACA the allowlist is mandatory: with an empty `allowedApplications` every agent receives 403.
- Role removal is not immediate: Agent Service keeps using a cached token until it expires; use the
  allowlist for urgent revocation.
- Foundry aborts the whole agent turn (HTTP 400 `tool_user_error`) when an MCP tool returns an
  error, so a `forbidden` call fails closed but ends the turn; `allowed_tools` must stay aligned
  with each agent's roles.
- Tokens carry no claim that marks an agent; the server must authorize by roles, not by caller type.
- With zero minimum replicas a cold MCP app adds about 30 s to an agent turn (22.6 s at HTTP
  level); demos should set `mcpMinReplicas=1`.
- The post-provision hook needs Microsoft Graph rights to create the app registration and assign
  app roles. The spike ran as a tenant administrator; the minimum Entra role was not measured.
- Teardown risk: in the spike the Foundry account could not be deleted after its agents were
  removed (Resource Manager blocked the account because of its default project, and the default
  project cannot be deleted on its own); `teardown.py` must detect and report this.

## Alternatives considered

1. **One Foundry project per agent with the project managed identity** (`ProjectManagedIdentity`
   connection, app roles on each project identity): the documented fallback and the pattern of
   public samples. Not needed; it doubles projects, model deployments and connections, and every
   agent inside a project would share one principal. Not executed.
2. **Shared project identity or a single project managed identity for both agents:** one principal
   for two privilege levels, which defeats D9. Rejected.
3. **Key-based connection (`CustomKeys`) with a key per agent:** secrets to store and rotate, no
   Entra audit trail. Rejected by the zero-secrets rule.
4. **OAuth identity passthrough or user Entra tokens:** authorizes the end user, not the agent,
   requires interactive consent and does not fit the scheduled Librarian routine. Rejected for
   agent authorization (may be revisited for per-user data access).
5. **Tool filtering only (`allowed_tools`, approvals):** visibility is not authorization. Kept as a
   complementary control, not as the boundary.
6. **JWT validation in the server instead of Easy Auth:** feasible, but Easy Auth already validates
   issuer, audience and client allowlist and strips spoofed headers; the spec mandates it.
7. **Legacy "publish as Agent Application" to obtain a distinct identity:** superseded by the agent
   object model in which every agent has its own identity from creation.

## Verification evidence (redacted)

Run on 2026-10-17 in `swedencentral` with `gpt-5.4-mini`, `azure-ai-projects` 2.9.0 and `mcp`
2.3.0. Full details, recipe and snippets: [identity spike report](../spikes/identity-spike.md).

| Check | Result |
|---|---|
| Distinct principals | Researcher and Librarian presented different object IDs, each equal to the agent's `instance_identity.principal_id`; the shared project identity and the project managed identity never appeared |
| Roles in token | Researcher `[Wiki.Read]`; Librarian `[Wiki.Operate, Wiki.Read]`; v2 tokens, `aud` = MCP API client ID |
| Server enforcement | Researcher `operate` -> `forbidden` (server log `denied`); Librarian `operate` -> `ok` |
| Anonymous call / other-audience token / malformed token | 401 / 401 / 401 |
| Valid token from a non-allowlisted client | 403 (Easy Auth: principal not in allowed applications) |
| Valid token without app role, with a forged principal header | forgery ignored; `operate` forbidden |
| Unassigned agent with `appRoleAssignmentRequired` | no token (`AADSTS501051`) |
| New agent version / recreated agent | same identity / new identity |
| Role removal / allowlist removal | not effective until token refresh / 403 within about one minute |
| Cold start (min replicas 0) | agent turn 38.8 s cold versus 7.5-8.0 s warm |
