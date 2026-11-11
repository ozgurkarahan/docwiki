# ADR 0015 — How agents consume the knowledge base

- Status: **Accepted** 2026-11-11, after the blind results of the
  [knowledge-access study](../../evals/experiments/2026-11-10-knowledge-access.md) (proposed
  2026-11-10)
- Relates to: [ADR 0001](0001-compiled-wiki-over-vector-index.md) (compiled wiki instead of a
  vector index by default), [ADR 0013](0013-index-first-researcher.md) (index-first Researcher),
  [ADR 0014](0014-hybrid-retrieval.md) (rejected at gate A)
- Guide: [How should an agent use a knowledge base?](../knowledge-access.md)

## Context

The question: should an agent consume the documents through retrieval (naive or optimised), the
compiled wiki, retrieval improved with the wiki's indexes, or a router that picks per question?

What we know before the blind runs:

- Three attempts to raise the Researcher's recall by changing retrieval failed their
  pre-registered gates: a meaning search added to the first candidates (gate A, rejected), and a
  fan-out per job site (F3, then F3 v2).
- The wiki ablation ([2026-11-09](../../evals/experiments/2026-11-09-wiki-ablation.md)) removed the
  compiled wiki and kept the agent. On 32 development questions the net effect was **0**
  (4 questions won, 4 lost; 20/32 in both arms). The wiki gave better exact numbers and citations
  and computed cross-job views; raw blocks served superseded details better.
- Compile fidelity shows the wiki holds the printed facts (30/30 compiled) but only 2 of 5
  cross-job syntheses, which matches the remaining multi-hop failures.
- On 32 questions, differences of one or two questions are noise, and the development split was
  seen while building. A decision needs a larger, independent set.

The research behind the arms is summarised in the guide. In short: hybrid search with a reranker
is the strong default; question decomposition helps multi-hop questions; routing is a known
pattern; long context is not a free substitute; agentic search is promising but depends on the
harness.

## Options

Every arm runs on the same frozen release and answer model. The study's file holds the exact
definitions, versions and measures.

| Arm | What it is |
|---|---|
| A0 | Naive retrieval: keyword search over the extracted blocks, top 8, one call |
| A1 | Optimised retrieval: Azure AI Search hybrid (keywords and vectors) with the semantic ranker, query decomposition, one answer call |
| A2 | All public documents in context |
| A3 | The compiled wiki's hubs, topics, views and source summaries in context |
| A8 | Managed agentic retrieval (Azure AI Search knowledge base), same answer call as A1 |
| W1 | Agent and compiled wiki: the production Researcher's definition |
| R1 | The same agent on raw blocks only (no wiki) |
| W2 | Agent and wiki with v2 instructions (plan sub-questions, search each, join), a dense lane and superseded revisions shown next to current ones |
| R2 | The same v2 instructions and dense lane on raw blocks |
| W2-high | W2 with high reasoning effort |
| Router | A cheap model labels each question (at most 3 classes) and one arm answers; table fitted on development questions only and frozen before the blind runs |

W1, R1, W2 and R2 form a 2 x 2 (wiki or raw, production or v2 instructions) that separates the
effect of the wiki from the effect of v2.

## Decision

**No single approach wins. For this corpus, the recommended way to consume the documents is long
context (A2); the production Researcher (W1, agent on the compiled wiki) stays, because it is
tied with it and has the highest accuracy.**

Blind results (120 questions, 3 runs per arm, mean single-run accuracy):

| Arm | Accuracy [95 % CI] | Claims supported | Cost per correct answer |
|---|---|---|---|
| W1 agent and wiki | 81.9 % [76.1, 87.2] | 79.1 % | $0.111 |
| W2-high | 80.0 % | 80.1 % | $0.160 |
| W2 | 79.4 % | 79.9 % | $0.126 |
| A2 all documents in context | 78.3 % [71.1, 85.0] | 81.5 % | $0.043 |
| A1 optimised retrieval | 77.8 % [71.1, 83.9] | 69.2 % | $0.053 |
| Router | 77.2 % [70.6, 83.6] | - | $0.095 |
| R2 / R1 agent on raw blocks | 76.7 % / 75.8 % | 80.1 % / 76.9 % | $0.114 / $0.095 |
| A3 wiki in context | 73.1 % | 78.1 % | $0.134 |
| A8 managed agentic retrieval | 72.2 % | 67.8 % | $0.042 |
| A0 naive retrieval | 66.7 % [58.6, 74.4] | 63.4 % | $0.037 |

Applying the pre-registered rule:

1. No arm beats every other significantly. Only A0 is worse than W1 (Holm p = 0.005).
2. The set within 5 points of the best is {W1, W2-high, W2, A2, A1, Router}. Ordered by claim
   support (the first tie-break), A2 leads with 81.5 %, so A2 is the recommended arm.
3. No arm leaked a restricted value or followed the planted injection.

What the 2 x 2 says: the compiled wiki adds +4.4 points inside the same agent (not significant
after correction, raw p = 0.031); the v2 instructions and dense lane add nothing (-0.8). The router
does not beat its best arm, while an oracle that picks the best arm per question reaches 95 %: the
approaches fail on different questions, but not in a way a question classifier can predict.

Where the wiki earns its cost: superseded revisions (79 % for the wiki agents against 27 to 55 %
for every retrieval and long-context arm), tables (87 %), contradictions and numeric exactness.
Where it does not: lookups that one search finds, and abstention (81 %, lower than retrieval).

The rule is fixed in the study before any blind run: the primary measure is mean single-run
accuracy over 3 runs on 120 blind questions; the recommended arm must beat every other arm by a
significant difference (Holm-adjusted paired permutation tests), otherwise the arms within 5
points of the best form a set that is ordered by claim support, numeric exactness, citation
overlap and cost per correct answer, and an unordered set is published as unresolved. A
restricted-value leak or an injection success excludes an arm.

## Consequences

- **Production does not change.** The Researcher keeps the definition of ADR 0013 (W1): it is in
  the recommended set, has the highest accuracy, and DocWiki's purpose is to show a cited wiki
  that agents work inside. Switching the demo to long context would hide the pattern it shows and
  would not scale past a corpus that fits in one prompt.
- **ADR 0001 is refined, not reversed.** The compiled wiki is worth it for revisions, tables,
  contradictions and audit; it is not a better general retriever. The guide now says so, with
  long context or hybrid retrieval as the baseline to beat on other corpora.
- **No router, no high reasoning effort, no v2 instructions in production.** None beat W1 here.
  The evaluation-only MCP flags (pin, dense lane, revision companions) stay off by default.
- **Next improvements target what the wiki agent misses:** abstention (it answers when it should
  say "not found") and the cross-site syntheses that compile fidelity found missing.
- **Robustness finding:** the MCP server with the dense lane hung under concurrent load (24 agent
  turns ended after its proxy cancelled requests at 600 s, all recovered on re-ask). Any
  production use of the dense lane needs a load test first.
- **The evaluation stack is temporary.** The variant agents, the evaluation MCP apps, the Azure
  AI Search service and the extra model deployment are removed after this ADR; the commands are
  in [`agents/README.md`](../../agents/README.md). They never called production.

## Links

- Study and freeze addendum: [`evals/experiments/2026-11-10-knowledge-access.md`](../../evals/experiments/2026-11-10-knowledge-access.md)
- Previous result: [`evals/experiments/2026-11-09-wiki-ablation.md`](../../evals/experiments/2026-11-09-wiki-ablation.md)
- Failed gates: [A](../../evals/experiments/2026-11-01-gate-a.md),
  [F3](../../evals/experiments/2026-11-01-f3-coverage.md),
  [F3 v2](../../evals/experiments/2026-11-01-f3v2-fanout.md)
- Guide: [`docs/knowledge-access.md`](../knowledge-access.md)
