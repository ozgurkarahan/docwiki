# ADR 0010 — The story site: documents, pipeline, wiki

- Status: Accepted 2026-10-22
- Amends: [0009](0009-one-site.md) (the page names, the header and the status words; the portal
  stays the only web app)
- Spec: v1.7

## Context

ADR 0009 put the wiki, the process and the agent in one site. A UX designer and a building-trade
expert then walked through it (2026-10-22) and found that the site does not yet tell the story
the proof of concept is for: *here are the raw documents → here is the process that compiles them
→ here is the wiki, with an agent that answers from it.*

- The process cannot be found from the home page: the only way in is a small link, and on a phone
  the explorer is behind a menu.
- "How it works" and "Studio" mean nothing to a builder. "Pipeline" does.
- The statuses are not true: a document reads `done` before it is in the published release, and
  a document kept out of the public site also reads `done`.
- The run list is mostly the scheduled checks that found nothing to do.

## Decision

1. **Three numbered tabs in the header of every page: ① Documents · ② Pipeline · ③ Wiki.** They
   are links with `aria-current="page"` and fit a 390 px screen.
   - `/documents`: the documents themselves (a list in this version; the register and the viewer
     come next).
   - `/pipeline`: the process, the owner's controls first. `/how-it-works` redirects to it.
   - `/`: the wiki. The agent stays the drawer on every page, not a tab.
2. **The header also carries a status chip and a Sign in button.**
   - The chip reads the portal's `GET /api/status` and says, in shape and word: "● Idle",
     "◐ Processing n documents", then "● In the wiki → <document>" for a while after a document
     reached the release. A presenter can start a run and walk away.
   - "Sign in" is for the owner and leads back to `/pipeline`. Signed in, it reads "Owner ✓".
   - On a static host (no `/api`) both stay hidden.
3. **One status vocabulary,** always a shape, a word and a colour together (Okabe-Ito colours,
   darkened for text), computed by the portal, never by the browser:

   | Shape | Status | When |
   |---|---|---|
   | ○ | Received | In `raw/`, not seen by the pipeline yet |
   | ◌ | Queued | Seen, no stage started |
   | ◐ | Processing n/13 *stage* | A stage is at work, **or every stage is done but the document is not in the published release yet** |
   | ● | In the wiki | In the published release |
   | ◑ | Superseded | In the release, replaced by a newer revision |
   | ⊘ | Held back | Above the site's audience, or quarantined by the pipeline |
   | ✕ | Failed | A stage failed; the owner sees the reason |

4. **The run list shows the runs that did something.** Scheduled checks that found nothing are
   counted ("n scheduled checks found nothing to do since …"), not listed.
5. **The pipeline page leads with the owner's box and the live view.** The 13 technical steps are
   in a disclosure; the graph view is not shown on the Pipeline and Documents pages.

## Consequences

- The three-part story is one click away from every page, on a phone too.
- Status words can be trusted: "In the wiki" always comes with a page that exists.
- `post_login_redirect_uri` and the links in the site change to `/pipeline`; old links keep
  working through the redirect.
- A business view of the pipeline (four phases, one document's journey, what changed in a
  release), the documents register and its viewer, and the story home are later slices of the
  same plan; this ADR fixes the frame they go into.
