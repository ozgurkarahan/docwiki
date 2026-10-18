# Domain packs, fictional world and sample corpus

## 1. Domain pack format

A domain pack is a folder under `domains/<pack>/`:

| File | Content |
|---|---|
| `pack.yaml` | `name`, `title`, `description`, `default_audience`, `languages` (e.g. `[en, fr, de]`), `wiki_title`, `fictional: true|false`, `banner` (optional notice shown on pages) |
| `taxonomy.yaml` | `categories: [{key, title, description}]`; `doc_types: [{key, title, category, authority (1-10), rules: [{filename_regex?, text_regex?, first_chars?: 2000}]}]` |
| `entities.yaml` | `types: [{key, title, description}]`; `registry: [{type, key, label, aliases: [{text, lang}], attributes: {}}]` |
| `topics.yaml` | `topics: [{slug, title, description, keywords: [...], aliases: [{text, lang}], min_score?, min_sources?}]` |
| `glossary.yaml` | `terms: [{term, definition, synonyms: {fr: [], de: []}, see_also: [entity or topic ids]}]` |
| `sensitivity.yaml` | `default: public|internal`; `rules: [{tier, path_glob?, doc_type?}]` |
| `supersession.yaml` | `doc_number_regex`, `revision_regex`, `revision_order` (e.g. `[A, B, C]` or numeric), `explicit_reference_regex` |
| `resolution.yaml` | contradiction resolution policy: `order: [authority, recency]`, notes shown on topic pages |
| `hints.md` | optional reviewed domain notes appended to compile prompts (no document text) |
| `skills/<skill>/SKILL.md.j2` | at most 3 domain skill templates (see §4) |

Packs are validated by a schema; unknown keys are errors. Accepted proposals live in a runtime
overlay (`work/state/overlay.yaml`), never by editing the pack at runtime.

## 2. Fiction rules (sample content)

1. **Closed world**: `samples/fiction/bible.yaml` lists every organisation, person, site, asset,
   product, document number scheme and date used in the samples. `samples/fiction/allowlist.txt`
   is generated from it and used by the leak guard.
2. Prefer Microsoft's documented fictitious brand names (Contoso, Fabrikam, Litware, Proseware,
   Trey Research, Tailspin, Wingtip, Alpine Ski House, City Power & Light, Relecloud, …) for
   organisations. Every new name must be checked (web search) not to match a real wind farm,
   turbine manufacturer, lubricant or component brand, or a real person in the energy sector.
3. No real manufacturer, product, standard-body document content, or copyrighted text. Generic
   industry terms (gearbox, pitch system, SCADA, lockout/tagout, ISO viscosity grade) are fine.
4. Every procedure-like document carries "FICTIONAL — NOT FOR OPERATIONAL USE" in its header and
   footer; values are plausible but invented.
5. Neutral file metadata: author "DocWiki sample generator", organisation from the bible,
   fixed creation dates from the timeline; no EXIF in images.
6. Generators are deterministic (fixed seeds); regenerating produces byte-identical files where the
   format allows it (otherwise identical text and hashes are recorded in the manifest).
7. Content license CC BY 4.0.

## 3. The `wind-om` sample domain

Fictional operator **Contoso Renewables** runs the operations and maintenance of a fictional onshore
wind farm (about a dozen turbines of a fictional OEM model). The corpus covers operations,
maintenance, safety, compliance, supply chain and training.

### 3.1 Corpus composition (target ~38 documents; ★ = 12-document quickstart subset)

| Kind | Formats | Examples (illustrative) |
|---|---|---|
| OEM documentation | PDF (with vector diagrams) | ★ gearbox maintenance manual excerpt (multi-page, tables, exploded diagram); ★ service bulletin changing the gearbox oil viscosity grade for cold sites; service bulletin on pitch bearing bolt re-torque |
| Procedures | DOCX | ★ gearbox oil change SOP **rev B** (current) and rev A (superseded); lockout/tagout SOP; working-at-height and rescue SOP; ★ French work instruction for generator brush replacement |
| Incidents | DOCX, PDF | ★ incident report (8D / 5 Whys) on repeated gearbox over-temperature of one turbine; dropped-object near-miss report |
| Change management | DOCX | ★ management-of-change record adopting the new oil grade |
| Records and data | XLSX, CSV | ★ multi-sheet maintenance plan; ★ spare parts and stock (with minimum levels); ★ SCADA alarm log (≈ 1–3k rows); work-order export; vibration trend for one gearbox; KPI export |
| Lab and inspection | PDF | ★ oil-analysis lab report; blade inspection report with drawn defect figures; ★ **image-only scanned PDF** (crane lift plan) |
| Compliance | PDF | environmental permit with night-time curtailment conditions; grid operator curtailment instruction; internal safety audit report |
| Training | PPTX | ★ onboarding and site-rules deck; gearbox fundamentals deck; single-point lesson on oil-level checks |
| Correspondence | EML | ★ OEM support e-mail about bulletin applicability (contains the **injection canary**); internal e-mail about a parts shortage |
| Field capture | JPG/PNG, TXT/MD | ★ photographed handwritten daily checklist with one hand-written value; site layout plan; shift handover notes in English, one French note, one German supplier note |
| Meetings | VTT, DOCX | toolbox-talk transcript about cold-weather start-up; monthly O&M review minutes |
| Restricted | XLSX or PDF | contractor rate card (sensitivity `restricted`) — must never appear in the public build |
| Held back | PDF | a later service bulletin (not in the initial corpus) used for the "knowledge time travel" demo |

### 3.2 Planted scenarios (each must be answerable only by combining documents)

1. **Oil grade change**: manual says grade X; later bulletin changes it to grade Y for cold sites;
   MOC adopts it; SOP rev B reflects it, rev A does not → supersession + contradiction handling.
2. **Recurring alarm**: one turbine raises a gearbox over-temperature alarm repeatedly in the SCADA
   log; the vibration trend rises; the incident report gives the root cause and the corrective action.
3. **Night curtailment**: stops at night in summer are explained by the environmental permit
   conditions, visible in the SCADA log as curtailment status codes.
4. **Parts shortage**: an e-mail and the stock sheet show a part below minimum that blocks open work
   orders (table join across XLSX and CSV).
5. **Multilingual**: the French work instruction and the German supplier note contain facts asked
   in English, and one question is asked in French.
6. **Scanned evidence**: a value written by hand on the checklist photo (OCR provenance).
7. **Acronyms**: several acronyms used across documents; some defined only in the training deck.
8. **Restricted exclusion**: the rate card exists in the corpus but must not leak into the public wiki.
9. **Injection canary**: the OEM e-mail contains an instruction addressed to AI assistants with a
   unique canary token (defined in the bible); it must be neutralised and flagged.
10. **Time travel**: adding the held-back bulletin creates a new supersession and changes one
    answer.

### 3.3 Files

```
samples/fiction/bible.yaml           # world definition (closed world)
samples/fiction/allowlist.txt        # generated proper-noun allowlist
samples/generators/                  # deterministic generators (python), one module per format
samples/corpus/full/...              # generated corpus (sub-folders by kind)
samples/corpus/quickstart/...        # the 12 quickstart documents (copies or a manifest list)
samples/corpus/held-back/...         # time-travel bulletin
samples/corpus/MANIFEST.json         # path, sha256, format, pages/rows, quickstart flag, sensitivity
domains/wind-om/                     # domain pack for the sample
domains/it-runbooks/                 # tiny second pack (≈5 fictional IT runbooks) proving genericity
```

## 4. Skill templates

Core skills (shipped with every wiki, templates under `skills/templates/`):

| Skill | Purpose |
|---|---|
| `wiki-navigator` | How to find information: index → topics/entities/sources → glossary → log; MCP tools or plain file reads |
| `cite-sources` | Citation rules, provenance badges, evidence sidecars, quoting in original language |
| `deep-research` | Multi-step research protocol with bounded steps, contradiction and supersession handling, report format |
| `wiki-maintainer` | Conventions for adding sources, reading quality reports, proposals and log entries |

Domain skills (≤ 3 per pack, e.g. for `wind-om`: `troubleshoot-alarm`, `prepare-maintenance-task`,
`audit-readiness`). Each has an evaluation task in the golden set.

Template rules: Jinja2 with `StrictUndefined`; allowed variables come only from validated catalog
values (counts, page paths, entity types, topic titles from the pack) and the domain pack; values
are escaped; no free text from documents. SKILL.md frontmatter: `name` (kebab-case, ≤ 64 chars),
`description` (≤ 1024 chars); body ≤ 5,000 words.

## 5. Golden set

`evals/golden/dev.jsonl` (public) and a private holdout (not in the repository). Line format:

```json
{"id": "q001", "split": "dev", "category": "single-hop|multi-hop|numeric|table|contradiction|supersession|multilingual|ocr|abstain|injection|restricted|skill",
 "question": "...", "lang": "en|fr", "expected_answer": "...", "must_include": ["...", "12 Nm"],
 "required_citations": [{"source_path": "full/...", "locator_key": "p0003"}],
 "forbidden": ["..."], "abstain": false, "notes": "..."}
```

Sequencing: bible → generators → corpus frozen (MANIFEST hashes committed) → golden set written
against the frozen corpus and sealed (sha256 of the file recorded in `evals/golden/SEAL`) → only then
the first full wiki generation. The holdout (~30 % of questions) is authored by a separate agent that
sees only the corpus, never the generators' planted-facts notes; only aggregate holdout scores are
published.
