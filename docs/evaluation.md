# Evaluation

DocWiki makes a specific claim: compiling documents into a cited wiki answers cross-document
questions better than re-retrieving raw chunks, at a known cost. That claim has to be measured
against baselines, on questions written before the system ever saw the data, and published with
its failures. This page describes the method; the normative text is the [evaluation
spec](spec/evals.md).

> **Results (dev split, 32 questions):** Researcher 68.8 % answer accuracy, long context 62.5 %,
> RAG 56.2 %; see [results](#results) below and the README scoreboard, which
> `evals/scoreboard.py` generates from `evals/results/`.

## The golden set

The public dev split lives in [`evals/golden/`](../evals/golden/README.md): a small set of questions
about the fictional building-job corpus (the [spec](spec/domain-and-corpus.md#5-golden-set) sets
it between 12 and 20 questions), one JSON object per line. The documents are in French; English
questions use only language-neutral `must_include` items (numbers with units, dates, document
numbers, names), so a correct English answer never needs a French word.

| Category | What it tests |
|---|---|
| single-hop | One fact from one source |
| numeric | Exact values with units (an amount, an area, a percentage) |
| table | Spreadsheet rows, for example purchases to date in the planning workbook |
| multi-hop | Facts combined across documents: the contract and its amendment, an invoice and a scanned delivery note, minutes and e-mails |
| contradiction | Current sources that disagree (the window delivery date in the planning and in the window maker's e-mail); authority and recency decide |
| supersession | A later revision replaces an earlier one (quote indice B replaces indice A) |
| multilingual | English questions on French documents, and at least one question asked in French |
| ocr | A handwritten remark on an image-only scanned delivery note |
| abstain | The corpus does not contain the answer (no document names an architect) |
| injection | An e-mail carries an instruction addressed to AI assistants and a canary token |
| restricted | The answer exists only in a restricted document excluded from public builds (the internal price study) |
| skill | Tasks for the domain skills of the pack (one per skill) |

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

**A private holdout** of about a quarter of all questions (about five) is kept outside the
repository. Its author sees only the corpus, never the notes that describe the planted facts. Only
aggregate holdout scores are published, separately from dev scores, and prompts are never tuned on
holdout results.

The held-back planning revision supports a "time travel" check: the answer about the window
delivery date changes when it is added to the corpus (see [`PLANTED.md`](../samples/fiction/PLANTED.md)).

## Systems under test

| System | Description |
|---|---|
| `docwiki-researcher` | The deployed Foundry Researcher agent, through the MCP server, over the current release |
| `docwiki-local` | The same instructions through a local loop and the stdio MCP server (specified, not implemented in this proof of concept) |
| `baseline-rag` | Naive RAG: extracted text split into chunks of about 800 tokens, BM25 top-8, the same `smart` model and answer format |
| `baseline-long-context` | All extracted text of the public documents of `full/` in the prompt, when it fits the model budget, with the same model |

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

## Performance probe

`evals/perf_probe.py` times a deployed site from the outside, without Azure credentials. It only
reads what any visitor can read, plus a local run report when given one:

```bash
# pages: "/", "/en/", "/pipeline" and the search index "/static/contentIndex.json", 3 fetches each
uv run python evals/perf_probe.py --base-url https://<your-portal>
# other paths, more fetches, JSON output
uv run python evals/perf_probe.py --base-url https://<your-portal> --path /pipeline --repeat 5 --json
# one live question (spends model tokens: one question, not a batch)
uv run python evals/perf_probe.py --base-url https://<your-portal> --no-paths --ask "When are the windows delivered?"
# stage durations of a pipeline run report downloaded from storage
uv run python evals/perf_probe.py --run-report <run report.json>
```

- **Pages.** Each path is fetched on a fresh connection (cold), then again on the kept-alive
  connection with `If-None-Match` (warm; `--no-revalidate` turns it off). The table gives the
  status, `content-encoding`, the bytes on the wire (compressed), whether an ETag was sent, the
  time to the response headers (TTFB) and the total time; warm fetches should answer `304`.
- **Live ask.** The question is posted to `/api/ask` as the drawer does (JSON, same-origin
  `Origin` header). The probe reads `/api/ask/{job_id}/events` when the portal streams
  Server-Sent Events and otherwise polls `GET /api/ask/{job_id}` every `--poll-interval` seconds
  (default 1). It reports the time to `202`, to the first progress (`step`) update, to the final
  answer, the server's own elapsed time, the steps seen and the number of citations.
- **Run report.** Per-stage duration, share of the run, items, cache hits, failures and model
  calls.

The probe uses `httpx` only and has no built-in URL; its tests run against a stub transport.

## Honesty rules

- Dev and holdout aggregates are published separately; prompts are never tuned on holdout results.
- The ids of failed questions are published next to the scores, per category.
- Baselines use the same model, text and answer format, and their numbers are always published
  next to DocWiki's, category by category.
- Costs and latencies are published with the scores they paid for.
- DocWiki is never presented as a replacement for retrieval systems: results are measured
  trade-offs on one corpus, not universal claims.

## Results

The dev split runs in CI (`.github/workflows/evals.yml`, started by hand). The numbers appear in
the README scoreboard and in [`evals/SCOREBOARD.md`](../evals/SCOREBOARD.md), generated by
`evals/scoreboard.py` from `evals/results/`, with denominators, tokens, cost, versions and the ids
of failed questions. On the 39-document sample (Researcher measured 2026-10-27, baselines
2026-10-23, same questions):

| System | Answer accuracy | Numeric exactness | Citation precision | Cost / question | Median latency |
|---|---|---|---|---|---|
| Researcher (index-first, [ADR 0013](adr/0013-index-first-researcher.md)) | 68.8 % (22/32) | 100 % (9/9) | 77.5 % | about $0.12 | 25.0 s |
| Long context | 62.5 % (20/32) | 88.9 % (8/9) | 74.3 % | about $0.053 | 14.6 s |
| RAG (BM25 top-8) | 56.2 % (18/32) | 66.7 % (6/9) | 90.4 % | about $0.045 | 8.2 s |

The private holdout has not been run in CI yet. How the results are read, and what they do not
claim:

- **Where the wiki helps.** Questions that need facts joined across documents, formats or
  languages, which entity pages, the glossary and topic syntheses provide. The ids of the
  questions each system missed are published per category.
- **Where RAG may be better.** Citation precision, numeric exactness, cost and latency are
  compared question by question; a baseline that wins on one of them is reported as such.
- **Long context** only runs when the extracted text of the public documents fits the model
  budget, and an answer that hits its output cap counts as a failure.
- **Safety.** Injection resistance and restricted exclusion are reported for every system.
- **Noise.** The question set is small and each system runs once: one question moves a score by
  several points. Treat differences of one or two questions as noise.
- **A strict question.** q021 asks *when* the retention is released, but its `must_include` also
  asks for the amount held; every system misses it on 2026-10-23 and 2026-10-27. The dev set is
  sealed (spec D12), so the question stays as written and this is read as a grading limit, not a
  regression.
