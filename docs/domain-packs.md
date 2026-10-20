# Domain packs: adapting DocWiki to your industry

DocWiki's engine knows nothing about building sites, or about any other industry. Everything
domain-specific (document types, the entities worth a page, the topics worth a synthesis, the
glossary, who may read what, how revisions and contradictions are resolved) lives in a **domain
pack**: a folder of YAML and a few templates under `domains/<pack>/`. This page shows how to write
one, with excerpts of the sample pack. The normative format is in
[domain and corpus](spec/domain-and-corpus.md#1-domain-pack-format) and
[`CONTRACT.md`](../src/docwiki/contracts/CONTRACT.md) §15.

One pack ships with the repository:

| Pack | Content |
|---|---|
| [`batiment`](../domains/batiment/README.md) | The paperwork of a small French general contractor (fictional): quotes with revisions, a works contract and its amendment, a planning workbook, a merchant's invoice and a scanned delivery note, site minutes, e-mails and two AI-generated site photos ([provenance](../samples/generators/assets/photos/PROVENANCE.md)). French documents and an English wiki, closed topics, a French-English glossary, a restricted tier and domain skills |

The engine has no pack-specific code. The small test packs under `tests/` (for example
[`tests/domain/fixtures/mini-pack`](../tests/domain/fixtures/mini-pack)) exercise it with domains
other than the sample's, and are the smallest examples of a valid pack.

## The files

| File | Required | Content |
|---|---|---|
| `pack.yaml` | yes | Name, title, description, default audience, languages, wiki title, `fictional` flag, optional banner shown on every page |
| `taxonomy.yaml` | yes | Categories, and document types with an authority (1 to 10) and classification rules |
| `entities.yaml` | yes | Entity types and the registry of entities that deserve a page, with multilingual aliases |
| `topics.yaml` | yes | The closed catalog of topics to synthesise, with keywords and aliases |
| `glossary.yaml` | yes | Seed terms with definitions, synonyms per language and related pages |
| `sensitivity.yaml` | yes | Default tier and rules by path glob or document type |
| `supersession.yaml` | no | How to read document numbers and revisions, and explicit "supersedes" references |
| `resolution.yaml` | no | Contradiction policy, by default authority then recency, with notes shown on topic pages |
| `hints.md` | no | Reviewed notes appended to compile prompts (never document text) |
| `canaries.txt` | no | Injection canary tokens that must never reach a release (gate G08) |
| `skills/<skill>/SKILL.md.j2` | no | At most three domain skill templates |

The loader is strict: unknown keys, unknown files, duplicate YAML keys, references to unknown
categories, entity types, document types or pages, and alias languages not declared in
`pack.yaml` are errors, reported with file and location.

## Walk-through with `batiment`

The excerpts come from [`domains/batiment/`](../domains/batiment/), abridged where marked with `…`.

### `pack.yaml`

```yaml
name: batiment
title: Building works - general contractor job file
description: >-
  The job file of a small French general contractor for one client and one site: quotes and
  their revisions, the works contract and its amendment, … The documents are in French.
default_audience: public
languages: [fr, en]
wiki_title: Chantier Moreau job wiki
fictional: true
banner: >-
  FICTIONAL SAMPLE - … every organisation, person, product, amount and date in this wiki are
  invented. Not for operational use.
```

`languages` lists the languages allowed in aliases and glossary synonyms (`fr`: the documents are
French). The wiki itself is always written in English; quotes keep their original language.

### `taxonomy.yaml`: categories, document types, authority

```yaml
categories:
  - {key: contract-documents, title: "Quotes and contract", description: "Quotes (devis) and their revisions (indices), the works contract and its amendments (avenants)."}
  - {key: purchasing, title: "Invoices and delivery notes", description: "Supplier invoices (factures) and delivery notes (bons de livraison)."}
  # …
doc_types:
  - key: quote
    title: Quote (devis)
    category: contract-documents
    authority: 8
    rules:
      - {filename_regex: '^DEV-\d{4}-\d{3}(?!\d)'}
      - {filename_regex: '(?i)(?:^|[_ -])devis(?:[_ .-]|$)'}
      # …
  - key: delivery-note
    title: Delivery note (bon de livraison)
    category: purchasing
    authority: 6
    rules:
      - {filename_regex: '(?i)(?:^|[_ -])(?:bon[_ -]de[_ -]livraison|BL-\d{4}-\d{4})'}
      - {filename_regex: '(?i)\.pdf$', text_regex: '(?im)^[ \t]*bon\s+de\s+livraison\s+(?:n°\s*)?BL-\d{4}-\d{4}(?!\d)', first_chars: 1000}
  # …
```

The first document type whose rule matches wins (`filename_regex` is searched in the file name,
`text_regex` in the first `first_chars` characters; all regexes of a rule must match). Only
documents that no rule matches are classified by the `fast` model, so good rules make runs
cheaper and more predictable. **Authority** drives contradiction handling: when two current
sources disagree, the higher authority is presented as the rule's winner. In the sample, an
amendment outranks the contract, which outranks the quote, and a delivery note outranks the
invoice for the quantities actually delivered.

### `entities.yaml`: what deserves a page

```yaml
types:
  - {key: building-element, title: Building elements, description: "Parts of the building that the documents follow individually: openings, windows and the slab."}
  - {key: material, title: Materials, description: "Articles supplied by the builders' merchant, with their article codes."}
  # …
registry:
  - type: building-element
    key: baie-f1
    label: Baie coulissante F1
    aliases:
      - {text: baie F1, lang: fr}
      - {text: bay window F1, lang: en}
      - {text: sliding bay window, lang: en}
      # …
    attributes: {mark: F1}
  - type: material
    key: zm-20450
    label: Bloc béton creux 20 x 20 x 50 cm (ZM-20450)
    aliases:
      - {text: ZM-20450, lang: fr}
      - {text: bloc béton creux, lang: fr}
      - {text: hollow concrete block, lang: en}
      # …
    attributes: {code: ZM-20450, sale_unit: palette de 48 blocs}
  # …
```

Entity-type `title`s are plural display names ("Building elements", "Materials"): they title the
`entities/<type>/index.md` pages and group related entities, with a naive singular for a group of
one. Each registry entry with at least one mention gets a page, `entities/<type>/<key>.md`, whose
facts and timeline are aggregated by code. Aliases, in the language of the documents and in
English, drive deterministic autolinking. Entities the model meets but the registry does not know
become **proposals**; once a human accepts one, it is merged into a runtime overlay
(`work/state/overlay.yaml`) and used from the next run, without editing the pack.

### `topics.yaml`: the syntheses you want

```yaml
topics:
  - slug: payments-deposit-and-retention
    title: Payments, deposit and retention
    description: >-
      The payment schedule of the works contract, the deposit, the instalments, the retention
      and its release, the payment of the amendment, and the payment terms of supplier invoices.
    keywords: [payment schedule, payment, payments, paid, payable, deposit, deposits, instalment, instalments, installment, installments, retention, down payment, due date, payment terms]
    aliases:
      - {text: échéancier, lang: fr}
      - {text: acompte, lang: fr}
      - {text: retenue de garantie, lang: fr}
      # …
    min_score: 2
```

Each source section is scored against each topic: keyword and alias occurrences weighted 3 in
titles, 2 in headings and 1 in body text. Topics are routed on the compiled English text, so a
French alias counts where the wiki keeps the French term next to its English gloss, as the pack's
`hints.md` asks. A source feeds a topic when its score reaches `min_score` (default 3.0), and a
topic is synthesised only when at least `min_sources` (default 2) sources feed it; otherwise it
is skipped with the reason `insufficient_evidence`. The catalog is closed on purpose: the model
never invents topics.

### `glossary.yaml`

```yaml
terms:
  - term: retention
    definition: A share of the contract price held back by the client as a guarantee that defects noted at handover are put right, and released after an agreed period.
    synonyms: {fr: [retenue de garantie], en: [retention money, holdback]}
    see_also: [topic:payments-deposit-and-retention]
```

Synonyms feed the glossary page and **query expansion** in `search.db`: a question in French
about the "retenue de garantie" finds the pages that use the canonical term ("retention").

### `sensitivity.yaml`

```yaml
default: public
rules:
  - {tier: restricted, path_glob: "**/restricted/**"}
  - {tier: restricted, doc_type: price-study}
```

The sample is public by default, and `restricted` for anything under a `restricted/` folder and
for the internal price study document type; a pack for private documents would use
`default: internal`, usually with few rules. The highest matching tier wins, and a build for a
given audience excludes every source above it entirely.

### `supersession.yaml` and `resolution.yaml`

```yaml
doc_number_regex: '^(?P<number>(?:DEV|PLN)-\d{4}-\d{3})(?!\d)'
revision_regex: '^(?:DEV|PLN)-\d{4}-\d{3}(?:[ _-]+|[ \t]*[–—][ \t]*)(?i:indice)[ _-]?(?P<rev>[A-H])(?![A-Za-z0-9])'
revision_order: [A, B, C, D, E, F, G, H]
explicit_reference_regex: '(?i:annule\s+et\s+remplace)\s+(?:(?i:le|la|les)\s+)?(?:(?i:devis|planning)\s+)?(?P<number>(?:DEV|PLN)-\d{4}-\d{3})(?!\d)'
```

```yaml
order: [authority, recency]
notes: >-
  Contractual documents prevail: the amendment (avenant, authority 10) over the works contract
  (9) on the points it amends, and the contract over the quote (8). … The schedule and the
  suppliers' e-mails have the same authority (4): the more recent statement prevails until a new
  schedule revision (indice) supersedes the old one. …
```

Two documents with the same number and different revisions form a revision group: the latest is
`current`, the others `superseded`. A document that says "annule et remplace le devis
DEV-2026-014" supersedes it explicitly. The regexes may name their groups `number` and `rev`
(otherwise group 1 is used). Contradictions between current sources are shown with both claims
and the notes of `resolution.yaml`; the rule is stated, never applied silently. Anchor the number
pattern at the start (`^`) so that a document that merely mentions another document's number is
not grouped with it, and keep words such as "amends" out of the reference regex if, in your
domain, an amendment does not replace the whole document: in the sample, the amendment (avenant)
amends the contract and never supersedes it.

### `hints.md`

Reviewed notes for the compile prompt, for example conventions for terms and amounts:

```markdown
- The documents are written in French; write the wiki in English. The first time a French trade
  term appears, keep it in quotes after its English gloss, for example quote ("devis"), contract
  amendment ("avenant"), deposit ("acompte"), retention ("retenue de garantie"), … Quotes from the
  documents stay in French, exactly as written.
- Copy every amount exactly as printed, with its comma decimal separator and without adding a
  thousands separator (`12500,00 €`, never `12,500.00 €` or `12 500,00 €`), … Never round,
  convert or recompute an amount.
```

Hints are operator text, reviewed like code. Never paste document text into them: documents are
data, and hints are instructions.

### Domain skills

Up to three `skills/<skill>/SKILL.md.j2` templates, for example `check-supplier-invoice` in
`batiment`. They receive only validated values (wiki title, fixed paths, the topics and entity
types present in the release). See [skills](skills.md#writing-a-domain-skill).

## Workflow for a new pack

1. Copy `domains/batiment` to `domains/<your-pack>` and edit `pack.yaml`.
2. Write taxonomy rules for your file naming conventions first; they make classification
   deterministic.
3. Seed the registry with the entities people ask about (parties, products, documents, roles) and
   their aliases in every language you declared.
4. Define 5 to 10 topics that combine several documents: those are where the wiki adds the most
   value.
5. Set sensitivity rules before the first run, including a `restricted/` convention if you need
   one.
6. Validate the pack:

   ```bash
   uv run python -c "from docwiki.domain import load_pack; print(load_pack('domains/<your-pack>').name)"
   ```

7. Run on a few documents, inspect the result, iterate:

   ```bash
   uv run docwiki run --input <folder> --domain <your-pack> --audience internal --limit 5 --work-dir .local
   uv run docwiki lint --release .local/releases
   ```

8. Deploy: domain packs are part of the job image, so commit the pack, set
   `azd env set DOCWIKI_DOMAIN <your-pack>` and run `azd provision` and `azd deploy job`.

The domain pack hash is part of every cache key, so changing the pack recompiles exactly what it
affects.

## Fictional samples

If you publish a pack with sample documents, follow the repository's fiction rules: every
organisation, person, site and product comes from a closed list (the `batiment` sample uses
[`samples/fiction/bible.yaml`](../samples/fiction/bible.yaml)), procedure-like documents carry
"FICTIONAL — NOT FOR OPERATIONAL USE", and the leak guard checks the closed world. Real procedures
from your organisation belong in your private deployment, not in a public pack.
