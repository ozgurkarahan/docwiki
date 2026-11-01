# ADR 0014 — Words and meaning: hybrid retrieval

- Status: Proposed 2026-11-01 (slice S3: embedding deployment and its cost bound). Accepted or
  rejected after the offline pilot (gate A) and the paired evaluation (gate B); completed in
  slice S9.
- Amends (if accepted): [ADR 0001](0001-compiled-wiki-over-vector-index.md), "no vector index by
  default"
- Spec: v1.10

## Context

`answer_context` finds its candidates with the release's lexical index only (`search.db`, FTS5).
The diagnosis of the ten development questions it misses shows that most of them are vocabulary
gaps: the question paraphrases the document, or asks in English about French documents. Words
alone cannot match them; the meaning of the text can.

## Decision (proposed)

1. **One small embedding model in Foundry.** `text-embedding-3-small`, deployment `embed`,
   GlobalStandard (owner decision: no data-residency requirement), 512 dimensions.
2. **Vectors are a file of the immutable release, not a vector database** (to be detailed in
   slice S5): the same rows as the lexical index, embedded at build time with the versioned
   input rule `embed-input-v1`, searched in memory next to the lexical index and fused by rank
   (reciprocal rank fusion).
3. **Lexical stays the floor.** Without the embedding deployment, or when it fails, retrieval is
   lexical and says so; nothing else changes.
4. **The deployment is optional.** `embedCapacity = 0` creates no deployment and sets no
   embedding settings. If gate A fails, the deployment is removed.

## Cost bound

The deployment's capacity is a hard limit enforced by Azure: requests above it are refused
(HTTP 429), never billed. The capacity is therefore the daily cost ceiling:

| Item | Value |
|---|---|
| Capacity (`embedCapacity`, default) | 50 units = 50,000 tokens per minute, 300 requests per minute |
| Tokens per day at most | 50,000 × 1,440 = 72,000,000 |
| List price, input tokens only | 0.02 USD per 1M tokens |
| **Maximum spend per day** | **72 × 0.02 = 1.44 USD** |

Expected spend is far lower: embedding the whole current release (3,852 indexed rows, about
442,000 tokens) costs about 0.009 USD, and a question is a few dozen tokens. Lowering the
capacity lowers the ceiling proportionally (1 unit = 0.0288 USD a day). Slice S9 adds the
ceilings outside Azure (token budget per day, telemetry of embedding tokens) and checks the
observed daily spend against this bound.

The pipeline's client-side limits follow the capacity (`DOCWIKI_EMBED_TPM` = capacity × 1,000,
`DOCWIKI_EMBED_RPM` = capacity × 6 in GlobalStandard), so the job waits instead of being
throttled. The MCP server gets its embedding setting and role only in slice S6.

## Consequences

- One more model deployment to keep current (`versionUpgradeOption: OnceCurrentVersionExpired`,
  retirement checked by `scripts/preflight.py`, which also checks its quota).
- Removing it is explicit: Bicep deployments are incremental, so setting the capacity to 0 stops
  using it but does not delete it; deleting it is a separate, deliberate command.
