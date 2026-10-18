# ADR 0002 — Batch compilation in an ACA Job; agents as the control plane

- Status: Accepted (spec v1)

## Context

Compiling dozens to thousands of documents takes minutes to hours. Foundry hosted agents run
conversational requests in per-session sandboxes; a foreground request is not resumed after a
crash or redeploy, and the resilient background mode is in preview. Foundry routines can schedule
an agent but cannot react to new blobs.

## Decision

- The pipeline runs as an **Azure Container Apps Job**, woken by a storage queue (Event Grid on new
  or deleted blobs, or the Librarian's `ingest_start`), with KEDA capped at one execution, a
  renewable blob lease, level-triggered diffing, and a scheduled reconcile job as a safety net.
- The **Librarian** is a Foundry **prompt agent** that operates the pipeline through MCP tools:
  start ingests, read run status and quality gates, diagnose quarantined documents, recompile with
  hints, decide proposals and write health reports. Mutating tools require human approval.
- Stages are idempotent and content-addressed; resume never depends on workflow checkpoints.
  Microsoft Agent Framework workflows orchestrate fan-out and telemetry.

## Consequences

- Robust to bursts, crashes and lost messages; no long-running agent requests.
- The "transform agent" is honest about its role: it orchestrates and repairs, the job computes.
- Human review never blocks a running job: it happens through proposals between runs.
