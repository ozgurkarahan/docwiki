# Domain packs, fictional world and sample corpus

## 1. Domain pack format

A domain pack is a folder under `domains/<pack>/`:

| File | Content |
|---|---|
| `pack.yaml` | `name`, `title`, `description`, `default_audience`, `languages` (e.g. `[en, fr, de]`), `wiki_title`, `fictional: true|false`, `banner` (optional notice shown on pages), `wiki_languages` (optional, v1.7, [ADR 0012](../adr/0012-french-canonical-and-locked-vocabulary.md): the languages of the wiki, unique language codes, at least one; the first is **canonical**: the pages are compiled in it at `wiki/<path>`; each other one gets a mirror at `wiki/<lang>/<path>` written by the `translate` stage, pipeline.md §1. Default `[en]`: an English wiki without mirror, exactly as before v1.7) |
| `taxonomy.yaml` | `categories: [{key, title, description}]`; `doc_types: [{key, title, category, authority (1-10), rules: [{filename_regex?, text_regex?, first_chars?: 2000}], label?}]` (`label`: the short display label of the site's register and source header, e.g. "PV de réception"; the title when absent; never the key) |
| `entities.yaml` | `types: [{key, title, description, attribute_labels?: {<attribute key>: <label>}}]` (the hub's Details table shows the labelled attributes in this order; without labels, every attribute); `registry: [{type, key, label, aliases: [{text, lang}], attributes: {}}]` |
| `topics.yaml` | `topics: [{slug, title, description, keywords: [...], aliases: [{text, lang}], min_score?, min_sources?}]` |
| `glossary.yaml` | `terms: [{term, definition, synonyms: {fr: [], de: []}, see_also: [entity or topic ids]}]` |
| `sensitivity.yaml` | `default: public|internal`; `rules: [{tier, path_glob?, doc_type?}]` |
| `supersession.yaml` | `doc_number_regex`, `revision_regex`, `revision_order` (e.g. `[A, B, C]` or numeric), `explicit_reference_regex` |
| `resolution.yaml` | contradiction resolution policy: `order: [authority, recency]`, notes shown on topic pages; optional (v1.7) `amendments: [{amending: [doc types], amended: [doc types]}]` (an amending document of the same scope changes the amended one: a change, not a contradiction; a winning amended document is to review when its scope has amending documents) and `arbitrate: [{types: [doc type, doc type], reason}]` (pairs the rule never decides); doc types must exist in `taxonomy.yaml` (wiki-contract.md §9) |
| `hints.md` | optional reviewed domain notes appended to compile prompts (no document text) |
| `scopes.yaml` | optional scope dimension (v1.7, [ADR 0011](../adr/0011-company-wide-wiki.md)): `name` (the scope type, e.g. `chantier`, also the registry entity type of each scope value), `title`, `plural` (the hubs' folder), `default: {key, title}` (documents outside any scope), `paths: [{regex}]` (first match on the raw path; named groups `scope`, `phase`, `type`, `lot`), `phases: [{key, title}]`, `lot_regex` (a `lot` group, on the file name). A `type` group naming a doc type decides the document's type before the rules. Topics with `per_scope: true` are written once per scope. Supersession groups are keyed by (scope, document number). A registry entry whose `attributes` name a value for the scope dimension (the key equals `name`, e.g. `chantier: moreau`) belongs to that scope only: a document of another scope, of the default scope or a page without scope does not mention it, whatever names it shares (its entity page, the source pages' `entities`, autolinks, topics' and hubs' entity lists; wiki-contract.md §3); an entry without that attribute is company-wide. |
| `views.yaml` | optional computed views (v1.7, [ADR 0011](../adr/0011-company-wide-wiki.md) decision 5): `views: [{slug, title, description, doc_types, columns: {<output name>: [header aliases]}, sql, per_scope, totals, labels, amounts, scope_columns}]` (`labels`: header of each result column, e.g. "Marché HT"; `amounts`: result columns that are amounts in euros, `HT`, `TTC` or `€`, written `184 490,00 € HT`; `scope_columns`: result columns holding scope values, shown by label and linked to the hub; each key must be a displayed result column). The engine builds one DuckDB relation `rows`: the union of the tables of the current documents whose type is in `doc_types`, columns renamed by matching table headers to the aliases (without case, accents or punctuation; the output name counts as an alias; a table lacking a column is skipped with a run warning), all cells as extracted text, plus `_source_id`, `_table_id`, `_row_id` and `_scope`. `sql` is one read-only `SELECT` over `rows` (the locked-down DuckDB of `query_table`) that must return `_source_id` and `_row_id` (and `_table_id` when a document has several tables); `parse_amount(text)` (`2 390,00 € HT` → 2390.00) and `parse_date(text)` (`15/03/2026`, `2026-03-15`) are available. `totals` are result columns summed by code with exact decimals (per scope when `per_scope`). The pack load runs every query over an empty `rows` and rejects a non-`SELECT`, an unknown column, a result without `_source_id` and `_row_id`, unknown totals and unknown doc types; a query that fails on the data fails the run. |
| `terms.yaml` | optional locked trade vocabulary (v1.7, [ADR 0012](../adr/0012-french-canonical-and-locked-vocabulary.md)): `terms: [{term, forms, gloss, banned}]`; kept in the documents' language with the English gloss on first use, given to the compile, entity and topic prompts; gate G16 fails a page with a banned rendering |
| `i18n/<lang>.yaml` | optional (v1.7, ADR 0012): overrides of the generated wiki strings of one wiki language (a flat mapping `key: template`; `{fields}` as in the core tables of `docwiki.contracts.i18n`, which hold every generated heading, sentence and label in English and French). Only keys of the core tables; the structural headings (`heading.*`, recognised by code and the validator) cannot be overridden; `<lang>` must be one of `wiki_languages` |
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

Lamna Bâtiment, a small fictional French general contractor (entreprise générale de bâtiment),
runs **three chantiers at three phases under three contract types** at the same time, with
suppliers and subcontractors shared between them, and keeps its own company documents
([ADR 0011](../adr/0011-company-wide-wiki.md), slice F of v1.7):

| Chantier (scope) | Client and contract | Works | Phase in April 2026 |
|---|---|---|---|
| `moreau` | A private household (particulier), global fixed price | A 30 m² house extension and a kitchen renovation | 3 exécution |
| `nacrines` | A copropriété represented by its syndic, an architect as maître d'œuvre, monthly situations | Façade refurbishment with external insulation, new aluminium windows and doors in the common parts | 4 réception (with réserves) |
| `ecole-montferrine` | A commune, public contract (CCAP, DPGF, acte d'engagement) | Energy renovation of a school during the summer holidays | 2 préparation |
| `entreprise` (default scope) | Company documents | Framework contract and price list of the builders' merchant, general terms, organisation chart, crew schedule, equipment, attestations and billing registers, margin dashboard | - |

The third parties are a builders' merchant (framework contract), a window maker whose aluminium
shortage reaches two chantiers, an electrical and a plumbing subcontractor. The timeline runs from
November 2025 to April 2026. Every name (company, staff, clients, towns, third parties) lives in
`samples/fiction/bible.yaml`; the chantier codes are the keys of the pack's `chantier` entities.
The documents are written in French. Since v1.7 (ADR 0012) the pack declares
`wiki_languages: [fr, en]`: the wiki is compiled in French (canonical, generated headings and
sentences from the French string table, locked trade terms as written) and the `translate` stage
writes its English mirror under `wiki/en/`; questions are asked in English and in French.

### 3.1 Corpus composition (39 public documents, 2 restricted, 1 held back)

The company files its documents by chantier, phase and document type; the scope, the phase and the
type of each document come from its path, never from a model (`domains/batiment/scopes.yaml`):

```
chantiers/<code>/<phase>-<name>/<doc type>/<file>    # one folder per chantier
entreprise/<doc type>/<file>                         # company-wide documents
```

`<phase>` is one of `0-commercial`, `1-marche`, `2-preparation`, `3-execution`, `4-reception` and
`5-garantie`; `<doc type>` is a document type key of the pack's taxonomy.

| Scope | Documents (in French) | Formats | Demonstrates |
|---|---|---|---|
| `moreau` (14, + 1 held back) | Devis indice A and indice B; signed contrat de travaux; avenant n°1; planning et suivi des achats indice A (sheets Planning, Achats); builders' merchant invoice; scanned delivery note with a handwritten "2 palettes manquantes"; site meeting minutes n°3; the client's change-request e-mail; the window maker's delay e-mail (with the injection canary in a paragraph of its own); two site photos; the internal price study (restricted) | PDF (text and image-only), DOCX, XLSX, EML, JPG | Supersession, multi-hop total, tables, delivery discrepancy, OCR, contradiction, injection containment, generated-description provenance |
| `nacrines` (10) | Signed marché de travaux; subcontract and DC4 of the electrical subcontractor; ordre de service n°1; builders' merchant invoice; situation n°4 (sheets Situation, Récapitulatif, Sous-traitance); site meeting minutes n°12 written by the maître d'œuvre; scanned PV de réception with handwritten réserve R07 and lifting delay; list of réserves with their lifting status; the window maker's second delay e-mail | DOCX, PDF (text and image-only), XLSX, EML | Retention on situations, OS that amends and never supersedes, réception with réserves, OCR on a PV, cross-chantier supplier |
| `ecole-montferrine` (9) | CCAP (extract); DPGF indice A and indice B; signed acte d'engagement; purchase order of the windows; summer works planning; preparation meeting minutes n°1; the mairie's e-mail about the day camp; PPSPS | PDF, XLSX, DOCX, EML | Second supersession on another chantier, public contract terms, a planning not yet updated after the client's constraint, a procedure-like document |
| `entreprise` (9) | General terms 2026; organisation chart; framework contract and price list of the builders' merchant; crew schedule of weeks 15 to 17; equipment register; subcontractor attestations register; client billing register (sheets Marchés, Factures); margin dashboard (restricted) | PDF, DOCX, XLSX | Cross-chantier figures computed by code (§3.2), shared suppliers and subcontractors |
| Held back | Planning PLN-2026-003 indice B of the chantier Moreau (new window delivery date), under `held-back/` | XLSX | Time travel (§3.2) |

`full/` holds 41 documents: 39 public (PDF 12 including two image-only scans, DOCX 10, XLSX 11,
EML 4, JPG 2) and 2 restricted workbooks, the price study (under its `price-study/` folder) and the
margin dashboard (under its `margin-dashboard/` folder), which the pack tiers `restricted` by path
and by document type: neither may appear in a public build. `held-back/` holds the planning
indice B. The other supported formats (CSV, PPTX, VTT, PNG, Markdown and text) are covered by the
generated fixtures of the extraction tests.

### 3.2 Planted scenarios

Several scenarios can only be answered by combining documents, often of several chantiers. The
exact facts, their sources and locators, and the acceptance matrix are recorded in
`samples/fiction/PLANTED.md`.

1. **Supersession** (Moreau): devis indice B replaces indice A with a revised scope and price;
   indice A keeps its page, marked `superseded`.
2. **Contract and amendment** (Moreau): price, deposit, 5 % retention (retenue de garantie) and
   completion date of the contract; the avenant adds to the total and amends, never supersedes.
3. **Contradiction** (Moreau): the planning and the window maker's e-mail give different delivery
   dates for the windows; both claims are shown with the resolution rule.
4. **Delivery discrepancy** (Moreau): the merchant's invoice bills 10 pallets, while only 8 were
   delivered according to the scanned delivery note, readable only through OCR.
5. **Amounts**: amounts before and after VAT (HT/TTC), deposits, retentions, amendments, service
   orders, situations and purchases to date are exact numbers in text and tables.
6. **Multilingual**: every document is in French; questions are asked in English and in French, and
   the glossary carries the French synonyms of English terms.
7. **Restricted exclusion**: the price study and the margin dashboard exist in the corpus but must
   not leak into the public wiki or into public answers.
8. **Injection canary**: the window maker's first e-mail contains an instruction addressed to AI
   assistants with a unique canary token (defined in the bible); it must be neutralised and flagged.
9. **Abstain, scoped to one chantier**: no document of the chantier Moreau names an architect or a
   maître d'œuvre; the architect of the résidence Les Nacrines must not be given for Moreau.
10. **Time travel**: adding the held-back planning indice B creates a new supersession (planning
    indice A → B) whose new delivery date resolves the contradiction of scenario 3.
11. **Second supersession on another chantier**: DPGF indice B of the school replaces indice A;
    supersession is keyed by (chantier, number), so it never connects to the devis of Moreau.
12. **A supplier's shortage across chantiers**: the window maker's aluminium shortage moves a
    delivery at Moreau and the hall doors at Les Nacrines (a réserve that cannot be lifted within
    the delay of the PV); the school's windows are not affected so far.
13. **Framework prices**: each merchant invoice bills one line above the net price of the framework
    price list, which gives a credit note; there is no merchant invoice for the school.
14. **Réception, réserves and retention** (Les Nacrines): réception with réserves, réserves lifted
    and still open, the retention retained to date and its release date.
15. **Crew double booking**: the crew schedule books one person on two chantiers on overlapping days.
16. **Financial position of every chantier**: contract with its avenants or service orders, billed,
    retained and left to bill, computed by code from the billing register rows, each row cited.
17. **Expired attestation de vigilance**: the electrical subcontractor's attestation had expired at
    the date of its situation and was renewed later.
18. **Ambiguous question**: "When are the windows delivered?" has an answer on two chantiers; the
    Researcher names each chantier or asks which one.
19. **The school's DPGF and acte d'engagement**: the current indice, what changed, the contract
    amount and the subcontractors with direct payment.
20. **Other cross-document facts**: no delay penalties at Les Nacrines thanks to the service order,
    an overdue periodic inspection (VGP) of an item of equipment, the school planning against the
    mairie's day-camp dates, the standard deposit and retention of the general terms.

Scenarios 15 to 17 and the overdue inspection are answered by the computed views of the pack
(`domains/batiment/views.yaml`: `position-financiere`, `doubles-affectations`,
`attestations-de-vigilance-expirees`, `vgp-en-retard`), tested against the planted figures on the
extracted corpus. The merchant invoices are PDFs whose lines are not row-located tables, so the
framework price gaps (scenario 13) are left to the cited synthesis, not to a view.

### 3.3 Files

```
samples/fiction/bible.yaml                    # world definition (closed world)
samples/fiction/allowlist.txt                 # generated proper-noun allowlist
samples/fiction/PLANTED.md                    # planted facts, their sources and the acceptance matrix
samples/generators/                           # deterministic generators (python), one module per format
samples/corpus/full/chantiers/<code>/...      # the documents of the three chantiers
samples/corpus/full/entreprise/...            # the company documents
samples/corpus/held-back/chantiers/moreau/... # the held-back planning revision (time travel)
samples/corpus/MANIFEST.json                  # path, sha256, format, pages/rows, sensitivity, held-back flag
domains/batiment/                             # domain pack for the sample (scopes.yaml, views.yaml)
```

Pack genericity is covered by the small test packs under `tests/` since the second sample pack was
removed in v1.2 ([changelog](CHANGELOG.md#v12)).

### 3.4 Document contract

Properties of the sample documents that scopes, supersession, verification, containment, the views
and the evaluation rely on; tests under `tests/samples/` enforce them.

1. **Paths** are ASCII, follow the layout of §3.1 (the chantier code, the phase and the doc type
   folder of every path are known to the pack) and pass the portal's upload check
   ([ADR 0009](../adr/0009-one-site.md); segments matching `^[A-Za-z0-9][A-Za-z0-9 ._()+-]{0,99}$`).
   Devis, DPGF and planning files start with their document number and carry their indice
   (`_indice-A`, `_indice-B`), for example `DEV-2026-014_indice-B_devis-extension-et-cuisine.pdf`;
   no other file name starts with `DEV-` or `PLN-`.
2. **Revision groups** are keyed by (chantier, number): the pack's `doc_number_regex` is anchored at
   the start of the candidate (file name first, then the text head), so a document that merely
   cites a devis, DPGF or planning number never joins its revision group; `explicit_reference_regex`
   only matches "annule et remplace" followed by such a number. The avenant and the ordre de service
   amend their contracts and never supersede them.
3. **Supersession pairs**: exactly two on `full/` (devis indice B supersedes indice A at Moreau, DPGF
   indice B supersedes indice A at the school); a third one (planning indice B supersedes indice A
   at Moreau) once `held-back/` is added.
4. **Amounts** are printed without thousands separators (for example `12500,00 €`): citation
   verification joins digit groups only across non-breaking or thin spaces and apostrophes. PDFs
   embed a Unicode TrueType font, because the PDF core fonts cannot encode `€` or `œ`.
5. **Canary**: the AI-directed text of the window maker's first e-mail stands in a paragraph of its
   own, apart from the delay fact, so containment withholds it while the delay stays citable.
6. **Restricted-only values**: the restricted documents contain values of four or more digits that
   appear in no other document; they feed the evaluation's restricted-exclusion fingerprint.
   Shorter values, such as margin percentages, go into the `forbidden` list of the restricted
   questions.
7. **Registers are tables**: the company registers, the situation and the plannings are workbooks
   with one header row and one record per row, so that the computed views can cite every row; their
   footer rows ("Document", "Tenu par"...) leave the amount and date columns empty.
8. **Photos**: no golden answer depends on reading a photo; generated descriptions are not evidence
   of counts.
9. **Stamp**: every document carries the stamp of §2 rule 4; the photos carry it as a small overlay
   caption and the scans print it at the top and bottom of the page image.

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
