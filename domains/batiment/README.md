# Domain pack `batiment` (fictional sample)

The job file of a small French general contractor ("entreprise générale de bâtiment") for one
private household and one site ("chantier"): a 30 m² single-storey extension and a kitchen
renovation, with a builders' merchant, a window maker and an electrical subcontractor. The
documents are in French and the wiki is compiled in English. Every name comes from
[`samples/fiction/bible.yaml`](../../samples/fiction/bible.yaml) and the sample corpus is
`samples/corpus`; the pack repeats names only in the banner of `pack.yaml` and in the registry of
`entities.yaml`. The pack follows [domain and corpus](../../docs/spec/domain-and-corpus.md)
sections 1 and 3 (including the document contract of section 3.4) and loads with
`docwiki.domain.load_pack("domains/batiment")`.

| File | Content |
|---|---|
| `pack.yaml` | Pack identity, languages (`fr`, `en`), wiki title, fictional banner; default audience `public` |
| `taxonomy.yaml` | 6 categories and 11 document types with authority 1-10; every sample file matches a `filename_regex`; `text_regex` fallbacks match only the title line of their own type in PDF, DOCX (or XLSX for the price study) files |
| `entities.yaml` | 6 entity types (organisations, people, work packages, building elements, materials, commercial documents) and 44 registry entries with French and English aliases |
| `topics.yaml` | 7 closed topics with English keywords and French aliases |
| `glossary.yaml` | Generic French building-trade terms with their English term, French synonyms and related pages |
| `sensitivity.yaml` | `public` by default; anything under a `restricted/` folder, and the price study type, is `restricted` |
| `supersession.yaml` | Quote (`DEV-`) and schedule (`PLN-`) numbers at the start of the file name or text, revisions `indice A` to `indice H`, explicit references only as "annule et remplace" |
| `resolution.yaml` | Contradictions: authority first, then recency, with the notes shown on topic pages |
| `hints.md` | Reviewed compile hints (no document text): French terms, exact amounts, HT/TTC, day-first dates, indices, amendments, delivery reserves |
| `canaries.txt` | The injection canary of the sample corpus (gate G08) |
| `skills/` | Domain skill templates: `check-supplier-invoice`, `prepare-site-meeting`, `track-contract-amounts` |

## Document types and authority

Authority decides which current source prevails when two disagree; the rule is stated on topic
pages next to both claims, never applied silently.

| Doc type | Authority | Sample document |
|---|---|---|
| `contract-amendment` | 10 | Amendment n°1 ("avenant"): amends the contract, never supersedes it |
| `works-contract` | 9 | Signed works contract |
| `quote` | 8 | Quote ("devis") indices A and B |
| `site-meeting-minutes` | 7 | Site meeting minutes n°3 |
| `delivery-note` | 6 | Scanned delivery note with handwritten reserves |
| `supplier-invoice` | 5 | Builders' merchant invoice |
| `schedule` | 4 | Schedule and purchase tracking ("planning") indice A, and the held-back indice B |
| `supplier-email` | 4 | Window maker's e-mail (delivery postponed; carries the injection canary) |
| `client-email` | 3 | Client's change request |
| `price-study` | 3 | Internal price study (restricted) |
| `site-photo` | 2 | Two site photos |

The schedule and the supplier's e-mail share the same authority on purpose: their window delivery
dates disagree, and the more recent statement prevails until the held-back schedule indice B
supersedes indice A. A delivery note outranks the invoice for the quantities actually delivered.

## Supersession

`doc_number_regex` is anchored at the start of the candidate and the revision is the indice that
follows the number, so only the quote and schedule files (named `DEV-…_indice-A…`,
`PLN-…_indice-B…`) form revision groups; the contract, the amendment, the minutes, the e-mails and
the price study cite those numbers without joining the groups. Expected pairs: quote indice B
supersedes indice A on `full/`; schedule indice B supersedes indice A once `held-back/` is added.

## Topics

Routing scores the compiled English title, headings and text (title 3, heading 2, body 1). The
sources expected to feed each topic in the sample:

| Topic | Expected sources |
|---|---|
| `quotes-contract-and-amendment` | quote indices A and B, contract, amendment |
| `schedule-and-window-delivery` | schedule, window maker's e-mail, minutes, contract (dates); the window delivery contradiction |
| `materials-deliveries-and-invoices` | invoice, delivery note, schedule (purchases sheet), minutes, pallets photo |
| `client-change-requests` | client's e-mail, amendment, quote indice B |
| `payments-deposit-and-retention` | contract, amendment, quotes (deposit), invoice (payment terms) |
| `site-progress-and-meetings` | minutes, schedule (progress), site photos |
| `kitchen-renovation` | quotes, contract, schedule, minutes |

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
| `topics` | list of `{slug, title, path}` | `{slug: kitchen-renovation, title: Kitchen renovation, path: topics/kitchen-renovation.md}` | topic pages present in the release |
| `entity_types` | list of `{key, title, path}` | `{key: material, title: Materials, path: entities/material/index.md}` | entity types with at least one page |

Template rules: no other variables, filters reading files or includes; the frontmatter `name`
stays literal (kebab-case, at most 64 characters, equal to the folder name); the rendered
`description` stays under 1,024 characters and the body under 5,000 words; loops over `topics`
and `entity_types` render correctly when the lists are empty. The documentation lives in this
README because the pack loader accepts only skill folders under `skills/`.
