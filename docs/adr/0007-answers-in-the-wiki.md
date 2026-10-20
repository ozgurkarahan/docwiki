# ADR 0007 — Answers in the wiki: filed Researcher answers and an "Ask this wiki" panel

- Status: Proposed (spec v1.3, owner review pending)
- Amends: D13 ("Quartz static site for humans; no custom UI to maintain")

## Context

Visitors of the public wiki never meet the agents: the Researcher lives in DocWiki Studio, an
owner-only app, and the wiki itself is static. The owner wants the agent inside the wiki ("on the
same page or as a popup, never in another app") and its citations to lead to the evidence.

Constraints:

- The public site (served by the Azure portal) is static, `default-src 'self'`, without
  analytics or external scripts (site.md §2, §5). It has no backend and no sign-in.
- A live Researcher answer costs about 0.12 USD and 20 to 110 s (docs/cost.md). Anonymous live
  questions mean model spend, abuse handling and a backend for every public host.
- The wiki contract already defines `queries/` pages, "research answers filed back after
  approval" (wiki-contract §1, §3), and the pipeline carries them into every new release and flags
  citations of withdrawn sources (`carry_queries`). Nothing writes them yet.

## Decision

1. **Visitors get reviewed answers, not a live model.** The public site lists suggested questions
   whose answers were produced by the Researcher, reviewed by the owner and filed as `queries/`
   pages. Live questions stay with the owner (Studio) and with anyone's own agent (MCP, stdio).
2. **One small static component.** An "Ask this wiki" button on every page opens a drawer: the
   filed questions (those that cite the current page first), the selected answer with its numbered
   citations and provenance badges, "How the agent worked" and a provenance line (agent version,
   date, release, reviewed by the owner). A citation opens the evidence in the main view: on wide
   screens the drawer stays open beside it (it takes the place of the right-hand panel and the page
   column narrows); on narrower screens it collapses to a "Back to the answer" button. No free-text
   input. Data: `answers.json`, emitted by the site build from the `queries/` pages and rendered
   with DOM nodes and `textContent` only. The drawer is part of every page's HTML (a layout
   component), so Quartz's page navigation keeps it; its state lives in `sessionStorage`.
3. **Filing path.** A reviewed answer becomes a query page in an inbox, `work/inbox/queries/`, and
   the next run merges the inbox into `queries/`. Every model output is cached, so this run costs
   nothing and takes about three minutes.
   - Writers: the owner's CLI (deployer data role) and the Studio's "File to wiki" button (its
     identity gets a custom role on `work`, blob read, write and create only, with a condition:
     writes only under `inbox/queries/`; no delete, move or container management). The jobs
     identity merges and deletes consumed items.
   - Trigger: an Event Grid subscription on `work` blobs created under `inbox/queries/` sends to the
     `ingest` queue (the job is level-triggered; the six-hourly reconcile covers a perimeter
     deployment). A non-empty inbox is never a no-op.
   - Format: the contract's query page. `asked_by: human` for a person's question,
     `approved_by: owner` (a fixed label, never a name or address), `sources` = every cited source,
     `sensitivity` = the highest tier among them. The body is the answer with contract footnotes to
     evidence sidecars, then "How this answer was produced" (agent and version, date, release, tool
     steps), then the footnote definitions. An honest "Not found in the wiki." answer is allowed
     (`sources: []`). Filed answers are written in English (D10); quotations keep their language.
   - Safety: the filed text goes through the content-safety rules of wiki-contract §10 before it
     reaches the inbox, and again in the run (quality gates G05, G08).
4. **Audience and staleness.** A build drops the whole query page, never only its citations, when
   its audience excludes any cited source (D11: "no mention"); the tier is never lowered. A cited
   source that was withdrawn keeps today's warning banner; a cited source that was superseded adds
   a banner naming the current revision.
5. **Evaluation stays honest.** Filed answers are a map, never evidence: the Researcher already
   cites sources, not wiki pages. Suggested questions never repeat golden questions; the golden set
   is evaluated before the first filing and again after it, and both results are published.

## Alternatives considered

- **Live agent in the public portal**: model spend and abuse risk for anonymous visitors, a
  backend on every public host, and a CSP exception for the public host. Rejected by the owner.
- **Cross-origin API called from a separately hosted static site**: same spend, plus CORS and a
  second deployment to keep in step with the static site.
- **Agent only in the Studio**: the owner's requirement is the agent inside the wiki.

## Consequences

- The wiki compounds: an owner's good question becomes a page that people and agents can read,
  search and link, with the same evidence links as any compiled page.
- One custom component to maintain in the overlay (D13 amended), with tests for the drawer, the
  page navigation and 375 px.
- Answers are snapshots: the release date, the provenance line and the staleness banners show their
  age; refiling refreshes them.
- New infrastructure: one custom role (creating it needs
  `Microsoft.Authorization/roleDefinitions/write`, which Owner and User Access Administrator
  include), one role assignment with a condition and one Event Grid subscription.
