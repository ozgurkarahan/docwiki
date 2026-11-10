# Wiki ablation - the same agent with and without the compiled wiki (paired A/B)

An expert in retrieval asks first: is it the wiki or the agent? The published baselines are
one-shot (BM25 top 8; one model reading every document), while the Researcher is an agent that
plans, searches several times and reads tables. This experiment removes the compiled wiki and
keeps everything else. This file states the reading rules **before** the paid run; the results are
appended below the line, whatever they show.

## Arms (same day, same release, same question file)

- **wiki** = production: the production Researcher on the production MCP server.
- **no wiki** = the evaluation Researcher (`agents/deploy.py --eval`: the same definition,
  instructions and model, another name and MCP connection) on the evaluation MCP app, which runs
  the production code with `DOCWIKI_MCP_WIKI_ABLATION=raw`: `answer_context` and `search` return
  only the documents' extracted blocks (no revision status, home index, hub or views),
  `get_evidence` and `query_table` work, and the wiki tools (`read_page`, `get_index`,
  `get_links`, `glossary`, `get_skill`, `list_skills`, `recent_changes`) answer `not_found`.

Both arms serve the same release id, recorded in every result file; production is not changed.
Questions: the public dev split (`evals/golden/dev.jsonl`, 32 questions). A question passes when
`answer_accuracy == 1` (abstention accuracy for `abstain=true`). Every discordant question is
replayed 2 more times per arm; verdict = majority of 3.

## Reading rules (fixed before the run)

This is a measurement, not a switch: nothing is deployed to production whatever the result.

1. **Net effect of the wiki** = questions passing with the wiki and not without, minus the
   reverse, after replays.
   - **>= +3**: the wiki adds answers the same agent cannot find in the raw blocks.
   - **-2 to +2**: no measurable difference on 32 questions (two questions is noise).
   - **<= -3**: the raw blocks serve the agent better than the wiki.
2. Reported per category (multi-hop, numeric, tables, supersession, contradictions, abstention,
   skills), with question ids, so the effect can be located even when the net is small.
3. Safety must hold in both arms: restricted exclusion and injection resistance at 100 %. A
   failure in either arm is reported first.
4. Also reported: numeric exactness, citation precision and recall, median and p95 latency, tool
   calls (median, p95) and cost per question, and the number of calls the no-wiki agent made to
   switched-off tools.

## Known biases (stated before the run)

- The instructions were written for the wiki (start with `answer_context`, read sections, use the
  views). The no-wiki agent keeps them, so it may spend calls on switched-off tools: this favours
  the wiki arm. Their count is published (rule 4).
- The search still expands queries with the domain pack's glossary synonyms (hand-written
  configuration, not compiled), in both arms.
- The questions were written for a corpus whose wiki was then compiled; dev results have been
  read before (the dev split is not held out).

## Cost

Estimate: about 4 USD per arm on dev, plus replays: about 12 USD (unverified list prices).

---

## Results (run 2026-11-10 UTC, both arms the same hour)

Same release `20261027T222241Z-f4e7ba11` and git SHA `a68bd29` in both result files; production
Researcher v10, evaluation Researcher v3 with the same definition; evaluation MCP app on image
`mcp-eval:ablation-a68bd29` with `DOCWIKI_MCP_WIKI_ABLATION=raw` (a smoke question confirmed that
every hit was a source block). Production was not changed. Result files:
[`wiki-dev.json`](2026-11-09-wiki-ablation/wiki-dev.json),
[`nowiki-dev.json`](2026-11-09-wiki-ablation/nowiki-dev.json).

| Measure (dev, 32 questions, first run) | wiki | no wiki |
|---|---|---|
| Answer accuracy | 62.5 % (20/32) | 62.5 % (20/32) |
| Numeric exactness | 88.9 % (8/9) | 66.7 % (6/9) |
| Citation precision | 75.4 % (n=31) | 67.0 % (n=30) |
| Citation recall | 55.5 % (n=30) | 52.9 % (n=30) |
| Must-include coverage | 86.3 % | 82.3 % |
| Abstention accuracy | 96.9 % (31/32) | 100.0 % (32/32) |
| Restricted exclusion, injection resistance | 100 %, 100 % | 100 %, 100 % |
| Latency p50 / p95 | 22.6 s / 45.0 s | 24.9 s / 48.8 s |
| Tool calls p50 / p95 | 5.5 / 11 | 5.5 / 10 |
| Calls to switched-off wiki tools | - | 12 |
| Cost (unverified prices) | 3.70 USD | 3.20 USD |

Eight questions were discordant on the first run; each was replayed twice more per arm (pass on
runs 1, 2, 3; verdict = majority):

| Question | Category | wiki | no wiki | Verdict |
|---|---|---|---|---|
| q014 | skill (check a supplier invoice) | pass, pass, pass | fail, fail, fail | wiki |
| q025 | numeric (financial position of each chantier) | pass, pass, pass | fail, fail, fail | wiki |
| q026 | numeric (same, in French) | pass, pass, pass | fail, pass, fail | wiki |
| q030 | multi-hop (when are the windows delivered, French) | pass, fail, pass | fail, fail, pass | wiki |
| q011 | abstain (architect of the Moreau extension) | fail, fail, pass | pass, pass, pass | no wiki |
| q029 | multi-hop (when are the windows delivered) | fail, fail, fail | pass, pass, fail | no wiki |
| q031 | supersession (school DPGF indice A to B) | fail, fail, pass | pass, pass, pass | no wiki |
| q032 | supersession (same, in French) | fail, fail, fail | pass, pass, pass | no wiki |

**Reading (rules fixed above).**

1. Net effect of the wiki: 4 - 4 = **0**: **no measurable difference** in answer accuracy on 32
   questions.
2. Where it differs: the wiki wins where it holds a **computed or compiled synthesis**. The
   financial position of every chantier is one call to a computed view; without it, the agent
   misses the totals after 5 to 9 calls and three `query_table` calls. Without the wiki the
   supplier-invoice skill is switched off, and the answer misses the billed unit price (79,20 €)
   in all three runs. The raw blocks win on the superseded detail: the wiki holds the total of the
   superseded indice A (85 200,00 € HT, on its source page and in the topic's table), but the agent
   answered from the current revision and left it out, while without the wiki it queried both
   DPGF tables and compared them. The abstain
   question is a scoring artefact, not a wrong answer: with the wiki the agent also says that no
   architect is named for the Moreau chantier, but it cites the contract while doing so, and the
   abstention metric only accepts an answer that cites nothing (`evals/metrics.py`,
   `is_abstention`).
3. Safety held in both arms.
4. With the wiki, numbers are more often exact (8/9 against 6/9) and citations more precise
   (75.4 % against 67.0 %), the median answer is 2.3 s faster and a run costs 16 % more.

What this says, and what it does not. On this corpus, an agent that can search, read the evidence
and query the parsed tables already answers as many questions from the raw blocks as from the
wiki; the wiki's measurable value is in exact numbers, more precise citations and the computed
cross-chantier views, and its measurable weakness is that an agent reading summaries of the
current revision leaves out superseded details the wiki does hold. The no-wiki arm kept
instructions written for the wiki (12 calls to switched-off tools), a bias in favour of the wiki
arm. The wiki arm passed 20/32 here against 22/32 on 2026-10-27 with the same agent: run-to-run
variance is of the size of the effects. 32 questions on one small corpus: the next measurement
needs more questions and the blind or holdout sets.

Cost: first runs 6.90 USD, smoke 0.09 USD, replays 3.26 USD: **10.25 USD** (unverified list
prices).