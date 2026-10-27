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
  (a panel on wide screens; on phones, below 800 px, a bottom sheet: full width, about 90% of the
  height, with a 44 px close button). The button is hidden until the client
  knows there is something in it: the build has filed answers (`docwiki-site.json` `answers`, the
  panel's `data-filed-answers`), or the portal reports a live agent (`GET /api/ask/status` returns
  `{"enabled": true}`). A build with no filed answers on a static host (no `/api`) shows nothing.
- **Filed answers**: `static/docwiki/answers.json`, built from the `queries/` pages: the question
  list (those about the current page first), the selected answer with numbered citations,
  provenance badges, "How the agent worked" and the provenance line. A citation opens the evidence
  beside the drawer on wide screens; below the desktop breakpoint the drawer collapses to "Back to
  the answer". State in `sessionStorage`; on a phone the drawer is never restored open on a page
  load (the selected answer is kept for the next opening).
- **Answer view**: the sources are numbered 1..n in the order the answer first cites them and the
  inline markers are renumbered to match (`renumberCitations`), shown as separate "[1] [3]". "Pages
  in the wiki" (the wiki pages of the cited sources) comes above "Sources".
- **Empty drawer**: three example questions the sample corpus answers (`EXAMPLE_QUESTIONS`) are
  buttons. With live ask they fill the question box and ask it; otherwise only the examples with a
  filed answer are offered and a click opens that answer.
- **Live ask** (only when enabled): above the question list a labelled textarea (at most 500
  characters) and an "Ask" button. The client posts `{"question"}` to `/api/ask`, polls
  `/api/ask/{job_id}` every 2 s and shows "The Researcher is reading the wiki… n s" in a polite live
  region while the form is disabled. The result goes through the same answer view, marked live:
  the banner "Live answer from the Researcher agent — not reviewed by the owner." in neutral
  colours (information, not an alarm), no "Open as a
  page", and for an `unverified` answer no citation links plus the portal's message. A limit (429),
  an error or a timeout shows the portal's message and keeps the filed list. Live answers of the
  session are listed under "Your live questions" and kept in `sessionStorage` (parsed back with
  the same validation as the live JSON), so the last answer survives page navigation; they are
  never sent anywhere or written to the wiki.
- Everything is rendered with DOM nodes and `textContent`; every request goes to the site's own
  origin (CSP `connect-src 'self'`). The parsing and checks of the live JSON are pure helpers in
  `docwiki-text.ts`, tested with Node.
- The portal side (guards, gate before display, gateway limits): `src/docwiki/portal/live_ask.py`
  and [docs/live-ask.md](../live-ask.md).

## 8. Pipeline page

([ADR 0010](../adr/0010-the-story-site.md); the business view of slice C.)

- `/pipeline` is the second of the three header tabs (① Documents · ② Pipeline · ③ Wiki). It
  leads with the owner's box, then the live view filled from `GET /api/process` (DOM nodes and
  `textContent` only, site-absolute links only), then the 13 technical steps in a disclosure.
- **Four phases.** Under each document's title (the status column stays narrow) one line of four
  phases, Read → File → Write → Check and publish (discover, extract · classify · compile to
  agentkit · evidence to publish), each with a shape, a word and a colour: ● done, ◐ in progress,
  ○ not started, ✕ failed. A processing document has the phases before its `phase` done; a
  document in the release has all four done; received and queued have none started; a failed one
  is failed at the phase of its stage (Read when unknown); held back and removed have no bar. A
  visually hidden text says it ("Phase 3 of 4: Write, step 4/13 compile").
- **Follow this document.** A disclosure button per row (`aria-expanded`) opens the document's
  journey under it: the original as in the register ("Original ↗" in a new tab, "Download .eml",
  or "Original not published", from `original_url`) with its path, its document page ("Pages and
  full text"), its status, the wiki pages its last recorded run added or removed (chips) or
  changed (`last_change`; "No recorded run changed it" without one), and its wiki page. When that
  run made the current release, "and n more" links to "What changed in this release"
  (`#docwiki-what-changed`).
- **What changed in this release.** After the documents: the pages added, changed and removed and
  the contradictions opened and closed by the run of the current release (`runs[].changes`), or
  "This release rebuilt the site; no page changed." Lists show at most 10 items, then "and n
  more". While a run is unfinished, the live view names its stage and its documents.
- **Owner rebuild.** When `/api/owner/me` returns `rebuild`, the owner sees a 44 px "Rebuild the
  wiki" button (every page and the site from the cache; about $0 when no document changed; at most
  5 a day), which sends `PUT /api/owner/runs/<random key>` and speeds up the polling.
- **Live updates.** A poll updates the document rows by key (path): unchanged rows are left as
  they are, so focus, open journeys and scroll stay. Only real changes (a new document, a new
  state, a new phase) are announced, in the one polite region of the page, never on the first
  render. The pure parts are in `scripts/pipeline.ts`, tested with Node.

## 9. Documents register and explorer with scopes

(v1.7, [ADR 0011](../adr/0011-company-wide-wiki.md).)

- `docwiki-site.json` gives each source its `scope`, `phase` and `lot` (from the source
  frontmatter; `null` when the pack declares no scopes), `scopes` (every scope value with its
  title: the title of its hub page and the hub's slug, or the value capitalised for a scope
  without a hub such as the default `entreprise`), `register` and `explorer`.
- **Register.** When at least one source has a scope, the ① Documents register is grouped by
  scope, then phase, then type (`register`, computed by `docwiki.site.register`): scopes with a
  hub first, by title, each heading linking to its hub, then the scopes without a hub, then
  documents without a scope ("Other documents"); phases by key ("Phase 3", "No phase" last);
  types alphabetically (untyped last); inside a type, by n° and indice, then date. Entries show
  the lot when there is one. Without scopes `register` is `null` and the register stays one flat
  list. Types show the pack's label (`docTypeLabel`, from the source page's `doc_type_label`:
  "PV de réception", "DC4"), in the register and the source page header; only a release built
  before the labels shows the key in words.
- **Explorer.** Top-level groups in this order: the hub folders (`explorer.hubFolders`, from
  the `index:hubs/<folder>` pages, e.g. "Chantiers"), `entities`, `sources`, `topics`, then the
  rest (folders before files, by name). When the wiki has scopes, the `entities` folder is shown
  under the title of the one scope without a hub (`explorer.entitiesTitle`, "Entreprise"); its
  pages keep their paths. Per-scope topic folders show their scope's title
  (`explorer.folderTitles`: `topics/moreau` → "Chantier Moreau"). Tags, evidence, documents and
  pipeline stay hidden. Quartz runs the explorer functions in the browser from their source text,
  so these values are written into it.
- **Breadcrumbs.** A per-scope topic (`topics/<scope>/<slug>`) shows Home / Topics / <scope
  title>, the scope's crumb going to its hub page (the folder has no page of its own).
- **Data tables.** Up to 800 px the wiki's tables (the dashboard, the views, the hubs; not the
  evidence sidecars') are stacked cards: one card per row, each cell under its column's label
  (`data-label`, set by the DocWiki transformer from the header row). Wider, a table that overflows
  its column says "Scroll sideways →" above it and shows a shadow on its hidden side; a computed
  view's tables are named after the view's title (`data-caption`). The home page's dashboard
  stays stacked up to 1000 px (its five columns do not fit beside the sidebar between 801 and
  1000 px). An ISO date in a data table's cell (`(2026-04-21)`) never wraps at its hyphens
  (`docwiki-nowrap`).

## 10. Accessibility

(v1.7, slice H, from the accessibility checklist of the UX review of 2026-10-22.) The target is
WCAG 2.2 AA; axe reports no serious or critical violation on the home, documents, pipeline, a
source page and a topic page with the drawer open, at 1280×800 and 390×844, light and dark.

- **Skip link.** "Skip to content" is the first focusable element of every page (the first
  component of the left column), off screen until it has the focus, then a 44 px button at the
  top left. It moves the focus to the page title (`h1#docwiki-main`, `tabindex="-1"`, rendered by
  DocWiki's `ArticleTitle`) itself: following the hash natively would fire `popstate`, on which
  Quartz's router reloads the page.
- **Quartz's own markup**, corrected from the overlay after every navigation (Quartz is not
  vendored): `aria-expanded` moves from the explorer's `div` to the buttons that toggle it and
  follows its state; the phone's menu button is named "Browse the wiki"; the table of contents'
  button controls the id its list really has; the page column is the `main` landmark, the side
  columns `navigation` ("Wiki") and `complementary` ("About this page"), and the page column's
  `header` is not a second banner.
- **Drawer focus.** Opening moves the focus into the drawer (its heading, or the selected answer's
  heading). A rebuilt drawer keeps the focus on the same control (its focus key), else on its
  heading, never on the page body. Where the drawer covers the page (up to 1200 px, the phone's
  bottom sheet included) Tab cycles inside it; wider, it is a non-modal panel beside the text and
  Tab goes on into the page. Escape closes it and returns the focus to what opened it: the
  floating button, or the home page's "Try: …" button.
- **Contrast.** Text at least 4.5:1 on the page, its surface and the highlight tint (the light
  theme's grey is `#666560`, the failed status `#a84300`). The borders of controls, cards, inputs,
  stage cards, the documents table and the link pills use `--dw-border` (`#85837a` light,
  `#767a70` dark: at least 3:1 on the page and the highlight tint); provenance badge and notice
  borders at least 3:1 against the page and their own fill; stage cards mark their state with the
  status colours. `--lightgray` stays for decorative separators only. The dates of folder
  listings are `--darkgray` at full opacity (Quartz fades them to 0.6).
- **Motion.** Under `prefers-reduced-motion: reduce` nothing animates, fades or scrolls smoothly:
  transitions and animations (Quartz's popovers, explorer, table of contents, progress bar; the
  drawer's sheet) end at once, `scroll-behavior` is `auto`, and scripted smooth scrolling
  (`scrollIntoView({behavior: "smooth"})`, Quartz's explorer) jumps. There are no spinners.
- **Targets.** Every visible link, button, summary and input is at least 24 × 24 px, except links
  inside a sentence (WCAG 2.5.8's inline exception): navigation lists (explorer, table of
  contents, backlinks, breadcrumbs, tags), a link alone in its list item, paragraph or cell (the
  transformer marks it `docwiki-target`; in a cell it is also at least 24 px wide, its text
  centred, for one-digit links such as the dashboard's open-contradiction counts), Quartz's theme and reader-mode buttons, footnote
  references and back links, the drawer's citation markers (inline padding, which does not move
  the lines) and source lists. Main actions are 44 px on the phone: the tabs, Sign in, the story
  cards, "Try: …", the floating button, the drawer's close and Ask buttons, the menu button.
- **Language.** Each page has the `lang` of its language (§11: French at the root of a French
  wiki, English under `en/`; English for a wiki without languages); the documents' own words are
  marked with the document's language (`original_lang` of the source page, given to the site as
  the source's `lang`, when it differs from the page's): the quoted passages ("…", “…”, « … »)
  and the non-notice blockquotes of a source page, the verbatim blockquotes and the table rows of
  an evidence sidecar. Source titles are the compiled titles of the page's language and the
  drawer's citations carry no excerpt, so neither is marked. The site translates nothing itself.
- **Zoom.** At 320 px and at 200 % zoom (640 CSS px) no page scrolls sideways; a wide table
  scrolls inside its own box, which becomes a focusable, labelled region.
- The pure parts are in `docwiki-a11y.ts`, tested with Node.

## 11. Languages: French canonical, English mirror

(v1.7, slice G, [ADR 0012](../adr/0012-french-canonical-and-locked-vocabulary.md) decision 3.)

- **What the build reads** (one adapter in `src/docwiki/site/build.py`): the manifest's
  `wiki_languages` (`["fr", "en"]`, the first canonical); without it, the `lang` of the home
  page in `catalog.json` (else of `wiki/index.md`), the other languages being those of the
  catalog's pages. A mirror exists when `wiki/<lang>/index.md` does. Canonical pages are at
  `wiki/<path>` (`lang: fr`); a mirror's pages at `wiki/<lang>/<same path>` (`lang: en`,
  `translation_of: <id>`, the same `id`), linking the mirror's pages and the shared evidence.
  Catalog pages are unique by `(id, lang)`. A release without any of this (the mock release)
  builds exactly as before: one tree, English.
- **Trees.** The canonical tree is the content root; each mirror is under `<lang>/` with the same
  slugs, `documents` and `pipeline` included (written by `docwiki.site.process_page` in each
  language). Evidence sidecars, document pages and originals exist once, in the canonical tree;
  they are shown in the canonical language, and the mirror's pages link to them.
  `docwiki-site.json` gives `languages` and, per mirror, its title, sources (page and title),
  scopes, register, explorer and steps. With a mirror the build also writes
  `static/docwiki/languages.json` (`{"schema": 1, "canonical": "fr", "languages": ["fr", "en"]}`)
  for the portal.
- **Page language.** A page's language is its frontmatter `lang` when it is one of the wiki's
  languages, else its tree's; `<html lang>` follows (the client sets it again after Quartz's
  in-site navigation). Quartz's own components (search, theme and reader buttons, table of
  contents, backlinks, graph, dates and reading time, folder and tag listings) get the locale of
  that language (`DocWiki.Localized`); the site title, the breadcrumbs' root and the tabs lead to
  the home, documents and pipeline pages of that language. A mirror's home (`en/index`, a folder
  page for Quartz) reads like the home page: the story, "About this wiki", no folder listing.
- **Strings.** Every string of the overlay's components and scripts (tabs, status chip and status
  vocabulary, Sign in, the drawer, the register, the pipeline page, the story home, the banner,
  the skip link, "Scroll sideways →", badges' words and meanings…) comes from one typed table per
  language: `site/quartz/components/docwiki/i18n/en.ts` and `fr.ts` (`Strings` in `strings.ts`).
  The locked trade terms stay untranslated in English (réception, avenant, situation, PV,
  réserves, DPGF, CCAP, PPSPS, conducteur de travaux, indice, lot…). The wiki's citation markers
  stay English in the Markdown (`✓ quote verified`); the reader sees them in the page's language.
  A language without a table gets English.
- **Switch.** "FR · EN" in the header: plain links with `hreflang` and `lang`, the page's language
  marked `aria-current="true"`, at least 24 × 24 px (44 px tall on phones); with a switch, the
  tabs, Sign in and the switch share the first row and the chip goes under them; on phones the
  tabs have the first row and the chip, Sign in and the switch the second. Each link leads to the
  same slug in the other language, else (evidence) to its documents page, else to its home, as a
  full page load; clicking it sets the cookie `docwiki_lang=<lang>` (one year, `SameSite=Lax`).
  Each page's head lists its `<link rel="alternate" hreflang>` twins (absolute with a base URL)
  and `x-default` (the canonical page).
- **Explorer and search.** One explorer per language: the canonical one never lists a mirror's
  folder; a mirror's lists only its folder, as the root, with the same grouping and folder titles.
  The content-index loader (`static/docwiki/content-index.js`, given the languages) hands Quartz's
  search, explorer and graph the pages of the language of the page on screen (evidence is shared
  by both).
- **Links from the portal and the drawer.** The pipeline page and the header link the wiki pages of
  the portal's replies in the page's language (`/sources/x` → `/en/sources/x`; evidence, static
  files and files stay shared); the drawer's "Pages in the wiki" are the pages of its language.
  Filed answers are those of the canonical tree (`queries/`).
- **Negotiation (portal).** With `languages.json`, a top-level navigation (`Sec-Fetch-Dest` absent
  or `document`) to a canonical HTML page whose twin exists is redirected (302, query kept) to
  `/<lang>/…` when the reader's language is a mirror's: the `docwiki_lang` cookie when it names a
  language of the site (it wins), else `Accept-Language` (the mirror's best q-value strictly above
  the canonical's; ties stay canonical). Mirror pages, `static/`, `evidence/`, `api/`, `404` and
  non-HTML files are never redirected; canonical HTML responses carry `Vary: Accept-Language,
  Cookie`. Old URLs redirect in both languages (`/how-it-works`, `/en/how-it-works` → `pipeline`).
  Without `languages.json` (or with one language) the portal behaves as before.

## 12. The demo: evaluation panel, guided tour, architecture page

(Slice D2: the site tells the demo of the project to a visitor who arrives from GitHub. No wiki
content changes; every word is in the overlay's string tables, in French and English.)

### 12.1 Evaluation panel ("Wiki + agent vs RAG")

- On each language's home page, inside the story, under the question to try: one small table of
  three systems, the wiki and its Researcher agent first, then the long-context baseline (every
  document in the prompt) and the RAG baseline (chunks). Columns: answer accuracy and exact numbers
  (percentage, with passed/n under it), cost per question and median latency (p50). Under it: the
  split and its question count, the run date, "costs are estimates" when the price table is not
  verified (the cost then reads "≈ $0.164"), and a link to the full scoreboard
  (`evals/SCOREBOARD.md` on GitHub).
- **Data.** `evals/results/latest.json` (`docwiki.evals.latest/v1`, written by
  `evals/scoreboard.py`, which already summarises cost and latency per system) is read at build
  time by `docwiki.site.evals.read_eval_panel`; nothing is recomputed. The build passes it to
  `docwiki-site.json` as `evals` (`split`, `questions`, `date`, `scoreboardUrl`, `systems[]` with
  `accuracy`/`numeric` `{value, n, passed}`, `costPerQuestion`, `pricesVerified`, `latencyP50`).
  A missing, unreadable or foreign file, or a split without `docwiki-researcher`, gives `null` and
  the panel is absent. The job image ships `evals/results/latest.json` next to `site/`.
- **Presentation.** A real `<table>` with a visually hidden caption, `scope="col"` headers and
  `scope="row"` system names; at 390 px the cells shrink and wrap, and only the table's frame could
  scroll, never the page. Both themes use the site's tokens.

### 12.2 Guided tour

- "Take the 2-minute tour", a button of the home story (shown by the script: the tour needs
  JavaScript), starts six steps across the pages of the reader's language (a mirror's tour stays
  under `/en/`):
  1. `documents`: an "Original ↗" link of the register (`.docwiki-documents-links`);
  2. the source page of the first document of the register that has a wiki page, and its links to
     the document and the original (`.docwiki-source-links`);
  3. `pipeline`: the live view (`.docwiki-process`): runs, stages, gates, cost;
  4. the first topic page (by slug, `type: topic`): its first citation (`a[data-footnote-ref]`);
  5. on the same page, the "Ask this wiki" drawer opens with the first example question in its
     form, through `docwiki:ask` with `fill: true` (live: the question waits for the reader to send
     it, nothing is asked; filed answers: its answer opens as for "Try");
  6. the home page's evaluation panel, with links to the quality report and the architecture page.
  The pages are chosen at build time (`Tour.tsx`, `data-pages`); no sample document is named.
- **Callout.** A small non-modal dialog (`role="dialog"`, labelled by its title) anchored under
  (or above) its element, which is outlined and scrolled into view; centred, with a short note,
  when the element is missing (a static host, no drawer). On a phone, and for the drawer, it docks
  at the bottom of the viewport (at the top when the element is in the lower half). Back, Next
  (Done on the last step) and Close, 44 px targets; Esc closes when the focus is in the callout or
  nowhere; the focus moves to the step's title, and a polite status region announces "Step n of
  6. Title". Closing returns the focus to the start button (else the page title).
- **State.** The step is kept in `localStorage` (`docwiki-tour`, `{"step": n}`) inside try/catch;
  without storage it lives in memory for the page load. After a navigation the callout reappears
  when the page is the step's page; elsewhere it waits. The pure helpers (`tourStep`,
  `tourPlacement`, `askEventFill`) are in `docwiki-text.ts`, tested with Node.

### 12.3 Architecture page

- `/architecture` and `/<mirror>/architecture` are written by the site build like `pipeline` and
  `documents` (`docwiki.site.process_page.write_architecture_page`, never over a release's own
  page). The `Architecture` component shows `docs/assets/architecture.svg`, copied by the build to
  `static/docwiki/architecture.svg` (absent diagram: the text stays), above a short "how it works":
  documents → the 14-step pipeline → a release with quality and leak gates → the static site and a
  private MCP server → two Foundry agents (the Researcher reads, starting from the wiki's indexes
  and search in one call; the Librarian maintains) behind API Management limits; Container Apps,
  owner sign-in with Easy Auth, managed identities, `azd up`. Visitors ask through the drawer.
- Linked from the home story ("How it is built: the architecture") and from the tour's last step.
  Like the other two pages it has no graph, no dates and no explorer entry.
