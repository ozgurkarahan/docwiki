# ADR 0013 — Index-first Researcher

- Status: Accepted 2026-10-27 (slice D1; measured on the next dev evaluation)
- Amends: [mcp-and-agents.md](../spec/mcp-and-agents.md) §2, Researcher instruction requirements
  2 and 3 (every decisive fact confirmed with `get_evidence`, at most 12 tool calls)
- Spec: v1.8

## Context

The Researcher is the live agent of the public demo: a visitor asks a question in the wiki and
waits for the answer. The development evaluation of 2026-10-23 measured it at a median of 32 s
and a 95th percentile of 71 s per answer. It made 13 sequential tool calls per answer on average
(of 417 calls: 168 `read_page`, 128 `get_evidence`, 87 `search`, 22 `query_table` and only 5
`get_index`), about 2.9 s per step, and resent about 24,000 input tokens per question because
the whole context goes back to the model at every step.

Most of these calls re-read what the wiki already says with its citations. A compiled wiki page
cites, sentence by sentence, the evidence sidecar of the locator it comes from; the quote of a
native-text citation was verified by code when the page was compiled (badge "quote verified"),
and every table citation names the exact rows. The protocol still asked the agent to open
`get_evidence` for every decisive fact and to explore with `search`, then `read_page` of whole
pages, then `get_links`, one call at a time. That is the vector-search habit the compiled wiki
was built to remove ([ADR 0001](0001-compiled-wiki-over-vector-index.md)).

## Decision

1. **One broad call first: `answer_context`.** A new read tool (role `Wiki.Read`) returns, in one
   size-bounded result built at run time from the release's `search.db` and `catalog.json` (no
   new pipeline output, no recompile): the best search hits for the question, each with the text
   of its own section (or, for a source block, the verbatim content of its evidence sidecar) and
   the citations of that text in the same fields as `read_page`; the start of the home index; the
   start of the hub page of the scope given in `within`, or shared by most hits; and the list of
   computed views. It filters by `within` and `lang` like `search`, and never returns content
   above the release's audience.
2. **Cite what the tools returned.** An answer may cite the citations returned by
   `answer_context`, `read_page` or `search` (a source hit with its evidence path). `get_evidence`
   is only needed to quote a decisive passage verbatim when the returned text is not enough.
3. **At most 6 tool calls**, independent calls in parallel: `answer_context`, then at most one or
   two targeted calls (`read_page` of one section, `query_table` for numbers, `read_page` of a
   computed view, `search` with other words), then the answer.
4. Unchanged: the abstention rule ("Not found in the wiki."), the restricted exclusion, the
   citation and source-list format, current over superseded, explicit contradictions.

## Consequences

- Target: median ≤ 12 s and ≤ 6 tool calls per answer, with answer accuracy ≥ 71.9 %, numeric
  exactness 100 %, restricted exclusion 100 % and citation precision not lower than the
  2026-10-23 baseline. The next dev evaluation decides whether the protocol stays.
- Citations still point to evidence sidecars, and live answers still pass the quote and leak
  checks of ADR 0008 before they are shown; what changes is that the agent trusts the citations
  the compiled wiki already verified instead of re-opening each sidecar.
- A citation is only as good as the sentence that carries it: the agent must cite a citation
  only for what its text says. The evaluation's citation precision watches this.
- The wiki's own agent kit (the `wiki-navigator` skill and `AGENTS.md` written by the
  `agentkit` stage for local agents) keeps the search-first protocol and its 12-call budget
  until the next stage version: changing it changes the published wiki.

## Measured (2026-10-27) and first revision

The first dev evaluation of this protocol (32 questions) halved the tool calls (13.0 → 6.2 on
average) and lowered the median latency from 32.3 s to 25.0 s (p95 62 → 47.5 s), the cost from
$0.164 to $0.124 a question and raised citation precision from 65.9 % to 77.5 %; answer
accuracy moved from 71.9 % to 68.8 % (one question; partial omissions on questions that span
several chantiers). The time left was mostly the model's own work per turn: long answers (800 to
4,400 output tokens) and reasoning, and a few hard questions still made 13 to 16 calls.

The revision keeps the tool and changes the agent only: reasoning effort `low` (new optional
`reasoning_effort` in `agent.yaml`), answers under 150 words before the source list, a hard stop
at six calls, `read_page` of a section only, and `answer_context` with `limit: 10` when the
question names no chantier.

Its evaluation (agent version 8) reached a 12.3 s median ($0.087 a question) but answer accuracy
fell to 59.4 % and numeric exactness to 77.8 %: low effort mostly lost the number questions.
The Researcher therefore runs at reasoning effort `medium`, keeping the short answers and the
six-call stop; `reasoning_effort` stays available for any agent.

At medium effort (agent version 9) the median was 18.5 s and accuracy still 59.4 % (numeric
exactness 88.9 %): the loss came from the 150-word limit, which dropped requested dates and
amounts from answers that list several items. **Decision:** the Researcher keeps the first
index-first definition (agent version 7: 25.0 s median, 68.8 % accuracy, 100 % numeric
exactness, citation precision 77.5 %, $0.124 a question), with no word limit and the default
reasoning effort. Faster answers next need streaming (the answer appears as it is written) or a
smaller model for simple questions, not shorter answers.

