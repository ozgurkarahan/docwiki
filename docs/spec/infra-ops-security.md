# Infrastructure, operations and security

## 1. Deployment model

- `azd` + Bicep (`infra/main.bicep`, modules under `infra/modules/`), one resource group per
  environment, parameters in `infra/main.parameters.json` fed from azd environment values.
- Allowed regions (parameter `@allowed`): `swedencentral` (default), `eastus2`, `westeurope` —
  regions where Foundry models, agents and Content Understanding are available.
- Container images built remotely in the registry (no local Docker required):
  `docker/job.Dockerfile` (Python + Node 22 + pinned Quartz for the site stage),
  `docker/mcp.Dockerfile`, `docker/portal.Dockerfile` (three images; `docker/studio.Dockerfile`
  was removed in v1.6 with the Studio, [ADR 0009](../adr/0009-one-site.md)).
- Parameters (with defaults): `fastModel`/`fastModelVersion`/`fastCapacity`,
  `smartModel`/`smartModelVersion`/`smartCapacity`, `deploymentSku` (`GlobalStandard` by
  default; `DataZoneStandard` for data residency), `mcpMinReplicas` (0; set 1 for demos), `enablePortal` (false),
  `enableEventTrigger` (true), `reconcileCron` (`0 */6 * * *`), `budgetAmount` (monthly, USD),
  `budgetContactEmails` (passed at deploy time, never committed), `audience` (`internal`),
  `domainPack` (`batiment`), `enableFoundrySkillsPreview` (false), `enableRoutine` (false),
  `evalMcpVariants` (empty).
- Optional evaluation environment (`evalMcpVariants`, azd value `DOCWIKI_EVAL_MCP_VARIANTS`,
  empty = off): one MCP app `ca-mcp-<name>-<token>` per variant, each built like the production
  one (same managed identity, registry, storage settings, Entra built-in auth with the same
  audience and token validation, external ingress) at zero replicas at rest, with the variant's
  `DOCWIKI_MCP_*` settings added to the production environment (never the authentication ones),
  and its own project connection `<mcpConnectionName>-<name>`. The value is the base64 of a JSON
  array `[{"name": "<a-z0-9, at most 8>", "env": {"DOCWIKI_MCP_*": "<value>"}}]` (azd substitutes
  values into the parameters file as raw text, so raw JSON would break it); `agents/variants.yaml`
  declares the arms of the knowledge-access study and `scripts/eval_stack.py encode` produces the
  value. Further settings: `evalMcpImage` (one explicit image or digest for every evaluation app;
  empty = the production image), `evalReleaseId` (adds `DOCWIKI_MCP_PIN_RELEASE` to every
  evaluation app, so a run reads one immutable release), `evalSmartCapacity` (when > 0, a
  `smart-eval` deployment with the model, version and SKU of `smart`, so evaluation agents never
  compete with production for tokens), `evalEmbedAccess` (grants the MCP identity Cognitive
  Services User on the Foundry account so that evaluation apps can call the `embed` deployment,
  and adds the embedding settings to their environment; the MCP identity is shared with the
  production app, which therefore gets the permission too, though it does not use it). One output,
  `DOCWIKI_EVAL_MCP_VARIANTS_OUT` (JSON, name -> `{url, connection}`), and
  `DOCWIKI_EVAL_SMART_DEPLOYMENT`. Evaluation Researchers `docwiki-researcher-<name>`
  (`agents/deploy.py --variant`) differ from the production one only by instructions, reasoning
  effort, model deployment and MCP connection, so a feature is A/B evaluated against production
  without touching production resources: with no variant, no evaluation resource exists and the
  production resources are unchanged. It needs a provisioned environment (`mcpApiClientId`); the
  agents' identities are allowed by the evaluation apps only
  (`DOCWIKI_EVAL_MCP_ALLOWED_CLIENT_IDS`) and are granted `Wiki.Read` by
  `scripts/eval_stack.py grant` (the hooks manage the production agents only). All of it is
  removed after the gates: `agents/deploy.py --variant all --delete`, then delete the apps and the
  connections (emptying the value does not delete them: provisions are incremental) and the
  `smart-eval` deployment, and unset the settings. The operator sequence is in
  [`agents/README.md`](../../agents/README.md).
- Preflight script (`scripts/preflight.py`): azd/az versions, logged-in account, region allowed,
  model availability and quota in the region, deployer roles (Owner or Contributor + User Access
  Administrator; Entra Application Developer), Python and Node versions. Never switches region or
  model silently; prints exact remediation.
- Post-provision hooks (idempotent): create/update the Entra app registration for the MCP API
  (app roles `Wiki.Read`, `Wiki.Operate`), assign roles to the agent principals, configure
  built-in auth on the `mcp` app, deploy/update the Foundry agents, optionally configure Content
  Understanding model defaults.
- `scripts/teardown.py`: deletes the resource group and the app registrations created by the hooks
  (listed in a local state file under `.azure/`, never committed).

## 2. Identity model

See architecture.md §6. Additional rules:

- No API keys, connection strings, SAS tokens or `listKeys()` anywhere in Bicep or code.
- Foundry account: `disableLocalAuth: true`, custom subdomain; storage: `allowSharedKeyAccess:
  false`; registry: admin user disabled, AcrPull via the runtime identity.
- Built-in auth for `mcp`: Microsoft identity provider, `unauthenticatedClientAction: Return401`,
  allowed audience = MCP API application ID URI, token store disabled. No client secret is needed
  for bearer-token validation.
- The optional `portal` requires an interactive sign-in. Prefer a managed-identity federated
  credential for the sign-in client if the platform supports it; otherwise the portal stays
  disabled by default and the documented exception (client secret stored as an ACA secret,
  rotated) applies only when an operator enables it.
- Agent principals get MCP app roles per `docs/adr/0003-mcp-agent-identity.md`.

## 3. Operations

- Upload documents to `raw/` (Storage Explorer or `azcopy` with Entra sign-in); Event Grid wakes the
  job; or ask the Librarian to start an ingest.
- Runbook pages: `BOOTSTRAP.md` (agent-executable deployment runbook with GOAL / COMMAND / VERIFY /
  ON_FAIL blocks), `docs/operations.md` (day-2: re-ingest, recompile, roll back `current.json`,
  rotate releases, read run receipts, budget alerts).
- Rollback: point `current.json` to a previous release id (script `docwiki release rollback`).
- Logs: Log Analytics retention 30 days; structured logs carry `run_id`, `source_id`, `stage`.

## 4. Threat model (summary)

| Threat | Mitigation |
|---|---|
| Prompt injection in documents | Data-only prompts, structured outputs, no tools during compilation, sanitization, canary gate, template-only skills, agent instructions |
| Malicious Markdown/HTML in the site | No raw HTML, link allowlist, Quartz raw-HTML disabled, built-site scan |
| Researcher misusing operations | Server-side roles from distinct principals; approvals for mutations |
| Data exfiltration via links/images | No external links or images in compiled content |
| Access-right flattening | Sensitivity tiers, per-audience builds, no cross-tier consolidation |
| Cost abuse | No public LLM endpoint; bounded work; budget alerts; scale to zero |
| Secrets leakage | Zero secrets by design; secret scanning and push protection on the repository |
| Supply chain | Pinned dependencies in CI, Dependabot, CodeQL, minimal images |
| Partial/inconsistent reads | Immutable releases and atomic pointer swap |

## 5. Leak guard (publication safety)

- `tools/leakguard/` scans: working tree, full git history, text extracted from every binary
  (PDF, DOCX, XLSX, PPTX, images via OCR where available), Office/PDF metadata, EXIF, built site
  output and generated wiki.
- Closed-world check: capitalised multi-word names and known name patterns not present in
  `samples/fiction/allowlist.txt` or the technology allowlist are reported.
- Private deny-list: terms are read from a file **outside the repository** (path from
  `DOCWIKI_DENYLIST`) or a CI secret available only to the private development repository.
  The scanner never prints matched secrets in public logs (it prints file, line and a hash of the
  matched term).
- Identifier patterns: GUIDs, e-mail addresses (except the GitHub noreply author and
  `example.com`/`example.org`), internal host names, Windows/Unix home paths, keys and tokens.
- A pre-push hook (`.githooks/pre-push`) runs the scanner and fails closed.

## 6. Release process

1. All CI green, evaluation results committed, leak guard 0 findings, code and security reviews done.
2. Explicit IP / open-source clearance confirmed by the owner.
3. Squash to a single commit "Initial public release" authored with the GitHub noreply address.
4. Create a new public repository; push; enable secret scanning + push protection, Dependabot
   alerts and updates, CodeQL default setup, private vulnerability reporting, branch protection.
5. Deploy the public demo on Azure Container Apps (portal with a public-audience build).
6. Verify the rendered repository and site; record the published commit.
