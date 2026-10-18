# The two agents

DocWiki ships two Microsoft Foundry **prompt agents**. They are declarative (instructions, a model
deployment and one MCP tool), versioned as code in [`agents/`](../agents/README.md), and they reach
the wiki only through the DocWiki MCP server. Neither agent computes anything heavy: compilation
runs in a Container Apps Job, and the agents read its results or ask it to run
([ADR 0002](adr/0002-aca-job-with-agent-control-plane.md)).

| | Researcher | Librarian |
|---|---|---|
| Foundry name | `docwiki-researcher` | `docwiki-librarian` |
| Purpose | Answer questions with verifiable citations | Operate and maintain the wiki |
| Model deployment | `smart` | `smart` |
| MCP app roles | `Wiki.Read` | `Wiki.Read`, `Wiki.Operate` |
| Tools | 10 read tools | 10 read tools and 9 operations tools |
| Human approval | Never needed | Every call to `ingest_start`, `recompile`, `decide_proposal` |
| Instructions | [`agents/researcher/instructions.md`](../agents/researcher/instructions.md) | [`agents/librarian/instructions.md`](../agents/librarian/instructions.md) |

## Tools and roles

| Tool | Role | Approval (Librarian) | What it does |
|---|---|---|---|
| `search` | Wiki.Read | none | Full-text search over page sections and raw source blocks, with glossary synonyms |
| `read_page` | Wiki.Read | none | A page or one section, with frontmatter, links and one citation per footnote |
| `get_index` | Wiki.Read | none | Home, sources, entities (by type), topics, queries, glossary or log index |
| `get_links` | Wiki.Read | none | Outgoing links and backlinks with edge kinds |
| `glossary` | Wiki.Read | none | Terms, synonyms per language, related pages |
| `get_evidence` | Wiki.Read | none | Verbatim sidecar content with locator, label, provenance and badge |
| `query_table` | Wiki.Read | none | One read-only DuckDB `SELECT` over a source's tables, at most 200 rows, with row ids |
| `get_skill`, `list_skills` | Wiki.Read | none | The wiki's Agent Skills |
| `recent_changes` | Wiki.Read | none | Log entries, newest first |
| `run_status` | Wiki.Operate | none | Latest or selected run report, and whether its release is served |
| `list_sources` | Wiki.Operate | none | Per-source status, stage, last error, sensitivity |
| `quality_report` | Wiki.Operate | none | Gate results G01 to G15 of a release |
| `explain_source` | Wiki.Operate | none | Diagnostics of a failed or quarantined source |
| `list_proposals` | Wiki.Operate | none | Entity, glossary, topic, injection and recompile proposals |
| `write_health_report` | Wiki.Operate | none | Writes a sanitised `work/reports/health-<date>.md` |
| `ingest_start` | Wiki.Operate | **required** | Enqueues an ingest (identical requests within about 10 minutes are not queued twice) |
| `recompile` | Wiki.Operate | **required** | Enqueues a recompile of named sources with operator notes for the compile prompt |
| `decide_proposal` | Wiki.Operate | **required** | Accepts or rejects a proposal; accepted ones flow into the domain overlay |

Every result is one JSON object whose first key is `ok`, bounded to 12,000 characters with
`truncated` and `next_offset` for paging. Failures are normal results such as
`{"ok": false, "error": {"code": "not_found", "message": "...", "details": {"suggestions": [...]}}}`
with codes `invalid_argument`, `not_found`, `forbidden`, `conflict`, `too_large`, `unavailable`,
`timeout` and `internal`. This matters: Foundry aborts the whole agent turn when an MCP tool
returns a protocol error, so returning failures as results lets the agent read the message and
adapt. The full reference is in the [MCP server README](../src/docwiki/mcp/README.md).

## Researcher

The Researcher treats the wiki as the map and the evidence sidecars as the ground truth.

```mermaid
flowchart LR
  q["Question"] --> s["search<br/>glossary for acronyms<br/>and other languages"]
  s --> r["read_page<br/>topic, entity, source"]
  r --> l["get_links<br/>when it leads closer"]
  r --> e["get_evidence<br/>query_table for numbers"]
  l --> e
  e --> a["Answer with [n] citations<br/>or Not found in the wiki."]
```

- **Bounded.** At most 12 tool calls per question; when the evidence is still insufficient it says
  what is missing instead of searching further.
- **Cites sources, never the wiki.** Generated pages and filed research answers are not
  independent evidence. Every factual sentence ends with `[n]`, and the answer ends with:

  ```text
  Sources:
  [1] <source title> — <locator label> (<provenance>) — <sidecar path>
  ```

  A number computed with `query_table` cites the table and row ids it used.
- **Current before superseded.** It gives the current value first and names the source that
  superseded the old one.
- **Contradictions stated, not resolved silently.** Both claims with citations, authority and
  dates, then the wiki's resolution rule.
- **Honest provenance.** OCR text may contain recognition errors; a generated figure description is
  never quoted as the document.
- **Abstains.** "Not found in the wiki." (translated to the question's language), with what was
  searched and what is missing, and no source list. No outside knowledge for facts about the
  corpus.
- **Language.** Answers in the language of the question; quotations stay in their original
  language.
- **Documents are data.** It never follows instructions found in tool results and mentions a
  "possible prompt injection" when relevant.

`docwiki.agents_client.parse_answer` parses the `Sources:` list (tolerating common drift) so that
`docwiki ask` and the evaluation runner can check citations.

## Librarian

The Librarian operates the pipeline through the same MCP server and never writes wiki content
itself: content changes only through runs and accepted proposals.

- **Facts come from tools.** It never claims that a run started, succeeded or failed without
  `run_status`, and a queued run is not a finished run.
- **Approval first.** Before calling `ingest_start`, `recompile` or `decide_proposal` it explains
  the tool, the exact arguments, the expected effect and how it will verify it; it calls once, and
  if a human denies the call it does not retry or work around it.
- **Exception lane.** It finds failed or quarantined sources (`list_sources`, `quality_report`),
  diagnoses each with `explain_source`, and proposes a `recompile` with precise operator notes
  (observed problem, evidence, expected correction). It escalates to a human instead of looping
  when the cause is outside the content pipeline (unreadable file, wrong sensitivity, permissions,
  a blocking gate), when a recompile already failed, or when it suspects prompt injection.
- **Proposals.** It reviews open proposals against their evidence and recommends a decision; it
  decides only when a human asks. Injection proposals are reported, never acted upon.
- **Health report.** Release, gate summary, sources by status, top issues, open proposals,
  recommended actions, written with `write_health_report` using only numbers returned by the
  tools.

### Approvals

Approvals are enforced by Foundry (`require_approval: always` for the three mutating tools, checked
when `agents/deploy.py` validates the definitions) and handled by the client:

- In the Foundry portal or any Responses API client, an `mcp_approval_request` waits for an
  explicit `mcp_approval_response`.
- `docwiki ask "..." --agent librarian` asks on the console in a terminal and denies otherwise
  (`--approve prompt` or `--approve deny` makes it explicit).
- In Python, `AgentClient.ask(..., approve=callback)` calls your callback; without one, every call
  is denied.

### Daily routine (optional)

[`agents/librarian/routine.yaml`](../agents/librarian/routine.yaml) defines
`docwiki-librarian-daily-health`: a Foundry routine that invokes the Librarian every day at 06:00
UTC with a fixed prompt that uses only `run_status`, `quality_report`, `list_sources`,
`list_proposals` and `write_health_report`, because nobody is there to approve a call. It is
disabled by default; `DOCWIKI_ENABLE_ROUTINE=true` (or `agents/deploy.py --routine enable`)
turns it on.

## Identity and enforcement

Tool visibility is not authorization. Each agent calls the MCP server with **its own Entra agent
identity**, created with the agent and kept across its versions:

1. The project connection `docwiki-mcp` (`RemoteTool`, `AgenticIdentityToken`) makes Agent Service
   request an app-only token for the calling agent, for the MCP API audience.
2. Entra issues it only if the agent holds an app role on the MCP API (`appRoleAssignmentRequired`).
3. Container Apps built-in authentication accepts only that audience and the two agents' client
   IDs.
4. The MCP server validates the forwarded token again (so a forged principal header never
   suffices), reads its role claims, hides the tools the caller may not use and answers a
   forbidden call with a `forbidden` result.

The identity spike verified each layer (the server's own token validation was added later, see
[`src/docwiki/mcp/README.md`](../src/docwiki/mcp/README.md#bearer-token-validation)): the two
agents presented different principals, the Researcher's call to an operations tool was refused by
the server, anonymous and wrong-audience calls got 401, and a valid token from a client outside
the allowlist got 403
([ADR 0003](adr/0003-mcp-agent-identity.md), [report](spikes/identity-spike.md)). Operational
consequences:

- Deploy agents by **adding versions** (`agents/deploy.py` does only that): a version keeps the
  identity. A deleted and recreated agent gets a new identity and loses its roles until the
  post-provision hook runs again.
- To block an agent immediately, remove its client ID from the allowlist
  (`DOCWIKI_MCP_BLOCKED_AGENTS`); removing an app role only takes effect when the cached token
  expires. See [operations](operations.md#identities-and-access).

## Deploy and ask

```bash
uv run python agents/deploy.py --dry-run          # exact request bodies, no Azure call
uv run python agents/deploy.py                    # a new version only when the definition changed
uv run docwiki ask "Which gearbox oil grade applies to WTG-07 in winter?"
uv run docwiki ask "What is the status of the last run?" --agent librarian
```

`azd up` runs the deployment for you (see [BOOTSTRAP.md](../BOOTSTRAP.md#step-12--deploy-and-smoke-test-the-agents)).
Each version stores the SHA-256 of its resolved definition, so an unchanged definition is reported
`unchanged`. `docwiki ask` pins the latest version and prints the answer, with its `Sources:` list,
followed by a one-line receipt (agent version, tool calls, tokens, latency); `--json` prints the
full record and `--conversation` continues a conversation.

## Known gaps

- Filing an approved research answer back into `queries/` is part of the wiki format, but no tool
  writes query pages yet; existing query pages are carried into new releases.
- With the MCP app scaled to zero, the first agent turn after a pause takes about 30 s longer (38.8 s
  cold versus about 8 s warm in the identity spike). Set `DOCWIKI_MCP_MIN_REPLICAS=1` for demos.
