# ADR 0006 — Immutable releases and an atomic pointer

- Status: Accepted (spec v1)

## Context

Agents and humans must never read a half-built wiki. Document pipelines often keep their state in a
database and coordinate through a message bus, which adds operations work and fixed cost.

## Decision

- State lives in Blob Storage: per-source state shards with ETag-conditional writes,
  content-addressed stage artifacts, run reports and proposals. No database, no message bus.
- Each run builds a complete release (`releases/<id>/`: wiki, evidence, site, catalog, search
  index, manifest), validates it with the quality gates, and only then swaps `current.json` with
  an If-Match conditional write. The MCP server and portal follow the pointer.
- Blob versioning and soft delete are enabled; the last 10 releases are kept; rollback is a
  pointer change.

## Consequences

- Readers always see a consistent, validated snapshot; failed runs leave the current release intact.
- Storage grows with releases; retention bounds it.
