# ADR 0005 — Skills generated only from reviewed templates

- Status: Accepted (spec v1)

## Context

DocWiki ships Agent Skills with every wiki so that any agent (Foundry, GitHub Copilot, Claude Code,
Codex) knows how to navigate, cite and research. Skills are instructions. If skills were written
by a model from document content, a malicious document could plant persistent instructions in
every agent that reads the wiki.

## Decision

- Skills are rendered from reviewed Jinja2 templates with strict undefined variables, filled only
  with validated catalog values (counts, paths, entity types, topic titles from the domain pack).
- One canonical source is projected identically into `.agents/skills`, `.claude/skills` and
  `.github/skills`; a quality gate verifies identity and limits.
- A canary test proves that injected document text never reaches `AGENTS.md`, skills or indexes.
- Skills are also served on demand by the MCP tool `get_skill`; Foundry Skills (preview) is opt-in.

## Consequences

- Skills are safe to distribute and portable across agent clients.
- Domain skills are limited to a few, each with an evaluation task.
