# Site (human view)

## 1. Generator

- **Quartz**, pinned to a specific release tag. Quartz is not vendored: `docwiki site` (and
  `scripts/site/build.py`) clones the pinned tag into `.cache/quartz/` (git-ignored), installs it,
  copies the overlay from `site/` (config, layout, custom components, styles), copies the release
  `wiki/` into Quartz `content/` and `evidence/` into `content/evidence/`, then builds to the
  release's `site/` folder (or `--out`).
- Lock files produced against local package mirrors are never committed; the build installs with
  the public registry in CI.

## 2. Configuration

- `pageTitle` from the domain pack `wiki_title`; `baseUrl` from settings (set to the host that serves
  the site).
- Enabled: full-text search, graph view, backlinks panel, popover previews, table of contents,
  breadcrumbs, explorer, tag pages, last-modified dates from frontmatter.
- Fonts served locally (no third-party font CDN); no analytics; no external scripts.
- Raw HTML rendering disabled in the Markdown pipeline; a custom transformer removes the DocWiki
  backlinks block (between the marker comments) because Quartz shows its own backlinks panel.
- Custom components: provenance badges for footnotes (`✓ quote verified`, `table`, `OCR`,
  `generated description`), a "fictional sample" banner when the domain pack sets one, and a
  landing section on `index.md` explaining DocWiki with a link to the repository.

## 3. Evidence microscope

- Footnotes link to evidence sidecar pages (`evidence/<source_id>/<locator_key>`), which show the
  page image with highlight boxes, the table rows, the slide, the transcript cue or the OCR crop,
  with the provenance badge, a link back to the source page and — for the public sample — to the
  original file (PDF links use `#page=N`).
- Every citation link is checked by the build (no 404) and by a link checker on the deployed site.

## 4. Public sample on Azure Container Apps

- The public demo is served by the `portal` container (§5) from the current release of a
  public-audience build; there is no separate static host and no committed copy of the wiki.
  (v1.4: GitHub Pages retired.)
- The published sample includes the original sample documents (CC BY 4.0) under the evidence tree.

## 5. Private portal (optional)

- `portal` container: a minimal static file server that syncs the current release's `site/` from
  Blob (on start and when `current.json` changes), sets security headers (CSP `default-src 'self'`,
  `frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`) and
  runs behind ACA built-in auth with interactive Entra sign-in.
- Disabled by default (`enablePortal=false`).

## 6. Site security checks

The built site is scanned for `<script` tags other than Quartz bundles, `<iframe`, inline event
handlers originating from content, `javascript:` and `data:` URLs, external `src`/`href` hosts
outside an allowlist (the repository URL and the site's own host), and the injection canary.

## 7. "Ask this wiki" drawer

(v1.3 filed answers, [ADR 0007](../adr/0007-answers-in-the-wiki.md); v1.5 live ask,
[ADR 0008](../adr/0008-one-experience-live-agent-in-the-wiki.md).)

- A layout component on every page except `404` renders a floating button and a non-modal drawer
  (a panel on wide screens, a full-screen sheet on phones). The button is hidden until the client
  knows there is something in it: the build has filed answers (`docwiki-site.json` `answers`, the
  panel's `data-filed-answers`), or the portal reports a live agent (`GET /api/ask/status` returns
  `{"enabled": true}`). A build with no filed answers on a static host (no `/api`) shows nothing.
- **Filed answers**: `static/docwiki/answers.json`, built from the `queries/` pages: the question
  list (those about the current page first), the selected answer with numbered citations,
  provenance badges, "How the agent worked" and the provenance line. A citation opens the evidence
  beside the drawer on wide screens; below the desktop breakpoint the drawer collapses to "Back to
  the answer". State in `sessionStorage`.
- **Live ask** (only when enabled): above the question list a labelled textarea (at most 500
  characters) and an "Ask" button. The client posts `{"question"}` to `/api/ask`, polls
  `/api/ask/{job_id}` every 2 s and shows "The Researcher is reading the wiki… n s" in a polite live
  region while the form is disabled. The result goes through the same answer view, marked live:
  the banner "Live answer from the Researcher agent — not reviewed by the owner.", no "Open as a
  page", and for an `unverified` answer no citation links plus the portal's message. A limit (429),
  an error or a timeout shows the portal's message and keeps the filed list. Live answers of the
  page load are listed under "Your live questions"; they are never persisted.
- Everything is rendered with DOM nodes and `textContent`; every request goes to the site's own
  origin (CSP `connect-src 'self'`). The parsing and checks of the live JSON are pure helpers in
  `docwiki-text.ts`, tested with Node.
- The portal side (guards, gate before display, gateway limits): `src/docwiki/portal/live_ask.py`
  and [docs/live-ask.md](../live-ask.md).
