# ADR 0008 — One experience: the live agent in the wiki

- Status: Accepted 2026-10-21
- Supersedes in part: [0007](0007-answers-in-the-wiki.md) (decision 1, "visitors get reviewed
  answers, not a live model", and "no free-text input"); D13's invariant "no public endpoint calls
  an LLM" (architecture.md section 8)
- Spec: v1.5

## Context

DocWiki is a public proof of concept that has to be easy to understand and easy to present: messy
documents become a cited wiki served on Azure Container Apps, with Foundry agents working *inside*
that wiki. ADR 0007 put the agent in the wiki for visitors only as reviewed, filed answers, and left
live questions to the owner's Studio, a separate app. A visitor could read what the agent once
said, never ask it.

## Decision

The owner decided on 2026-10-21 (`AGENTS.md`, "Owner decisions"): the wiki and the agents are one
product, the agent lives in the wiki page, and a public LLM endpoint is allowed, with limits.

1. **Same origin.** The drawer asks the portal that serves the wiki: `POST /api/ask` (202 and a
   job id), `GET /api/ask/{job_id}` (polled every 2 s), `GET /api/ask/status`. No CORS, no second
   host; the CSP stays `connect-src 'self'`. Off unless `DOCWIKI_LIVE_ASK=1` and the agent endpoint
   are set; a static host or a disabled portal reports no live agent and the drawer shows the filed
   answers only (or nothing on a build without any).
2. **Limits at a gateway, not in the app.** The portal reaches the Researcher through an existing,
   shared API Management instance, passed in as `liveAskEndpoint` (never created here, never
   committed). The gateway accepts only the portal's managed identity, then applies a per-visitor
   rate (3 questions per 300 s, the longest window the v2 tiers accept), per-visitor token budgets
   (20,000 per minute, 60,000 per day), a global daily budget (1,500,000 tokens: the cost cut-off)
   and emits token metrics. The visitor's address travels in `X-Visitor-IP` and is removed before
   Foundry. The portal adds cheap guards of its own (body 4 KB, question 3 to 500 characters, JSON
   only, same origin, one running question per visitor, three in total, 15 minutes of expiry) so
   that abuse is refused before it costs a call.
3. **Gate before display.** Documents and model output are untrusted, so a deterministic check runs
   before an answer is shown as verified: every `[n]` cited in the text must name a source that is
   an evidence sidecar path (`evidence/<source_id>/<locator>.md`) AND whose page exists in the site
   being served. Anything else is `unverified`: the text without its citations and the message
   "This answer could not be checked against the sources, so it is not shown as verified." The text
   goes through the Markdown safety rules first; the drawer renders it with DOM nodes and
   `textContent` only. Live answers carry the banner "Live answer from the Researcher agent — not
   reviewed by the owner.", their badges never say "quote verified", and there is no "Open as a
   page" (they are not filed). Exception text never reaches the visitor; questions are not logged
   above DEBUG and visitors only as a salted hash.
4. **Fallback to the filed answers.** A limit (the gateway's 429), an error or a timeout leaves the
   drawer's list of filed answers in place with a short message. The owner's path to a *good*
   answer is unchanged: ask in the Studio, review, file.

## Next steps

- The owner's powers in the same drawer: the Librarian, approvals, uploads, the run status and
  "File to wiki" for a signed-in owner; then retire the standalone Studio.
- Stream the answer instead of polling.
- A cheaper deployment for anonymous questions (a smaller model behind the same gateway).
- Quote verification of live answers against the sidecars (today the gate proves that the cited
  page exists, not that the quoted text is on it).

## Alternatives considered

- **Keep the agent in the Studio and the wiki static** (ADR 0007): the visitor cannot ask, and the
  product is two apps. Rejected by the owner.
- **Call Foundry from the browser or from a separate public app**: a second host, CORS, and the
  project endpoint exposed. Rejected: one origin, one app.
- **Limits in the portal only**: in memory, per replica, forgotten at a restart, and the cost cap
  would live in the process that is being abused. Kept as a first line, not the cap.
- **A new API Management instance for DocWiki**: cost and another thing to operate for a proof of
  concept. Rejected: an existing, shared instance passed in as a parameter.
- **Show live answers as verified without the gate**: a model may cite a path that does not exist.
  Rejected: deterministic checks before display.

## Consequences

- A public endpoint can spend model money. The gateway's global daily quota bounds it, the filed
  answers keep the demo working past it, and turning it off is one setting
  ([docs/live-ask.md](../live-ask.md)).
- The visitor key is the first `X-Forwarded-For` entry: it can be forged where the ingress does not
  overwrite it, which the global quota still bounds.
- One more custom client path in the overlay (the form, the polling) with Node tests for its pure
  parts, and one more portal module with fake-agent tests.
