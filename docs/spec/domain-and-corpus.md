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
2. Prefer Microsoft's documented fictitious brand names for organisations. Every new name must be
   checked (web search) not to match a real construction company, builders' merchant, window or
   joinery maker, electrical contractor, building-product brand, French commune or real person.
3. No real manufacturer, product, standard-body document content, or copyrighted text. Generic
   industry terms (devis, avenant, retenue de garantie, gros œuvre, menuiseries, …) are fine.
4. Every procedure-like document carries "FICTIONAL — NOT FOR OPERATIONAL USE" in its header and
   footer; values are plausible but invented.
5. Neutral file metadata: author "DocWiki sample generator", organisation from the bible,
   fixed creation dates from the timeline; no EXIF in images.
6. Generators are deterministic (fixed seeds); regenerating produces byte-identical files where the
   format allows it (otherwise identical text and hashes are recorded in the manifest).
7. Content license CC BY 4.0.

## 3. The `batiment` sample domain

A small fictional French general contractor builds a 30 m² house extension and renovates the
kitchen of one private household in an invented town: one client, one chantier. The third parties
are a builders' merchant, a window maker and an electrical subcontractor. The timeline runs from
January to April 2026; the works are still in progress. This specification names roles only: the
names of the company, its staff, the household, the town and the third parties live in
`samples/fiction/bible.yaml`. The documents are written in French and the wiki is compiled in
English (D10 in the [decision log](README.md#4-decision-log-v1)); questions are asked in English and
in French.

### 3.1 Corpus composition (12 public documents, 1 restricted, 1 held back)

| # | Document (in French) | Format | Demonstrates |
|---|---|---|---|
| 1 | Devis (quotation) indice A | PDF | Superseded revision |
| 2 | Devis indice B, with a revised scope and price | PDF | Supersession |
| 3 | Contrat de travaux (signed works contract) | DOCX | Price, payment schedule, retention, start date, duration |
| 4 | Avenant n°1 (contract amendment) | DOCX | Multi-hop total (contract plus amendment); amends, never supersedes |
| 5 | Planning et suivi des achats (schedule and purchase tracking, two sheets), indice A | XLSX | Tables, progress, `query_table` |
| 6 | Facture fournisseur matériaux (builders' merchant invoice) | PDF | Numbers; discrepancy with #7 |
| 7 | Bon de livraison (delivery note), scanned, with a handwritten remark about missing pallets | Image-only PDF, one page | OCR |
| 8 | Compte rendu de chantier n°3 (site meeting minutes) | DOCX | Progress, decisions |
| 9 | E-mail from the client (change request) | EML | Multilingual questions |
| 10 | E-mail from the window maker (delivery delay; the injection canary in a paragraph of its own) | EML | Contradiction with the planning; injection containment |
| 11–12 | Two site photos (slab poured; delivered pallets) | JPG | Generated-description provenance |
| 13 | Étude de prix interne (internal cost study with margins), under `full/restricted/` | XLSX | Sensitivity `restricted`: never in the public build |
| Held back | Planning indice B (new window delivery date), under `held-back/` | XLSX | Time travel (§3.2) |

The sample uses PDF (text and image-only), DOCX, XLSX, EML and JPG; the other supported formats
(CSV, PPTX, VTT, PNG, Markdown and text) are covered by the generated fixtures of the extraction
tests.

### 3.2 Planted scenarios

Several scenarios can only be answered by combining documents. The exact facts, their sources and
the acceptance matrix are recorded in `samples/fiction/PLANTED.md`.

1. **Supersession**: devis indice B replaces indice A with a revised scope and price; indice A keeps
   its page, marked `superseded`.
2. **Contradiction**: the planning and the window maker's e-mail give different delivery dates for
   the windows; both claims are shown with the resolution rule.
3. **Delivery discrepancy**: the merchant's invoice bills 10 pallets, while only 8 were delivered
   according to the scanned delivery note.
4. **Amounts**: amounts before and after VAT (HT/TTC), the deposit, the 5 % retention (retenue de
   garantie), the amendment and the purchases to date are exact numbers in text and tables.
5. **Multi-hop total**: the total contract amount is the contract price plus the avenant.
6. **Scanned evidence**: the handwritten remark on the delivery note is only readable through OCR
   (OCR provenance).
7. **Multilingual**: every document is in French; questions are asked in English and in French, and
   the glossary carries the French synonyms of English terms.
8. **Restricted exclusion**: the internal cost study exists in the corpus but must not leak into the
   public wiki or into public answers.
9. **Injection canary**: the window maker's e-mail contains an instruction addressed to AI
   assistants with a unique canary token (defined in the bible); it must be neutralised and flagged.
10. **Abstain**: no architect takes part in the project; a question about one must be answered as
    not found.
11. **Time travel**: adding the held-back planning indice B creates a new supersession (planning
    indice A → B) whose new delivery date resolves the contradiction of scenario 2.

### 3.3 Files

```
samples/fiction/bible.yaml           # world definition (closed world)
samples/fiction/allowlist.txt        # generated proper-noun allowlist
samples/fiction/PLANTED.md           # planted facts, their sources and the acceptance matrix
samples/generators/                  # deterministic generators (python), one module per format
samples/corpus/full/...              # the 12 public documents (sub-folders by kind)
samples/corpus/full/restricted/...   # the restricted document
samples/corpus/held-back/...         # the held-back planning revision (time travel)
samples/corpus/MANIFEST.json         # path, sha256, format, pages/rows, sensitivity, held-back flag
domains/batiment/                    # domain pack for the sample
```

Pack genericity is covered by the small test packs under `tests/` since the second sample pack was
removed in v1.2 ([changelog](CHANGELOG.md#v12)).

### 3.4 Document contract

Properties of the sample documents that supersession, verification, containment and the
evaluation rely on; tests under `tests/samples/` enforce them.

1. **File names** are ASCII and every corpus path passes the upload check (the Studio's until
   v1.6, the portal's since [ADR 0009](../adr/0009-one-site.md); segments matching
   `^[A-Za-z0-9][A-Za-z0-9 ._()+-]{0,99}$`). Devis and planning files start with their document
   number and carry their indice (`_indice-A`, `_indice-B`), for example
   `DEV-2026-014_indice-B.pdf`; no other file name starts with `DEV-` or `PLN-`.
2. **Revision groups**: the pack's `doc_number_regex` is anchored at the start of the candidate
   (file name first, then the text head), so a document that merely cites a devis or planning
   number never joins its revision group. `explicit_reference_regex` only matches "annule et
   remplace" followed by a devis or planning number. The avenant amends the contract and never
   supersedes it.
3. **Supersession pairs**: exactly one on `full/` (devis indice B supersedes indice A); a second one
   (planning indice B supersedes indice A) once `held-back/` is added.
4. **Amounts** are printed without thousands separators (for example `12500,00 €`): citation
   verification joins digit groups only across non-breaking or thin spaces and apostrophes. PDFs
   embed a Unicode TrueType font, because the PDF core fonts cannot encode `€` or `œ`.
5. **Canary**: the AI-directed text of the window maker's e-mail stands in a paragraph of its own,
   apart from the delay fact, so containment withholds it while the delay stays citable.
6. **Restricted-only values**: the restricted document contains at least two values of four or more
   digits that appear in no other document; they feed the evaluation's restricted-exclusion
   fingerprint. Shorter values, such as the margin percentage, go into the `forbidden` list of the
   restricted question.
7. **Photos**: no golden answer depends on reading a photo; generated descriptions are not evidence
   of counts.
8. **Stamp**: every document carries the stamp of §2 rule 4; the photos carry it as a small overlay
   caption.

## 4. Skill templates

Core skills (shipped with every wiki, templates under `skills/templates/`):

| Skill | Purpose |
|---|---|
| `wiki-navigator` | How to find information: index → topics/entities/sources → glossary → log; MCP tools or plain file reads |
| `cite-sources` | Citation rules, provenance badges, evidence sidecars, quoting in original language |
| `deep-research` | Multi-step research protocol with bounded steps, contradiction and supersession handling, report format |
| `wiki-maintainer` | Conventions for adding sources, reading quality reports, proposals and log entries |

Domain skills (≤ 3 per pack; for `batiment`, for example, checking a supplier invoice against the
delivery notes). Each has an evaluation task in the golden set.

Template rules: Jinja2 with `StrictUndefined`; allowed variables come only from validated catalog
values (counts, page paths, entity types, topic titles from the pack) and the domain pack; values
are escaped; no free text from documents. SKILL.md frontmatter: `name` (kebab-case, ≤ 64 chars),
`description` (≤ 1024 chars); body ≤ 5,000 words.

## 5. Golden set

`evals/golden/dev.jsonl` (public) and a private holdout (not in the repository). Line format (path
and values illustrative):

```json
{"id": "q001", "split": "dev", "category": "single-hop|multi-hop|numeric|table|contradiction|supersession|multilingual|ocr|abstain|injection|restricted|skill",
 "question": "...", "lang": "en|fr", "expected_answer": "...", "must_include": ["...", "30 m²"],
 "required_citations": [{"source_path": "full/devis/DEV-2026-014_indice-B.pdf", "locator_key": "p0001"}],
 "forbidden": ["..."], "abstain": false, "notes": "..."}
```

Size: the dev split has 12 to 20 questions covering the 12 categories; the private holdout has
about 5 questions (about a quarter of all questions).

Language: a question asked in English about French documents uses only language-neutral
`must_include` items (numbers with units, dates, document numbers, names from the bible), so a
correct English answer never needs a French word; French words appear in `must_include` only for
`lang: fr` questions.

Sequencing: bible → generators → corpus frozen (MANIFEST hashes committed) → golden set written
against the frozen corpus and sealed (sha256 of the file recorded in `evals/golden/SEAL`) → only then
the first full wiki generation. The holdout is authored by a separate agent that sees only the
corpus, never the planted-facts notes (`samples/fiction/PLANTED.md`), the generators or the dev set;
only aggregate holdout scores are published.
