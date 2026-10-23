# DocWiki specification (v1, frozen)

This folder is the **authoritative design** for DocWiki. Implementation lanes build only from these
documents and the contracts derived from them. Changes require a new spec version.

| Document | What it defines |
|---|---|
| [architecture.md](architecture.md) | Components, Azure topology, storage layout, run control, releases, identities |
| [wiki-contract.md](wiki-contract.md) | Wiki layout, page types, frontmatter, IDs, links, anchors, indexes, agent kit |
| [evidence-contract.md](evidence-contract.md) | ExtractedDoc, blocks, locators, provenance, sidecars, quote verification |
| [pipeline.md](pipeline.md) | Stages, cache keys, LLM usage, quality gates, CLI |
| [mcp-and-agents.md](mcp-and-agents.md) | MCP tools and auth, Researcher and Librarian agents, routines, local use |
| [domain-and-corpus.md](domain-and-corpus.md) | Domain packs, fiction rules, sample corpus, golden set |
| [evals.md](evals.md) | Metrics, baselines, evaluation runner, scoreboard |
| [infra-ops-security.md](infra-ops-security.md) | Azure resources, identities, operations, threat model, leak guard, release |
| [site.md](site.md) | Quartz site, evidence microscope, portal |
| [engine-interfaces.md](engine-interfaces.md) | Cross-lane engine signatures (v1 addendum) |
| [CHANGELOG.md](CHANGELOG.md) | v1.1 clarifications discovered while building; v1.2 sample-world amendment |

## 1. Product in one paragraph

DocWiki turns a folder of heterogeneous documents into a **compiled knowledge base**: a Markdown wiki
following the "LLM wiki" pattern (raw sources stay immutable; an LLM-maintained wiki sits on top;
a schema file tells agents how to use it). The wiki is human-navigable (static site, Obsidian,
GitHub) and agent-ready (`index.md`, `AGENTS.md`, `llms.txt`, `catalog.json`, a search index,
Agent Skills and an MCP server). Every claim is linked to an **evidence sidecar** showing the
exact page, sheet rows, slide or transcript cue it came from, with a provenance badge.

## 2. Goals and non-goals

Goals:

- G1. Compile PDF, DOCX, XLSX, CSV, PPTX, EML, images/scans, VTT and Markdown/TXT inputs.
- G2. Produce source pages, entity pages, topic syntheses, indexes, glossary, log and agent kit.
- G3. Cite every generated fact to a locator; verify quotes deterministically where possible.
- G4. Run as an Azure Container Apps Job with Microsoft Foundry models; publish immutable releases.
- G5. Expose the wiki through an MCP server used by two Foundry prompt agents and by local agents.
- G6. Detect contradictions and supersession between documents; respect sensitivity tiers.
- G7. Prove quality with a golden set and baselines; publish honest, reproducible numbers.
- G8. Ship a public sample (fictional French general contractor with several chantiers at
  different phases and the company's own documents; v1.7, ADR 0011) browsable on Azure Container
  Apps.

Non-goals (v1): multi-tenant SaaS, private networking, real-time collaborative editing, audio/video
beyond transcripts, vector database by default, replacing enterprise search.

## 3. Principles

1. **Deterministic where possible, LLM where valuable.** Paths, IDs, links, indexes, tables and
   gates are computed. LLMs summarise, classify ambiguous cases and synthesise topics.
2. **Evidence first.** No citation, no claim. Provenance types are explicit.
3. **Idempotent and content-addressed.** Every stage output is keyed by its inputs and versions.
4. **Immutable releases.** Readers only ever see a complete, validated release.
5. **Documents are untrusted.** They never become instructions, skills, HTML or external links.
6. **Zero secrets.** Managed identities everywhere; no keys or connection strings.
7. **Portable.** The same wiki, skills and MCP tools work in Foundry, Copilot CLI, VS Code and
   Claude Code, and offline from a folder.
8. **Honest proof.** Baselines, denominators, versions and costs are published with every score.

## 4. Decision log (v1)

| ID | Decision | Rationale |
|---|---|---|
| D1 | Batch compilation runs in an ACA Job; the Librarian agent is a Foundry **prompt agent** acting as control plane. | Long batches must not run inside an agent request; prompt agents are GA and declarative. |
| D2 | The Researcher is a Foundry prompt agent using MCP tools (full-text search, evidence, DuckDB table queries, on-demand skills). No vector database by default. | Wiki navigation plus FTS covers the target scale at near-zero idle cost; a managed search service is an optional extension. |
| D3 | One ExtractedDoc evidence contract with two adapters (Azure Content Understanding, local). Tables always parsed deterministically. | Avoid adapter drift; exact numbers. |
| D4 | Standard relative Markdown links; deterministic backlinks block; headings as stable anchors; no raw HTML. | Renders on GitHub, Quartz, Obsidian and VS Code; safe. |
| D5 | Skills are generated **only** from reviewed templates with deterministic slot-filling, projected for every agent client. | Prevents skill poisoning from documents; portability. |
| D6 | Evidence provenance types: native-text, ocr, deterministic-table, model-description. | Honest verification badges. |
| D7 | Queue-woken, level-triggered single-execution job plus scheduled reconcile. | Robust to bursts, crashes and lost messages. |
| D8 | Blob-only state with ETags; content-addressed artifacts; immutable releases plus atomic pointer. | No database to operate; consistent readers. |
| D9 | Server-side role enforcement in the MCP server based on distinct agent principals. | Tool visibility is not authorization. |
| D10 | Wiki written in English; original-language quotes preserved; multilingual glossary synonyms. | One searchable canonical language without losing source fidelity. |
| D11 | Sensitivity tiers (public, internal, restricted); builds per audience; never merge across tiers. | Consolidation must not flatten access rights. |
| D12 | Golden set authored after the corpus is frozen and before the first full generation; private holdout. | Credible evaluation. |
| D13 | Quartz static site for humans; the public sample is served by the portal on ACA (v1.4: GitHub Pages retired); optional sign-in portal on ACA. | No custom UI to maintain; strong navigation features. |

## 5. Glossary

| Term | Meaning |
|---|---|
| Source | One input document (file) with a stable `source_id`. |
| Revision | A newer source that supersedes an older one (same document number). |
| Block | A unit of extracted content (paragraph, table, figure, slide, cue…) with a locator. |
| Locator | Precise position of a block in the original (page, sheet+rows, slide, paragraph, cue…). |
| Provenance | How a block's text was obtained (native-text, ocr, deterministic-table, model-description). |
| Evidence sidecar | Generated page showing a locator (page image with highlight, row table…) next to the original. |
| Page | A wiki Markdown file (source, entity, topic, index, query, meta). |
| Entity | A registry object of the domain (organisation, person role, document type, work package, product, code…). |
| Topic | A curated subject from the domain's closed topic catalog, synthesised from several sources. |
| Domain pack | Configuration describing a domain: taxonomy, entities, topics, glossary, rules, skill templates. |
| Release | Immutable, validated snapshot of the wiki, site, evidence, catalog and search index. |
| Agent kit | `AGENTS.md`, `llms.txt`, `catalog.json`, search index and skills shipped with every wiki. |
| Proposal | A suggested change (new entity, glossary term, topic, flagged injection) awaiting approval. |
| Audience | Sensitivity level a build targets: `public`, `internal` or `restricted`. |
