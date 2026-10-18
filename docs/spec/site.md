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

- `pageTitle` from the domain pack `wiki_title`; `baseUrl` from settings (public sample:
  `docwiki.ozgurkarahan.com`).
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

## 4. Public sample on GitHub Pages

- Workflow `pages.yml`: on changes to `samples/wiki/**` or `site/**`, build the site from the
  committed sample release with Node 22 and the pinned Quartz, then deploy to GitHub Pages.
- Custom domain `docwiki.ozgurkarahan.com` (CNAME file in the build output) after the domain is
  verified for the GitHub account; HTTPS enforced.
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
