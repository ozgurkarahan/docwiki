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
  `--system docwiki-researcher --agent <Foundry agent name>` targets another deployed Researcher;
  the run is then recorded under that agent name, beside the production one, for an A/B
  comparison.
- `evals/scoreboard.py` → `evals/results/latest.json` and a Markdown table injected into the README
  between `<!-- scoreboard:start -->` and `<!-- scoreboard:end -->`.
- `evals/compile_fidelity.py` → `evals/results/<date>-compile-fidelity.json`
  (`docwiki.evals.compile-fidelity/v1`): what the compiled wiki states, checked on a release with
  no LLM call against `evals/golden/compile-fidelity.yaml`, whose expectations come from the
  fictional world (`samples/fiction/bible.yaml`) and only use values printed in a public document.
  Revision statuses, facts synthesised on a topic or view page of their scope (and compiled on any
  page), cross-chantier syntheses, abstain facts, the bible's forbidden strings in the wiki,
  evidence and catalog, and the pages that state the document stamp.
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
