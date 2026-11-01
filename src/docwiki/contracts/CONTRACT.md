# DocWiki contracts v1 (frozen interface)

This is the code-level interface every lane builds against. It implements `docs/spec/` (v1, frozen);
where the spec was silent or ambiguous, the decision taken is listed in §17 ("Decisions beyond the
spec"). Changing anything here is a contract change: update this file, the JSON Schemas
(`uv run python -m docwiki.contracts.export_schemas`) and tell the other lanes.

| Package | Purpose |
|---|---|
| `docwiki.contracts` | Pydantic models, ids/slugs/paths, locators, frontmatter, Markdown helpers and safety, storage protocol, settings keys, JSON Schema export |
| `docwiki.domain` | Domain-pack schema, `load_pack`, runtime overlay, deterministic rule helpers |
| `docwiki.search` | `search.db` builder and `SearchIndex` (SQLite FTS5 + pure-Python BM25 fallback) |
| `docwiki.release` | `ReleaseWriter`, publishing (pointer swap, retention, rollback), `ReleaseReader`, tables, `validate_release` |
| `samples/fixtures/mock-release/` | Hand-made release that passes `validate_release` with zero violations |

JSON Schemas of every contract live in `src/docwiki/contracts/schemas/*.schema.json`; a test fails
when they are stale.

## 1. Model conventions

- Every model derives from `ContractModel`: **strict** (no coercion: `"3"` is not an int) and
  `extra="forbid"`. Enumerations are `Literal` types (`docwiki.contracts.enums`), so YAML/JSON
  strings validate directly; tuples such as `PAGE_TYPES`, `SENSITIVITIES` and `PROVENANCES`
  list them at runtime.
- Dates (`IsoDate`) accept `date` objects or `YYYY-MM-DD`; datetimes (`UtcDateTime`) accept aware
  `datetime` objects or RFC 3339 strings and are normalised to UTC (serialised with `Z`).
- Serialise with `model.to_json_dict()` / `model.to_json()` (aliases such as `schema`, `from`) and
  parse with `Model.from_json(text)`. Lists usually default to `[]` and optional values to
  `None` (except `CompiledSource`, where every key is required for strict structured outputs).
- Hashes: raw content `sha256:<hex>` (`sha256_bytes`); file and manifest hashes plain 64-hex.
- `canonical_json(obj)` (sorted keys, compact, UTF-8) is the only input to identity hashes.

## 2. Identifiers, slugs and paths (`contracts.ids`, `contracts.layout`)

| Helper | Contract |
|---|---|
| `source_id_for(relative_path)` | `src-` + 12 hex of sha256(NFC, lower-cased raw POSIX path); rejects absolute, `..`, backslashes |
| `slugify_ascii(text, max_len=60)` | NFKD → ASCII (+ ß→ss, æ→ae, œ→oe, ø→o, đ/ð→d, ł→l, þ→th, ı→i), lower, `[^a-z0-9]+`→`-`, trimmed; `""` if nothing remains |
| `source_slug(stem, source_id)` | `slugify_ascii(stem)` or the `source_id` when empty |
| `assign_source_slugs(stems, existing=None)` | order-independent; keeps slugs of `existing` (previous release); every other source whose base slug is shared gets `-<4 hex of source_id>` (8/12 hex if still taken) |
| `assign_unique_slugs(names, max_len=40, fallback="item")` | ordered names (sheet names) → `x`, `x-2`, `x-3`… |
| `format/parse_entity_id` | `<type>:<key>`, both kebab ≤ 64; reserved types: `entities evidence glossary index log meta queries query source sources src topic topics` |
| `format/parse_topic_id`, `format/parse_query_id` | `topic:<slug>`, `query:<yyyy-mm-dd>-<slug>` |
| page paths | `sources/<slug>.md`, `entities/<type>/<key>.md`, `topics/<slug>.md`, `queries/<date>-<slug>.md`, `index_page_path(scope)` |
| `check_wiki_path(path)` | `None` or an error (gate G09): `^[a-z0-9][a-z0-9\-/._]*$`, no `.` in folder names, no `none/null/nan/undefined` segments; exempt fixed kit paths `AGENTS.md`, `_meta/…`, `.agents|.claude|.github/skills/<name>/SKILL.md` |
| `normalize_tags(tags)` | lower, strip, de-duplicate, sort |
| `cache_key(stage, input_hashes, *, stage_version, prompt_version, model_id, model_version, domain_pack_hash, schema_version=1)` | 64 hex of sha256(canonical_json([...])) with `input_hashes` sorted |
| `new_run_id(now, entropy)` | `run-YYYYMMDD-HHMMSS-<8 hex>` (lower-case: usable in `_meta/runs/<run_id>.md`) |
| `proposal_id_for(kind, payload)` | `prop-<12 hex>` of canonical `[kind, payload]` (same suggestion → same id) |
| `format/parse_release_id` | `YYYYMMDDTHHMMSSZ-<8 hex>` (see §12) |

Storage keys (`StorageKeys`): first segment is the container. `raw/<path>`,
`work/state/sources/<source_id>.json`, `work/state/lease`, `work/state/overlay.yaml`,
`work/state/domain-pack.json` (`DOMAIN_PACK`: the base domain pack recorded by every run, read by
the MCP server to validate proposal decisions),
`work/artifacts/<stage>/<cache_key>/…`, `work/runs/<run_id>/report.json`,
`work/proposals/<proposal_id>.json`, `work/reports/health-<date>.md`, `releases/<release_id>/…`,
`releases/current.json`. Helpers: `source_state_key`, `artifact_prefix`, `run_report_key`,
`proposal_key`, `health_report_key`, `release_prefix`.

## 3. Pages and frontmatter (`contracts.pages`, `contracts.frontmatter`)

`Frontmatter` is a union discriminated on `type`; `parse_frontmatter(dict)` validates YAML data.
`Page(path, frontmatter, body)` with `Page.parse(text, path)` / `page.render()`.

| Type | `id` | Path | Extra fields |
|---|---|---|---|
| source | `source_id` | `sources/<slug>.md` | `source_id, source_path, source_hash, media_type, doc_type, category, doc_number, revision, status, supersedes, superseded_by, original_lang, pages, entities, topics, authority (1–10), extraction{adapter, version, provenance_mix}` |
| entity | `<type>:<key>` | `entities/<type>/<key>.md` | `entity_type, key, aliases[{text, lang}], sources` |
| topic | `topic:<slug>` | `topics/<slug>.md` | `topic_slug, sources, confidence, contradictions, superseded_claims, contradiction_pairs` (v1.7, optional) |
| query | `query:<date>-<slug>` | `queries/<date>-<slug>.md` | `question, asked_by, sources, approved_by` |
| index | `index:home`, `index:sources`, `index:entities`, `index:entities/<type>`, `index:topics`, `index:queries` | `index.md`, `<scope>/index.md` | — |
| glossary / log | `glossary` / `log` | `glossary.md` / `log.md` | — |
| meta | `meta:agents`, `meta:quality`, `meta:runs/<run_id>`, `meta:<name>` | `AGENTS.md`, `_meta/quality.md`, `_meta/runs/<run_id>.md`, `_meta/<name>.md` | — |

Common fields: `id, type, title, summary (one line), lang, sensitivity, updated (date),
tags, docwiki{schema: 1, release}`; mirror pages (v1.7) add `translation_of` (equal to `id`),
written only on them. `lang` is a language code (`en` by default). Rules enforced by the models: tags lower-case ASCII words
joined by `-`, `_` or `/`, sorted, unique; id lists (`sources, entities, topics, supersedes, superseded_by`) sorted and unique;
`superseded` ⇒ `superseded_by` non-empty, `current` ⇒ empty; ids consistent with their fields.
`provenance_mix` counts blocks per provenance.

Writing: `write_frontmatter(data, body)` → `---` YAML in insertion order (model field order),
Unicode kept, no wrapping, `null` for unknown optional values, then one blank line and the body,
LF only, one trailing newline. Reading: `read_frontmatter(text) -> (dict, body)`; malformed blocks,
duplicate keys, BOM or CR raise `FrontmatterError`.

Skills: `SkillFile.parse(text, folder_name)`; frontmatter `name` (kebab ≤ 64, equal to the folder)
and `description` (≤ 1024); body ≤ 5,000 words.

## 4. Links, anchors and citations (`contracts.markdown`)

- **Content namespace.** Links are relative to the page in a namespace whose root is the wiki
  folder with the release's `evidence/` mounted at `evidence/` (exactly the Quartz `content/`
  layout). `wiki/evidence` is therefore reserved. Use `relative_link(from_path, to_path)`
  (`sources/a.md` → `evidence/<sid>/p0003.md` gives `../evidence/<sid>/p0003.md`; from an entity
  page `../../evidence/…`) and `resolve_href(from_path, href) -> ResolvedHref`.
- `heading_anchor(text)` = github-slugger (identical for ASCII); `Slugger` de-duplicates
  (`x`, `x-1`, …); `extract_headings(md)` uses rendered heading text.
- Footnotes: labels `c1…cN` in order of first use; definitions are single lines
  `[^cN]: [<source title> — <locator label>](<sidecar>) · <badge>` with
  `badge_for(provenance, status)` ∈ `✓ quote verified | paraphrase | table | OCR | generated description`.
- Backlinks block: `<!-- docwiki:backlinks:start -->` … `<!-- docwiki:backlinks:end -->`, each
  marker alone on its line; `strip_backlinks_block(md)`.
- Other helpers: `extract_links`, `extract_footnotes`, `split_sections`, `markdown_to_text`.

## 5. Evidence and locators (`contracts.locators`, `contracts.extracted`)

`Locator` is a union discriminated on `kind`. Bounding boxes are `[x0, y0, x1, y1]` normalised to
`[0, 1]`, origin top-left.

| `kind` | Fields | `locator_key` | `locator_label` |
|---|---|---|---|
| `pdf-page` | `page`, `bbox?` | `p0003` | `p. 3` |
| `docx-paragraph` | `paragraph` | `para-0042` | `¶ 42` |
| `docx-table` | `table`, `row_start`, `row_end` | `tbl-02-r0003-r0007` | `table 2, rows 3–7` |
| `xlsx-rows` | `sheet`, `sheet_slug?`, `row_start`, `row_end`, `cols?` | `sheet-<slug>-r0012-r0020` | `sheet "Plan", rows 12–20` |
| `csv-rows` | `row_start`, `row_end` | `r0012-r0020` | `rows 12–20` |
| `pptx-slide` | `slide`, `shape?` | `slide-05` | `slide 5` |
| `eml-part` | `part` (`headers`, `body`, `attachment:<name>`), `line_start?`, `line_end?` | `msg-body-l0010-l0018`, `msg-headers`, `msg-att-<slug>` | `message body, lines 10–18` |
| `vtt-cue` | `cue_start`, `cue_end` (`HH:MM:SS`) | `cue-00-03-15` | `03:15–03:42` |
| `image-region` | `page` (= 1), `region`, `bbox` | `img-b07` | `region 7` |
| `text-lines` | `line_start`, `line_end` | `l0010-l0018` | `lines 10–18` |

Single rows/lines use the singular (`row 3`, `line 4`). `parse_locator_key(key) -> LocatorKeyParts`
(round trip `parse_locator_key(k).key == k`). Rows are 1-based with the header as row 1; a table
row's `row_id` is `r` + 4-digit original row number (`row_id_for(12) == "r0012"`).

`ExtractedDoc{schema: 1, source_id, source_path, source_hash, media_type, lang, title_hint,
metadata{doc_number, revision, authored, page_count}, blocks, tables, figures, extraction{adapter,
adapter_version, analyzer, model, warnings}}`; block ids `b0001`, table ids `t01`, figure ids `f01`
(unique); table rows have exactly one cell per column; a figure `description` always comes with
`description_provenance: model-description`.

Sidecars: `evidence/<source_id>/<locator_key>.md` with `EvidenceFrontmatter{id:
"evidence:<sid>:<key>", type: evidence, title, source_id, locator, provenance, sensitivity}`;
per-source `evidence/<sid>/index.md` with `EvidenceIndexFrontmatter{id: "evidence:<sid>", type:
evidence-index, title, source_id, sensitivity}`; assets under `evidence/<sid>/img/`, published
originals as `evidence/<sid>/original.<ext>` (Markdown originals as `original.txt`, since every
`.md` under `evidence/` is a page). XLSX/CSV sidecars use `## Row N` headings (anchors
`#row-n`).

## 6. Catalog (`contracts.catalog`)

`Catalog{schema: 1, release_id, audience, generated_at, pages, edges, sources, glossary}` exactly
as wiki-contract §6, written to `catalog.json` and byte-identically to `wiki/catalog.json`. Build
entries with `catalog_page_for(frontmatter, path)` (source pages list themselves in `sources` and
copy `entities`/`topics`/`status`; entity/topic/query pages copy `sources`; others empty) and
`catalog_source_for(source_frontmatter)`.

Edge kinds (`from` → `to`): `mentions` source → entity; `supersedes` newer → older source;
`topic-of` topic → each source it synthesises; `cites` page → source whose evidence it cites;
`related` page → page linked from its `## Related` section when no other edge covers the pair.
Edges are unique; generators sort them by `(from, to, kind)`.

## 7. Compilation output (`contracts.compiled`, `contracts.strict_schema`)

`CompiledSource` follows pipeline §3; `quote` and `type_guess` are nullable, all keys required.
`CompiledSource.strict_schema()` / `strict_json_schema(model)` produce a self-contained schema
for OpenAI/Azure strict structured outputs (refs inlined, every property required,
`additionalProperties: false`, `anyOf [..., null]` for optionals, unsupported keywords removed);
`CompiledSource.response_format()` is the Responses API `text.format` payload;
`check_strict_schema(schema)` verifies the rules. Ids inside are plain strings, checked later by
citation verification (never by schema validation, so one bad id does not fail the whole call).

## 8. Run control and state

- `QueueMessage{schema: "docwiki.ingest/v1", kind, scope{source_ids, prefix}, hints: {str: str},
  requested_by, idempotency_key, created_at}`; `recompile` requires `scope.source_ids`; reviewed
  operator text goes in `hints["operator_notes"]`. `parse_queue_message(body)` accepts native
  messages, Event Grid or CloudEvents blob events (object or one-element list), plain or base64;
  events become `kind=ingest, requested_by=event, idempotency_key="event:<id>"`, empty scope,
  `hints{event_type, blob}`.
- `SourceState{schema: 1, source_id, raw_path, content_hash, size, media_type, sensitivity,
  revision_group, stages{<stage>: {status, cache_key, error, updated_at, retryable, attempts}},
  last_error, deleted, first_seen_at, updated_at, deleted_at}`; `source_id` must match `raw_path`;
  a deleted raw file keeps its shard as a tombstone (`deleted` + `deleted_at`). Write it with
  `If-Match`. A quarantine caused by a transient problem has `retryable: true`; `attempts` counts
  the consecutive failures of the stage for the current content, and the next runs retry it while
  `attempts < RETRY_ATTEMPTS` (3; `SourceState.retry_pending`); other quarantines are final until
  the content changes or a recompile is requested.
- `RunReport{schema: 1, run_id, kind, requested_by, status (running|succeeded|failed|no-op),
  started_at, finished_at, audience, release_id, previous_release_id, messages, counts, stages,
  gates, versions, cost, errors, warnings}`; `warnings` lists problems that did not fail the run
  (overlay entries left out, retention failures, refused queue renewals);
  `CostReceipt{currency: USD, price_table, llm[LlmUsage],
  content_understanding[…], duration_s, total_cost, notes}`; `LlmUsage.role` is `fast`, `smart`
  or `embed` (embedding batches: `calls` counts batches, `output_tokens` stays 0);
  `VersionInfo{docwiki, wiki_schema,
  domain_pack, domain_pack_hash, prompts, models{role: {deployment, model, version}}, extractors}`.
- `Proposal` = union on `kind` (`entity|glossary|topic|injection|recompile`) with typed payloads,
  `evidence[{source_id, block_id}]`, `status open|accepted|rejected`, `decided_by`, `decided_at`,
  `note`; `new_proposal(kind, payload, created_at=…)` sets the deterministic id; decisions need
  `decided_by`.
- `SettingsKeys` (`DOCWIKI_*`) and `SETTINGS_DEFAULTS`; new keys are added here first.

## 9. Storage protocol (`contracts.storage`)

```python
class Storage(Protocol):
    def read_bytes(self, key) -> bytes                       # KeyNotFoundError
    def read_with_etag(self, key) -> tuple[bytes, str]
    def write_bytes(self, key, data, *, if_match=None, if_none_match=None) -> str   # "*" = create only
    def exists(self, key) -> bool
    def etag(self, key) -> str | None
    def list(self, prefix="") -> list[str]                   # recursive, sorted
    def delete(self, key, *, if_match=None) -> bool          # False when missing
    def acquire_lease(self, key, duration_s, *, owner=None) -> Lease | None   # None = held
    def renew_lease(self, lease, duration_s=None) -> Lease   # LeaseLostError
    def release_lease(self, lease) -> None                   # LeaseLostError if someone else holds it
```

Failed preconditions raise `PreconditionFailedError`. ETags are opaque. `FolderStorage(root,
fsync=True)`: ETag = sha256 hex of the content, atomic writes (temp file + fsync + replace;
`fsync=False` for caches and tests), conditional writes and
leases serialised by per-key lock files, lease records with expiry under `.docwiki-storage/`
(never listed); acquiring a lease creates the key empty if missing; an expired lease can be
renewed while nobody else took it. The Blob implementation (engine lane) must keep these
semantics (map leases to blob leases, clamp durations to 15–60 s).

## 10. Release layout

```
releases/<release_id>/
  manifest.json      # ReleaseManifest; lists every other file with sha256 and size
  catalog.json       # also copied to wiki/catalog.json
  search.db
  wiki/              # wiki-contract §1 (no wiki/evidence)
  evidence/<source_id>/{index.md, <locator_key>.md, img/…, original.<ext>}
  tables/<source_id>/{index.json, <table_id>.parquet}
  site/              # optional Quartz output
releases/current.json  # CurrentPointer
```

**Tables** (not in the spec): one Parquet file per extracted table, `tables/<source_id>/t01.parquet`,
written with DuckDB `COPY … (FORMAT parquet)`. Columns: `row_id` (VARCHAR, `r0012`) then the table
columns renamed to unique ASCII snake_case (`Prix unitaire HT` → `prix_unitaire_ht`, empty →
`col_<n>`, leading digit → `c_…`). Types are inferred conservatively: `BIGINT`/`DOUBLE` only when
every non-empty cell is a plain number without leading zeros, otherwise `VARCHAR` with the exact
cell text; empty numeric cells are `NULL`. `index.json` = `SourceTablesIndex{schema: 1, source_id,
sensitivity, tables[{id, file, locator, provenance, columns[{name, header, type}], row_count,
row_ids}]}`. `connect_tables(release_root, source_id)` loads them as tables `t01…` into an
in-memory DuckDB with external access disabled and configuration locked; `query_tables(…, sql,
max_rows=200)` accepts a single `SELECT` and returns `TableQueryResult(columns, rows, truncated)`.

## 11. Release I/O (`docwiki.release`)

```python
writer = ReleaseWriter(staging_dir, created_at=…, audience=…, versions=VersionInfo(…),
                       inputs=ReleaseInputs(sources={sid: "sha256:…"}), run_id=…)
writer.release_id, writer.stamp            # DocwikiStamp for page frontmatter
writer.write_page(page) / write_wiki_file(path, text) / write_evidence(evidence_page)
writer.write_catalog(catalog) / write_tables(sid, tables, sensitivity) / write_search_db(pages, blocks, synonyms)
writer.write_text(rel, text) / write_bytes(rel, data) / copy_file(rel, src)
problems = validate_release(writer.root, require_manifest=False, audience=…)   # candidate gates
staged = writer.finalize(gates=gate_results(problems, skipped=[...]), counts={...})
pointer = publish_release(storage, staged, keep=10)   # upload (manifest last) → If-Match swap → retention
```

`publish_release` refuses manifests with failing blocking gates and raises `PointerConflictError`
when `current.json` changed concurrently. Retention runs after the swap and is best effort
(`try_retention(storage, keep=10) -> RetentionOutcome(deleted, error)` never raises; a failure is
logged and the next publish prunes again); `keep=None` leaves it to the caller (the pipeline
records its build state first). Also: `read_current_pointer`, `swap_current_pointer`,
`upload_release`, `rollback(storage, release_id)`, `apply_retention(storage, keep=10)` (newest
`keep` plus the current release are kept), `list_release_ids`, `read_manifest`,
`materialize_release(storage, release_id, dest_dir, expected_manifest_sha256=…)` (verified local
copy for the MCP cache).

`ReleaseReader.open(path, verify=False)` accepts a release folder, a portable wiki folder (§19), a
`releases/` folder with `current.json`, or a folder containing `releases/current.json`. API:
`layout`, `portable`, `manifest`, `manifest_sha256`, `release_id`, `audience`, `pointer`,
`pointer_bytes`, `catalog`, `wiki_root`, `evidence_root`, `tables_root`, `search_db_path`,
`file_for(manifest_path)`, `verify_files()`, `sources_with_tables()`, `list_pages(page_type=None)`, `page_entry(id_or_path)`,
`read_page(id_or_path) -> Page`, `read_page_text`, `read_section(page, heading_or_anchor)`,
`links(page) -> {outgoing, backlinks}`, `resolve_evidence(sid, key) -> EvidenceRecord(path,
frontmatter, body, original)`, `list_evidence(sid=None)`, `content_file(ns_path)`,
`open_search(force_fallback=False) -> SearchIndex`, `tables(sid)`, `table_file(sid, tid)`,
`connect_tables(sid)`, `query_table(sid, sql, max_rows=200)`, `list_skills() -> [SkillInfo(name,
description, path)]`, `read_skill(name)`.

## 12. Manifest and pointer (`contracts.manifest`)

`ReleaseManifest{schema: 1, release_id, created_at (second precision), audience, run_id,
inputs{sources: {source_id: sha256:…}}, versions: VersionInfo, counts, gates: [GateResult],
files: {path: {sha256, size}}}` (`manifest.json` never lists itself).
`release_id = <created_at as YYYYMMDDTHHMMSSZ>-<first 8 hex of sha256(canonical_json(identity))>`
with identity = `{schema, created_at, audience, run_id, inputs, versions}`
(`ReleaseManifest.compute_release_id(...)`); the model rejects a manifest whose id does not match.
`CurrentPointer{release_id, created_at (when the pointer was written), audience,
manifest_sha256 (sha256 of the manifest.json bytes)}`.

## 13. Search index (`docwiki.search`)

`build_search_db(pages, blocks, synonyms, path, *, release_id=None, audience=None, use_fts5=None)`
writes the frozen pipeline §6 schema plus two additive tables: `pages(page_id, type, path, title)`
and `page_refs(page_id, ref_kind, ref_id)` (`entity`/`topic` refs: source pages → their entities
and topics, entity/topic pages → themselves). `meta`: `schema=1, tokenizer, fts5 (1|0), rows,
release_id, audience`. Rows: one `page-section` per non-empty section (backlinks block and
footnotes removed, `section` = heading, `anchor` = heading anchor; text before the first heading
uses the page title) and one `source-block` per extracted block (`SearchBlock`, or
`blocks_from_extracted(doc, page_path=…, title=…, sensitivity=…)`, with `section` = locator label).
Synonyms are `(term, synonym, lang)` rows (`docwiki.domain.glossary_synonym_rows(pack)`).

`SearchIndex.open(path, force_fallback=False).search(query, kinds=None, types=None, entity=None,
topic=None, limit=10) -> list[SearchHit{kind, page_id, path, title, section, anchor, snippet,
source_id, locator_key, score}]`. Queries are tokenised like `unicode61 remove_diacritics 2`,
expanded with synonym groups (multi-word synonyms become phrases) and matched with OR semantics.
With FTS5, `MATCH` selects the candidates; without it (or `force_fallback=True`, or a database
built with `use_fts5=False`) candidates come from in-memory postings. Both paths rank with the same
BM25 (k1 1.2, b 0.75, IDF `log(1 + (N − df + 0.5)/(df + 0.5))`, weights title 3 / section 2 /
text 1), so results are identical. `entity`/`topic` filters keep the entity/topic page itself and
pages referencing it. Snippets are plain text windows of about 240 characters. Open read-only (`immutable`).

## 14. Validator and gates (`docwiki.release.validate_release`, `contracts.gates`)

`validate_release(path, *, canaries=(), require_manifest=True, audience=None,
orphan_threshold=0.05, glossary_seeded=None, locked_terms=None) -> list[Violation{gate, code,
severity, path, line, message}]` (paths relative to the validated folder: `wiki/…` in a release
folder, plain wiki paths and `.docwiki/…` in a portable folder (§19); lines 1-based in the file).
Checks:

| Gate | Checks |
|---|---|
| G01 | page/evidence/catalog/manifest/pointer/tables/search schemas; manifest hashes, missing or unlisted files; release stamps; UTF-8/LF; catalog = pages (via `catalog_page_for`), sources, both copies identical; derivable edges present; `search.db` schema and meta |
| G02 | relative links and anchors resolve in the content namespace; footnote refs ↔ definitions; entity/topic/source references in frontmatter have pages; glossary anchors |
| G03 | footnote labels `c1..cN` in first-use order; citation format, title, locator label and honest badge; every `Key facts` (source) and `Facts`/`Timeline` (entity) item cited |
| G05 | `find_violations` on every Markdown/text file (markers allowed only in pages) |
| G06 | every citation targets an existing sidecar |
| G07 | pages, evidence, catalog entries, search rows and tables at or below the audience; evidence/tables only for sources of the release; entity/topic/query tier = max of their sources |
| G08 | canary strings absent from wiki, evidence, catalog and site |
| G09 | `check_wiki_path` for wiki and evidence files; page id ↔ path; sidecar names ↔ locator keys |
| G10 | with `glossary_seeded=True`: glossary non-empty |
| G11 | supersession symmetric; superseded sources have status `superseded` and link the replacement before their first `##` section; topics with contradictions / superseded claims have those sections |
| G12 | tag errors in frontmatter |
| G13 | warning when more than `orphan_threshold` of pages (except `index.md`) have no inbound link outside backlinks blocks |
| G14 | skill projections byte-identical, core skills present, `SkillFile` limits, no extra files |
| G16 | with `locked_terms` (`{locked term: [banned renderings]}`): no page title or body line (except `_meta/quality.md`) contains a banned rendering as a whole word or phrase, case-insensitive, plural `s`/`es` allowed; blockquote lines and text between double quotes (straight, curly or guillemets) are not checked; code `banned-rendering`; mirror pages included |
| G17 | (v1.7) with more than one `wiki_languages` (manifest, else catalog): each canonical page of a mirrored type has `<lang>/<path>` with `translation_of` = its id (warning `mirror-missing`); a mirror starting with the untranslated marker warns (`mirror-untranslated`); a mirror without its canonical page is a G01 `mirror-orphan`; `lang` per tree is a G01 `page-lang` check |

G04 (quote verification) and G15 (quarantine rate) need pipeline data and stay with the `verify`
stage, which reports G16 as skipped without `locked_terms`. `gate_results(violations, skipped=…,
metrics=…)` folds violations into one `GateResult` per gate (errors fail blocking gates, warnings
warn).

## 15. Domain packs (`docwiki.domain`)

`load_pack(path, *, overlay=None) -> DomainPack`; errors are collected into
`PackValidationError.errors: [PackError(file, location, message)]`, e.g.
`taxonomy.yaml: doc_types[0].rules[0].filename_regex: invalid regex: …`. Required files:
`pack.yaml, taxonomy.yaml, entities.yaml, topics.yaml, glossary.yaml, sensitivity.yaml`; optional:
`supersession.yaml`, `resolution.yaml` (default `[authority, recency]`), `hints.md`,
`skills/<name>/SKILL.md.j2` (≤ 3, Jinja syntax-checked, names must not clash with core skills).
Unknown keys, unknown files/folders (`README.md`, `LICENSE*` and `.gitkeep` are ignored),
duplicate YAML keys, unknown references (categories, entity
types, doc types, `see_also` ids) and alias/synonym languages outside `pack.yaml languages` are
errors. `DomainPack.content_hash()` (overlay included) is the `domain_pack_hash` for cache keys.

Rules: `match_doc_type(pack, filename, text)` — first doc type in pack order whose rule matches
(`filename_regex` searched in the base name, `text_regex` in the first `first_chars`; all given
regexes must match) → `DocTypeMatch(doc_type, category, authority, rule_id="<doc_type>#<i>")`.
`sensitivity_for(pack, raw_path, doc_type)` — highest tier among matching rules, else the default;
globs: `**` spans folders, `*`/`?` stay in a segment, case-insensitive.
`sensitivity_floor(pack, raw_path)` — the lowest tier over `None` and every doc type of the pack
(a doc-type rule may set a tier below the default): a source is above an audience before
classification only when its floor is. Supersession:
`parse_doc_number(pack, *candidates)` / `parse_revision(pack, *candidates)` (named groups `number`
/ `rev`, else group 1, else the match; first matching candidate wins — pass the file name first,
then the text head), `revision_rank`, `compare_revisions`, `explicit_references(pack, text)`,
`order_revisions`, `supersession_pairs` → `(newer, older)`. Topics: `score_topic(topic, title,
sections)` counts every word-bounded, case- and accent-insensitive occurrence of keywords and
aliases × weight (title 3, heading 2, body 1); `route_topics(pack, title, sections)` keeps scores
≥ the topic's `min_score` (default 3.0).

Overlay (`work/state/overlay.yaml`, `Overlay{schema: 1, entities, glossary, topics}`):
`add_proposal(overlay, accepted_proposal)` (a payload that cannot become an entry raises
`PackValidationError`), `apply_overlay(pack, overlay)` — scalars from the
overlay win, aliases/keywords/synonyms/see_also are unioned, new items appended; entity types must
exist; errors name `overlay.yaml`. `filter_overlay(pack, overlay) -> (kept, problems)` tries the
entries one at a time and leaves out those that do not apply (the pipeline reports them as run
warnings and never fails on them). `dump_overlay(overlay)` gives stable YAML.

## 16. Markdown safety (`contracts.safety`)

- `sanitize_markdown(md, *, allow_markers=True, allowed_hosts=()) -> (clean, findings)`: removes
  HTML tags (keeps their text) and dangerous elements with content (`script, style, iframe, svg…`),
  comments (markers kept only when alone on a line), `javascript:/data:/vbscript:/file:` links and
  images (also when entity-, percent- or whitespace-obfuscated), external and absolute links (keeps
  the text) and images (keeps the alt text), external reference definitions; bare URLs, e-mail
  addresses and external autolinks become inline code; escapes leftover `<`. Code spans and fences
  are untouched. Guarantee (tested): `find_violations(sanitize_markdown(x)[0]) == []`, idempotent.
- `find_violations(md, …)` reports `raw-html, html-comment, marker, unsafe-url, external-link,
  external-image, absolute-link, bare-url, control-char` as a renderer would see them.
- `detect_injection(text)` flags text addressed to AI systems (EN/FR/DE heuristics: ignore-previous
  instructions, addressing an AI, prompt references, chat/tool-call syntax, exfiltration, secrecy,
  command execution), robust to case, accents, full-width and zero-width characters; it may flag
  rare legitimate sentences, so its findings feed injection proposals (human review).
  `neutralize_injections(md)` drops only the flagged sentences.

## 17. Decisions beyond the spec

1. **Release id hash** = first 8 hex of the manifest *identity* hash (schema, created_at, audience,
   run_id, inputs, versions). Hashing the full manifest is circular because pages embed the
   release id and the manifest lists page hashes; the pointer still pins the full manifest.
2. **Content namespace** for links (§4): the spec's `../evidence/…` footnote target is literally
   correct for pages one folder deep when `evidence/` is mounted at the wiki root, as in Quartz.
   Entity pages use `../../evidence/…`. Raw GitHub browsing of a release folder therefore does
   not resolve evidence links; the site and the MCP server do.
3. **Ids of non-content pages**: `index:<scope>`, `glossary`, `log`, `meta:agents|quality|runs/<run_id>`;
   `AGENTS.md` carries frontmatter (`meta:agents`) like every page.
4. **Badge `paraphrase`** for unverified paraphrases of native text (the spec's four badges have
   none for this case); `failed` citations never reach a page.
5. **Locator details**: discriminator `kind`; normalised top-left bboxes; singular labels for one
   row/line; optional `sheet_slug` assigned per workbook to keep keys collision-free; e-mail part
   keys `msg-headers`, `msg-body[-lNNNN-lNNNN]`, `msg-att-<slug>`; VTT keys use the cue start only
   (one sidecar per start second); image locators are always page 1.
6. **Path rule exemptions** for the fixed agent-kit paths (§2); suspicious repr segments rejected.
7. **Slugs**: NFC before hashing ids; small transliteration table; collisions suffix every
   colliding source (order-independent) unless a previous assignment exists.
8. **Frontmatter canon**: id lists sorted/unique; optional keys written as `null`; one-line
   summary; `lang` the canonical wiki language (v1.7; `en` by default); source `topics` list only
   topic pages of the release.
9. **Evidence frontmatter** adds `title`; evidence indexes use `type: evidence-index`.
10. **Tables layout** in releases (§10) incl. snake_case column names and type inference.
11. **search.db** additive `pages`/`page_refs` tables and BM25 ranking outside FTS5 (FTS5's own
    `bm25()` clamps the IDF of terms found in more than half of the rows to ~0, which breaks
    ranking on focused wikis).
12. **Proposals**: typed payload per kind, deterministic ids, extra `decided_at`.
13. **Queue**: `hints` is `{str: str}` (`operator_notes`); Event Grid/CloudEvents/base64 accepted.
14. **State shard** tombstone fields `deleted`/`deleted_at`.
15. **Pointer `created_at`** = time the pointer was written (rollbacks get a new time).
16. **run_id** is lower-case `run-YYYYMMDD-HHMMSS-<8 hex>` so it can appear in wiki paths.
17. **Validator gate mapping** (§14), file-relative line numbers, orphans ignore backlinks blocks.
18. **Domain packs**: required/optional files, unknown files rejected, alias languages must be
    declared, reserved entity types, regex/glob/scoring semantics of §15, overlay merge rules.
19. **Portable wiki folder** (§19) for local use and export: the content
    namespace as the folder root with machine files in `.docwiki/`; `site/` is not exported.
20. **Run report `warnings`** (§8) for problems that do not fail a run; `RunContext.notices`
    adds the problems noticed by the queue worker (a refused visibility renewal).
21. **Overlay validation** (§15): entries that do not apply are left out one by one and reported,
    never failing the run; every run records the base pack in `work/state/domain-pack.json` and
    `decide_proposal` refuses (`invalid_argument`) an acceptance that pack could not apply.
22. **Transient quarantines** (§8): `StageState.retryable`/`attempts`, retried by the next runs up
    to `RETRY_ATTEMPTS`; Content Understanding throttling, outages and authorization failures are
    systemic (the run fails and is retried) instead of quarantining sources.
23. **Raw files and retention**: remote raw files are downloaded on demand into a scratch folder
    keyed and verified by content hash (cleared at the start of each run); retention after the
    pointer swap is best effort, after the build state is recorded (§11).

## 18. Spec clarifications to propose (v2)

- State the content-namespace rule for evidence links (decision 2) in wiki-contract §5.
- Define the release-id hash input (decision 1) in architecture §3.
- Add the `paraphrase` badge (decision 4) to wiki-contract §5 and site.md §2.
- Add the tables layout (decision 10) to architecture §3 and the `query_table` description.
- Describe the portable wiki folder (§19) as a plain-folder layout in site.md and
  mcp-and-agents.md §3.
- Add `work/state/domain-pack.json`, the state shard retry fields and the run report `warnings`
  (decisions 20–22) to architecture §3–§5 and §7, and the transient-quarantine rule to pipeline
  §1 (stage 2) and §5.
- Architecture §6: the jobs identity needs *Storage Queue Data Contributor* on `ingest` (Update
  Message, used to renew visibility, requires `queues/messages/write`, which also authorizes Put
  Message) and *Storage Queue Data Message Sender* on `ingest-poison`.

## 19. Portable wiki folder (`docwiki.release.export_portable`, `ReleaseLayout`)

A portable wiki folder is the content namespace (§4) written as a plain folder, so every relative
link (`../evidence/<source_id>/<locator_key>.md`, `../../sources/x.md`…) resolves as a file path on
GitHub, in Obsidian or VS Code and for agents that only read files. Published releases keep
the release layout (§10).

```
<folder>/
  index.md  AGENTS.md  llms.txt  log.md  glossary.md  catalog.json    # wiki root = folder root
  sources/  entities/  topics/  queries/  _meta/
  .agents/skills/  .claude/skills/  .github/skills/
  evidence/<source_id>/{index.md, <locator_key>.md, img/…, original.<ext>}
  .docwiki/
    manifest.json     # copied unchanged (its paths stay release-relative)
    current.json      # pointer copy
    search.db
    tables/<source_id>/{index.json, <table_id>.parquet}
```

- `export_portable(release_root, out_dir, *, force=False) -> Path` accepts anything
  `ReleaseReader.open` accepts (release folder, `releases/` folder or fixture root, portable
  folder). Every file is checked against the manifest before it is written
  (`ReleaseIntegrityError`); the output is deterministic and re-exporting is idempotent. Owned
  entries of `out_dir` are replaced: every non-dot entry, `.docwiki/` and the `skills/` folders of
  `.agents`, `.claude` and `.github` (`portable_owned_entries(folder)`); other dot entries
  (`.git`, `.obsidian`, `.github/workflows`…) are kept. A non-empty folder that is not already a
  portable folder is only cleaned with `force=True`; `out_dir` must not overlap the source release.
  `site/` (Quartz output) is not exported.
- Pointer copy: the pointer that selected the release, or the release folder's sibling
  `current.json`, when it names this release; otherwise a pointer derived from the manifest
  (`created_at` = the manifest `created_at`). A pointer naming the release with another manifest
  hash raises `ReleaseIntegrityError`.
- Path mapping, `ReleaseLayout("portable", root).file_for(manifest_path)`: `wiki/<p>` → `<p>`;
  `catalog.json` and `wiki/catalog.json` → `catalog.json`; `evidence/<p>` → `evidence/<p>`;
  `search.db`, `tables/<p>` and any other release-root file → `.docwiki/…`; `site/…` → absent.
  `ReleaseLayout.detect(path)` returns the `release` or `portable` layout rooted at `path` (pointers
  are not followed); `is_portable(path)` tests for `.docwiki/manifest.json`. Layout properties:
  `wiki_root`, `evidence_root`, `meta_root`, `manifest_path`, `search_db_path`, `tables_root`,
  `catalog_path`, `pointer_path`, `content_file(ns_path)`, `display(manifest_path)`.
- `ReleaseReader.open(folder)` detects the layout; `verify=True` (or `verify_files()`) checks every
  manifest hash through the mapping. `validate_release(folder)` validates a portable folder like a
  release folder: manifest hashes through the mapping, owned files missing from the manifest,
  the pointer copy (`pointer-release-mismatch`, `pointer-hash-mismatch`,
  `pointer-audience-mismatch` at `.docwiki/current.json`) and links resolved as plain paths.
- `read_tables_index`, `connect_tables` and `query_tables(root, …)` accept both layouts; the
  `*_at(tables_root, …)` variants take the tables folder itself.
- Code that joins `wiki/`, `tables/` or `search.db` to a release root by hand must switch to
  `ReleaseLayout.detect(path)` or the reader properties to serve portable folders (for example the
  MCP folder source and the site's content assembly).
