# Domain pack `wind-om` (fictional sample)

Operations and maintenance of the fictional Quellmoor Ridge Wind Farm run by Contoso Renewables.
Every name comes from `samples/fiction/bible.yaml`; the sample corpus is `samples/corpus`.
The pack follows `docs/spec/domain-and-corpus.md` section 1 and loads with
`docwiki.domain.load_pack("domains/wind-om")`.

| File | Content |
|---|---|
| `pack.yaml` | Pack identity, languages (en, fr, de), wiki title, fictional banner |
| `taxonomy.yaml` | 12 categories and 30 document types with authority 1-10; every sample file matches a `filename_regex`; `text_regex` rules match only the title line of their own type |
| `entities.yaml` | 9 entity types; 101 registry entries (site, 12 turbines, substation, met mast, O&M building, components, spare parts, products, alarm and status codes, procedures, bulletins, organisations) with en/fr/de aliases |
| `topics.yaml` | 10 topics with multilingual keywords |
| `glossary.yaml` | Generic industry terms with French and German synonyms; site-specific acronyms are left to the documents that define them |
| `sensitivity.yaml` | `public` by default; anything under a `restricted/` folder (and the rate card type) is `restricted` |
| `supersession.yaml` | Document numbers at the start of the file name or text (SOP, WI, SPL, SB-LWS, LWS-MM), letter revisions A-H, explicit "supersedes/replaces" references; "amends" is not a supersession |
| `resolution.yaml` | Contradictions: authority first, then recency |
| `hints.md` | Reviewed compile hints (no document text) |
| `skills/` | Domain skill templates: `troubleshoot-alarm`, `prepare-maintenance-task`, `audit-readiness` |

## Skill template variables

The engine renders `skills/<skill>/SKILL.md.j2` with Jinja2 (`StrictUndefined`, escaped values)
and **only** the variables below. Values come from the validated release catalog and this pack,
never from document text. Paths are relative to the wiki root and use `/`.

| Variable | Type | Example | Source |
|---|---|---|---|
| `wiki_title` | string | `Quellmoor Ridge O&M wiki` | `pack.yaml` `wiki_title` |
| `paths.index` | string | `index.md` | wiki layout |
| `paths.glossary` | string | `glossary.md` | wiki layout |
| `paths.log` | string | `log.md` | wiki layout |
| `paths.sources_index` | string | `sources/index.md` | wiki layout |
| `paths.entities_index` | string | `entities/index.md` | wiki layout |
| `paths.topics_index` | string | `topics/index.md` | wiki layout |
| `topics` | list of `{slug, title, path}` | `{slug: gearbox-lubrication, title: Gearbox lubrication and oil changes, path: topics/gearbox-lubrication.md}` | topic pages present in the release |
| `entity_types` | list of `{key, title, path}` | `{key: alarm-code, title: Alarm codes, path: entities/alarm-code/index.md}` | entity types with at least one page |

Template rules: no other variables, filters reading files or includes; the frontmatter `name`
stays literal (kebab-case, at most 64 characters, equal to the folder name); the rendered
`description` stays under 1,024 characters and the body under 5,000 words; loops over `topics`
and `entity_types` render correctly when the lists are empty. The documentation lives in this
README because the pack loader accepts only skill folders under `skills/`.
