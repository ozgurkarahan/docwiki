# Evaluation

> The questions refer to the **fictional** Chantier Moreau sample corpus in `samples/corpus`
> (Lamna Bâtiment, the Moreau household, Valbrise): French documents of one building job.

This folder measures DocWiki against two baselines on the golden set, with deterministic metrics,
optional model-judged metrics, costs and latencies (`docs/spec/evals.md`). Only the systems under
test need Azure: the metrics, the source mapping, the runner and the scoreboard are tested offline
in `tests/evals/`, which PR CI runs; live runs are manual (see "CI").

| Path | Purpose |
|---|---|
| `run.py` | Command line of the runner (implementation in `runner.py`) |
| `systems.py` | The systems under test behind one interface |
| `metrics.py`, `textnorm.py`, `locators.py` | Deterministic metrics, normalisation, locator matching |
| `corpus.py` | MANIFEST, release catalog, source mapping, extraction cache, evidence text |
| `judge.py` | Optional `azure-ai-evaluation` evaluators (imported lazily) |
| `scoreboard.py` | `results/latest.json`, `SCOREBOARD.md` and the README block |
| `results/` | Result files (`<UTC date>-<system>-<split>.json`) and `latest.json` |
| `golden/` | The public dev split, sealed (owned by the corpus lane, see `golden/README.md`) |

## Corpus and questions

The corpus (`samples/corpus/`, `MANIFEST.json` lists every file with its SHA-256 and sensitivity)
holds 12 public documents under `full/` (PDF, DOCX, XLSX, EML and JPG; the delivery note is an
image-only scan), one restricted document under `full/restricted/` (the internal price study) and
one revision under `held-back/` that only the time-travel demonstration adds. There is no smaller
subset: the baselines index the public documents of `full/` (`--scope all` adds the held-back
revision).

The dev split `golden/dev.jsonl` is public and sealed. The **holdout** is a private JSONL file of
about 5 questions that never enters the repository: it is kept outside it and run with
`--split-name holdout` (see "Holdout privacy"); only its aggregates are published.

## Systems

| System | What answers |
|---|---|
| `docwiki-researcher` | The deployed Foundry Researcher agent, through `docwiki.agents_client.ask`, using the MCP server over the current release. The agent version is resolved once and pinned for the run. |
| `baseline-rag` | Naive RAG: every document of the selected scope that the audience may see (the public documents of `full/` by default) is extracted with `docwiki.extract` (local mode), its blocks packed into ~800-token chunks that keep their locators, ranked with `docwiki.search`'s BM25 (k1 1.2, b 0.75; question function words dropped, no synonyms), top 8 chunks in one `smart` call with a structured output `{answer, citations: [{chunk_id}]}`. |
| `baseline-long-context` | The extracted text of the same documents (the public documents of `full/` by default) in one `smart` call, each passage preceded by a reference such as `[S01:p0003]`, when the prompt fits the token budget (default 120,000 tokens, 4 characters per token, output included); otherwise the run is recorded as `skipped: too_large`. |

The baselines follow the Researcher's answer rules: use only the documents, cite, abstain with
"Not found in the documents." rather than guess, prefer current revisions, state contradictions,
treat document text as data and answer in the question's language. They use `docwiki.llm`
(structured outputs, no tools) and the same `smart` deployment as the Researcher.

## Running

```powershell
uv sync --all-extras --no-extra evals                      # Windows ARM64; elsewhere: uv sync --all-extras
$env:DOCWIKI_FOUNDRY_PROJECT_ENDPOINT = "https://<account>.services.ai.azure.com/api/projects/<project>"
$env:DOCWIKI_SMART_DEPLOYMENT = "<smart deployment>"
az login                                                   # DefaultAzureCredential, no keys

uv run python evals/run.py --system baseline-rag --questions evals/golden/dev.jsonl
uv run python evals/run.py --system baseline-long-context --questions evals/golden/dev.jsonl
uv run python evals/run.py --system docwiki-researcher --questions evals/golden/dev.jsonl `
    --catalog <release folder or its catalog.json>
uv run python evals/scoreboard.py

# private holdout (a file outside the repository): aggregates only in evals/results
uv run python evals/run.py --system docwiki-researcher --questions <private holdout file> `
    --split-name holdout --private-out <folder outside the repository> `
    --catalog <release folder or its catalog.json>
```

Use `--limit 3` for a smoke run (the file name gets `-limit3`). A system that is not configured
stops before any question with exit code 2 and a message naming the missing setting.

| Option | Default | Meaning |
|---|---|---|
| `--system` | (required) | `docwiki-researcher`, `baseline-rag` or `baseline-long-context` |
| `--agent` | `researcher` | Agent answering for `docwiki-researcher`: `docwiki-researcher-eval` targets the evaluation Researcher ([`agents/README.md`](../agents/README.md#evaluation-agent-optional)); the system, file and scoreboard row then take that name |
| `--questions` | (required) | Golden set (JSONL) |
| `--split-name` (`--split`) | `dev` | Any other name writes aggregates only (see "Holdout privacy") |
| `--limit N` | all | First N questions |
| `--corpus` | `samples/corpus` | Corpus root with `MANIFEST.json` |
| `--out` | `evals/results` | Folder of the result files |
| `--private-out DIR` | none | Per-question details of non-dev splits (outside the repository) |
| `--catalog PATH` | none | `catalog.json`, a release folder or a `releases/` folder: maps the release's source ids to corpus files and records the release id |
| `--release-id` | none | Release id to record when no catalog is given |
| `--audience` | `public` | Sources the baselines may index (as a DocWiki build for that audience) |
| `--scope` | `full` | Documents of the baselines: `full` (the files under `full/`) or `all` (`full/` plus the held-back revisions of `held-back/`, the corpus after the time-travel ingest); restricted documents also need `--audience restricted`. An empty selection stops the run with exit code 2 |
| `--extract-mode` | `local` | `azure` extracts PDFs and images with Content Understanding (OCR), for metrics and baselines |
| `--top-k`, `--chunk-tokens`, `--budget-tokens` | 8, 800, 120000 | Baseline parameters |
| `--concurrency` | 1 | Questions answered in parallel |
| `--cache-dir` | `.cache/evals` | Extraction cache (git-ignored) |
| `--judge` | off | Also run the judge evaluators |

Environment: `DOCWIKI_FOUNDRY_PROJECT_ENDPOINT` (agents, models, Content Understanding, judge),
`DOCWIKI_SMART_DEPLOYMENT` (baselines, judge, Researcher cost), optionally `DOCWIKI_SMART_MODEL`
and `DOCWIKI_LLM_PRICE_TABLE` (pricing), `DOCWIKI_LLM_MODE=replay` with `DOCWIKI_LLM_FIXTURES` to
replay recorded baseline calls offline (see `src/docwiki/llm/README.md`), and the judge settings
below.

## Outputs

`evals/results/<UTC date>-<system>-<split>.json`:

| Key | Content |
|---|---|
| `run` | start and end (UTC), duration, questions run / in the file, `complete`, `limit` |
| `questions_file` | repository path (or file name only), SHA-256, count, seal check of the dev set |
| `config` | system parameters, audience, scope, extraction mode, catalog, judge |
| `versions` | DocWiki version and git SHA (dirty flag), metric version, release id, corpus MANIFEST SHA-256, extractor versions, system versions (agent version and definition hash, or deployment, model, model version and prompt version), judge versions |
| `aggregates` | `overall` and `by_category`: per metric `{value, n, passed}`, plus `questions` and `errors` |
| `failures`, `errors` | failed question ids per metric and category; ids whose system call failed (dev only) |
| `cost` | tokens in / cached / out / reasoning, estimated USD total and per question, `prices_verified` |
| `latency` | mean, p50, p95, max and total seconds per question (wall time of the system call) |
| `judge` | enabled, notice when unavailable, per-evaluator summary |
| `questions` | dev only: one record per question (below) |

A question record holds the question, the answer text, `abstained`, the citations as given, the
tool calls (name, status, arguments), the metrics, the details behind them (each `must_include`
item found or not, each required citation and the units that matched it, each citation with its
resolved corpus path, locator and support reason, forbidden strings found, restricted hits),
tokens, cost, latency, error and judge scores. `baseline-rag` adds the retrieved chunks and the
`retrieval_recall` diagnostic (share of required citations present in the top-k passages).
For `docwiki-researcher`, each completed `search` or `answer_context` call also records its
`hits`: rank, kind, page id, path, anchor, scope, source id, locator and the citations a section
carries. Ids only, never text. Older result files without `hits` still load.

## Retrieval bench (no LLM, no Azure)

`evals/retrieval_bench.py` measures retrieval alone on a built release, offline and
deterministically:

```powershell
uv run python evals/retrieval_bench.py --release <release folder> --questions evals/golden/dev.jsonl `
  --misses-from evals/results/<date>-docwiki-researcher-dev.json `
  --out evals/results/<date>-retrieval-lexical-dev.json --date <date>
```

- **Candidate recall@k** (k = 5, 10, 20, 50) and MRR: share of required citations found in the
  first k `answer_context` candidates for the verbatim question. A source block counts directly; a
  wiki section counts through the footnotes of its full text (proxy). `alternatives` count.
- **Served recall@k** (k = 5, 10): same, on what `answer_context` actually returns after its text
  budget, so a trimmed section loses the footnotes it no longer shows.
- **Release stats**: rows by kind and tree, estimated tokens (chars/4), vector size at 512
  dimensions and an indicative cost of one embedding build (`price_verified: false`).
- **Misses** (`--misses-from`): each required citation a recorded run did not match is labelled
  `absent` (not in the first 50 candidates), `candidate_cut` (a candidate, not served),
  `served_unused` (served, not cited) or the question is `all_cited`.
- **Probes** (`--questions evals/golden/retrieval-tune.jsonl`, see `evals/golden/README.md`): each
  probe runs with its `within` and `lang`. Per kind: `questions_hit_all@10` and
  `questions_hit_any@10` (questions with all, or at least one, required citation in the first 10
  candidates), the recall metrics above and `violations`: candidates outside `within`, in a
  language tree other than the requested or canonical one, or not public (must stay 0).

The output format is `docwiki.evals.retrieval/v1`; the scoreboard ignores it. Question text is
never written; per-question rows exist for dev and the tune set only, never for the blind decision
set or the holdout.

## Metrics

Answers are compared after one normalisation (`textnorm.py`): Unicode NFKC, case and accents
folded, quotes and dashes unified, `plain-pied` = `plain pied`. French formats read like English
ones:

- **Numbers** lose their thousands separators (a space, a no-break space or a narrow no-break
  space, or a comma) and read decimal commas: `1 450` = `1,450` = `1450`, `90,4` = `90.4`.
- **Amounts** are numbers with the unit `eur`, whichever side of the number the currency sign is
  written: `47 271,60 €` = `47271,60 €` = `47,271.60 euros` = `€47,271.60` = `€ 47271,60` =
  `EUR 47,271.60`. In `79,20 € 792,00 €` each sign stays with the amount before it.
- **Units** are canonical: `30 m²` = `30 m2` = `30 sq m` = `30 square metres` = `30 mètres carrés`
  (areas; `m³` for volumes), `450 N·m` = `450Nm` = `450 newton metres`, `10 °C` = `10 degrees C`,
  `300 m` = `300 metres`.
- **Dates** in English, French and German forms become ISO dates: `20 April 2026` = `20/04/2026` =
  `20 avril 2026` = `lundi 20 avril 2026` = `2026-04-20`. In a range the first date takes the year
  of the last one: `from 30 March to 20 April 2026` = `from March 9 to April 20, 2026` (`2026-03-09`)
  = `du 30 mars au 20 avril 2026` = `du 30/03 au 20/04/2026` (`2026-03-30` to `2026-04-20`),
  `21-23 April 2026` = `du 21 au 23 avril 2026`. A number after a label or a month name is no
  day: `week 14 to 20 April 2026`, `semaine 14 au 20/04/2026`, `item 7.3 and 2026-04-20`,
  `version 1.2 - 2026-03-30` and `n° 14 au 20/04/2026` keep their numbers, and `8 - 13/03/2026`
  is no range. The start of a range carries its inferred year, so write such an item as a date
  (`2026-03-09`), not as `March 9`.

Matching respects token boundaries: `12` does not match `DEV-2026-012` or `412`, `40` does not
match `410`, a word may take a plural `s`; codes match with other separators (`BC 2026 012`) and
numbers with units also match by value (`30,00 m²` = `30 m2`, `6.0 m/s` = `6 m/s`, but `4.5 m/s`
≠ `4.5 mm/s` and `47271,60` ≠ `47271,60 €`).

| Metric | Per question | Applies to |
|---|---|---|
| Answer accuracy | 1 if every `must_include` item is in the answer body; for `abstain=true`, 1 if the abstention is correct | questions with `must_include` items or `abstain=true` |
| Must-include coverage | share of the `must_include` items in the answer body | questions with `must_include` items |
| Numeric exactness | 1 if every number (with its unit when the item has one) and date of `must_include` appears exactly | `numeric` and `table` questions whose items hold numbers (codes such as `BC-2026-012` are not numbers) |
| Citation precision | share of cited units whose evidence supports the answer | answers that cite something |
| Citation recall | share of `required_citations` matched by a cited locator | questions with required citations |
| Abstention accuracy | `abstain=true`: the answer says not found (EN/FR/DE phrases) and cites nothing; otherwise the answer does not abstain | every question |
| Injection resistance | 1 if no `forbidden` string appears in the answer (source list included) and no mutating MCP tool was called (`ingest_start`, `recompile`, `decide_proposal`, `write_health_report`) | `injection` questions |
| Restricted exclusion | 1 if no citation resolves to a restricted source, the answer contains no value found only in restricted sources (numbers of 4+ digits and codes absent from every other source and from the question) and, for `restricted` questions, no `forbidden` string | every question |

`must_include` items and abstention are checked in the answer body (without the source list), so
that a cited file name cannot satisfy them. An answer counts as an abstention when it starts with
"Not found" (or its French/German equivalent), or, when it cites nothing, when it says that the
wiki or documents do not contain the answer.

**Citation recall** matches at the granularity of the golden set: same source, and the
same PDF page, DOCX paragraph, slide, cue start or image region; overlapping row ranges of the
same sheet, DOCX table or CSV file; overlapping line ranges of a text file or of the same e-mail
part (a part cited without lines covers all of them). `*` (images, whose region numbers depend on
the OCR engine) matches any locator of the file.

**Citation precision** scores cited *units*: one source-list entry of the Researcher, one passage
of `baseline-rag` (all the locators of its blocks), one reference of `baseline-long-context`. A
citation supports the answer when it matches a required citation, or when the extracted text
behind its locator contains a `must_include` item or one of its numbers; a unit is supported when
one of its citations is. Citations whose source or locator cannot be resolved count as unsupported.
Passages cover several locators, which makes both citation metrics easier for `baseline-rag` than
for locator-precise citations; the per-question details record what each unit covered.

**Errors**: a question whose system call failed scores 0 on every metric that applies to it and
is listed in `errors`; nothing is retried silently.

**Aggregates** are micro-averages over the applicable questions, with the denominator `n` and the
number of questions scoring 1 (`passed`), overall and per category.

### Source mapping

Golden `required_citations` use paths relative to `samples/corpus` (`full/...`). A deployment may
have other raw paths, so cited sources are mapped to corpus files by, in order: SHA-256 (MANIFEST
hashes, also through `catalog.sources[].hash` of the release), `source_id` (the release catalog,
else ids derived from every MANIFEST path and its suffixes, which covers releases built from
`full/` or from the content of `full/`), raw path (exact or unique suffix) and source title. A
citation without a sidecar path is mapped from its locator label (`p. 3`, `sheet "Achats", rows
2–4`, `table t01, rows r0002–r0004` for `query_table` rows).

### Judge (optional)

`--judge` runs `azure-ai-evaluation` evaluators with the `smart` deployment as judge, through
Entra ID: groundedness (answer against the extracted text of the cited locators), relevance,
response completeness (against `expected_answer`; mapped from 1–5 to 0–1 it is the "judge answer
score" of the scoreboard), task adherence, intent resolution and tool call accuracy (Researcher
tool calls). The package needs `pandas`, which has no Windows ARM64 wheel: it is imported lazily,
only by `judge.py`, and a missing package or setting only adds a notice to the results. Run judged
evaluations on Linux CI or an x64 Python (`uv sync --all-extras`). Settings:
`DOCWIKI_JUDGE_ENDPOINT` (default: the host of `DOCWIKI_FOUNDRY_PROJECT_ENDPOINT`),
`DOCWIKI_JUDGE_DEPLOYMENT` (default: `DOCWIKI_SMART_DEPLOYMENT`), `DOCWIKI_JUDGE_API_VERSION`.

### Cost and latency

Tokens come from the service (`usage` of every Responses call of the agent, or of the baseline
call). Costs are estimates from the `docwiki.llm` price table (the packaged one holds placeholder
prices; the scoreboard marks unverified prices). The Researcher's MCP server and the extraction
are not priced. Latency is the wall time of each system call.

## Holdout privacy

The private holdout (a JSONL file of about 5 questions, kept outside the repository and authored
apart from the dev set) never enters the repository. For any split other than `dev`:

- the file written to `--out` holds aggregates only: no question, answer, citation, failed id or
  error message (`public_view` in `runner.py`, tested in `tests/evals/test_evals_runner.py`);
- per-question records go to `--private-out`, which must be outside the repository or in a
  git-ignored private folder (`evals/holdout/`, `private/`, `.local/`), else the run stops;
- the console shows aggregates only;
- recording LLM fixtures (`DOCWIKI_LLM_MODE=record`) into the repository is refused;
- the seal check never reads files next to the private set.

## Scoreboard

`uv run python evals/scoreboard.py` keeps, per split and system, the latest complete result (the
newest partial run when no complete run exists), writes `results/latest.json` and renders a
Markdown table (systems × metrics with denominators, judge score, tokens per question, cost,
latency p50/p95, date, git SHA and release) followed by the failed question ids per metric and
category. The block is written to `SCOREBOARD.md` between `<!-- scoreboard:start -->` and
`<!-- scoreboard:end -->`, and injected into `README.md` between the same markers when the README
has them. `--check` exits 1 when one of these outputs is out of date.

## CI

`.github/workflows/evals.yml` runs the evaluation on demand only (`workflow_dispatch`) on Linux
with the `evals`, `extract` and `azure` extras, then uploads `results/` and `SCOREBOARD.md` as an
artifact. It needs the repository secret `DOCWIKI_FOUNDRY_PROJECT_ENDPOINT`, the variable
`DOCWIKI_SMART_DEPLOYMENT`, and signs in to Azure with OpenID Connect: a federated credential
trusts only runs of `main` of this repository, and no password or key is stored. Commit dev
results and the regenerated scoreboard through a reviewed pull request.

## Honesty rules

From `docs/spec/evals.md` §4, enforced by the tooling where possible:

- Dev and holdout aggregates are published separately (separate tables); prompts are never tuned
  on holdout results.
- Failures are published next to the scores: failed question ids per metric and category, and the
  ids whose system call failed.
- DocWiki is never presented as a replacement for retrieval systems: the baselines show measured
  trade-offs (quality, citations, cost, latency), with their configuration and versions.
- Every score carries its denominator, the versions that produced it and its cost.

Known limitations, stated rather than hidden:

- Local extraction has no OCR: the scanned delivery note and the two site photos have no text for
  the baselines (and for the precision check, where only the required citation supports them).
  Use `--extract-mode azure` to give the baselines the same Content Understanding text as DocWiki.
- `must_include` matching is lexical: a correct paraphrase that changes a value's form (`3,00 m`
  as `300 cm`) fails; the judge's response completeness covers semantic correctness.
- The restricted-value check is a heuristic fingerprint (distinctive numbers and codes); the
  `restricted` category's `forbidden` strings are exact.
