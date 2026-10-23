# Domain pack `batiment` (fictional sample)

The company files of a small French general contractor ("entreprise générale de bâtiment")
that runs three chantiers at three phases and under three contract types, with suppliers and
subcontractors shared between them (slice F, [ADR 0011](../../docs/adr/0011-company-wide-wiki.md)):

| Chantier (scope) | Client and contract | Phase | Documents |
|---|---|---|---|
| `moreau` | A private household (particulier): a 30 m² extension and a kitchen renovation | exécution | 14 (+ 1 held back) |
| `nacrines` | A copropriété (private contract, syndic, an architect as maître d'œuvre): façade refurbishment with external insulation and new aluminium windows and doors | réception | 10 |
| `ecole-montferrine` | A commune (public contract): the energy renovation of a school during the summer holidays | préparation | 9 |
| `entreprise` | Company documents: framework contract and price list, crew schedule, equipment and attestation registers, billing register, general terms, organisation chart, margin dashboard | - | 9 |

The documents are in French and the wiki is compiled in English for now (French canonical
later, [ADR 0012](../../docs/adr/0012-french-canonical-and-locked-vocabulary.md)). Every name
comes from [`samples/fiction/bible.yaml`](../../samples/fiction/bible.yaml) and the sample
corpus is `samples/corpus`; the pack repeats names only in the banner of `pack.yaml` and in the
registry of `entities.yaml`. The pack follows [domain and corpus](../../docs/spec/domain-and-corpus.md)
sections 1 and 3 and loads with `docwiki.domain.load_pack("domains/batiment")`.

| File | Content |
|---|---|
| `pack.yaml` | Pack identity, languages (`fr`, `en`), wiki title "Lamna Bâtiment", fictional banner; default audience `public` |
| `scopes.yaml` | The scope `chantier` (plural `chantiers`, default `entreprise`) read from the path `chantiers/<code>/<phase>-<name>/<doc type>/<file>` or `entreprise/<doc type>/<file>`; six phases (0 commercial to 5 garantie); no lot regex |
| `taxonomy.yaml` | 12 categories and 31 document types with authority 1-10; the doc type folder of the path decides the type, and every sample file also matches a `filename_regex` of the same type |
| `entities.yaml` | 12 entity types (chantiers, organisations, sous-traitants, maîtres d'œuvre, people, work packages, building elements, materials, matériel, réserves, situations, commercial documents) with French and English aliases |
| `topics.yaml` | 9 closed topics: 6 per chantier (`per_scope: true`) and 3 company topics |
| `glossary.yaml` | Generic French building-trade terms with their English term, French synonyms and related pages |
| `terms.yaml` | The locked trade vocabulary (ADR 0012): kept in French with an English gloss; banned renderings where they are wrong |
| `sensitivity.yaml` | `public` by default; the price study and the margin dashboard are `restricted` by path (their doc type folder, or any `restricted/` folder) and by doc type |
| `supersession.yaml` | Quote and DPGF (`DEV-`) and schedule (`PLN-`) numbers at the start of the file name or text, revisions `indice A` to `indice H`, explicit references only as "annule et remplace"; groups are keyed by (chantier, number) |
| `resolution.yaml` | Contradictions: authority first, then recency, with the notes shown on topic pages |
| `hints.md` | Reviewed compile hints (no document text): chantiers, French terms, exact amounts, HT/TTC, day-first dates, indices, amendments and OS, situations, réserves, registers |
| `canaries.txt` | The injection canary of the sample corpus (gate G08) |
| `skills/` | Domain skill templates: `check-supplier-invoice`, `prepare-site-meeting`, `track-contract-amounts` |

## Document types and authority

Authority decides which current source prevails when two disagree; the rule is stated on topic
pages next to both claims, never applied silently. Doc type keys are English, except the
documents named by a locked trade term, which keep the French term.

| Authority | Doc types |
|---|---|
| 10 | `contract-amendment` (avenant), `ordre-de-service`, `pv-de-reception` |
| 9 | `works-contract`, `acte-d-engagement`, `ccap`, `framework-agreement` |
| 8 | `quote`, `dpgf`, `subcontract`, `dc4` |
| 7 | `site-meeting-minutes`, `liste-des-reserves`, `general-terms` |
| 6 | `delivery-note`, `situation`, `billing-register`, `price-list` |
| 5 | `supplier-invoice`, `purchase-order`, `ppsps`, `equipment-register`, `compliance-register` |
| 4 | `schedule`, `crew-schedule`, `supplier-email` |
| 3 | `client-email`, `price-study`, `margin-dashboard` |
| 2 | `site-photo`, `organisation-chart` |

The schedule and the supplier's e-mail share the same authority on purpose: their window delivery
dates disagree on the chantier Moreau, and the more recent statement prevails until the held-back
schedule indice B supersedes indice A. A delivery note outranks the invoice for the quantities
actually delivered.

## Supersession

`doc_number_regex` is anchored at the start of the candidate and the revision is the indice that
follows the number, so only the quote, DPGF and schedule files (named `DEV-…_indice-A…`,
`PLN-…_indice-B…`) form revision groups. Expected pairs: quote DEV-2026-014 indice B supersedes
indice A (Moreau) and DPGF DEV-2026-031 indice B supersedes indice A (school) on `full/`; schedule
PLN-2026-003 indice B supersedes indice A once `held-back/` is added. Groups are keyed by
(chantier, number), so two chantiers' documents never supersede each other.

## Topics

Routing scores the compiled title, headings and text (title 3, heading 2, body 1). Per chantier:
`marche-et-avenants`, `planning`, `achats`, `situations-et-paiements`, `reception-et-reserves`,
`suivi-de-chantier`; company: `fournisseurs-et-contrat-cadre`, `equipes-et-materiel`,
`sous-traitance-et-conformite`.

## Skill template variables

The engine renders `skills/<skill>/SKILL.md.j2` with Jinja2 (`StrictUndefined`, escaped values)
and **only** the variables below. Values come from the validated release catalog and this pack,
never from document text. Paths are relative to the wiki root and use `/`.

| Variable | Type | Example | Source |
|---|---|---|---|
| `wiki_title` | string | the `wiki_title` of `pack.yaml` | `pack.yaml` `wiki_title` |
| `paths.index` | string | `index.md` | wiki layout |
| `paths.glossary` | string | `glossary.md` | wiki layout |
| `paths.log` | string | `log.md` | wiki layout |
| `paths.sources_index` | string | `sources/index.md` | wiki layout |
| `paths.entities_index` | string | `entities/index.md` | wiki layout |
| `paths.topics_index` | string | `topics/index.md` | wiki layout |
| `topics` | list of `{slug, title, path}` | `{slug: achats, title: Achats, path: topics/moreau/achats.md}` | topic pages present in the release |
| `entity_types` | list of `{key, title, path}` | `{key: material, title: Materials, path: entities/material/index.md}` | entity types with at least one page |

Template rules: no other variables, filters reading files or includes; the frontmatter `name`
stays literal (kebab-case, at most 64 characters, equal to the folder name); the rendered
`description` stays under 1,024 characters and the body under 5,000 words; loops over `topics`
and `entity_types` render correctly when the lists are empty. The documentation lives in this
README because the pack loader accepts only skill folders under `skills/`.
