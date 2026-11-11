# How the knowledge-access study was done

Companion to [the study](../2026-11-10-knowledge-access.md) and
[ADR 0015](../../../docs/adr/0015-knowledge-access.md). It records the approach, the research
behind the arms, every test that guarded the result, what the development runs got wrong, and
the limits. Use it as a template for the same question on another corpus.

## 1. The approach, step by step

| Step | What was done | Why |
|---|---|---|
| 1. Start from the evidence | Three retrieval changes had failed their pre-registered gates (gate A, F3, F3 v2); the wiki ablation gave net 0 on 32 development questions; compile fidelity found 2 of 5 cross-site syntheses. | Know what is already measured before buying more measurements. |
| 2. Research | A research agent surveyed 2024 to 2026 work on retrieval, compiled knowledge, agents, routing and long context (section 2). | Pick arms that represent the state of the art, not only DocWiki's own ideas. |
| 3. Plan and adversarial review | A first plan was reviewed by a separate critic agent. Changes it forced: a 2 x 2 design (wiki or raw, production or v2 instructions) to separate the effects; the mean of 3 runs as the measure; Holm adjustment; a 5-point practical margin; a safety gate; a blind LLM judge; an evaluation stack isolated from production; a freeze before the blind runs. | A plan reviewed only by its author keeps its blind spots. |
| 4. Independent blind questions | A separate agent session wrote 120 questions from the public documents only, without the code, the wiki, the development questions or any result. Its sha256 was committed (#70) before any blind run; the file stayed outside the repository until the results were written. | The builder must not be able to tune on the questions that decide. |
| 5. Pre-registration | Arms, measures, decision rule, margin and safety gate committed in the study file (#70) before any blind run. | The rule cannot bend to the result. |
| 6. Build in parallel | Five lanes in separate worktrees, each by a different model, one pull request each: comparison, router and judge (#71); MCP v2 features (#72); evaluation stack and agent variants (#73); Azure AI Search arms (#74); the wiki in context (#75). Changes were reviewed by a separate review agent before merge. | Speed, and independent implementations reviewed by someone else. |
| 7. Development runs | Every arm ran the 32 development questions 3 times. Four defects surfaced and were fixed before freezing (#76 to #79, section 3). | Find broken plumbing on questions that do not decide anything. |
| 8. Router and freeze | The router table was fitted on development runs only; versions, image digest, release, vectors, agent definitions and the router table were frozen (#80, #81) before any blind score was read. | Nothing changes after this point. |
| 9. Blind runs | 11 arms x 120 questions x 3 runs = 3,960 answers. 45 answers that failed for infrastructure reasons were asked again once, under the rule written in #81; none failed twice. | Infrastructure failures are not wrong answers; the rule for them was fixed in advance. |
| 10. Analysis | `evals/compare.py` (bootstrap intervals clustered by question, paired permutation tests with Holm adjustment, the 2 x 2 effects, the decision rule), the blind judge on every answer, the router and the oracle. | Apply the rule mechanically, then explain. |
| 11. Publish and decide | Results, blind questions, aggregates, this file, ADR 0015 and the guide (#82 and after). The owner then made the product decision (ADR 0015). | Publish whatever the result; keep the rule's outcome and the product decision apart. |

## 2. The research, and what the blind runs said about it

Survey of 2026-11-10. Primary sources are linked; *(secondary)* marks blogs, vendor figures or
aggregations of several papers, to be read as direction only. The last column is DocWiki's blind
result, on one 39-document corpus.

| Claim from the literature | Source | Arm that tested it | Blind outcome on this corpus |
|---|---|---|---|
| Hybrid keyword and vector search with a reranker is the strongest default; failed top-20 retrievals fell from 5.7 % to 1.9 % | [Contextual retrieval](https://www.anthropic.com/research/contextual-retrieval) (2024); Azure query rewriting and semantic ranker, up to +22 NDCG@3 ([vendor](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/raising-the-bar-for-rag-excellence-query-rewriting-and-new-semantic-ranker/4302729)) | A1 against A0 | **Confirmed in direction**: 77.8 % against 66.7 % (+11 points), best citation overlap |
| Splitting a question into sub-questions, retrieving each and joining helps multi-hop questions (MRR@10 +36.7 %) | [arXiv:2507.00355](https://arxiv.org/abs/2507.00355) | A1 (decomposition); W2 and R2 (v2 instructions) | **Mixed**: helps one-shot retrieval (multi-hop 79 % against 65 %); adds nothing inside the agent (v2 effect -0.8 points, multi-hop W2 80 % against W1 83 %) |
| Routing per question improves accuracy and cost | [Adaptive-RAG](https://aclanthology.org/2024.naacl-long.389) (NAACL 2024); [RouteLLM](https://arxiv.org/abs/2406.18665) | Router | **Not confirmed**: 77.2 %, below its best arm; an oracle would reach 95 %, so the headroom exists but a three-class classifier cannot find it |
| Long context can beat retrieval but costs more; models read long inputs unevenly | [arXiv:2407.16833](https://arxiv.org/abs/2407.16833); [Context rot](https://www.trychroma.com/research/context-rot) (2025) | A2 (35,000 tokens), A3 (120,000 tokens) | **Partly**: at 35,000 tokens no degradation was visible and A2 was the cheapest arm per correct answer; at 120,000 tokens of summaries A3 dropped to 73.1 % (content and length are confounded) |
| Agentic, grep-style search can beat vectors on exact lookups, depending on the harness | [arXiv:2605.15184](https://arxiv.org/abs/2605.15184) (very recent) | R1, R2 against A1; the dense lane in v2 | **No difference**: agents on raw blocks 75.8 % and 76.7 % against 77.8 % for A1; adding a dense lane to the agent changed nothing |
| Managed agentic retrieval plans sub-queries and reranks | [Azure documentation](https://learn.microsoft.com/azure/search/agentic-retrieval-overview) | A8 | **Not better**: 72.2 %, below A1 on the same index |
| A compiled layer (wiki or graph) pays on relational and corpus-wide questions, less on lookups | [GraphRAG](https://arxiv.org/abs/2404.16130); [LLM wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f); *(secondary)* graph benchmarks | W1 against R1, W2 against R2 | **Direction confirmed, not significant**: wiki effect +4.4 points (Holm p = 0.31); tables +12 points for both wiki agents; best numeric exactness (W1 87.7 %); single-hop lookups no better |
| Keep old facts with their validity period instead of overwriting them | [Zep / Graphiti](https://arxiv.org/abs/2501.13956) | W2 (superseded revisions shown next to current ones) | **Not confirmed as built**: supersession W2 67 % against W1 79 %; the production wiki's revision status already did the work |
| Higher reasoning effort helps hard questions | general practice | W2-high | **No gain**: 80.0 % against 79.4 % for W2, 44 % more cost per correct answer |
| Small evaluation sets mislead; report intervals | McNemar sample-size guidance *(secondary)* | the whole design | **Confirmed strongly** (section 4): the development ranking was reversed by the blind set |

Other work surveyed and not tested here: late chunking ([arXiv:2409.04701](https://arxiv.org/abs/2409.04701)),
HyDE ([arXiv:2212.10496](https://arxiv.org/abs/2212.10496)), RAPTOR
([arXiv:2401.18059](https://arxiv.org/abs/2401.18059)), reasoning-intensive retrieval (BRIGHT,
[arXiv:2407.12883](https://arxiv.org/abs/2407.12883)), multi-hop benchmarks (MultiHop-RAG,
[arXiv:2401.15391](https://arxiv.org/abs/2401.15391)), lighter graph systems (LightRAG,
HippoRAG 2, LazyGraphRAG; their published comparisons mix setups *(secondary)*), and hosted file
search. Several 2026 analyses discourage graph indexing below about 10,000 documents unless the
questions are heavily relational *(secondary)*; DocWiki has 39.

## 3. Tests and checks

| Check | What it guarded | Result |
|---|---|---|
| Offline unit tests | Comparison statistics, decision rule, router, judge, registry, search and wiki-in-context arms, MCP v2 features and their concurrency, agent variants, Bicep | 123 tests in the new test files, plus additions to existing ones; full suite 3,341 tests, no network |
| CI on every pull request | Lint, tests, Bicep build, secret scan, site build, CodeQL | Green on #70 to #82 |
| Leak guard, strict | No private names, identifiers or local paths in what is published, including the blind set | Pass |
| Code review by a separate agent | The lanes' changes, before merge | Found a lock held too long and a too-broad `not_found` rule in #72, fixed before merge |
| Smoke tests | Two development questions on each of the five agent variants before the paid runs, to check identities, roles and citations | No errors; one variant re-run after a configuration fix |
| Development runs (3 per arm) | Plumbing, before anything decides | Four defects found and fixed: the dense query vector was not normalised, so every dense call returned unavailable (#76, 12 runs discarded); agent rate limits were scored as wrong answers (#77); the judge ran out of output tokens (#78); the judge penalised formats instead of substance (#79) |
| Judge validation | The LLM judge agrees with the deterministic scorer | 27/32 and 26/32 on two development runs; every disagreement a judge "partial" on a missing key fact |
| Blind set integrity | The questions that decide are the ones fingerprinted before the runs | `author.py --check` 120/120; sha256 matches the value committed in #70 |
| Freeze | Nothing changes between dev and blind | Image digest, release, vectors, agent definition hashes and router table committed before the blind runs |
| Production isolation | The demo is never touched | Separate MCP apps, agents and identities; production revisions checked unchanged after provisioning |
| Re-ask rule | Infrastructure failures are not scored as wrong | 45 re-asked once, all answered; counts published per arm |
| Safety gate | No arm leaks or obeys an injection | 0 restricted values, 0 injection successes in 3,960 answers |

## 4. What the development runs got wrong

Mean of 3 runs on the 32 development questions, against the blind result:

| Arm | Development | Blind |
|---|---|---|
| W2-high | **77.1 %** (best) | 80.0 % |
| W2 | 74.0 % | 79.4 % |
| R2 | 72.9 % | 76.7 % |
| A3 | 65.6 % | 73.1 % |
| R1 | 64.6 % | 75.8 % |
| A2 | 63.5 % | 78.3 % |
| A0, A1 | 61.5 % | 66.7 %, 77.8 % |
| A8 | 60.4 % | 72.2 % |
| W1 | 59.4 % (last) | **81.9 %** (first) |

On development questions, the v2 instructions and high reasoning effort looked like an 18-point
gain over the production agent. On independent blind questions the order reversed: the production
agent came first and v2 added nothing. The v2 instructions were written while looking at the
development failures, and 32 questions cannot separate arms a few questions apart. Had the
decision been taken on the development split, DocWiki would have shipped a more expensive agent
that is not better. This is the strongest argument for a blind set written by someone else.

## 5. Limits

- **One corpus**: 39 public, fictional documents generated for this demo (about 35,000 tokens),
  one domain, French with an English mirror. Long context wins partly because everything fits.
- **One model family** answers, judges and runs the router, and the blind questions were also
  written by an AI agent. A shared bias cannot be ruled out.
- **120 questions** detect differences of about 8 points; smaller gaps, including every gap
  among the six arms of the recommended set, are not resolved.
- **Instructions**: W1 and R1 use the production instructions, written for the wiki; the v2
  instructions are tool-neutral.
- **Infrastructure**: agents and one-shot arms answered through two deployments of the same
  model, so latencies are compared within each group only. Prices are unverified placeholders.
- **The router** was fitted on 32 questions; a larger labelled set might route better.

## 6. Lessons to reuse

1. Write the arms, measures and decision rule before the run that decides, and keep the rule's
   outcome apart from the product decision.
2. Have someone who cannot see the system write at least 100 confirmation questions; fingerprint
   them before the runs.
3. Run every arm at least 3 times and report intervals.
4. Use the development split to find broken plumbing, not to pick a winner.
5. Separate infrastructure failures from wrong answers, with a rule fixed in advance.
6. Measure an oracle before building a router.
7. Validate an LLM judge against a deterministic scorer, and show both.
8. Run the evaluation on an isolated stack, never on production.
