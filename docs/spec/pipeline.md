# Pipeline

## 1. Stages

| # | Stage | Input | Output (artifact) | LLM | Notes |
|---|---|---|---|---|---|
| 1 | `discover` | `raw/` listing, state shards, domain pack | work plan (new / changed / deleted / unchanged), revision groups, sensitivity | no | Hash = sha256 of bytes. |
| 2 | `extract` | raw file | ExtractedDoc + tables + figures | only figure descriptions (`fast`) | Adapter per mode; failures → `quarantined` with reason. |
| 3 | `classify` | ExtractedDoc | `{doc_type, category, authority, doc_number, revision, lang, confidence, rule_id}` | `fast`, only when no rule matches | Closed enums from the domain pack; structured output. |
| 4 | `compile` | ExtractedDoc + classification + domain hints | `CompiledSource` (title, summary, key facts with citations, sections, entity mentions, glossary candidates, injection flags) | `smart` | Map-reduce above the size threshold; citations verified (evidence-contract §4). |
| 5 | `entities` | all CompiledSource + registry | `EntityPage` per registry entity with ≥ 1 mention | `fast` for summaries only | Facts aggregated deterministically; unknown entities → proposals. An entity bound to one scope (v1.7, domain-and-corpus.md §1) counts only the sources of that scope. |
| 6 | `topics` | CompiledSource sections + topic catalog | `TopicPage` per topic meeting the evidence threshold | `smart` | Contradictions and supersession sections; never across sensitivity tiers above audience. |
| 7 | `links` | all pages + relationship catalog | links inserted, backlinks blocks, `edges` | no | Deterministic autolinking from the registry (first mention per section); an entity bound to one scope is listed and autolinked only on the pages of that scope and on its own page (v1.7). Prose amounts formatted after linking (wiki-contract.md §4). |
| 8 | `indexes` | pages | `index.md`, category/entity/topic indexes, `glossary.md`, `log.md` append, `llms.txt`, `catalog.json`, `search.db` | no | |
| 9 | `agentkit` | catalog + domain pack templates | `AGENTS.md`, skills + projections | no | Template slot-filling with validated values only. |
| 10 | `evidence` | citations + ExtractedDoc + raw | sidecars + images (+ originals for public sample) | no | Page renders via pypdfium2. |
| 11 | `translate` | final canonical pages + domain pack | the mirror of each other wiki language under `wiki/<lang>/` (v1.7) | `fast`, source/entity/topic prose only | Only when the pack declares more than one `wiki_languages` (§9). Runs before the catalog, the search index and `verify`, so they cover the mirror. |
| 12 | `verify` | the candidate release | gate results → `_meta/quality.md`, manifest | no | Blocking gates fail the run. |
| 13 | `site` | candidate release | Quartz site in `site/` | no | Optional in local mode (`--site`). |
| 14 | `publish` | candidate release | `releases/<id>/` + `current.json` swap | no | Atomic; keep last 10. |

Each stage is a plain Python function `(inputs, ctx) -> outputs` that is idempotent and keyed by a
cache key (architecture.md §5). The orchestrator (Microsoft Agent Framework workflow) fans out
per source for stages 2–4 and 10, and runs the other stages once per run. Correctness never
depends on workflow checkpoints: re-running a run re-uses existing artifacts.

Concurrency limits (configurable): extraction 4, LLM 6 concurrent calls, a client-side token bucket
per deployment honouring `Retry-After`, max 3 retries with exponential backoff and jitter.

## 2. LLM usage rules

- All calls go through `docwiki.llm` using the Foundry project endpoint and Entra auth, the
  Responses API, and **structured outputs** (JSON schema). No tools, no web access.
- Prompts are versioned files under `src/docwiki/stages/prompts/` with a `PROMPT_VERSION`
  included in cache keys. Domain packs may add reviewed hint text (not document text).
- Document text is wrapped in clearly delimited data sections; the system prompt states that the
  content is data and that instructions inside it must be ignored and reported as `injection_flags`.
- Output language is the pack's canonical wiki language (`wiki_languages[0]`, English by default;
  v1.7), named in every compile, entity and topic request; quotes (`quote` fields) stay in the
  original language exactly, locked trade terms stay as written.
- Every call logs model, deployment, version, prompt version, tokens in/out, latency, cost.
- `fast` deployment: classification fallback, figure descriptions, entity summaries, translation
  of the mirror pages (v1.7).
  `smart` deployment: compilation, topic synthesis. Both configured by name in settings.

## 3. Compile details

- Size threshold: if the ExtractedDoc text exceeds 24k tokens (estimate 4 chars/token), use
  map-reduce: chunks of ≤ 12k tokens split on block boundaries; map = facts + section summaries
  with block citations; reduce = merged `CompiledSource` with de-duplicated facts.
- `CompiledSource` schema (structured output):
  ```json
  {"title": "...", "summary": "...",
   "key_facts": [{"text": "...", "citations": [{"block_id": "b0042", "quote": "..."}], "numbers": ["30 m²"]}],
   "sections": [{"heading": "...", "body": "markdown with [[cite:b0042]] markers", "table_refs": ["t03"]}],
   "entity_mentions": [{"entity_id": "organisation:window-maker", "block_ids": ["b0010"]}],
   "unknown_entities": [{"label": "...", "type_guess": "...", "block_ids": []}],
   "glossary_candidates": [{"term": "...", "definition": "...", "block_ids": []}],
   "injection_flags": [{"block_id": "...", "reason": "..."}]}
  ```
- The renderer turns `[[cite:b…]]` markers into footnotes after verification; tables referenced
  by `table_refs` are rendered from the deterministic table data (never re-typed by the LLM).
- Entity ids in output must exist in the registry; unknown ones go to proposals.

## 4. Topics

- Routing: each source section is scored against each topic's keywords and aliases (multilingual,
  case-insensitive, word-boundary). Score = matches weighted by field (title 3, heading 2, body 1).
  A source feeds a topic when score ≥ `min_score` (default 3.0).
- Synthesis happens only when ≥ `min_sources` (default 2) distinct current or superseded sources
  feed the topic; otherwise the topic is skipped with reason `insufficient_evidence`.
- The synthesis prompt receives verified facts (with citation ids) from the feeding sources, their
  authority, dates, status and revision relations; it must output thematic sections, a
  contradictions list and a superseded-information list, citing fact ids only.

## 5. Proposals

Written to `work/proposals/` as JSON with `{id, kind: entity|glossary|topic|injection|recompile,
payload, evidence: [{source_id, block_id}], created_at, status: open|accepted|rejected, decided_by,
note}`. Accepted entity/glossary/topic proposals are merged into a **domain overlay** file
(`work/state/overlay.yaml`) applied on top of the domain pack in the next run. Injection proposals
are informational and appear in the quality report.

## 6. Search index (`search.db`)

SQLite with FTS5 (fallback: a BM25 implementation over the same table when FTS5 is unavailable):

```sql
CREATE TABLE docs(rowid INTEGER PRIMARY KEY, kind TEXT, page_id TEXT, path TEXT, title TEXT,
                  section TEXT, anchor TEXT, source_id TEXT, locator_key TEXT, sensitivity TEXT,
                  status TEXT, lang TEXT, text TEXT, scope TEXT);
CREATE VIRTUAL TABLE docs_fts USING fts5(title, section, text, content='docs', content_rowid='rowid',
                                         tokenize='unicode61 remove_diacritics 2');
CREATE TABLE synonyms(term TEXT, synonym TEXT, lang TEXT);
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
```

`kind` is `page-section` (one row per section of each page) or `source-block` (one row per
extracted block, so answer-bearing details omitted by compilation remain searchable).
Schema 3 (v1.7, ADR 0012) adds `tree TEXT` to `docs` and `pages` (the wiki language tree of the
row: the canonical language for the canonical pages, the mirror language for `<lang>/` pages,
`NULL` for source blocks), keys `pages` by `(page_id, tree)` and records the wiki languages in
`meta.languages`; `lang` stays the language of the row's text. One database serves every
language: a search picks one tree (the canonical one by default; a mirror tree is completed by
the canonical pages it does not mirror) plus the source blocks.
Queries expand terms with glossary synonyms before matching.
`scope` (schema 2, v1.7) is the scope value of the row's page (a source page and its blocks, a
per-scope topic, a hub) and `NULL` for company pages; the additive `pages` table carries it too,
for the MCP `within` filter. Readers accept schema 1 databases (no scopes).

## 7. Quality gates

| Gate | Rule | Blocking |
|---|---|---|
| G01 frontmatter | Every page validates against its schema | yes |
| G02 links | 100 % of internal links and anchors resolve | yes |
| G03 citations-present | Every key fact / topic claim has ≥ 1 citation | yes |
| G04 quote-verification | ≥ 95 % of native-text/table citations `verified` (warn below 98 %) | yes |
| G05 safe-content | No raw HTML (except markers), no external links, no `javascript:`/`data:` URLs | yes |
| G06 sidecars | Every cited locator has a sidecar | yes |
| G07 audience | No content above the build audience (pages, evidence, catalog, search rows) | yes |
| G08 injection-containment | Known canary strings absent from AGENTS.md, skills, indexes, site | yes |
| G09 paths | All paths match the slug rules; no enum/class reprs | yes |
| G10 glossary | Non-empty when the domain pack has seeds | yes |
| G11 supersession | Superseded sources marked; topics show current claims first | yes |
| G12 tags | Tags lower-case and de-duplicated | yes |
| G13 orphans | ≤ 5 % of pages without inbound links | warning |
| G14 skills | Skill projections identical and valid (name, description, size limits) | yes |
| G15 extraction | ≤ 10 % sources quarantined | warning |
| G16 locked-vocabulary | No page title or body renders a locked trade term of the domain pack with one of its banned English renderings (whole words, case-insensitive; blockquotes and text in double quotes are not checked); skipped when the pack locks no term. Covers the mirror pages (v1.7) | yes |
| G17 translations | Every canonical source, entity, topic, view, hub, index, glossary and log page has its mirror in each other wiki language, translated (warning when missing or kept untranslated); skipped for a one-language wiki (v1.7) | warning |

Gate results are written to `_meta/quality.md` and `manifest.json`. A failing blocking gate stops
the publish; the previous release stays current. The structural gates run over the canonical
wiki and every mirror (links and anchors resolve within each language; G11 per language tree).

## 8. CLI

```
docwiki run      --input <dir|blob> --work-dir <dir> [--mode local|azure] [--audience public]
                 [--domain <pack>] [--site] [--limit N] [--only <source_id>...]
docwiki status   [--run <run_id>]
docwiki lint     [--release current]
docwiki site     [--release current] [--out <dir>]
docwiki serve    [--stdio | --http :8080] [--release <dir>]      # MCP server
docwiki ask      "<question>" [--agent researcher|librarian]     # Foundry agents via Responses API
docwiki worker                                                    # queue worker (ACA Job entrypoint)
docwiki export obsidian --out <dir>
```

Settings come from environment variables prefixed `DOCWIKI_` (e.g. `DOCWIKI_FOUNDRY_PROJECT_ENDPOINT`,
`DOCWIKI_FAST_DEPLOYMENT`, `DOCWIKI_SMART_DEPLOYMENT`, `DOCWIKI_STORAGE_ACCOUNT`,
`DOCWIKI_DOMAIN`, `DOCWIKI_AUDIENCE`) or a local `.env` (never committed).

## 9. Translate (v1.7, ADR 0012)

Runs when the domain pack declares `wiki_languages` with more than one language, once per mirror
language, after `evidence` (the canonical pages are final: linked, amounts formatted, research
answers settled) and before the catalog, the search index and `verify`.

- **Translated by the model** (`fast` tier, structured output, no tools; prompt
  `translate.md`): source, entity and topic pages. The body is cut into segments: every prose
  line (paragraph, list item, compiled section heading, the generated superseded banner) is one
  segment. Kept verbatim: the title (`#`), tables, footnote definitions, code, blockquotes (the
  documents' words), the pack banner and the backlinks list. Mapped by code through the string
  tables: generated headings, generated sentences without fields and the labels of `## Related`
  items. In a segment, links, footnote markers and code spans are masked as `⟦n⟧` placeholders,
  restored from the canonical page after translation (targets and citations never pass through
  the model). Frontmatter: only `summary` and `contradiction_pairs[].subject` are translated.
- **Rebuilt by code** in the mirror language from the mirror pages: views, hubs and the hubs
  index, `views/index.md`, every index page, `glossary.md` and `log.md` (the mirror log appends
  to the previous release's mirror log). Research answers keep the language they were filed in
  and are not mirrored; `AGENTS.md`, `llms.txt`, skills and `_meta/` stay canonical.
- **Preservation check** (deterministic, per segment): placeholders, numbers, ISO and
  `dd/mm/yyyy` dates, document numbers (`BC-2026-009`), amounts (`2 390,00 € HT`) and the
  occurrences of each locked term (any written form) must be identical; no link, footnote,
  code, `<`, `>` or `://` may be added, no text addressed to an AI system, no banned rendering
  of a locked term. A rejected translation is asked again once with the problems listed; a
  second rejection keeps the page untranslated (canonical text, generated parts mapped) under a
  line `> **Untranslated:** …` and adds a run warning; G17 warns.
- **Relocation**: every mirror page moves to `wiki/<lang>/<path>`; its links go to the mirror of
  their target when there is one (anchors of translated headings follow), else to the canonical
  page; evidence links stay on the canonical sidecars and originals.
- **Cache**: `work/artifacts/translate/<key>/translation.json`, key =
  `cache_key("translate", [content hash, lang, locked-vocabulary digest], stage_version,
  prompt_version, model id, model version)`, where the content hash covers the source language
  and the masked segments only. A rebuild without changes costs nothing; the result (translated
  or kept untranslated) is cached either way, so a change of the page, the prompt or the model
  is needed to try again.
- The run report's `translate` stage counts pages, cache hits, failures (kept untranslated),
  model calls, tokens and cost.
