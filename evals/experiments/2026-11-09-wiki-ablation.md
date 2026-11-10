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
