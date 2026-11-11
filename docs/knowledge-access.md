# How should an agent use a knowledge base?

You have a pile of documents and an agent that must answer questions about them. There are four
common ways to connect the two. This guide explains each one in plain words, says what research
and what DocWiki's own tests show, and gives a first rule of thumb for choosing. It also shows how
to repeat the test on your own documents.

Decision record: [ADR 0015](adr/0015-knowledge-access.md). Pre-registered study:
[`evals/experiments/2026-11-10-knowledge-access.md`](../evals/experiments/2026-11-10-knowledge-access.md).
How it was run, the research behind each arm and every check:
[method](../evals/experiments/2026-11-10-knowledge-access/method.md).

> **Read this first.** DocWiki measured one small fictional corpus (39 public documents), one
> model family and 32 development questions, plus a blind set of 120. What it measured is stated
> as a result. Everything else here is a **hypothesis** from the literature, and is labelled so.

## 1. The four approaches

| | 1. RAG | 2. Compiled wiki | 3. Optimised RAG with the wiki's indexes | 4. Router |
|---|---|---|---|---|
| **Built ahead of time** | Chunks, a keyword index, often vectors | A Markdown wiki written by a model: source, entity and topic pages, indexes, links, computed views, evidence per claim | Same as 1, plus the wiki's own structure: indexes, revision status, glossary terms | Nothing for the data; a small classifier and a routing table |
| **At question time** | Find the best chunks, put them in one prompt, answer | The agent reads indexes, opens pages, follows links, checks evidence, queries tables | The agent plans sub-questions, searches each (words and meaning), joins the results | A cheap model labels the question, then one of the other three answers it |
| **Strengths** | Simple, cheap, fast to stand up; good on a fact that sits in one passage | Knowledge accumulates; cross-document syntheses and revisions are written down once; precise citations; exact numbers through parsed tables | Keeps the wiki's map and adds recall for paraphrases; one retrieval path serves many questions | Each question gets the cheapest approach that works |
| **Weaknesses** | Re-discovers everything on every question; misses facts spread over several documents | A compile step; a stale or incomplete wiki misleads; summaries can drop superseded details | More moving parts; needs an embedding model and tuning | A wrong label sends a question to a weak path; needs enough labelled questions to fit |
| **Cost profile** | Low build cost, low cost per question | Build cost grows with the corpus and every change; cost per question is moderate (several tool calls) | Build cost of vectors, then the cost of several searches per question | Cost of the classifier on every question, plus the arms it can choose |

Two more ideas appear in the results:

- **Long context** puts all the documents (or all the wiki's summaries) in one prompt. It needs no
  index. It only works while the corpus fits, and models read long inputs unevenly.
- **Agent with tools** is not a fifth approach but a way to run 2 or 3: a model that decides which
  search, which page and which table to read, one step at a time.

## 2. What the state of the art says

Sources are linked. Numbers marked *(secondary)* come from blogs, vendors or aggregations of
several papers; use them as direction, not as precise deltas. Details and caveats were collected
on 2026-11-10.

- **Hybrid search plus a reranker is the strong default.** Keyword and meaning search fused, then
  a reranker, cut the number of failed top-20 retrievals from 5.7 % to 1.9 % in
  [Anthropic's contextual retrieval study](https://www.anthropic.com/research/contextual-retrieval)
  (2024-09-19). Azure reports up to 22 points of NDCG@3 from query rewriting and its semantic
  ranker ([Microsoft Tech Community, 2024-11-19](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/raising-the-bar-for-rag-excellence-query-rewriting-and-new-semantic-ranker/4302729), vendor
  figure).
- **Decomposing a question helps multi-hop questions.** Splitting a question into sub-questions,
  retrieving for each and reranking the merge raised MRR@10 by 36.7 % and F1 by 11.6 % on two
  multi-hop sets ([arXiv:2507.00355](https://arxiv.org/abs/2507.00355)). The join step matters,
  not only the fan-out.
- **Routing is a known pattern.** Choosing no retrieval, one step or many steps per question
  improves accuracy and efficiency over a fixed strategy
  ([Adaptive-RAG, NAACL 2024](https://aclanthology.org/2024.naacl-long.389)); routing between a
  strong and a weak model cuts cost by more than half while keeping quality on the benchmarks tested
  ([arXiv:2406.18665](https://arxiv.org/abs/2406.18665)).
- **Long context is not a free replacement.** Long context can beat RAG on understanding, but RAG
  is much cheaper ([arXiv:2407.16833](https://arxiv.org/abs/2407.16833)). All 18 models in a
  [2025-07-14 report on "context rot"](https://www.trychroma.com/research/context-rot) lost accuracy
  unevenly as the input grew.
- **Agentic search can beat vectors on exact lookups, depending on the harness.** One May 2026
  study found grep-style search generally ahead of vector retrieval on a 116-question sample, with
  results that depend on the agent harness ([arXiv:2605.15184](https://arxiv.org/abs/2605.15184);
  very recent, to be confirmed).
- **Graph indexes pay off on corpus-wide and relational questions, less on simple lookups.**
  [GraphRAG](https://arxiv.org/abs/2404.16130) improves comprehensiveness on corpus-wide
  questions. A secondary comparison reports gains on complex reasoning and a loss on simple fact
  retrieval *(secondary)*. Several 2026 analyses discourage graph indexing below about 10,000
  documents unless the questions are heavily relational *(secondary)*.
- **Managed agentic retrieval exists.** Azure AI Search and Foundry IQ plan sub-queries, run them
  in parallel and rerank ([Azure documentation](https://learn.microsoft.com/azure/search/agentic-retrieval-overview),
  updated 2026-09-17). Independent benchmarks are still few.
- **The compiled-wiki idea** is described in the
  [LLM wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (2026-04-04):
  a model reads sources once and maintains linked Markdown pages instead of re-finding facts on
  every question. Community critiques say it gets hard past about 1,000 files and that unattended
  model maintenance can compound mistakes *(secondary)*.
- **Revisions need explicit validity.** Temporal memory systems keep an old fact with the period
  in which it was true instead of overwriting it ([arXiv:2501.13956](https://arxiv.org/abs/2501.13956)).
  Their benchmark numbers come from blogs *(secondary)*; treat the pattern, not the score.
- **Small evaluation sets mislead.** Detecting a difference of a few questions needs far more than
  32 paired questions; report intervals, not only point scores.

## 3. What DocWiki measured

Corpus: 39 public documents of a fictional building contractor (French, with an English mirror),
one compiled release, one answer model family. Scores are share of questions answered correctly
unless stated.

**Published before the blind runs**

- **Compile fidelity** (no model, ground truth from the fictional world): on the served release of
  2026-10-27, every printed fact was compiled (30/30) and 26 of 30 were synthesised in a topic or
  view page. Only 2 of 5 cross-chantier syntheses existed. This matches the agent's misses on
  questions that span several job sites. Method: [evaluation](evaluation.md#compile-fidelity).
- **Wiki ablation** ([study](../evals/experiments/2026-11-09-wiki-ablation.md)): the same agent
  with and without the compiled wiki, 32 development questions, replays on every discordant
  question. Net effect **0**: 4 questions won with the wiki, 4 lost. Accuracy was 20/32 in both
  arms. With the wiki, exact numbers were better (8/9 against 6/9), citations more precise
  (75.4 % against 67.0 %) and computed cross-job views were found in one call. Without it, the
  agent did better on the detail of superseded revisions.
- **Earlier gates failed.** Adding a meaning search to the first candidates (gate A), and a
  per-job fan-out (F3, F3 v2), did not meet their pre-registered criteria
  ([gate A](../evals/experiments/2026-11-01-gate-a.md),
  [F3](../evals/experiments/2026-11-01-f3-coverage.md),
  [F3 v2](../evals/experiments/2026-11-01-f3v2-fanout.md)).
- **One-shot arms on development questions**: naive retrieval 18/32, all documents in context
  20/32. At 32 questions these arms are statistically indistinguishable from each other and from
  the agent.

**Blind results (120 questions written by an independent author, 3 runs per arm, 95 % intervals)**

| Approach | Arm | Accuracy | Claims supported (judge) | Cost per correct answer |
|---|---|---|---|---|
| Agent on the compiled wiki | W1 | **81.9 %** [76.1, 87.2] | 79.1 % | $0.111 |
| Same, with question planning and a dense lane (v2) / high reasoning effort | W2 / W2-high | 79.4 % / 80.0 % | 79.9 % / 80.1 % | $0.126 / $0.160 |
| All documents in one prompt | A2 | 78.3 % [71.1, 85.0] | **81.5 %** | $0.043 |
| Optimised RAG: hybrid search, semantic ranker, decomposition | A1 | 77.8 % [71.1, 83.9] | 69.2 % | $0.053 |
| Router fitted on development questions | R | 77.2 % [70.6, 83.6] | - | $0.095 |
| Agent on raw extracted blocks (no wiki), v2 / production instructions | R2 / R1 | 76.7 % / 75.8 % | 80.1 % / 76.9 % | $0.114 / $0.095 |
| The compiled wiki in one prompt | A3 | 73.1 % [65.3, 80.6] | 78.1 % | $0.134 |
| Managed agentic retrieval (Foundry IQ) | A8 | 72.2 % [64.7, 79.7] | 67.8 % | $0.042 |
| Naive RAG (keyword top 8) | A0 | 66.7 % [58.6, 74.4] | 63.4 % | $0.037 |
| *Oracle: best arm per question (upper bound)* | | *95.0 %* | | |

- Only naive RAG is significantly worse than the agent on the wiki (-15 points, Holm p = 0.005).
  The agent on the wiki, long context, optimised RAG, the v2 variants and the router are
  statistically tied; the pre-registered tie-break (claim support) recommends **long context** for
  this corpus. DocWiki keeps the agent on the wiki, the most accurate arm, for the reasons in
  [ADR 0015](adr/0015-knowledge-access.md): a product choice on a tie, not a proof.
- The compiled wiki wins where compilation did the work: superseded revisions (79 % for the agent
  on the wiki, 61 to 67 % for the other agents, 27 to 55 % for every retrieval and long-context
  arm), tables (87 %, +12 points over the same agent without the wiki), contradictions and
  numeric exactness (87.7 %). The agent abstains less well (81 %).
- The wiki's effect inside the same agent is +4.4 points, not significant after correction.
- Question planning, a dense lane and high reasoning effort did not help. A three-class router did
  not beat its best arm, although an oracle would reach 95 %: the approaches are complementary,
  but which one succeeds is hard to predict from the question.
- No arm leaked a restricted value or followed the planted injection.

Full results, per category, tests and costs:
[the study](../evals/experiments/2026-11-10-knowledge-access.md#results-blind-runs-of-2026-11-10-and-2026-11-11).

**Reading the numbers.** The development split was seen while building, so it is for tuning only;
the blind split decides. On 120 questions, a difference under about 8 points is not significant
here. The development split even reversed the order: there, the v2 instructions with high
reasoning effort came first (77.1 %) and the production agent last (59.4 %)
([method](../evals/experiments/2026-11-10-knowledge-access/method.md#4-what-the-development-runs-got-wrong)).

## 4. Choosing an approach

> The first five rows are what DocWiki measured on its corpus (section 3). The rest goes beyond
> it, combining section 2 with the shape of the results: test it on your own documents
> (section 5) before you rely on it.

| If your corpus or need is... | Start with | Evidence |
|---|---|---|
| A few dozen documents that fit in one prompt with room to spare | **Long context**, as the baseline to beat | Measured: tied for best accuracy, best claim support, 2.6 times cheaper per correct answer than the agent |
| Anything bigger, mostly lookups | **Hybrid RAG with a reranker** (and question decomposition) | Measured: +11 points over naive RAG, best citations, tied with the agent |
| Revisions ("which version is current, what changed"), tables, contradictions, exact numbers | **An agent on a compiled wiki** with revision status, parsed tables and computed views | Measured: clear lead on supersession and tables, best numeric exactness |
| A choice between the approaches per question | Do not expect a simple question classifier to pick well | Measured: router no better than its best arm; the oracle shows the headroom |
| "Think harder" (high reasoning effort) | Keep the default effort | Measured: no gain, 44 % more cost per correct answer |
| Hundreds to thousands of documents that do not fit in context | Hybrid RAG with a reranker; add a compiled layer for revisions and tables | Hypothesis (literature) |
| Corpus-wide synthesis ("what are the themes") | A compiled layer (wiki or graph) | Hypothesis: top chunks cannot see the whole |
| Audit and quoting: every claim must point to a page | Evidence-first design: quote-verified citations | Hypothesis: compiled citations are checked once, at build time |
| Documents change daily | RAG or an incremental compile | Hypothesis: a full recompile per change is costly |
| Strict latency or budget per question | RAG or long context | Measured on this corpus: agents make 3 to 5 tool calls per answer |

A short path through the table:

1. Do all documents fit in context, with margin? Try long context first and measure.
2. If not, build hybrid retrieval with a reranker. Measure.
3. If it fails on tables, revisions or contradictions, compile them: revision status, parsed tables
   an agent can query, computed views. That is where the compiled wiki earned its place here.
4. Before adding a router or more reasoning, measure an oracle on your own questions: if it does
   not show a large gap, a router cannot help.

## 5. Reproduce on your own corpus

The tooling is in [`evals/`](../evals/README.md). Everything is tested offline; the live runs need
a Foundry project and `az login` (no keys).

1. **Write questions.** At least 100 for confirmation, kept apart from the ones you tune on, in
   the golden format ([`evals/golden/README.md`](../evals/golden/README.md)). Include lookups,
   table numbers, multi-hop, superseded revisions and questions with no answer. Have someone who
   cannot see the system write the confirmation set.
2. **Register your systems.** A module `evals/systems_<name>.py` calls `register_system` from
   [`evals/registry.py`](../evals/registry.py); the runner does not change. Existing systems:
   naive retrieval, long context, the wiki in context, two Azure AI Search arms
   (`evals/systems_search.py`), and the agents.
3. **Run each arm several times:**
   `uv run python evals/run.py --system <name> --questions <file> --split-name <split> --run-label r1`
   (see [`evals/README.md`](../evals/README.md) for the options). Keep every run.
4. **Compare:**
   `uv run python evals/compare.py --arm NAME=run1,run2,run3 --reference <arm> --out <report.json>`.
   It gives bootstrap intervals clustered by question, paired permutation tests with Holm
   adjustment and the safety exclusions.
5. **Judge claims blind:** `uv run python evals/judge_llm.py <result files> --out <folder>` asks a
   model, without the arm's name, whether each claim is supported by the cited passage. Read it
   next to the deterministic scores, not instead of them.
6. **Try a router:** `evals/router.py classify`, then `fit` on the development split only, then
   `apply` (and `oracle`, the upper bound) on the confirmation results.
7. **Check the wiki itself:** `uv run python evals/compile_fidelity.py --release <release folder>`
   compares a compiled wiki with a known ground truth, without a model.
8. **Agents and Azure search:** the agent variants and the isolated evaluation stack are described
   in [`agents/README.md`](../agents/README.md#evaluation-variants-optional-opt-in) and set up with
   `scripts/eval_stack.py`; `agents/variants.yaml` keeps W1 and R1 as a template (the other agent
   arms of this study are in commit `e8bbd14`). The search arms use `scripts/eval_search_index.py`.

Rules that keep the result honest: write the arms, measures and decision rule before the blind
run; freeze versions and the release; publish all runs, losses and costs; and say when the result
is unresolved. The [method](../evals/experiments/2026-11-10-knowledge-access/method.md) lists the
checks DocWiki ran and the lessons it would reuse.
