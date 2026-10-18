# Domain pack `it-runbooks` (fictional sample)

A tiny second pack proving that DocWiki is not tied to wind farms: runbooks, a failover
procedure, an on-call handbook, a postmortem and a service catalog of the fictional IT platform
team of Relecloud (`samples/corpus/it-runbooks`). It loads with
`docwiki.domain.load_pack("domains/it-runbooks")`; documents are `internal` by default.

The skill template `skills/respond-to-alert/SKILL.md.j2` uses the same variables as the
`wind-om` pack (see `domains/wind-om/README.md`): `wiki_title`, `paths.index`, `paths.glossary`,
`paths.log`, `paths.sources_index`, `paths.entities_index`, `paths.topics_index`, `topics` (list of
`{slug, title, path}`) and `entity_types` (list of `{key, title, path}`).
