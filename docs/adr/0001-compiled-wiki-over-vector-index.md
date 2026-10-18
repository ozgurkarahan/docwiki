# ADR 0001 — A compiled wiki instead of a vector index by default

- Status: Accepted (spec v1)
- Deciders: project owner, reviewed by three independent model reviewers (Claude Opus 5.5,
  GPT-6 Astra, Gemini 4 Argon)

## Context

Retrieval-augmented generation (RAG) re-discovers knowledge from raw chunks at every question.
For operational document sets (manuals, procedures, bulletins, logs, spreadsheets) the hard
questions are cross-document: which revision is current, which documents contradict each other,
how a log, a spreadsheet and a report combine. The "LLM wiki" pattern compiles that knowledge once
into interlinked pages that humans and agents can navigate.

A managed vector/agentic-retrieval service would add a fixed idle cost (the free tier cannot use
managed identity, which cited retrieval requires) and a second source of truth.

## Decision

- DocWiki compiles documents into a wiki with indexes, entity and topic pages, a glossary and a
  log, plus a SQLite FTS5 index over page sections **and** raw extracted blocks.
- The Researcher agent navigates through MCP tools (search, read, links, evidence, table queries).
- A managed retrieval service (for example Foundry IQ / Azure AI Search) is a documented optional
  extension for very large corpora, not the default.

## Consequences

- Near-zero idle cost; one source of truth; answers carry page/row citations.
- Compilation costs tokens up front; the evaluation compares DocWiki against naive RAG and
  long-context baselines on the same questions and publishes the trade-off honestly.
- Searching raw blocks keeps answer-bearing details reachable even when compilation omits them.
