# FAQ

- [Why not vector RAG?](#why-not-vector-rag)
- [Why an Azure Container Apps Job and not a hosted agent?](#why-an-azure-container-apps-job-and-not-a-hosted-agent)
- [Why prompt agents?](#why-prompt-agents)
- [How are citations verified?](#how-are-citations-verified)
- [What about permissions?](#what-about-permissions)
- [Which languages are supported?](#which-languages-are-supported)
- [How far does it scale?](#how-far-does-it-scale)
- [What does it cost?](#what-does-it-cost)
- [Can I use it offline?](#can-i-use-it-offline)
- [How can I contribute?](#how-can-i-contribute)

## Why not vector RAG?

Because the hard questions in operational documents are cross-document. Which revision of a
procedure is current? Does the maintenance plan contradict it? Which alarms in a long SCADA log
match the root cause in an incident report? Retrieval re-discovers those relations from raw
chunks at every question; DocWiki compiles them once into source, entity and topic pages with
explicit supersession and contradiction sections, and gives agents a map (indexes, typed links,
a glossary, a log) instead of a pile of chunks.

It does not give up on retrieval: `search.db` indexes page sections **and** every raw extracted
block, so details that compilation left out stay findable, and `query_table` answers numeric
questions from the parsed tables with row ids instead of from embeddings. There is no vector
database by default, which keeps idle cost near zero and leaves one source of truth.

The trade-off is real: compilation spends tokens up front. That is why DocWiki is evaluated
against a naive RAG baseline and a long-context baseline on the same questions, with the results
published either way ([evaluation](evaluation.md)). For very large or fast-changing corpora, a
managed retrieval layer such as Foundry IQ is the documented extension
([ADR 0001](adr/0001-compiled-wiki-over-vector-index.md)).

## Why an Azure Container Apps Job and not a hosted agent?

Compiling dozens to thousands of documents takes minutes to hours. An agent request is the wrong
place for that: a foreground request is not resumed after a crash or a redeploy, and agent
schedules cannot react to new files. DocWiki runs the pipeline as a Container Apps Job, woken by a
queue (new or deleted blobs, the Librarian, a schedule), with at most one execution, a renewable
blob lease and level-triggered diffing. Every stage is idempotent and content-addressed, so a
crashed or timed-out run loses nothing: the next execution reuses every artifact already computed.

The agent stays where it is useful: the Librarian is the **control plane**. It starts ingests,
watches runs, diagnoses failures and proposes fixes, with a human approving every change
([ADR 0002](adr/0002-aca-job-with-agent-control-plane.md)).

## Why prompt agents?

They are declarative: instructions, a model deployment and one MCP tool, versioned as code in
[`agents/`](../agents/README.md) and deployed by adding versions. No custom code runs inside the
agent, so there is nothing to host, patch or scale; the heavy work lives in the job and the MCP
server, which are ordinary, testable Python. Each prompt agent also gets its own Entra agent
identity, which DocWiki relies on to enforce roles server-side
([ADR 0003](adr/0003-mcp-agent-identity.md)). The same MCP tools and skills work unchanged with
local coding agents.

## How are citations verified?

By code, not by a model. Compilation returns facts with citations `{block_id, quote}`; then:

1. Quote and block text are normalised (Unicode NFKC, case-folded, straight quotes, collapsed
   whitespace, soft hyphens removed).
2. The quote must be a substring of the cited block, or of the cited blocks joined.
3. Every number with its unit in the fact must appear in a cited block or table cell.
4. Table citations must reference existing row ids, and cited cell values must match exactly.

A verified quote earns `✓ quote verified`; a citation without a quote whose numbers match is
labelled `paraphrase`; table cells parsed by code are labelled `table`; OCR text and generated
figure descriptions can never earn a check mark. Failed citations are removed, and gate G04 blocks
a release when fewer than 95 % of quoted citations verify. Every footnote opens an evidence
sidecar, so a human can check any claim in one click, and the evaluation measures citation
precision and recall. See [the wiki format](wiki-format.md#citations-and-provenance-badges).

## What about permissions?

DocWiki v1 does coarse, document-level access control. Each source gets a sensitivity tier
(`public`, `internal`, `restricted`) from the domain pack's rules, a build targets one audience,
and anything above it is excluded completely: no page, mention, evidence, catalog entry or search
row. Pages never mix tiers the audience may not see.

Per-user permissions (filtering by each reader's own rights) are out of scope for v1. Run one
deployment per audience and protect each one: Entra sign-in on the private portal, and the MCP
allowlist and app roles for agents. If you need permission-aware retrieval over live enterprise
sources, Foundry IQ is designed for that.

## Which languages are supported?

Documents can be in any language the models read; the sample corpus mixes English, French and
German. The wiki itself is written in **English**, one canonical language that is easy to search,
while **quotes stay in their original language** so that verification runs on the source text.
Glossary synonyms and entity and topic aliases are multilingual, and search expands queries with
them. The Researcher answers in the language of the question and never translates locator labels.

## How far does it scale?

The design targets corpora of dozens to thousands of documents. Work is bounded (300 pages per
document, map-reduce for long documents, concurrency limits per deployment), runs are incremental,
and search runs on SQLite FTS5 inside each release. Every release is a complete snapshot, so
storage grows with the corpus times the number of retained releases (10 by default). Beyond that
scale, or for content that changes by the minute, use a managed search service next to the wiki.
Measured on the 37-document sample: a full ingest took 20.4 minutes; it was only tested at that
size.

## What does it cost?

Close to nothing when idle: jobs and apps scale to zero, models are pay-per-token, and there is no
database or search service. You pay for tokens and Content Understanding pages when you compile,
and for tokens when an agent answers. Every run writes a cost receipt. On the 37-document sample, a
full ingest cost about 17 USD and a Researcher answer about 0.12 USD (receipt estimates); details
and levers in [cost](cost.md).

## Can I use it offline?

**Reading, yes.** A release is plain files: Markdown, SQLite, Parquet and images. Open the wiki in
Obsidian (`docwiki export obsidian` rewrites links as `[[wikilinks]]`), VS Code or any editor, and
serve it to local agents with the stdio MCP server, which needs no network once dependencies are
installed ([local agents](local-agents.md)).

**Compiling, no.** Compilation calls models on a Foundry project; there is no local model support in
v1. The test suite runs offline with a fake model client and recorded replays. Content
Understanding is used only in Azure mode, so locally, pages without a text layer (scans, photos)
are flagged and not OCR'd.

## How can I contribute?

Read [CONTRIBUTING.md](../CONTRIBUTING.md) and [AGENTS.md](../AGENTS.md). Good first contributions
are domain packs for other industries, extraction fixes with tests, and documentation. Sample
content must use the fictional names of the world bible; the design in [`docs/spec/`](spec/README.md)
is frozen, so propose spec changes rather than diverging silently. Report vulnerabilities
privately ([SECURITY.md](../SECURITY.md)).
