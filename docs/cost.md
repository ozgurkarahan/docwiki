# Cost

DocWiki is designed to cost close to nothing when idle and to make every run's cost visible. This
page explains the cost model and the levers, then lists the figures that will be measured on the
sample corpus (pending re-evaluation on the new sample); estimates are labelled as such.

## Cost model

### When nothing runs

| Resource | Idle behaviour |
|---|---|
| Container Apps jobs `ingest` and `reconcile` | Billed only while an execution runs (Consumption profile) |
| Container App `mcp` | Scales to zero after about 8.5 minutes without requests (measured in the identity spike); `DOCWIKI_MCP_MIN_REPLICAS=1` keeps one replica warm and billed |
| Container App `portal` | Disabled by default; enabled, it scales to zero. `DOCWIKI_PORTAL_MIN_REPLICAS=1` keeps one 0.25 vCPU / 0.5 GiB replica always on (small fixed monthly cost) |
| Foundry model deployments (Data Zone or Global Standard) | Pay-per-token: no calls, no charge |
| Container registry (Basic) | Small fixed daily fee |
| Storage account | Data stored (retained releases, state, artifacts) and transactions |
| Log Analytics and Application Insights | Data ingested, 30-day retention |
| Event Grid | Per event delivered |

There is no search service, database or always-on compute to pay for: retrieval runs on a SQLite
index inside each release, and the public sample is a static site.

### When you compile

| Driver | Where it comes from |
|---|---|
| `smart` tokens | Compilation of each new or changed source (map-reduce above 24k tokens, chunks of at most 12k), topic synthesis (one call per topic fed by at least two sources), one repair call when an output fails validation |
| `fast` tokens | Classification when no pack rule matches, figure descriptions (at most 64 per source, image and a fixed prompt only), entity summaries |
| Content Understanding pages | PDFs and images in Azure mode (`prebuilt-layout`); Word, PowerPoint, spreadsheets, CSV, e-mail, transcripts and text are always parsed locally for free |
| Job compute | vCPU and memory seconds of the execution, including the site build |
| Storage | One new release per successful run |

Runs are **incremental**. Every stage output is keyed by a hash of its inputs, prompt version,
model version and domain pack, so an unchanged source is never re-extracted or recompiled.
Entity summaries and topic syntheses read every source, so any change rebuilds them and they
dominate the cost of a one-document change. A run with no change is a no-op and publishes
nothing. Changing a prompt, a model version or the domain pack invalidates exactly the dependent
artifacts; changing the domain pack invalidates almost everything.

### When an agent answers

- One Researcher answer is one agent turn on the `smart` deployment with up to 6 tool calls. Tool
  results (each bounded to 12,000 characters) become input tokens, so input tokens dominate.
- The MCP app is billed while it serves requests; a cold start from zero adds about 30 seconds to
  the first turn.
- The optional Librarian routine runs once a day with five tools.
- The owner's uploads on the portal are capped at 10 a day (`DOCWIKI_PORTAL_DAILY_UPLOADS`) and
  50 MB each, because a new or changed document starts a pipeline run.

## Receipts

Every run report (`work/runs/<run_id>/report.json`) carries a **cost receipt**, and the release
contains a readable copy in `_meta/runs/<run_id>.md`:

- per tier and deployment: calls, failed calls, retries, input, cached, output and reasoning
  tokens, latency, the price row used and the estimated cost;
- the same totals per stage and per prompt;
- Content Understanding pages and the run duration;
- the price table used (file, SHA-256, whether it is verified).

The packaged price table, [`src/docwiki/llm/prices.yaml`](../src/docwiki/llm/prices.yaml), holds
Global Standard list prices copied by hand and is marked `verified: false`; receipts say so. Copy
it, verify every value against the Azure pricing page for your region and deployment type, set
`verified: true` and point `DOCWIKI_LLM_PRICE_TABLE` at the copy. Calls without a matching price
are counted as `unpriced_calls`, never silently as zero. A Log Analytics query that sums tokens and
estimated cost per tier is in [operations](operations.md#logs-and-queries).

## Guardrails

- Bounded work: at most 300 pages per document (`DOCWIKI_MAX_PAGES_PER_DOCUMENT`), map-reduce
  chunk limits, at most 64 described figures per source, at most 6 tool calls per research
  question, MCP results of at most 12,000 characters, `query_table` results of at most 200 rows.
- One job execution at a time (KEDA), a blob lease, and a poison queue after five failed
  deliveries, so a broken source cannot loop forever.
- No public endpoint calls a model.
- A monthly budget with alerts at 50, 80 and 100 % (`DOCWIKI_BUDGET_AMOUNT`, default 50 in the
  billing currency, created when `BUDGET_CONTACT_EMAILS` is set).
- Not yet enforced: a per-run token budget (`DOCWIKI_MAX_TOKENS_PER_RUN` is reserved in the
  settings).

## Levers

| Lever | Effect |
|---|---|
| Start small: `docwiki run --limit N` or `--only <source_id>` (the sample itself has 12 public documents) | Bounds the first runs |
| Keep raw paths stable | A path is a source identity: a moved file becomes a new source with a new page, and the old one is withdrawn |
| `DOCWIKI_FAST_MODEL`, `DOCWIKI_SMART_MODEL` (check with `scripts/preflight.py`) | Price per token of each tier |
| `DOCWIKI_DEPLOYMENT_SKU` (`GlobalStandard` by default, or `DataZoneStandard`) | Price, quota and data residency: Global Standard has the widest quota and the lowest list price; Data Zone keeps processing in the EU or US data zone for about 10 % more |
| `DOCWIKI_CONTENT_UNDERSTANDING=false` | No Content Understanding pages; PDFs fall back to the local text layer and scans lose OCR |
| `DOCWIKI_MCP_MIN_REPLICAS=0` | No idle MCP compute, at the price of a cold start |
| `DOCWIKI_RECONCILE_CRON` | Fewer scheduled safety-net executions |
| `DOCWIKI_RELEASE_RETENTION` (default 10) | Storage used by old releases |
| Domain-pack rules in `taxonomy.yaml` | Every rule match saves a classification call |

## Measured costs

Pending re-evaluation on the new sample (12 public documents): no figure is claimed here until it
has been measured. The table lists what will be reported and where each figure comes from. Costs
are receipt estimates: tokens × the unverified price table.

| Measurement | Where the figure comes from |
|---|---|
| Full ingest, cold cache | The cost receipt of the first run after a [data reset](../BOOTSTRAP.md#reset-the-sample-data): calls and tokens per tier, Content Understanding pages, duration, estimated cost |
| Recompile one source; entities and topics rebuilt | The receipt of a `recompile` run of one source |
| Rebuild with no source changed | The report of a run with no change, which is a no-op: no model or Content Understanding call is expected |
| Researcher answer and naive RAG answer | Tokens, latency and estimated cost per question in [`evals/SCOREBOARD.md`](../evals/SCOREBOARD.md); see [evaluation](evaluation.md#results) |
| Idle environment, one month | An estimate from the price list: the Basic registry, storage, logs and the scheduled reconcile job |

The identity spike (about 1.5 hours of throwaway resources, three remote image builds and about 25
agent turns on a small model) cost less than USD 1.
