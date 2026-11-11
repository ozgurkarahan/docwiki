# Knowledge access - how an agent should use the knowledge base (pre-registered)

Which way should an agent consume a document knowledge base: retrieval (naive or optimised), the
compiled LLM wiki, retrieval improved with the wiki's indexes, or a router that chooses per
question? This file states the arms, the measures and the decision rule **before** any blind run;
an addendum freezes the arms (definitions, image digests, release, router table) before the blind
runs start, and the results are appended below the line, whatever they show. Research summary and
the reasons for each arm: `docs/adr/0015-knowledge-access.md` (written with the results).

## Questions

- **Blind test set**: 120 questions (`split: blind-test`, ids `t001` to `t120`) written on
  2026-11-10 by an independent agent session from the public documents only (`probes.py --list`
  and `--dump`, the golden README, the domain glossary), without access to the code, the compiled
  wiki, the dev split, results or experiments. Every record passes `author.py --check --file`
  (120/120). Categories: multi-hop 28, single-hop 23, table 20, supersession 11, abstain 9,
  numeric 9, contradiction 8, OCR 5, skill 5, injection 2; 63 English, 57 French. No restricted
  question: the author could not read restricted documents; restricted exclusion is still checked
  on every answer. Fingerprint: [`blind-test.sha256`](blind-test.sha256). The file stays outside
  the repository until the results are published; the builder sees aggregates only.
- **Dev split** (`evals/golden/dev.jsonl`, 32 questions): development and router fitting only,
  never confirmatory.

## Arms

End-to-end tournament, every arm on the same frozen release and the same answer model (a separate
`smart-eval` deployment of the `smart` model, so the public demo is never touched):

| Arm | System | What it is |
|---|---|---|
| A0 | `baseline-rag` | naive retrieval: BM25 top 8 chunks, one call |
| A1 | `rag-plus` | optimised retrieval: Azure AI Search hybrid (BM25 + vectors) with the semantic ranker over the extracted blocks, query decomposition by `fast`, one answer call |
| A8 | `foundry-iq` | managed agentic retrieval (Azure AI Search knowledge base, extractive, pinned effort), same answer call as A1 |
| A2 | `baseline-long-context` | every public document in context |
| A3 | `wiki-long-context` | the compiled wiki's hubs, topics, views and source summaries in context |
| W1 | agent + wiki | the production Researcher's definition, on an evaluation MCP app |
| R1 | agent + raw blocks | same definition, `DOCWIKI_MCP_WIKI_ABLATION=raw` |
| W2 | agent + wiki + v2 | v2 instructions (plan sub-questions, search each, join) + hybrid dense lane + superseded revisions surfaced with current ones |
| R2 | agent + raw + v2 | the same v2 instructions and dense lane on raw blocks |
| W2-high | W2 with high reasoning effort | the "decision model" variant |
| R | router | `fast` classifies the question (at most 3 classes) and picks one arm; table fitted on dev only, frozen before the blind runs; its cost and latency include the classifier |

Controlled ablation inside the tournament: the 2 x 2 {wiki, raw} x {production instructions, v2}
(W1, R1, W2, R2) attributes effects to the wiki and to v2.

## Measures and decision rule (fixed now)

1. **Primary estimand**: mean single-run answer accuracy on the blind set over **3 repetitions**
   (every run kept), with 95 % confidence intervals by question-clustered bootstrap. Majority of 3
   is reported as a stability measure only.
2. **Comparison family** (Holm-adjusted paired permutation tests on per-question mean accuracy):
   every arm against W1; the best arm against the second; the two factors of the 2 x 2.
3. **Practical margin**: 5 points of accuracy. The recommended arm is the best one if it beats every
   other arm by a significant difference; otherwise the arms within 5 points of the best that are
   not significantly worse form a set, and within that set the order is: claim support judged by
   the LLM judge, numeric exactness, citation overlap, then cost per correct answer. If the set
   cannot be ordered that way, the result is published as unresolved.
4. **Safety gate**: any restricted value or injection success in any run excludes the arm.
5. **Secondary**: required-item coverage, numeric exactness, citation overlap and recall, abstention,
   per-category accuracy, latency p50/p95 (cold and warm for MCP apps), tool calls, cost per
   question and per correct answer (retrieval and indexing costs included where known).
6. **LLM judge** (blind to the arm, structured output, `smart-eval`): correct / partial / wrong,
   value-to-chantier assignment, contradictions, each claim supported by a cited passage. Validated
   on dev against a manual reading before the blind runs; reported next to the deterministic
   scores, never instead of them.

## Known limits (stated before the run)

One small fictional corpus (39 public documents), one model family: the conclusion holds for this
corpus, model and workload; general guidance is labelled as hypothesis. W1 and R1 use instructions
written for the wiki; v2 instructions are tool-neutral. A1 and A8 depend on a preview Azure
service; if A8 cannot run, it is published as not measured.

## Freeze addendum, part 1 (2026-11-10, before any blind run)

Code: `public/main` at `e8bbd14` (every arm merged: #70 to #79). Nothing below changes after this
commit; the blind results are under embargo until every arm has run.

- **Release** `20261027T222241Z-f4e7ba11` (the served release of 2026-10-27), pinned on every
  evaluation MCP app (`DOCWIKI_MCP_PIN_RELEASE`); the one-shot arms read the same corpus manifest
  and the same release folder.
- **Evaluation MCP apps** `wiki`, `raw`, `wiki2`, `raw2` on one image digest
  (`docwiki/mcp-eval@sha256:b7df12e8...6b02`, built from `807bdb2`, which includes the dense
  query normalisation fix #76); production apps and the production Researcher are not used.
- **Vectors** of the dense lane: `text-embedding-3-small`, 512 dimensions, `embed-input-v1`,
  3,852 rows, artifact sha256 `ffb888ab25cd6920...3119b2`; query embeddings through the `embed`
  deployment (capacity 500).
- **Agents** (version 1 each, definition sha256): `docwiki-researcher-w1` `4fc8878d...`,
  `-r1` `68b9b1fe...`, `-w2` `e9481a76...`, `-r2` `56941a37...`, `-w2high` `92f97ee5...`. W1 and R1
  use the production instructions; W2, R2 and W2-high use `agents/variants/v2/instructions.md`;
  W2-high has reasoning effort `high`, the others the production default.
- **One-shot arms**: `baseline-rag` (`baseline-rag-v1`), `baseline-long-context`
  (`baseline-long-context-v1`, 120,000-token budget), `wiki-long-context`
  (`wiki-long-context-v1`, 120,000 tokens: hubs, views and topics, topics truncated
  proportionally, sources and entities excluded), `rag-plus` (`rag-plus-decompose-v1`, Azure AI
  Search `2026-04-01`, hybrid + semantic ranker, top 8), `foundry-iq` (knowledge base API
  `2026-08-01-preview`, planner `gpt-5.4-mini`, reasoning effort `low`, extractive, top 8).
- **Model**: every arm answers with `gpt-5.5` version `2026-04-24`. Deviation from the plan: no
  separate `smart-eval` deployment could be created (the subscription's GlobalStandard quota for
  this model is used by `smart`). Agents answer through `smart` (GlobalStandard, 1M tokens per
  minute, shared with the public demo, whose traffic is small); the one-shot arms answer through
  `smart-dz` (DataZoneStandard, same model and version, 333k tokens per minute) so that the
  long-context arms do not throttle the agents. Latencies are therefore compared within each
  group, not across groups.
- **Retries**: a model rate limit (HTTP 429) inside an agent turn is retried up to 8 times with
  back-off and the wait is removed from the latency (#77); one-shot calls use the `docwiki.llm`
  retry policy (`DOCWIKI_LLM_MAX_RETRIES=10` for the blind runs). A question that still fails is
  scored 0 and reported with its error.
- **Metrics** `evals-metrics-v1`; abstention reported in v1 and v2 (`evals/compare.py`); **judge**
  `knowledge-access-judge-v2` (`smart-dz`, 3,000 output tokens), validated on two dev runs
  (agreement with deterministic accuracy 27/32 and 26/32, every disagreement a judge "partial"
  on a missing key fact).
- **Router**: classifier `knowledge-access-router-v1` (`fast`, three classes); the routing table
  is fitted on dev only and committed in part 2 of this addendum before it is applied to the blind
  results. Blind classes (counts only): aggregate-or-cross 40, lookup 52, revision-or-absent 28.
- **Blind runs**: 3 repetitions of every arm (`--run-label r1..r3`), per-question details written
  outside the repository; only aggregates are committed until the blind file is published.
## Freeze addendum, part 2 (2026-11-10, before any blind accuracy is read)

Written after the dev runs of every arm and while the blind runs are in progress; the builder has
read only the error counts of the blind result files, never a score.

- **Router table** fitted on dev only (`evals/router.py fit`, three repetitions of every arm,
  leave-one-out estimate 78.1 % on dev): `aggregate-or-cross` -> W2, `lookup` -> A2,
  `revision-or-absent` -> R2. Frozen file:
  [`2026-11-10-knowledge-access/router-table.json`](2026-11-10-knowledge-access/router-table.json)
  (hash of its inputs `0552d749...51ff2`). The oracle router (best arm per question, an upper
  bound) is reported next to it, labelled as such.
- **Infrastructure failures are re-asked.** Some blind questions failed before any answer because
  the local Azure CLI credential timed out under parallel load (`CredentialUnavailableError`,
  `LlmAuthError` on token acquisition): 20 of the first 5,400 planned answers. Such questions
  (credential, HTTP 429 after the retries, HTTP 5xx, network timeouts; never a wrong or empty
  answer) are asked again once with the same frozen arm, and the new record replaces the failed
  one; the count of re-asked questions per arm is published. A question that fails again is
  scored 0.
---

## Results (blind runs of 2026-11-10 and 2026-11-11)

All 11 arms ran the 120 blind questions 3 times (3,960 answers) on the frozen release. 45 answers
first failed for infrastructure reasons and were asked again once under the rule of part 2:
credential timeouts of the local Azure CLI (A2, A3, R1, W1), and 24 turns that Foundry ended with
`tool_user_error` because the `wiki2` evaluation MCP app (shared by W2 and W2-high, run at the
same time) stopped answering under load: its proxy cancelled requests after 600 s. None failed
again. The blind questions are now published:
[`blind-test.jsonl`](2026-11-10-knowledge-access/blind-test.jsonl) (sha256 matches
[`blind-test.sha256`](blind-test.sha256)). Reports:
[`compare-blind.md`](2026-11-10-knowledge-access/compare-blind.md) (abstention v1, primary),
[`compare-blind-abst-v2.md`](2026-11-10-knowledge-access/compare-blind-abst-v2.md),
[`judge-aggregates.json`](2026-11-10-knowledge-access/judge-aggregates.json), per-run aggregates in
[`results/`](2026-11-10-knowledge-access/results/).

| Arm | Accuracy (mean of 3 runs, 95 % CI) | Judge: claims supported | Judge: wrong | Numeric exactness | Citation overlap | Latency p50 | Cost per correct answer |
|---|---|---|---|---|---|---|---|
| W1 agent + wiki | **81.9 %** [76.1, 87.2] | 79.1 % | 3.9 % | 87.7 % | 81.2 % | 19.7 s | $0.111 |
| W2-high agent + wiki v2, high effort | 80.0 % [73.9, 85.8] | 80.1 % | 2.5 % | 80.2 % | 74.8 % | 28.9 s | $0.160 |
| W2 agent + wiki v2 | 79.4 % [72.8, 85.6] | 79.9 % | 1.9 % | 84.0 % | 76.9 % | 22.3 s | $0.126 |
| A2 all documents in context | 78.3 % [71.1, 85.0] | **81.5 %** | **0.6 %** | 77.8 % | 84.3 % | 37.6 s | $0.043 |
| A1 optimised RAG (hybrid + semantic ranker + decomposition) | 77.8 % [71.1, 83.9] | 69.2 % | 2.8 % | 82.7 % | 93.7 % | 25.4 s | $0.053 |
| R router (fitted on dev) | 77.2 % [70.6, 83.6] | - | - | 76.5 % | 80.8 % | 36.8 s | $0.095 |
| R2 agent + raw blocks v2 | 76.7 % [70.0, 82.8] | 80.1 % | 2.5 % | 77.8 % | 77.3 % | 20.7 s | $0.114 |
| R1 agent + raw blocks | 75.8 % [68.6, 82.5] | 76.9 % | 3.3 % | 80.2 % | 79.5 % | 18.2 s | $0.095 |
| A3 the wiki in context | 73.1 % [65.3, 80.6] | 78.1 % | 8.9 % | 81.5 % | 87.7 % | 119.8 s | $0.134 |
| A8 managed agentic retrieval (Foundry IQ) | 72.2 % [64.7, 79.7] | 67.8 % | 7.2 % | 81.5 % | 93.8 % | 24.3 s | $0.042 |
| A0 naive RAG (BM25 top 8) | 66.7 % [58.6, 74.4] | 63.4 % | 13.3 % | 75.3 % | 93.2 % | 25.3 s | $0.037 |
| *Oracle (best arm per question, upper bound, not deployable)* | *95.0 %* | | | | | | |

Latencies of the one-shot arms (A0 to A8, `smart-dz`) and of the agents (`smart`) come from two
deployments and are compared within each group only. Costs use the unverified price table.

**Safety**: no restricted value and no injection success in any of the 3,960 answers; no arm is
excluded.

**Tests** (Holm-adjusted paired permutation tests, 120 questions): against W1, only naive RAG is
significantly worse (A0 -15.3 points, p = 0.005). A8 (-9.7, p = 0.076), A3 (-8.9, p = 0.17) and
every other arm are not significantly different. Best against second (W1 - W2-high +1.9) is not
significant. Wiki effect of the 2 x 2 ((W1 + W2) - (R1 + R2)) +4.4 points, raw p = 0.031,
Holm p = 0.31: not significant after correction. v2 effect ((W2 + R2) - (W1 + R1)) -0.8 points:
none.

**Decision under the pre-registered rule.** No arm beats all others significantly, so the arms
within 5 points of the best and not significantly worse form a set: W1, W2-high, W2, A2, A1 and
the router. Ordered by claim support (judge), the first criterion: **A2 (81.5 %)**, W2-high
(80.1 %), W2 (79.9 %), W1 (79.1 %), A1 (69.2 %), router (no judge record). The recommended arm is
**A2, every public document in one prompt**. The support differences between A2, W2-high, W2 and
W1 are small (2.4 points) and were not tested; the result is a tie in accuracy between the agent
on the wiki, long context and optimised RAG, broken by claim support.

**By category** (mean accuracy, %):

| Category (questions) | A0 | A1 | A8 | A2 | A3 | W1 | R1 | W2 | R2 | W2-high | Router |
|---|---|---|---|---|---|---|---|---|---|---|---|
| single-hop (23) | 91 | 100 | 97 | 100 | 86 | 91 | 96 | 93 | 97 | 97 | 93 |
| multi-hop (28) | 65 | 79 | 62 | 86 | 75 | 83 | 69 | 80 | 71 | 81 | 77 |
| table (20) | 67 | 73 | 73 | 65 | 72 | 87 | 75 | 82 | 70 | 77 | 67 |
| numeric (9) | 59 | 67 | 59 | 67 | 78 | 81 | 67 | 74 | 70 | 74 | 85 |
| supersession (11) | 27 | 48 | 45 | 55 | 27 | 79 | 67 | 67 | 64 | 61 | 70 |
| contradiction (8) | 50 | 58 | 62 | 62 | 54 | 71 | 62 | 75 | 71 | 83 | 58 |
| abstain (9) | 100 | 96 | 96 | 93 | 100 | 81 | 78 | 70 | 85 | 70 | 89 |
| OCR (5) | 47 | 87 | 87 | 73 | 100 | 67 | 87 | 80 | 80 | 80 | 80 |
| skill (5) | 53 | 73 | 60 | 80 | 67 | 53 | 67 | 67 | 67 | 73 | 53 |
| injection (2) | 50 | 50 | 50 | 50 | 50 | 83 | 83 | 83 | 83 | 83 | 83 |

**What it says.**

1. On a corpus that fits in one prompt (39 documents, about 35,000 tokens), reading every document
   at once is as accurate as the best agent, supports its claims best, is wrong least often and
   costs 2.6 times less per correct answer than the agent on the wiki; it is the slowest one-shot
   arm and stops working when the corpus outgrows the context.
2. The agent on the compiled wiki (W1, the production design) has the highest accuracy and the
   best numeric exactness, and clearly wins where compilation did the work: superseded revisions
   (79 % against 27 to 55 % for every retrieval and long-context arm), tables (87 %) and contradictions. It
   abstains less well (81 %): it tends to answer with something it found.
3. Optimised retrieval (A1) is a strong, cheap default: +11 points over naive RAG, the best
   citation overlap, statistically tied with the agent. Managed agentic retrieval (A8) did not beat
   it here.
4. The wiki effect inside the agent (+4.4 points) is in the expected direction but not
   significant at 120 questions; it comes from tables, multi-hop and supersession.
5. Neither v2 (question decomposition, a dense lane, revision companions) nor high reasoning effort
   improved accuracy; high effort costs 44 % more per correct answer.
6. A router fitted on 32 development questions did not beat its best arm (77.2 %), although an
   oracle choosing the best arm per question would reach 95 %: the arms are complementary, but a
   three-class question classifier cannot tell in advance which one will succeed.
7. Putting the compiled wiki itself in one prompt (A3, 120,000 tokens of hubs, views and topics,
   sources dropped) is worse than the raw documents (73.1 % against 78.3 %): the summaries lose
   details the questions ask for.

Cost of the study (unverified prices): blind answers about $255 (the router reuses the answers of
its arms), blind judge about $80, development runs about $100.