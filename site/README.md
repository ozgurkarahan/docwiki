# DocWiki site overlay (Quartz)

The human view of a release: a [Quartz](https://github.com/jackyzha0/quartz) static site with
graph, backlinks, search, popover previews and an *evidence microscope* (spec: `docs/spec/site.md`).
Quartz is not vendored. This folder is an overlay copied over a pinned Quartz checkout.

```powershell
uv run python -m docwiki.site samples/fixtures/mock-release --out .cache/site-mock --base-url docwiki.ozgurkarahan.com
uv run python -m docwiki.portal --site-dir .cache/site-mock      # local preview on http://127.0.0.1:8080
uv run python -m docwiki.site.links .cache/site-mock             # link and anchor check
uv run python -m docwiki.site.scan .cache/site-mock --base-url docwiki.ozgurkarahan.com
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
   and drop Quartz static assets the layout never uses (giscus themes load from a CDN).
3. Assemble `content/` = the content namespace of `CONTRACT.md` §4: release `wiki/` + release
   `evidence/` mounted at `content/evidence/`, or a portable wiki folder as is. Hidden entries
   (`.docwiki/` machine files and the `.agents`/`.claude`/`.github` skill projections, which Quartz
   never publishes) are not copied. Then write `docwiki-site.json` (title, base URL, banner,
   release id and date, source pages and published originals).
4. `node quartz/bootstrap-cli.mjs build -d content -o public` (the same CLI as `npx quartz build`),
   copy `public/` to the output folder, then run the link checker and the security scan.

## Files

| Path | Purpose |
|---|---|
| `quartz.config.ts` | Plugins: no Obsidian/raw-HTML, LaTeX, analytics, OG images, aliases or CNAME emitters; relative link resolution; no smart quotes (verbatim evidence) |
| `quartz.layout.ts` | Search, graph, backlinks, table of contents, explorer, breadcrumbs, tags, popovers |
| `quartz/plugins/transformers/docwiki.ts` | Strips the backlinks block, renders raw HTML as text, drops the duplicated `# Title`, dates from `updated` (release date for sidecars), provenance badges in footnotes, notices, evidence decorations |
| `quartz/plugins/transformers/docwiki-text.ts` | Pure helpers (tested with Node by `tests/site/test_overlay_text.py`) |
| `quartz/components/docwiki/` | `Head` (no third-party requests, same-origin content-index loader), `Banner`, `EvidenceHeader`, `Breadcrumbs` (titles kept verbatim), `About`, `Footer` |
| `quartz/styles/custom.scss` | Stone and sage theme, system font stacks (no web fonts are downloaded), WCAG AA contrast in light and dark modes |
| `quartz/static/docwiki/` | Site icon and the content-index loader |

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
