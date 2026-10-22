# DocWiki

**Turn messy documents into a wiki humans can browse and agents can trust — cited to the page.**

[![CI](https://github.com/ozgurkarahan/docwiki/actions/workflows/ci.yml/badge.svg)](https://github.com/ozgurkarahan/docwiki/actions/workflows/ci.yml)
[![Code: MIT](https://img.shields.io/badge/code-MIT-3c6250.svg)](LICENSE)
[![Content: CC BY 4.0](https://img.shields.io/badge/content-CC%20BY%204.0-496955.svg)](LICENSE-CONTENT.md)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-6b6a62.svg)](pyproject.toml)

DocWiki compiles PDFs, Word documents, spreadsheets, CSV exports, slide decks, e-mails, scans and
meeting transcripts into a Karpathy-style Markdown wiki: source, entity and topic pages with
indexes, backlinks, a glossary and an append-only log. Every claim ends with a footnote that opens
the exact page, sheet rows, slide or transcript cue it came from. One immutable release serves
people (a static site), Microsoft Foundry agents (an MCP server) and your own coding agent (stdio
MCP and Agent Skills).

**Ask this wiki:** the Researcher agent answers in the page, with citations checked before display
([docs/live-ask.md](docs/live-ask.md)).

> **Status: demo / proof of concept.** DocWiki shows that the pattern works end to end on Azure;
> it is not a production-ready product. The sample is a small fictional corpus (the paperwork of
> one building job: 12 public documents in French). Scores and costs on this sample are pending
> re-evaluation and are published here once measured.

![How DocWiki works: documents are compiled by an Azure Container Apps Job into an immutable release that serves a static site, Foundry agents and local coding agents](docs/assets/architecture.svg)

## Why

- Retrieval-augmented generation re-discovers knowledge from raw chunks at every question; nothing
  accumulates between questions.
- Operational documents need cross-document reasoning: which revision is current, which sources
  contradict each other, how a log, a workbook and a report fit together, and exact table values.
- Agents need a map, not a pile of chunks: indexes, typed links, a glossary, a log, and evidence
  they can check.
- DocWiki compiles that map once, cites every claim, verifies quotes with code and keeps the raw
  extracted text searchable next to it. It complements retrieval; it does not try to replace it.

## What you get

| | |
|---|---|
| **Wiki pages** | One page per source (status `current`, `superseded` or `withdrawn`, revisions linked), entity pages (organisations, people, building elements, materials, quotes, invoices…), topic syntheses with `## Contradictions` and `## Superseded information` sections, indexes, a multilingual glossary and an append-only log. Plain Markdown with YAML frontmatter that renders on GitHub, Quartz, Obsidian and VS Code. |
| **Evidence microscope** | Every footnote opens an evidence sidecar: the page image with highlight boxes, the exact spreadsheet rows, the slide, the e-mail lines, the transcript cue or the OCR crop, with an honest provenance badge: `✓ quote verified`, `paraphrase`, `table`, `OCR` or `generated description`. |
| **Agent kit** | `AGENTS.md`, `llms.txt`, `catalog.json` (pages and typed edges), `search.db` (SQLite FTS5 over page sections **and** raw extracted blocks) and Agent Skills, projected identically for GitHub Copilot, Claude Code and Codex (`.github/skills`, `.claude/skills`, `.agents/skills`). |
| **MCP server** | `docwiki-mcp`: 10 read tools (search, pages, indexes, links, glossary, evidence, read-only SQL over tables, skills, recent changes) and 9 operations tools, over stateless streamable HTTP or stdio. Roles are enforced by the server, not by tool visibility. |
| **Two Foundry agents** | The **Researcher** answers with numbered citations and abstains when the wiki is silent; the **Librarian** runs and repairs ingests, with human approval for every change. |
| **Ask this wiki** | A button on every page of the site opens a drawer. It lists reviewed Researcher answers (wiki pages in `queries/` that the owner files with `docwiki file-answer`, [ADR 0007](docs/adr/0007-answers-in-the-wiki.md)) and, where the portal enables it, lets a visitor ask the Researcher live: the answer is shown as verified only when each citation opens an evidence page of the wiki, behind per-visitor and global limits ([ADR 0008](docs/adr/0008-one-experience-live-agent-in-the-wiki.md), [docs/live-ask.md](docs/live-ask.md)). Numbered citations open the evidence beside the drawer. |
| **How it works** | A page of the site that explains the pipeline and shows it live, read-only: each document's status, the ingest queue, the current release and the last runs (stages, timings, gates, cost). The owner signs in on the same site and uploads documents there; Event Grid and the ingest job do the rest ([ADR 0009](docs/adr/0009-one-site.md), [docs/operations.md](docs/operations.md#owner-sign-in-and-uploads-on-the-public-portal)). |
| **Quality gates** | 15 gates (G01–G15): schemas, links and anchors, citations, quote verification, safe content, sidecars, audience, injection canaries, paths, supersession, skills… A failing blocking gate keeps the previous release online. |
| **Immutable releases** | Each run publishes a complete, hashed release and swaps one pointer (`current.json`) with an ETag precondition. Readers never see a half-built wiki; rollback is a pointer change. |
| **Domain packs** | Taxonomy, entity registry, topics, glossary, sensitivity, supersession and contradiction rules as YAML. Ships with one sample pack, `batiment` (the paperwork of a small French building contractor); small test packs exercise the engine with other domains. |

## Try it

### 1. Browse the sample wiki

Live demo: **[docwiki.ozgurkarahan.com](https://docwiki.ozgurkarahan.com/)**, served from Azure
Container Apps. Open **Ask this wiki** on any page and ask the Researcher agent a question; the
site also has a graph view, full-text search, backlinks and the evidence microscope.

The sample stands in for *your* documents: the paperwork of one small building job, written in
French and compiled into an English wiki. A general contractor (Lamna Bâtiment) builds a 30 m²
extension and renovates the kitchen of a private household (the Moreau family) in the invented
town of Valbrise, from January to April 2026, with a builders' merchant, a window maker and an
electrician. The corpus holds 12 public documents (quotes, a works contract and its amendment, a
planning workbook, an invoice, a scanned delivery note, site minutes, two e-mails, two photos), a
restricted internal price study and one held-back planning revision. Everything is fictional and
stamped as such, and the two site photos are AI-generated images (model and prompts in
[`PROVENANCE.md`](samples/generators/assets/photos/PROVENANCE.md)). The documents hide the
situations that make real document sets hard; the wiki handles each one visibly:

| In the documents | In the wiki |
|---|---|
| Quote indice B cancels and replaces indice A | Indice A keeps its page, marked `superseded`; answers give the current price first |
| The planning and the window maker's e-mail give different window delivery dates | A topic lists both claims with their citations and the resolution rule |
| The invoice bills 10 pallets; a handwritten note on the scanned delivery note says 8 arrived | OCR evidence, cited next to the invoice line |
| The total price needs two documents: the contract and amendment no. 1 | A multi-hop answer with both citations |
| Purchases to date and task progress sit in a two-sheet workbook | `query_table` returns exact values with row ids |
| An e-mail tells AI assistants to confirm an early payment | The instruction is dropped, filed as an injection proposal and replaced by a visible placeholder |
| An internal price study with margins | Restricted: absent from the public build |
| A question no document answers (who is the architect?) | "Not found in the wiki." |
| A later planning revision, held back | The owner uploads it on the `how-it-works` page ([demo](docs/operations.md#live-upload-demo-optional)): it supersedes the first planning and the contradiction resolves |

| Home | Topic synthesis |
|---|---|
| [![Home page of the sample wiki: purpose, navigation, categories and topics](docs/assets/screenshots/home.png)](docs/assets/screenshots/home.png) | [![Topic page: a cited synthesis across documents, with graph view and table of contents](docs/assets/screenshots/topic.png)](docs/assets/screenshots/topic.png) |
| **Contradiction radar** | **Evidence microscope** |
| [![Contradictions section: the planning and the window maker's e-mail give different delivery dates; both claims are shown with their citations and the resolution rule](docs/assets/screenshots/contradictions.png)](docs/assets/screenshots/contradictions.png) | [![Evidence sidecar: the cited page with the quoted text highlighted and a provenance badge](docs/assets/screenshots/evidence.png)](docs/assets/screenshots/evidence.png) |

The site is built from a release. To build the hand-made mock release locally (Node 22+ and git
required):

```bash
uv run python -m docwiki.site samples/fixtures/mock-release --out .cache/site-sample
uv run python -m docwiki.portal --site-dir .cache/site-sample     # http://127.0.0.1:8080
```

### 2. Clone it and ask your coding agent (no Azure)

```bash
git clone https://github.com/ozgurkarahan/docwiki
cd docwiki
uv sync --all-extras        # Windows ARM64: uv sync --all-extras --no-extra evals
```

Open the folder in your agent. The repository ships the MCP configuration; every client launches
the DocWiki MCP server over stdio, with read tools only:

| Client | Configuration |
|---|---|
| GitHub Copilot in VS Code (agent mode) | [`.vscode/mcp.json`](.vscode/mcp.json) |
| Claude Code | [`.mcp.json`](.mcp.json) (approve the project server when asked) |
| GitHub Copilot CLI | snippet for `~/.copilot/mcp-config.json` in [docs/local-agents.md](docs/local-agents.md#github-copilot-cli) |
| Codex | snippet for `config.toml` in [docs/local-agents.md](docs/local-agents.md#codex) |

Then ask, for example: *"Use the docwiki tools: what is the total contract amount including
amendment no. 1? Cite the evidence."* The agent can also read the wiki's own Agent Skills
(`list_skills`, `get_skill`).

> The configurations serve a release folder on disk (the hand-made mock release in
> [`samples/fixtures/mock-release`](samples/fixtures/mock-release) until you compile your own).
> Details: [docs/local-agents.md](docs/local-agents.md).

### 3. Deploy your own on Azure

```bash
az login && azd auth login
azd env new docwiki-dev --location swedencentral
azd env set BUDGET_CONTACT_EMAILS "<address>"
python scripts/preflight.py
azd up
```

`azd up` provisions everything with Bicep (Foundry, storage, Event Grid, Container Apps, registry,
monitoring, budget), builds the images remotely, registers the MCP API in Entra ID, deploys both
agents with their own identities and smoke-tests the endpoint.

**Prefer to delegate? Hand [`BOOTSTRAP.md`](BOOTSTRAP.md) to your coding agent.** It is an
agent-executable runbook (GOAL, COMMAND, VERIFY and ON_FAIL for every step) that deploys, checks
RBAC and authentication, uploads the sample corpus, watches the first run, smoke-tests both agents
and tears everything down. Day-2 tasks are in [docs/operations.md](docs/operations.md).

### Compile your own documents

Local mode keeps storage in a folder and runs without a queue; it calls the models of a Foundry
project you can reach with `az login`:

```bash
export DOCWIKI_FOUNDRY_PROJECT_ENDPOINT="https://<account>.services.ai.azure.com/api/projects/<project>"
export DOCWIKI_FAST_DEPLOYMENT="<fast deployment>"
export DOCWIKI_SMART_DEPLOYMENT="<smart deployment>"
uv run docwiki run --input samples/corpus/full --domain batiment --audience public --work-dir .local
uv run docwiki status --work-dir .local
uv run docwiki serve --stdio --release .local/releases
```

Values can also live in a git-ignored `.env` file (in PowerShell, set them with
`$env:NAME = "value"`). The command above compiles the sample; `--audience public` leaves out the
restricted document of `full/restricted/`. The command line at a glance:

| Command | What it does |
|---|---|
| `docwiki run --input <dir> --domain <pack> [--audience …] [--limit N] [--only <source_id>] [--site] [--force] [--dry-run]` | Compile the documents and publish a release (direct call, no queue) |
| `docwiki status [--run <run_id>] [--json]` | Show the current release and the latest run reports |
| `docwiki lint [--release current\|<release_id>\|<folder>]` | Validate a release against the wiki contract and the quality gates |
| `docwiki site [--release …] [--out <dir>]` | Build the Quartz site of a release (Node 22+ and git) |
| `docwiki serve --stdio \| --http <host:port> [--release <dir>]` | Run the MCP server; `docwiki-mcp` is the same entry point |
| `docwiki ask "<question>" [--agent researcher\|librarian] [--approve prompt\|deny] [--json]` | Ask a deployed Foundry agent; prints the answer, its sources and a receipt |
| `docwiki file-answer "<question>" [--from-json <answer.json>] [--dry-run] [--yes]` | File a reviewed Researcher answer into the wiki: the next run publishes it as a `queries/` page ([docs/agents.md](docs/agents.md#filing-an-answer-into-the-wiki)) |
| `docwiki export obsidian --out <vault>` | Copy a release into an Obsidian vault with `[[wikilinks]]` |
| `docwiki release list`, `docwiki release rollback <release_id>` | List releases; point `current.json` back at an earlier one |
| `docwiki worker`, `docwiki reconcile` | Job entry points: drain the queue, or the scheduled safety net |
| `docwiki version` | Print the version |

## Architecture

```mermaid
flowchart LR
  docs["Documents<br/>PDF, Word, Excel, CSV,<br/>PowerPoint, e-mail, scans, VTT"] --> raw[("Blob container raw")]
  raw -->|"BlobCreated / BlobDeleted"| eg["Event Grid system topic"]
  eg --> queue[["Storage queue ingest"]]
  queue -->|"KEDA, one execution"| job["Container Apps Jobs<br/>ingest: queue-triggered<br/>reconcile: every 6 hours<br/>13 stages, 15 gates"]
  job -->|"structured outputs, no tools"| foundry["Microsoft Foundry<br/>fast and smart models<br/>Content Understanding"]
  job -->|"publish, then If-Match pointer swap"| releases[("Blob container releases<br/>immutable releases + current.json")]
  releases --> mcp["Container App: MCP server<br/>built-in auth, roles per tool"]
  releases --> site["Quartz site<br/>served by the portal Container App"]
  mcp -->|"MCP, Wiki.Read"| researcher["Researcher agent<br/>own Entra agent identity"]
  mcp -->|"MCP, Wiki.Read + Wiki.Operate"| librarian["Librarian agent<br/>own Entra agent identity"]
  librarian -.->|"ingest_start, recompile<br/>human approval"| queue
  site -->|"owner upload"| raw
```

| Component | Runs on | Role |
|---|---|---|
| Pipeline | Container Apps Job `ingest` (queue-triggered, one execution at a time) and `reconcile` (scheduled) | `docwiki worker` takes a blob lease, diffs `raw/` against per-source state, runs 13 idempotent, content-addressed stages and publishes a release |
| Storage | Storage account (shared keys disabled): containers `raw`, `work`, `releases`; queues `ingest`, `ingest-poison`; Event Grid system topic | Inputs, state shards, stage artifacts, run reports, proposals, immutable releases |
| Models | Microsoft Foundry deployments `fast` and `smart`; Content Understanding for PDFs and images | Classification fallback, figure descriptions and entity summaries (`fast`); compilation and topic synthesis (`smart`) |
| MCP server | Container App `mcp` behind built-in authentication | Serves the current release; enforces `Wiki.Read` and `Wiki.Operate` per tool |
| Agents | Foundry prompt agents `docwiki-researcher` and `docwiki-librarian` | Cited answers; operations with approvals |
| Site | Quartz served by the optional `portal` Container App (Entra sign-in, or no sign-in for a public-audience build with the owner's sign-in for uploads) | Human view, evidence microscope, the live `how-it-works` page and the owner's uploads |
| Operations | Log Analytics, Application Insights, Foundry tracing, budget alerts | Spans per stage, model call and tool call; a cost receipt per run |

Run control, release lifecycle and identities: [docs/architecture.md](docs/architecture.md).
Authoritative design: [docs/spec/](docs/spec/README.md) and the [ADRs](docs/adr/README.md).

## The two agents

**Researcher** (`docwiki-researcher`, app role `Wiki.Read`). Read tools only. It searches
(expanding acronyms with the glossary), reads the best topic, entity and source pages, confirms
every decisive fact with `get_evidence` or `query_table`, and answers in at most 12 tool calls.
Every factual sentence ends with `[n]`; the answer ends with a `Sources:` list of
`[n] <source title> — <locator label> (<provenance>) — <sidecar path>`. It gives current
information before superseded information, states contradictions with the wiki's resolution rule
instead of resolving them silently, and replies "Not found in the wiki." rather than guessing.

**Librarian** (`docwiki-librarian`, app roles `Wiki.Read` and `Wiki.Operate`). Read tools plus
operations: `run_status`, `list_sources`, `quality_report`, `explain_source`, `list_proposals` and
`write_health_report` run freely; `ingest_start`, `recompile` and `decide_proposal` require
**human approval on every call**. It never claims a run succeeded without `run_status`, never
edits content directly, diagnoses quarantined sources and proposes precise recompile hints. An
optional daily routine (disabled by default) writes a health report with approval-free tools only.

**Per-agent identity, enforced by the server.** Each agent calls the MCP server with its own Entra
agent identity. Entra issues a token only to identities holding an app role on the MCP API;
Container Apps built-in authentication accepts only that audience from the two allow-listed agent
client IDs; the server checks the role on every call (the tool list is not filtered per role,
decision D9). A forbidden call returns `{"ok": false, "error": {"code": "forbidden"}}`, so the agent turn
continues. The design was validated end to end before it was adopted
([ADR 0003](docs/adr/0003-mcp-agent-identity.md), [identity spike](docs/spikes/identity-spike.md)).
More: [docs/agents.md](docs/agents.md).

## Scoreboard

DocWiki is measured against a naive RAG baseline (BM25 top-8 over about 800-token chunks, same
`smart` model, same answer format) and a long-context baseline, on a golden set sealed before the
first wiki generation: a public dev split in 12 categories (single-hop, multi-hop, numeric,
tables, contradictions, supersession, multilingual, OCR, abstention, injection, restricted
content, skills) plus a private holdout. Dev and holdout scores are published separately, with
denominators, versions and the ids of failed questions. **Pending re-evaluation on the new
sample:** the Researcher and both baselines are re-run on the 12-document corpus, and the
scoreboard below is generated from those results. Method: [docs/evaluation.md](docs/evaluation.md).

<!-- scoreboard:start -->
No evaluation results yet. Run `uv run python evals/run.py --system <system> --questions evals/golden/dev.jsonl`, then `uv run python evals/scoreboard.py` (see `evals/README.md`).
<!-- scoreboard:end -->

**Reading the scores.** Pending re-evaluation on the new sample: the Researcher and both baselines
are re-run on the 12-document corpus, and this section is rewritten from the generated scoreboard
above. No comparison between the systems is claimed until then. On a corpus this small, a
difference of one or two questions is noise.

## Cost

- **Idle is close to zero.** Jobs and apps scale to zero, models are pay-per-token, and there is no
  search service or database to keep running. What remains when nothing runs: the Basic container
  registry, storage and Log Analytics ingestion.
- **You pay when you compile or ask:** tokens on the `fast` and `smart` deployments, Content
  Understanding pages (PDFs and images) and job compute. Unchanged sources are never re-extracted
  or recompiled (content-addressed cache); entity summaries and topic syntheses are rebuilt
  whenever a source changes, so they dominate the cost of a small change.
- **Every run writes a cost receipt** (tokens × price table, Content Understanding pages,
  duration). The packaged price table holds Global Standard list prices and is marked
  `verified: false`: check the prices of your region and deployment type before relying on it.

**Figures for the new sample are pending re-measurement.** After the first cold compile and the
evaluation on Azure, [docs/cost.md](docs/cost.md) reports, from the run receipts: a full ingest
with a cold cache, a recompile of one source, a rebuild with no source changed, the cost of a
Researcher answer and of a naive RAG answer, and an estimate of an idle month.

Cost model and levers: [docs/cost.md](docs/cost.md).

## Limitations

DocWiki is a proof of concept. Known limits of this version:

- **One small corpus.** The sample has 12 public documents; larger corpora, other domains and
  repeated runs are untested, and scores and costs are pending re-evaluation on it.
- **Document stamps read as content.** Compilation can list the `FICTIONAL — NOT FOR
  OPERATIONAL USE` stamp as a fact of a source page, or report it as a contradiction in a topic.
  A prompt rule would fix it, at the cost of a full recompile; to be re-checked on the new sample.
- **Coarse invalidation.** Any changed source rebuilds every entity summary and topic synthesis,
  which dominates the cost of a small change.
- **Unverified prices, optional judge.** Cost receipts use an unverified price table; the built-in
  judge evaluators are optional, and a score is a deterministic check unless it says otherwise.
- **Preview dependencies.** The per-agent identity relies on a preview API surface (the
  `AgenticIdentityToken` MCP connection, [ADR 0003](docs/adr/0003-mcp-agent-identity.md)); it may
  change.

## Security and responsible AI

- **Zero secrets.** Managed identities and `DefaultAzureCredential` everywhere: no keys,
  connection strings, SAS tokens or `listKeys()`. Foundry local auth, storage shared keys and the
  registry admin user are disabled.
- **Least privilege.** One managed identity per workload (jobs, MCP server, portal) and one Entra
  agent identity per agent; the MCP server may write only reports, proposals and the overlay.
- **Documents are untrusted data.** Model calls that read documents use structured outputs and no
  tools. Output is sanitised (no raw HTML, scripts or external links). Sentences addressed to AI
  assistants are dropped, filed as injection proposals and shown as a visible placeholder in the
  evidence. Skills come only from reviewed templates.
- **Injection canary.** The sample corpus plants an instruction with a unique canary token; gate
  G08 fails the release if the token reaches `AGENTS.md`, skills, indexes, evidence or the site.
- **Sensitivity tiers.** Sources are `public`, `internal` or `restricted`. A build targets one
  audience and excludes everything above it from pages, evidence, catalog and search rows (gate
  G07); the sample includes a restricted document that must never reach the public build.
- **Human in the loop and honest evidence.** Mutating operations need approval; OCR text and
  generated figure descriptions are labelled as such and never presented as quotes; the
  Researcher abstains rather than guess.
- **Publication safety.** A leak guard scans the tree, the git history and binary metadata, and a
  fail-closed pre-push hook runs it.

> **FICTIONAL — NOT FOR OPERATIONAL USE.** The sample corpus describes an invented building
> contractor, its client household, its suppliers and an invented works site in an invented town.
> Every organisation, person, product, price, date and value in it is fictional, and the two site
> photos are AI-generated images, not photographs of a real site
> ([provenance](samples/generators/assets/photos/PROVENANCE.md)). Documents that look like
> quotes, contracts, schedules or invoices carry this stamp and must never be used as real
> commercial, legal or construction guidance.

Threat model and publication process: [docs/security.md](docs/security.md). Report
vulnerabilities privately: [SECURITY.md](SECURITY.md).

## Documentation

| Guide | Content |
|---|---|
| [Architecture](docs/architecture.md) | Components, data flow, run control, release lifecycle, identities |
| [Wiki format](docs/wiki-format.md) | A tour of the wiki contract with an example page |
| [Agents](docs/agents.md) | Researcher and Librarian: behaviour, tools, approvals, routine |
| [Skills and agent kit](docs/skills.md) | `AGENTS.md`, `llms.txt`, catalog, search index, skill projections |
| [Local agents](docs/local-agents.md) | GitHub Copilot (VS Code and CLI), Claude Code and Codex on a release |
| [Security](docs/security.md) | Threat model, identity model, leak guard, publication process |
| [Evaluation](docs/evaluation.md) | Golden set, systems, metrics, honesty rules |
| [Cost](docs/cost.md) | Cost model and levers |
| [Domain packs](docs/domain-packs.md) | Adapting DocWiki to your industry |
| [FAQ](docs/faq.md) | Short answers to the usual questions |
| [Operations](docs/operations.md) | Day-2 runbook for an Azure deployment |

## Repository map

| Path | Content |
|---|---|
| [`src/docwiki/`](src/docwiki) | The Python package: `extract`, `evidence`, `stages`, `orchestration`, `llm`, `mcp`, `agents_client`, `release`, `search`, `storage`, `site`, `portal`, `domain`, `contracts` |
| [`agents/`](agents/README.md) | Researcher and Librarian definitions, instructions, routine and deployment script |
| [`skills/templates/`](skills/templates) | Reviewed templates of `AGENTS.md` and the four core skills |
| [`domains/`](domains) | The domain pack of the sample, `batiment` |
| [`samples/`](samples) | Fictional world bible, deterministic generators, sample corpus (its two site photos are AI-generated), mock release |
| [`evals/golden/`](evals/golden/README.md) | Sealed public dev split of the golden set |
| [`site/`](site/README.md) | Quartz overlay (pinned Quartz v4.5.2) |
| [`infra/`](infra), [`azure.yaml`](azure.yaml), [`docker/`](docker), [`scripts/`](scripts) | Bicep, azd hooks, images, preflight and teardown |
| [`tools/leakguard/`](tools/leakguard/README.md), [`.githooks/`](.githooks) | Publication-safety scanner and fail-closed pre-push hook |
| [`docs/`](docs/README.md) | Guides, [frozen spec](docs/spec/README.md), [ADRs](docs/adr/README.md), spikes |
| [`tests/`](tests) | Offline test suite (tests needing Azure are marked `live`) |

## Related work

- **[LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)** by Andrej
  Karpathy: the pattern DocWiki follows. Raw sources stay immutable, an LLM-maintained wiki sits on
  top, and a schema file tells agents how to use it. DocWiki applies it to operational document
  sets, with deterministic citations, releases and access tiers.
- **[WikiKB](https://github.com/githubnext/wikikb)** by GitHub Next: a knowledge base for people
  and agents stored in a GitHub repository's wiki, with local embeddings and an agent skill.
- **[qmd](https://github.com/tobi/qmd)** by Tobi Lütke: an on-device search engine for Markdown
  notes and transcripts (BM25, vector search and LLM re-ranking) with an MCP server.
- **[Foundry IQ](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/what-is-foundry-iq)**:
  Microsoft's managed knowledge layer that turns enterprise data into permission-aware knowledge
  bases for agents. It is the managed-retrieval alternative, and the documented extension for very
  large corpora ([ADR 0001](docs/adr/0001-compiled-wiki-over-vector-index.md)).

## Contributing

Contributions are welcome: read [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md)
(the instructions for coding agents and humans alike). The design is frozen in
[docs/spec/](docs/spec/README.md); propose changes instead of diverging silently.

## License

- Code: [MIT](LICENSE).
- Sample content (fictional world, corpus, fixtures, golden set, images and diagrams
  under `docs/`): [CC BY 4.0](LICENSE-CONTENT.md). Attribution: "DocWiki sample corpus by Ozgur
  Karahan, CC BY 4.0".

## Acknowledgements

- Andrej Karpathy for the LLM-wiki idea.
- The open-source projects DocWiki builds on, among them [Quartz](https://github.com/jackyzha0/quartz),
  the Model Context Protocol Python SDK, Microsoft Agent Framework, DuckDB, SQLite FTS5, pypdfium2,
  python-docx, openpyxl, python-pptx, Pillow, Jinja2, pydantic and Typer.
- Microsoft's fictitious brand names (Lamna, VanArsdel, Zava, Adatum), which name the companies of
  the sample world.

---

Created by [Ozgur Karahan](https://github.com/ozgurkarahan), cloud and AI solution architect.
DocWiki is an independent open-source project; it is not an official Microsoft or GitHub product.
