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
