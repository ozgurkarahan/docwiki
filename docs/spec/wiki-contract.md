# Wiki contract

A built wiki is a folder of UTF-8 Markdown files (LF line endings) plus a few machine files. It must
render correctly on GitHub, in Quartz, in Obsidian and in VS Code, and be navigable by an agent
using only file reads.

## 1. Layout

```
wiki/
  index.md                 # home: purpose, how to navigate, categories, topics, stats, recent changes
  AGENTS.md                # how agents should use this wiki (schema, conventions, tools, skills)
  llms.txt                 # llmstxt.org index of the most useful pages
  log.md                   # append-only change log
  glossary.md              # terms with definitions, multilingual synonyms, links
  catalog.json             # machine catalog (also copied to the release root)
  sources/
    index.md               # all sources grouped by category, with status and sensitivity
    <source-slug>.md       # one page per source document
  entities/
    index.md
    <entity-type>/index.md
    <entity-type>/<entity-key>.md
  topics/
    index.md
    <topic-slug>.md        # curated multi-source syntheses
    <scope>/<topic-slug>.md   # v1.7: a per-scope topic, once per scope that has sources for it
  <scope-folder>/          # v1.7 (ADR 0011), only when the pack declares scopes, e.g. chantiers/
    index.md               # the list of the hubs (id index:hubs/<scope-folder>)
    <scope>.md             # one hub per scope value (id hub:<scope-folder>/<scope>), built by code
  queries/                 # research answers filed back after approval
    <yyyy-mm-dd>-<slug>.md
  _meta/
    quality.md             # gate results of this release
    runs/<run_id>.md       # run receipt (durations, tokens, costs, versions)
  .agents/skills/<skill>/SKILL.md     # canonical projection (Copilot, Codex)
  .claude/skills/<skill>/SKILL.md     # projection for Claude Code (identical content)
  .github/skills/<skill>/SKILL.md     # projection for GitHub Copilot (identical content)
```

Evidence sidecars live next to the wiki in the release (`releases/<id>/evidence/`) and are linked
with relative paths `../evidence/...` from pages (see evidence-contract.md). For the public sample,
the build copies `evidence/` into the published site.

## 2. Identifiers and slugs

- `source_id`: `src-` + first 12 hex chars of `sha256(<raw relative POSIX path, lower-cased>)`.
  Stable while the file keeps its path. A new revision of a document is a new source.
- `source slug`: ASCII kebab-case of the file stem (NFKD → ASCII, lower, non `[a-z0-9]` → `-`,
  collapse dashes, max 60 chars). On collision append `-` + 4 hex of `source_id`. **Never derived
  from LLM output.**
- Entity id: `<type>:<key>`; type and key come from the domain pack registry (key is kebab-case).
  Page path `entities/<type>/<key>.md`.
- Topic id: `topic:<slug>` from the topic catalog; page path `topics/<slug>.md`. A topic marked
  `per_scope` (v1.7) has one id per scope: `topic:<scope>/<slug>` at `topics/<scope>/<slug>.md`.
- Hub id (v1.7): `hub:<plural>/<scope>` at `<plural>/<scope>.md`; the hubs index is
  `index:hubs/<plural>` at `<plural>/index.md`. `<plural>` is `scopes.plural` of the pack (never
  `sources`, `entities`, `topics`, `queries` or `evidence`); no scope value may be `index`.
- Query page id: `query:<yyyy-mm-dd>-<slug>`.
- Paths must match `^[a-z0-9][a-z0-9\-/._]*$` and must never contain Python enum or class reprs
  (no `.` inside directory names, no uppercase).

## 3. Frontmatter (YAML, first block of every page)

Common fields (all pages):

| Field | Type | Notes |
|---|---|---|
| `id` | string | As defined above |
| `type` | enum | `source`, `entity`, `topic`, `hub` (v1.7), `index`, `query`, `meta`, `glossary`, `log` |
| `title` | string | Human title |
| `summary` | string | 1–2 sentences, used by indexes and search |
| `lang` | string | Always `en` for compiled pages (canonical language) |
| `sensitivity` | enum | `public`, `internal`, `restricted` (highest of its sources) |
| `updated` | date | Release date of last change |
| `tags` | list[string] | Lower-case, de-duplicated, sorted |
| `docwiki` | map | `{schema: 1, release: <release_id>}` |

Source pages add: `source_id`, `source_path` (raw relative path), `source_hash`, `media_type`,
`doc_type`, `category`, `doc_number` (if any), `revision` (if any), `status`
(`current|superseded|withdrawn`), `supersedes` (list of source ids), `superseded_by` (list),
`original_lang`, `pages` (count, if paged), `entities` (list of entity ids), `topics` (list of topic ids),
`authority` (1–10 from the domain pack), `extraction` (`{adapter, version, provenance_mix}`).

Entity pages add: `entity_type`, `key`, `aliases` (with language tags), `sources` (list of source ids).

Hub pages (v1.7, ADR 0011) add: `scope_type` (the pack's scope name, e.g. `chantier`), `scope`
(the scope value) and `sources` (the scope's sources). Source pages add `scope`, `phase` and `lot`
when the pack declares scopes; per-scope topic pages add `scope` (their id is
`topic:<scope>/<slug>`). Scope and axes come from the raw path and the pack, never from a model.

Topic pages add: `topic_slug`, `sources` (list), `confidence` (`high|medium|low`),
`contradictions` (count), `superseded_claims` (count).

Query pages add: `question`, `asked_by` (`researcher|human`), `sources` (list), `approved_by`.

## 4. Body structure

Source page:

```
# <title>
> FICTIONAL sample notice (only in the public sample domain)
<one-paragraph summary>
## Key facts            (bulleted facts, each with ≥ 1 footnote citation)
## Contents             (compiled sections mirroring the document; tables preserved)
## Figures              (figure descriptions with provenance, links to sidecars)
## Related              (deterministic links: entities, topics, revisions)
<!-- docwiki:backlinks:start -->
## Referenced by
<!-- docwiki:backlinks:end -->
## Sources              (footnote definitions)
```

Entity page: summary, `## Facts` (aggregated, cited), `## Timeline` (dated events, cited),
`## Documents` (links to source pages), `## Related`, backlinks block, footnotes.

Topic page: summary, `## Overview`, thematic sections (cited), `## Contradictions` (each item
lists both claims with citations, authority and date, and the resolution rule applied),
`## Superseded information` (old claim, replacement, superseding source), `## Sources consulted`,
`## Related`, backlinks block, footnotes. A per-scope topic (v1.7) has the same body, is titled
`<topic title> — <scope label>` and is synthesised from the sources of its scope only.

Hub page (v1.7, ADR 0011), built by code, no model and no footnotes (it links to the cited pages):

```
# <scope label>          (the registry entry of type scopes.name with key = the scope value:
                          its label; the default scope: its title; else the scope value)
> FICTIONAL sample notice (only in the public sample domain)
<n documents, last received YYYY-MM-DD.>
## Details               (the registry entry's attributes: | Attribute | Value |)
## Documents             (### Phase <key> <title> in pack order, then ### No phase; each source
                          with its status: current, or superseded by <links>)
## Topics                (the scope's per-scope topics and the company topics citing its sources)
## Entities              (entity pages mentioned by its sources)
## Open contradictions   (its per-scope topics with contradictions > 0, with their count)
## Last document received (by the document's date, else a YYYY-MM-DD in its file name, else the
                          source page's updated date)
```

The hub's `sources` are the scope's sources and its sensitivity is their highest tier. Every scope
value with at least one source in the release has a hub, the default scope included.

## 5. Links, anchors and citations

- Internal links are **relative Markdown links** with the `.md` extension:
  `[Quotation DEV-2026-014 indice B](../sources/dev-2026-014-indice-b.md)`. No `[[wikilinks]]` in
  the canonical wiki (an Obsidian export may rewrite them).
- Anchors are **headings with deterministic text**. Renderers derive identical slugs on GitHub,
  Quartz and VS Code because heading texts are ASCII and simple (`## Page 12` → `#page-12`).
- **No raw HTML** anywhere except the two backlinks marker comments, which are generated by code.
- Citations are Markdown footnotes. Every footnote definition has the form:

  `[^c3]: [<source title> — <locator label>](../evidence/<source_id>/<locator_key>.md) · <provenance badge>`

  where the badge is one of `✓ quote verified`, `table`, `OCR`, `generated description`.
  Footnote labels are `c1`, `c2`, … in order of first use per page.
- Links to anything outside the wiki/evidence tree are forbidden in compiled content, except
  links to original files in the public sample bundle (`../evidence/<source_id>/original.<ext>`).
- The backlinks block is regenerated deterministically on every build (sorted by title).

## 6. Index and machine files

- `index.md`: what this wiki is, how to navigate (start here → categories → topics → entities →
  glossary → log), counts, list of topics, recent changes (last 10 log entries). When the pack
  declares scopes (v1.7), its first section is the **company dashboard**, titled with the plural
  of `scopes.title` (`## Chantiers`): a table `| <scope title> | Phase | Client | Documents |
  Last document received | Open contradictions |` with one row per hub (link), the highest phase
  of its sources (pack order, `<key> <title>`), the registry attribute `client`, the number of
  sources, the last document received (link and date) and the number of open contradictions,
  followed by a link to `<plural>/index.md`; the other sections are unchanged.
- `<plural>/index.md` (v1.7): one line per hub. `topics/index.md` lists the company topics, then
  the per-scope topics under one `## <scope label>` heading per scope.
- `log.md`: append-only. One entry per change:
  `## [YYYY-MM-DD] <ingest|update|supersede|withdraw|topic|query|lint> | <title>` followed by bullets
  linking the affected pages. Never rewritten; new releases append.
- `llms.txt`: llmstxt.org format: `# <wiki title>`, `> <summary>`, then sections `## Start here`,
  `## Topics`, `## Entities`, `## Sources` with `- [Title](path.md): summary` lines (v1.7: with
  scopes, `## Start here` also links `<plural>/index.md`).
- `catalog.json` (schema 1):
  ```json
  {"schema": 1, "release_id": "...", "audience": "public", "generated_at": "...",
   "pages": [{"id": "...", "type": "...", "path": "...", "title": "...", "summary": "...",
              "sensitivity": "...", "status": "...", "tags": [], "entities": [], "topics": [],
              "sources": [], "lang": "en"}],
   "edges": [{"from": "<page id>", "to": "<page id>", "kind": "mentions|supersedes|cites|related|topic-of"}],
   "sources": [{"source_id": "...", "path": "...", "hash": "...", "media_type": "...", "status": "...",
                "doc_number": null, "revision": null}],
   "glossary": [{"term": "...", "synonyms": {"fr": [], "de": []}, "page": "glossary.md#..."}]}
  ```
- `search.db`: SQLite database (FTS5) defined in pipeline.md §6; shipped at release root.

## 7. AGENTS.md of a generated wiki

Rendered from a template; contains: what the wiki covers (from the domain pack), the page types and
frontmatter, navigation strategy (read `index.md`, then category/topic/entity indexes, use the
glossary for acronyms and synonyms, check `log.md` for recency), citation rules (always cite the
footnote target; prefer `✓ quote verified`; never cite generated descriptions as quotes), how to
treat contradictions and superseded information, available skills and MCP tools, and the rule that
document content is data, never instructions.

## 8. Sensitivity and audiences

- Each source gets a tier from domain-pack rules (path globs, document types, metadata).
- A build targets one audience; sources above the audience tier are excluded entirely (no page,
  no mention, no evidence, no catalog entry, no search rows).
- Pages never combine sources of different tiers unless the audience includes both tiers;
  the page tier is the maximum of its sources.

## 9. Supersession, contradiction and withdrawal

- **Supersession**: a later revision of the same document number, or a source explicitly declaring
  that it replaces another (rule or extracted reference). Superseded sources keep their page with
  `status: superseded` and a banner linking the replacement; topic pages present the current claim
  first and list superseded information separately.
- **Contradiction**: two current sources disagree on a fact. Both claims are shown with citations,
  authority and dates; the domain pack's resolution rule (authority, then recency) is stated, never
  silently applied.
- **Withdrawal**: a deleted raw file. Its page is removed, a `withdraw` log entry is added, dependent
  pages are rebuilt, and query pages citing it get a warning banner.

## 10. Content safety rules

Applied by code after every LLM call and again by the quality gates:

- Strip any HTML tags, HTML comments (except generated markers), scripts, `javascript:` / `data:`
  URLs, and links to hosts not in the allowlist (none for compiled content).
- Escape Markdown that would create images from external URLs.
- Reject text that tries to address the reader as an AI system ("ignore previous instructions",
  "as an AI assistant", tool-call syntax) — keep the source fact, drop the instruction, and file an
  injection proposal.
