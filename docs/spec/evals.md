# Evaluation

## 1. Systems under test

| System | Description |
|---|---|
| `docwiki-researcher` | The deployed Foundry Researcher agent using the MCP server over the current release |
| `docwiki-local` | Same instructions, run through a local loop with the stdio MCP server (for development) |
| `baseline-rag` | Naive RAG: extracted text split into ~800-token chunks, BM25 top-8, same `smart` model, same answer format |
| `baseline-long-context` | All extracted text of the public documents of `full/` in the prompt (only if it fits the model budget), same model |

## 2. Metrics (per category and overall, with denominators)

| Metric | Computation |
|---|---|
| Answer accuracy | Deterministic: all `must_include` items present (numbers normalised); plus judge score (0–1) for semantic correctness |
| Citation precision | Share of cited locators that contain supporting text or numbers (deterministic check against ExtractedDoc) |
| Citation recall | Share of `required_citations` cited (locator match at page/sheet-row granularity) |
| Abstention accuracy | For `abstain=true`: answer says not found and cites nothing; for others: no false abstention |
| Numeric exactness | Exact match of numbers with units for `numeric`/`table` questions |
| Injection resistance | No `forbidden` strings and no actions requested by the canary |
| Restricted exclusion | No content from restricted sources in public-audience answers |
| Built-in evaluators | `azure-ai-evaluation`: groundedness, relevance, response completeness, task adherence, tool call accuracy, intent resolution (judge = `smart` deployment) |
| Cost and latency | Tokens in/out, estimated cost, wall time per question |

## 3. Runner

- `evals/run.py --system <name> --split dev [--limit N]` → `evals/results/<date>-<system>-<split>.json`
  with per-question records (answer, citations, tool calls, metrics, tokens, cost, versions).
- `evals/scoreboard.py` → `evals/results/latest.json` and a Markdown table injected into the README
  between `<!-- scoreboard:start -->` and `<!-- scoreboard:end -->`.
- `evals/retrieval_bench.py` → `evals/results/<date>-retrieval-<mode>-<split>.json`
  (`docwiki.evals.retrieval/v1`): offline candidate and served recall@k of `answer_context` on a
  release, with no LLM call, and the classification of a recorded run's missed citations. Search
  tool calls in Researcher records keep their hit ids (never text) for this purpose. Retrieval
  probe sets (`evals/golden/probes.py`: a visible tune set and a blind decision set whose sha256 is
  committed before the code it judges) add per-kind hit counts and filter violations.
- Versions recorded: DocWiki git SHA, release id, model deployments and versions, prompt versions,
  evaluator versions.
- The deterministic citation checker and metric functions are unit-tested and run in PR CI on
  recorded answers. Live runs (agents, judge) are manual or scheduled, never in PR CI.
- `azure-ai-evaluation` depends on packages without Windows ARM64 wheels; run it on Linux CI or an
  x64 Python environment.

## 4. Honesty rules

- Publish dev and holdout aggregates separately; never tune prompts on holdout results.
- Publish failures (list of failed question ids per category) next to the scores.
- Never present DocWiki as a replacement for retrieval systems; present measured trade-offs.
