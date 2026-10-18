# Domain packs: adapting DocWiki to your industry

DocWiki's engine knows nothing about wind turbines. Everything domain-specific (document types,
the entities worth a page, the topics worth a synthesis, the glossary, who may read what, how
revisions and contradictions are resolved) lives in a **domain pack**: a folder of YAML and a few
templates under `domains/<pack>/`. This page shows how to write one. The normative format is in
[domain and corpus](spec/domain-and-corpus.md#1-domain-pack-format) and
[`CONTRACT.md`](../src/docwiki/contracts/CONTRACT.md) §15.

Two packs ship with the repository:

| Pack | Content |
|---|---|
| [`wind-om`](../domains/wind-om/README.md) | Operations and maintenance of the fictional Quellmoor Ridge Wind Farm: 12 categories, 30 document types, 9 entity types with 101 registry entries, 10 topics, English, French and German |
| [`it-runbooks`](../domains/it-runbooks/README.md) | A deliberately tiny pack for the fictional IT platform team of Relecloud: runbooks, a failover procedure, an on-call handbook, a postmortem and a service catalog. It proves the engine is generic, and it is the best template to copy |

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

## Walk-through with `it-runbooks`

### `pack.yaml`

```yaml
name: it-runbooks
title: IT operations runbooks
description: >-
  Runbooks, procedures, on-call rules, postmortems and the service catalog of an IT platform
  operations team.
default_audience: internal
languages: [en]
wiki_title: Relecloud operations wiki
fictional: true
banner: >-
  FICTIONAL SAMPLE - Relecloud, its services and people are invented. Not for operational use.
```

`languages` lists the languages allowed in aliases and glossary synonyms. The wiki itself is
always written in English; quotes keep their original language.

### `taxonomy.yaml`: categories, document types, authority

```yaml
categories:
  - {key: operations, title: "Operations", description: "Runbooks, procedures and on-call rules."}
  - {key: learning, title: "Learning from incidents", description: "Postmortems."}
doc_types:
  - key: procedure
    title: Procedure
    category: operations
    authority: 8
    rules:
      - {filename_regex: '^PRC-[A-Z]{2}-\d{3}'}
  - key: postmortem
    title: Postmortem
    category: learning
    authority: 5
    rules:
      - {filename_regex: '^PM-\d{4}-\d{3}'}
      - {text_regex: '(?i)blameless postmortem - \d{4}-\d{2}-\d{2}', first_chars: 2000}
```

The first document type whose rule matches wins (`filename_regex` is searched in the file name,
`text_regex` in the first `first_chars` characters; all regexes of a rule must match). Only
documents that no rule matches are classified by the `fast` model, so good rules make runs
cheaper and more predictable. **Authority** drives contradiction handling: when two current
sources disagree, the higher authority is presented as the rule's winner.

### `entities.yaml`: what deserves a page

```yaml
types:
  - {key: service, title: Services, description: Services in the service catalog.}
  - {key: alert, title: Alerts, description: Monitoring alerts with their conditions.}
registry:
  - {type: service, key: orders-db, label: orders-db,
     aliases: [{text: orders-db, lang: en}, {text: orders database, lang: en}],
     attributes: {tier: 1, technology: PostgreSQL}}
  - {type: alert, key: ticketingapihighlatency, label: TicketingApiHighLatency,
     aliases: [{text: TicketingApiHighLatency, lang: en}], attributes: {service: ticketing-api}}
```

Entity-type `title`s are plural display names ("Services", "Spare parts"): they title the
`entities/<type>/index.md` pages and group related entities, with a naive singular for a group of
one. Each registry entry with at least one mention gets a page, `entities/<type>/<key>.md`, whose facts
and timeline are aggregated by code. Aliases drive deterministic autolinking. Entities the model
meets but the registry does not know become **proposals**; once a human accepts one, it is merged
into a runtime overlay (`work/state/overlay.yaml`) and used from the next run, without editing the
pack.

### `topics.yaml`: the syntheses you want

```yaml
topics:
  - slug: database-operations
    title: Database operations
    description: The orders database, replication, failover and recovery targets.
    keywords: [orders-db, database, failover, standby, replication, RPO, RTO, PostgreSQL]
    aliases: []
```

Each source section is scored against each topic: keyword and alias occurrences weighted 3 in
titles, 2 in headings and 1 in body text. A source feeds a topic when its score reaches
`min_score` (default 3.0), and a topic is synthesised only when at least `min_sources` (default 2)
sources feed it; otherwise it is skipped with the reason `insufficient_evidence`. The catalog is
closed on purpose: the model never invents topics.

### `glossary.yaml`

```yaml
terms:
  - term: recovery point objective
    definition: Maximum amount of data, expressed as time, that may be lost in an incident.
    synonyms: {en: [RPO]}
    see_also: [topic:database-operations]
```

Synonyms feed the glossary page and **query expansion** in `search.db`: a question about "RPO", or
about "multiplicateur" or "Getriebe" in the wind pack, finds the pages that use the canonical
term ("recovery point objective", "gearbox").

### `sensitivity.yaml`

```yaml
default: internal
rules: []
```

The wind pack shows the other case: public by default, `restricted` for anything under a
`restricted/` folder and for the rate-card document type. The highest matching tier wins, and a
build for a given audience excludes every source above it entirely.

### `supersession.yaml` and `resolution.yaml`

```yaml
doc_number_regex: '^(RB-[A-Z]{3}-\d{3}|PRC-[A-Z]{2}-\d{3}|PM-\d{4}-\d{3})(?![0-9])'
revision_regex: '\b[Vv](\d+)\b'
revision_order: numeric
explicit_reference_regex: '(?i)\b(?:supersedes|replaces)\s+((?:RB|PRC)-[A-Z]{2,3}-\d{3})'
```

```yaml
order: [authority, recency]
notes: >-
  Procedures win over runbooks, runbooks over the handbook and the handbook over postmortems.
  With equal authority the more recent document wins.
```

Two documents with the same number and different revisions form a revision group: the latest is
`current`, the others `superseded`. A document that says "supersedes PRC-DB-007" supersedes it
explicitly. Contradictions between current sources are shown with both claims and the notes of
`resolution.yaml`; the rule is stated, never applied silently. Anchor the number pattern at the
start (`^`) so that a document that merely mentions another document's number is not grouped with
it, and keep words such as "amends" out of the reference regex if, in your domain, an amendment
does not replace the whole document.

### `hints.md`

Reviewed notes for the compile prompt, for example identifier conventions:

```markdown
- Service names are lower-case identifiers such as `ticketing-api` and `orders-db`; keep them
  exactly as written.
- Severity levels are `SEV1` (highest) to `SEV4`.
```

Hints are operator text, reviewed like code. Never paste document text into them: documents are
data, and hints are instructions.

### Domain skills

Up to three `skills/<skill>/SKILL.md.j2` templates, for example `respond-to-alert` in
`it-runbooks`. They receive only validated values (wiki title, fixed paths, the topics and entity
types present in the release). See [skills](skills.md#writing-a-domain-skill).

## Workflow for a new pack

1. Copy `domains/it-runbooks` to `domains/<your-pack>` and edit `pack.yaml`.
2. Write taxonomy rules for your file naming conventions first; they make classification
   deterministic.
3. Seed the registry with the entities people ask about (assets, systems, products, procedures,
   roles) and their aliases in every language you declared.
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
organisation, person, site and product comes from a closed list (the `wind-om` sample uses
[`samples/fiction/bible.yaml`](../samples/fiction/bible.yaml)), procedure-like documents carry
"FICTIONAL — NOT FOR OPERATIONAL USE", and the leak guard checks the closed world. Real procedures
from your organisation belong in your private deployment, not in a public pack.
