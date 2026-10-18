# Evaluation

DocWiki makes a specific claim: compiling documents into a cited wiki answers cross-document
questions better than re-retrieving raw chunks, at a known cost. That claim has to be measured
against baselines, on questions written before the system ever saw the data, and published with
its failures. This page describes the method; the normative text is the [evaluation
spec](spec/evals.md).

> **Results:** a live run on 2026-10-18 measured the deployed Researcher and both baselines on the
> dev split and the private holdout; see [results](#results) below and the README scoreboard.

## The golden set

The public dev split lives in [`evals/golden/`](../evals/golden/README.md): **33 questions** about
the fictional Quellmoor Ridge corpus, one JSON object per line.

| Category | Questions | What it tests |
|---|---|---|
| single-hop | 4 | One fact from one source |
| numeric | 2 | Exact values with units |
| table | 4 | Spreadsheet and CSV rows, including a join across a workbook and a CSV |
| multi-hop | 6 | Facts combined across formats: SCADA log, incident report, asset register, decks, e-mail, minutes |
| contradiction | 2 | Current sources that disagree; authority and recency decide |
| supersession | 2 | A later revision replaces an earlier one |
| multilingual | 3 | English questions on French and German sources, and one question in French |
| ocr | 2 | A handwritten value on a photographed checklist, an image-only scanned PDF |
| abstain | 2 | The corpus does not contain the answer |
| injection | 2 | An e-mail carries an instruction addressed to AI assistants and a canary token |
| restricted | 1 | The answer exists only in a restricted document excluded from public builds |
| skill | 3 | Tasks for the domain skills `troubleshoot-alarm`, `prepare-maintenance-task`, `audit-readiness` |

Each record carries the question and its language, a reference answer, `must_include` strings
(numbers normalised), `required_citations` (source path and locator key), `forbidden` strings (for
example the canary token or restricted rates) and an `abstain` flag:

```json
{"id": "q001", "split": "dev", "category": "single-hop", "question": "...", "lang": "en",
 "expected_answer": "...", "must_include": ["..."],
 "required_citations": [{"source_path": "full/...", "locator_key": "p0003"}],
 "forbidden": [], "abstain": false, "notes": "..."}
```

**Sequencing protects the set from tuning.** The fictional world was defined first, the corpus
was generated deterministically and frozen (its `MANIFEST.json` hashes committed), then the golden
set was written against the frozen corpus and **sealed**: `evals/golden/SEAL` records the SHA-256
of `dev.jsonl` and of the corpus manifest, and a test fails if either drifts. Only then may the
first wiki be generated. Any later change to the set goes through its authoring script, with a
commit message that explains why the seal changed.

**A private holdout** of about 30 % of the questions is kept outside the repository. Its author
sees only the corpus, never the notes that describe the planted facts. Only aggregate holdout
scores are published, separately from dev scores, and prompts are never tuned on holdout results.

Fourteen dev questions cite only documents of the 12-document quickstart subset, so a cheaper
quickstart evaluation is possible. One question is a "time travel" check: its answer changes when
the held-back service bulletin is added to the corpus.

## Systems under test

| System | Description |
|---|---|
| `docwiki-researcher` | The deployed Foundry Researcher agent, through the MCP server, over the current release |
| `docwiki-local` | The same instructions through a local loop and the stdio MCP server (specified, not implemented in this proof of concept) |
| `baseline-rag` | Naive RAG: extracted text split into chunks of about 800 tokens, BM25 top-8, the same `smart` model and answer format |
| `baseline-long-context` | All extracted text of the quickstart subset in the prompt, when it fits the model budget, with the same model |

Same model, same extracted text, same answer format: the baselines differ from DocWiki only in how
knowledge is organised and reached.

## Metrics

Every metric is reported per category and overall, **with its denominator**.

| Metric | How it is computed |
|---|---|
| Answer accuracy | Deterministic: every `must_include` item present (numbers normalised); plus an LLM-judge score for semantic correctness |
| Citation precision | Share of cited locators whose text or table cells actually contain the supporting words or numbers, checked by code against the extracted documents |
| Citation recall | Share of `required_citations` that the answer cites, at page or sheet-row granularity |
| Abstention accuracy | When the answer is not in the corpus: says so and cites nothing; otherwise, no false abstention |
| Numeric exactness | Exact numbers with units for numeric and table questions |
| Injection resistance | No `forbidden` string, no action requested by the canary instruction |
| Restricted exclusion | No content from restricted sources in public-audience answers |
| Built-in evaluators | `azure-ai-evaluation`: groundedness, relevance, response completeness, task adherence, tool call accuracy, intent resolution, judged by the `smart` deployment |
| Cost and latency | Tokens in and out, estimated cost and wall time per question |

The deterministic checks (citation matching, normalisation, abstention detection) are plain code
and unit-tested; the judge-based scores are reported next to them, never instead of them.

## Running an evaluation

```bash
# the deployed Researcher (needs the azd environment values and a downloaded copy of the release)
uv run python evals/run.py --system docwiki-researcher --questions evals/golden/dev.jsonl \
    --catalog <release folder> --extract-mode azure --concurrency 1
# the baselines (same smart deployment, same extracted text)
uv run python evals/run.py --system baseline-rag --questions evals/golden/dev.jsonl --extract-mode azure
uv run python evals/run.py --system baseline-long-context --questions evals/golden/dev.jsonl --extract-mode azure
# a private split: aggregates only in the repository, details outside it
uv run python evals/run.py ... --questions <holdout.jsonl> --split-name holdout --private-out <folder>
uv run python evals/scoreboard.py
```

- `run.py` writes `evals/results/<date>-<system>-<split>.json` with one record per question:
  answer, citations, tool calls, metric values, tokens, cost and versions.
- `scoreboard.py` writes `evals/results/latest.json` and [`evals/SCOREBOARD.md`](../evals/SCOREBOARD.md),
  and replaces the compact table between `<!-- scoreboard:start -->` and `<!-- scoreboard:end -->`
  in the README.
- Every result records the DocWiki commit, the release id, the model deployments and versions, the
  prompt versions and the evaluator versions.
- Run one live system at a time: concurrent runs share the `smart` deployment's tokens-per-minute
  quota, and an answer lost to an HTTP 429 counts as a failure.
- Live runs (agents, judge) are started by hand or on a schedule, never in pull-request CI. The
  deterministic metric functions run in CI on recorded answers.
- `azure-ai-evaluation` (`--judge`) depends on packages without Windows ARM64 wheels: run it on
  Linux or an x64 Python.

To reproduce a live evaluation: deploy with [`BOOTSTRAP.md`](../BOOTSTRAP.md) using the public
audience (`DOCWIKI_AUDIENCE=public`), upload `samples/corpus/full` to `raw/`, wait for the release,
then run the systems above. `docwiki ask` uses the same client as the runner, so you can try
single questions first.

## Honesty rules

- Dev and holdout aggregates are published separately; prompts are never tuned on holdout results.
- The ids of failed questions are published next to the scores, per category.
- Baselines use the same model, text and answer format, and their numbers are always published
  next to DocWiki's, category by category.
- Costs and latencies are published with the scores they paid for.
- DocWiki is never presented as a replacement for retrieval systems: results are measured
  trade-offs on one corpus, not universal claims.

## Results

Live run of 2026-10-18: Sweden Central, `smart` = gpt-5.5 (Global Standard), Researcher measured
on release `20261018T092417Z-d2186573` (the committed sample, `20261018T104207Z-650d6d98`, was
rebuilt from the same cached model outputs with corrected navigation labels), one run per system,
judge not run (every published score is deterministic). Full tables with denominators, tokens,
versions and failed question ids: [`evals/SCOREBOARD.md`](../evals/SCOREBOARD.md).

| System | Split | Answer accuracy | Citation precision | Citation recall | Abstention | Injection resistance | Cost per question |
|---|---|---|---|---|---|---|---|
| `docwiki-researcher` | dev (33) | 90.6 % (29/32) | 79.5 % (n=30) | 77.3 % (n=30) | 100 % (33/33) | 100 % (2/2) | 0.118 USD |
| `baseline-rag` | dev (33) | 75.0 % (24/32) | 91.8 % (n=27) | 75.8 % (n=30) | 90.9 % (30/33) | 100 % (2/2) | 0.046 USD |
| `baseline-long-context` | dev (33), quickstart documents only | 50.0 % (16/32) | 75.2 % (n=22) | 44.5 % (n=30) | 72.7 % (24/33) | 100 % (2/2) | 0.145 USD |
| `docwiki-researcher` | holdout (15, aggregate) | 93.3 % (14/15) | 86.5 % (n=13) | 84.3 % (n=13) | 100 % (15/15) | 100 % (1/1) | 0.165 USD |
| `baseline-rag` | holdout (15, aggregate) | 66.7 % (10/15) | 96.9 % (n=13) | 86.5 % (n=13) | 100 % (15/15) | 100 % (1/1) | 0.051 USD |
| `baseline-long-context` | holdout (15, aggregate) | 46.7 % (7/15) | 71.7 % (n=9) | 37.8 % (n=13) | 66.7 % (10/15) | 100 % (1/1) | 0.169 USD |

What the numbers say, and what they do not:

- **Where the wiki helps.** The Researcher answered six dev questions naive RAG missed: two
  multi-hop (q011, q014), two multilingual (q021, q022) and two skill tasks (q031, q033). These
  need facts joined across formats or languages, which entity pages, the glossary and topic
  syntheses provide. Both systems missed q007 (one row of the stock workbook) and q012 (a permit
  curtailment rule joined with the SCADA log).
- **Where RAG is better.** Citation precision (91.8 % against 79.5 %), numeric exactness on dev
  (5/5 against 4/5), one supersession question (q019), cost (2.6 times cheaper) and latency
  (7.0 s against 22.6 s median).
- **Long context** fits only the 12 quickstart documents (about 111k tokens of a 120k budget), so
  most cross-document questions are out of its reach; two dev and three holdout answers also hit
  the 2,000-token output cap and count as failures.
- **Safety.** Every system resisted the injected e-mail; the Researcher and RAG never leaked the
  restricted document (long-context failures on that metric are errored answers).
- **Noise.** 33 + 15 questions and one run per system: one question is 3 points on dev and 7 on
  holdout. Treat differences of one or two questions as noise.
- **Rate limits.** A first Researcher dev run shared the `smart` quota with the long-context
  baseline and lost 8 answers to HTTP 429 and 500 errors; the published run used one question at a
  time and had no errors.
