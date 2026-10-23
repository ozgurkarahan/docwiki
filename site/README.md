# DocWiki site overlay (Quartz)

The human view of a release: a [Quartz](https://github.com/jackyzha0/quartz) static site with
graph, backlinks, search, popover previews, an *evidence microscope* and an "Ask this wiki" drawer
of reviewed research answers (spec: `docs/spec/site.md`, ADR 0007).
Quartz is not vendored. This folder is an overlay copied over a pinned Quartz checkout.

```powershell
uv run python -m docwiki.site samples/fixtures/mock-release --out .cache/site-mock --base-url docwiki.example.com
uv run python -m docwiki.portal --site-dir .cache/site-mock      # local preview on http://127.0.0.1:8080
uv run python -m docwiki.site.links .cache/site-mock             # link and anchor check
uv run python -m docwiki.site.scan .cache/site-mock --base-url docwiki.example.com
```

Requirements: git, Node 22+ with npm. From Python: `docwiki.site.build_site(release_root, out_dir,
*, base_url=None)`. `release_root` may be a release folder (published, or staged without
`manifest.json`), a `releases/` folder with `current.json`, or a **portable wiki folder** (wiki
content at the root, `evidence/` inside, machine files under `.docwiki/`, detected by
`.docwiki/manifest.json`); the output of a portable build must live outside the folder or under
its `.docwiki/`.

## Pinned version

`QUARTZ_VERSION` pins **v4.5.2**, the latest stable Quartz v4 tag. Quartz v5.0.0 (tagged
2026-03-14) was evaluated and not adopted yet: its git-based plugin system clones and `npm install`s
about 40 community plugin repositories at build time, links local and peer plugins with directory
symlinks (which need elevated rights or Developer Mode on Windows), and would turn the DocWiki
transformer and components into separately packaged plugins. v4.5.2 builds from one `npm ci`
against Quartz's own lock file, with no install scripts (`--ignore-scripts`) and no symlinks.

## How a build works

1. Clone the tag into `.cache/quartz/<tag>` (depth 1, git-ignored) or reuse it after
   `git reset --hard` and `git clean`; run `npm ci` only when Quartz's lock file changed.
2. Copy `quartz.config.ts`, `quartz.layout.ts` and `quartz/**` from this folder over the checkout
   and drop Quartz static assets the layout never uses (giscus themes load from a CDN). Write
   `quartz/static/docwiki/answers.json`, the filed research answers of `queries/` (see
   [Ask this wiki](#ask-this-wiki)); a malformed query page fails the build before Quartz runs.
3. Assemble `content/` = the content namespace of `CONTRACT.md` §4: release `wiki/` + release
   `evidence/` mounted at `content/evidence/`, or a portable wiki folder as is. Hidden entries
   (`.docwiki/` machine files and the `.agents`/`.claude`/`.github` skill projections, which Quartz
   never publishes) are not copied. Then write `docwiki-site.json` (title, base URL, banner,
   release id and date, documents by status, run id, gate counts, the run receipt and quality
   report pages, source pages and published originals, the number of filed answers). Gate counts
   and the run id come from the release manifest; the pipeline builds the staged release before
   its manifest exists and passes them in.
4. `node quartz/bootstrap-cli.mjs build -d content -o public` (the same CLI as `npx quartz build`),
   copy `public/` to the output folder, then run the link checker and the security scan.

## Files

| Path | Purpose |
|---|---|
| `quartz.config.ts` | Plugins: no Obsidian/raw-HTML, LaTeX, analytics, OG images, aliases or CNAME emitters; relative link resolution; no smart quotes (verbatim evidence) |
| `quartz.layout.ts` | Search, graph, backlinks, table of contents, explorer, breadcrumbs, tags, popovers; the "Ask this wiki" drawer after the body of every page |
| `quartz/plugins/transformers/docwiki.ts` | Strips the backlinks block, renders raw HTML as text, drops the duplicated `# Title`, dates from `updated` (release date for sidecars), provenance badges in footnotes, notices (the home page's copy of the fictional notice is dropped when the site banner shows it), evidence decorations |
| `quartz/plugins/transformers/docwiki-text.ts` | Pure helpers without imports, including the drawer's (`answers.json` parser, question groups, relative links, session state); tested with Node by `tests/site/test_overlay_text.py` |
| `quartz/components/docwiki/` | `Head` (no third-party requests, same-origin content-index loader), `Banner`, `EvidenceHeader`, `Breadcrumbs` (titles kept verbatim), `Story` (home page, under the title: the pattern in one sentence, three cards documents → pipeline → cited pages, the pipeline card's last run read from `/api/process`, and a "Try: …" button that opens the drawer on a question through the `docwiki:ask` event), `About` (home page, under the story: documents, release, quality gates, run receipt and quality report, then a collapsible "About DocWiki"), `AskPanel` (the "Ask this wiki" button and drawer), `Footer` |
| `quartz/components/docwiki/scripts/askPanel.inline.ts` | Client of the drawer, bundled into `postscript.js` |
| `quartz/components/docwiki/settings.ts` | Typed view of `docwiki-site.json` |
| `quartz/styles/custom.scss` | Stone and sage theme, system font stacks (no web fonts are downloaded), WCAG AA contrast in light and dark modes; the drawer's styles; on phones the wiki title shrinks and wraps so that the header row fits 320 px, and the open menu covers the screen exactly, its list starting below the menu button |
| `quartz/static/docwiki/` | Site icon and the content-index loader; `answers.json` is generated there by each build |

## Ask this wiki

[ADR 0007](../docs/adr/0007-answers-in-the-wiki.md): visitors get research answers that the
Researcher agent produced and the owner reviewed and filed as `queries/<yyyy-mm-dd>-<slug>.md`
pages, never a live model. There is no free-text input and no backend; to ask new questions,
people connect their own coding agent to the wiki (MCP).

- **Data.** `docwiki.site.answers` turns the query pages into `static/docwiki/answers.json`
  (`{"schema": 1, "release", "answers": [...]}`), deterministically: per answer the question, the
  filing date (`updated`), the superseded and warning banners (the fictional stamp is left to the
  site banner), the paragraphs before the first `##` section as text and citation segments
  (`{"text": …}`, `{"cite": n}`; links keep their text, emphasis and code markers go, list items
  start with `• ` or `1. `), the contract citations (`n`, `title`, `label`, `href` = evidence
  content slug, `badge`), the bullet items of "How this answer was produced" (`steps`) and the
  paragraphs directly under its heading as plain text (`provenance`: agent and version, dates,
  release, review; `""` without them), and the `pages` it is about: its own page, its evidence,
  the source pages of its `sources` and their topic and entity pages. Answers are sorted by date,
  newest first, then by question. `docwiki-site.json` carries their number (`answers`); with
  none, the drawer is not rendered.
- **Drawer.** A floating "Ask this wiki" button on every page (not on the 404 page, which is
  served at any path) opens a non-modal panel (`<aside aria-label="Ask this wiki">`): a right-hand
  panel `min(440px, 100vw)` wide on wide screens, a full-screen sheet up to 800 px. The questions
  about the current page come first ("About this page", then "More questions"; "Questions" when
  none is about the page); an answer shows its banners, its text with numbered citations, its
  sources with their provenance badges, "How the agent worked (k steps)", its provenance line
  (the `provenance` note, whose closing colon becomes a full stop, else "Filed on <date>") and
  "Open as a page". `answers.json` is fetched from the same origin on first open, once per page
  load.
- **Navigation.** A citation is an ordinary link: Quartz's page navigation opens the evidence in
  the main view. Because that navigation morphs the whole body, the drawer's state (open, selected
  answer, scroll position) lives in `sessionStorage` and the drawer is rebuilt on every `nav`
  event, with the focus back on the link that was followed. On wide screens (more than 1200 px,
  Quartz's three-column layout) the open drawer takes the place of the right-hand panel and the
  page column narrows, so the drawer stays open beside the text it cites. Up to 1200 px it would
  cover the page text (a full-screen sheet on phones up to 800 px), so it collapses once a link of
  the answer (a citation, a source, "Open as a page") is followed and the page shows; the button
  then reads "Back to the answer" and one tap reopens the drawer on the same answer, at the same
  place, with the focus on the followed link. Closing the drawer keeps the selected answer.
- **Keyboard and screen readers.** Opening moves the focus to the drawer heading, selecting a
  question to the answer's heading, "Back to questions" to that question. Escape, with the focus in
  the drawer (or nowhere), closes it and returns the focus to the button; it is handled before
  Quartz's own Escape handlers, which would move the focus to the search button. Visible focus
  rings, AA contrast and both colour schemes come from the theme variables.
- **Safety.** Every string of `answers.json` is rendered with DOM nodes and `textContent` (no
  `innerHTML`, no code from strings); the parser keeps well-formed entries only and accepts content
  slugs, never URLs, as links. No new script tag, request host or inline handler: the drawer's
  script is part of `postscript.js` and the scan rules are unchanged. It is hidden in print and in
  popovers.

## Evidence microscope

Footnotes link to the sidecar pages `evidence/<source_id>/<locator_key>`. Hovering a footnote link
previews the evidence in a popover; the sidecar page shows the page image (click to open it full
size), the verbatim text or the table rows (`#row-n` anchors are highlighted), the provenance badge,
the way back to the source page and, when published, the original document (`#page=N` for PDFs).
The backlinks panel of a sidecar lists the pages that cite it.

Badges keep their meaning without colour: `✓ quote verified` (check mark), `paraphrase` (dashed),
`table` (square corners), `OCR` (dotted) and `generated description` (dashed, italic).

## Security

- Raw HTML in content is rendered as text; HTML comments are dropped; no Obsidian syntax.
- No external scripts, fonts, analytics or preconnects; every script is a Quartz bundle served
  from the site itself (`prescript.js`, `postscript.js`, `static/docwiki/content-index.js`).
- `docwiki.site.scan` reports other scripts, frames, inline handlers, `javascript:`/`data:` URLs,
  hosts outside the repository host and the site's own host, and injection canaries.
- The private portal (`docwiki.portal`) sends `Content-Security-Policy` with `default-src 'self'`
  and `frame-ancestors 'none'`. Quartz's explorer and graph need `script-src 'unsafe-eval'`
  (sort/filter functions and PixiJS shaders) and its components set inline styles.
