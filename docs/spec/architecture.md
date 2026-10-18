# Architecture

## 1. Component view

```
                    raw/ container ── Event Grid (created/deleted) ──┐
 Librarian ──MCP ingest_start──────────────────────────────────────┤ queue "ingest" (wake-up)
                                                                   ▼
 ┌──────────── ACA Job "ingest" (event, single execution) + "reconcile" (schedule) ────────────┐
 │ discover → extract → classify → compile → entities → topics → links → indexes → agent kit   │
 │ → evidence sidecars → verify → site build → publish release → swap current pointer          │
 └─────────────────────────────────────┬──────────────────────────────────────────────────────┘
                                       ▼
            releases/<release_id>/{wiki,site,evidence,catalog.json,search.db,manifest.json}
            releases/current.json  (atomic pointer, ETag-guarded)
                                       ▼
 ┌──── ACA app "mcp" (FastMCP, streamable HTTP, stateless) ────┐   ┌─ ACA app "portal" (optional) ─┐
 │ read tools + ops tools, server-side roles                   │   │ serves current release site   │
 └──────────▲──────────────────────────────▲───────────────────┘   └───────────────────────────────┘
   Foundry prompt agent "researcher"   Foundry prompt agent "librarian" (+ optional routine)
   Foundry project: model deployments (fast, smart), Content Understanding, tracing → App Insights
```

Local mode replaces Blob with a folder (`--work-dir`, default `.local/`) using the same layout,
replaces the queue with a direct CLI call, and runs the MCP server over stdio or local HTTP.

## 2. Azure resources (one resource group)

| Resource | Purpose |
|---|---|
| Microsoft Foundry account (AIServices kind, custom subdomain, local auth disabled) + project | Model deployments (`fast`, `smart`), Content Understanding, agents, tracing |
| Storage account (shared key disabled, versioning + soft delete on) | Containers `raw`, `work`, `releases`; queues `ingest`, `ingest-poison` |
| Event Grid system topic + subscription | `raw` BlobCreated/BlobDeleted → queue `ingest` (delivery with managed identity) |
| Container Apps environment (Consumption) + Log Analytics | Hosts the job(s) and apps |
| ACA Job `ingest` (event trigger, KEDA azure-queue scaler with managed identity) | Compilation runs |
| ACA Job `reconcile` (schedule trigger) | Safety net for lost wake-ups |
| ACA app `mcp` (built-in auth, Return401) | MCP server for agents |
| ACA app `portal` (optional, disabled by default) | Private site behind Entra sign-in |
| Container registry (admin user disabled) | Images for job, mcp, portal |
| User-assigned managed identity | Runtime identity for jobs and apps |
| Application Insights | Telemetry for jobs, apps and Foundry tracing |
| Budget + action group | Cost alerting |

## 3. Storage layout

The same layout is used under a local folder in local mode.

```
raw/                         # inputs, immutable from DocWiki's point of view
  <any/relative/path>.<ext>
work/
  state/sources/<source_id>.json        # per-source state shard (ETag If-Match on write)
  state/lease                            # blob used for the run lease
  artifacts/<stage>/<cache_key>/...      # content-addressed stage outputs
  runs/<run_id>/report.json              # run report and cost receipt
  proposals/<proposal_id>.json           # entity / glossary / topic / injection proposals
  reports/health-<yyyy-mm-dd>.md         # Librarian health reports
releases/
  <release_id>/
    manifest.json        # release metadata, audience, versions, gate results, file hashes
    wiki/                # the wiki (see wiki-contract.md)
    evidence/            # evidence sidecars (see evidence-contract.md)
    site/                # Quartz build output (optional in local mode)
    catalog.json
    search.db
  current.json           # {"release_id", "created_at", "audience", "manifest_sha256"}
```

`release_id` = UTC timestamp `YYYYMMDDTHHMMSSZ` + `-` + first 8 hex of the manifest hash.
Retention: keep the last 10 releases plus any release referenced by `current.json`.

## 4. Run control

Queue message schema (JSON, UTF-8):

```json
{"schema": "docwiki.ingest/v1", "kind": "ingest|recompile|rebuild|reconcile",
 "scope": {"source_ids": [], "prefix": null}, "hints": {}, "requested_by": "librarian|event|cli|schedule",
 "idempotency_key": "string", "created_at": "RFC3339"}
```

Event Grid messages are accepted in their native Event Grid schema and treated as `kind=ingest`.

Job algorithm:

1. Acquire the blob lease on `work/state/lease` (60 s, renewed every 20 s). If the lease is held,
   exit successfully: the running execution will pick up changes (level-triggered).
2. Debounce: wait 30 s (configurable), then receive all visible messages (batches of 32), keeping
   their pop receipts; renew message visibility periodically while the run lasts.
3. Diff `raw/` against state shards (hash, deletion), merge with explicit `recompile` scopes.
4. Run the stages. Each stage is idempotent and content-addressed (see pipeline.md).
5. Build a release, run gates, write the release folder, then swap `current.json` with If-Match.
6. Delete only the messages whose pop receipts are still owned. On failure do not delete;
   messages dequeued more than 5 times move to `ingest-poison`.
7. Loop once more if new messages arrived during the run; otherwise release the lease and exit.

KEDA settings: parallelism 1, replica completion count 1, max executions 1, polling 30 s,
replica timeout 3600 s, retry limit 1. The `reconcile` job runs the same algorithm on a schedule
(default every 6 hours) with `kind=reconcile`.

## 5. State and caching

- Per-source state shard: `source_id`, raw path, content hash, size, media type, sensitivity,
  revision group, per-stage status (`pending|done|failed|quarantined|skipped`), cache keys,
  last error, timestamps. Written with ETag If-Match; conflicts retry with fresh state.
- Content-addressed artifacts: `cache_key = sha256(json([stage, input_hashes, stage_version,
  prompt_version, model_id, model_version, domain_pack_hash, schema_version]))`. A stage is skipped
  when its artifact exists. Changing any element invalidates exactly the dependent artifacts.
- Deletion of a raw file creates a tombstone in state; dependent pages are rebuilt or removed
  through the relationship catalog.

## 6. Identities and access

| Principal | Access |
|---|---|
| Runtime UAMI (jobs, apps) | Storage Blob Data Reader on `raw`; Storage Blob Data Contributor on `work`, `releases`; Storage Queue Data Message Processor on `ingest`; Cognitive Services User + Azure AI User (or equivalent) on the Foundry account; AcrPull |
| Event Grid system topic identity | Storage Queue Data Message Sender on `ingest` |
| MCP app (built-in auth) | Accepts tokens for the MCP API app registration only; roles enforced in code |
| Researcher agent principal | App role `Wiki.Read` on the MCP API |
| Librarian agent principal | App roles `Wiki.Read` and `Wiki.Operate` on the MCP API |
| Deployer | Owner (or Contributor + User Access Administrator) on the RG, Application Developer in Entra |

The concrete agent principals (per-agent identity, or one Foundry project per agent as fallback) are
decided by the identity spike and recorded in `docs/adr/0003-mcp-agent-identity.md`.

## 7. Observability

- OpenTelemetry in the job and MCP app exporting to Application Insights (spans per stage, per
  LLM call with model, tokens, latency; per MCP tool call with principal role, latency, result size).
- Foundry tracing enabled for both agents.
- Every run writes `work/runs/<run_id>/report.json` and a human summary page `_meta/runs/<run_id>.md`
  in the next release, including a **cost receipt** (tokens × price table, Content Understanding
  pages, duration).

## 8. Cost guardrails

- Everything scales to zero; models are pay-per-token.
- Bounded work: max pages per document (default 300), max map-reduce chunks, max tokens per run,
  max research tool calls per question (12).
- Budget alert at 50 / 80 / 100 % of a configurable monthly amount, with an action group.
- No public endpoint calls an LLM; the public demo is a static site.
