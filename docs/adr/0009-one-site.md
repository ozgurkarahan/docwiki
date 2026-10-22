# ADR 0009 — One site: the process, the uploads and the agent in the wiki

- Status: Accepted 2026-10-22
- Supersedes: [0007](0007-answers-in-the-wiki.md)'s Studio ("File to wiki" from a separate app)
  and the owner's Studio of the spec v1.1 to v1.3; completes [0008](0008-one-experience-live-agent-in-the-wiki.md)'s
  "next step"
- Spec: v1.6

## Context

DocWiki is a proof of concept. Its job is to show how the LLM-wiki pattern applies to ordinary
documents, and the owner restated on 2026-10-22 what a visitor must be able to see:

- **one website**, not a wiki plus a second app;
- **the process**: how a document becomes cited wiki pages, run by run, stage by stage;
- **an upload that ends in the wiki**: someone adds a document, watches it go through the
  pipeline and opens its new pages a few minutes later;
- **the agent next to the wiki**: an answer with its citations and the pages it used, in the same
  screen, so the reader moves between the agent and the wiki. In this version asking never writes
  to the wiki.

The standalone Studio had the uploads and the run status, but on Azure it never worked:
Container Apps built-in authentication answers **403 to every POST that carries the sign-in
cookie and a browser User-Agent**, before the request reaches the container. A GET, PUT or DELETE
with the same cookie reaches the app, so does an anonymous POST, and so does a POST to a path
excluded from authentication. An ingress CORS policy (the app's own origin, with credentials) does
not change it (measured on 2026-10-22; `docs/operations.md`).

## Decision

1. **The portal is the only web app.** It serves the wiki, the drawer and the process at
   `https://<custom domain>`; the Studio app, its image, identity, roles and sign-in registration
   are removed.
2. **"How it works" is a page of the wiki** (`how-it-works`, written by the site build with the
   rest of the site, so it has the wiki's navigation, search and drawer). It explains the pipeline
   and shows, live and to everyone, read-only: each document's status (`new`, `pending` with its
   stage, `done`, `failed`, `quarantined`) with a link to its source page once published, the
   ingest queue, the current release and the last runs with their stages, timings, gates and cost.
   It reads `GET /api/process`. A document whose sensitivity is above the site's audience is
   listed without its name; error details are shown to the owner only.
3. **Only the owner uploads, signed in on the same site.** Built-in authentication runs in
   `AllowAnonymous` mode: every page stays public and anonymous, `/.auth/login/aad` signs the owner
   in, and the app itself refuses an owner call unless the platform's principal header names an
   object ID of `DOCWIKI_PORTAL_OWNERS` (fail closed: empty refuses everyone). Owner calls use GET
   and PUT only (`GET /api/owner/me`, `PUT /api/owner/documents/{path}`), never POST, and require
   the `X-DocWiki-Owner: 1` header and a same-origin request. The public `POST /api/ask` is an
   excluded path, so it also works for a signed-in owner. An upload writes `raw/<path>` (no
   delete, no overwrite without `?replace=1`, 50 MB, the supported formats, a daily allowance);
   Event Grid and the ingest job do the rest, exactly as for any other document.
4. **Asking is read-only.** The live answer shows its verified citations and links to the wiki
   pages of the cited sources in the drawer; there is no "File to wiki". Answers filed earlier
   (ADR 0007) are still shown; the owner can still file one with `docwiki file-answer`.
5. **Rights.** The portal identity reads `releases/` (as before), `raw/` and `work/` (the source
   states and run reports), peeks the ingest queue, and, when owners are configured, writes to
   `raw/` under a condition that forbids deletes. It has no queue send, no Foundry role and no
   other write.

## Consequences

- A visitor follows one document from upload to wiki page without leaving the site; the process
  is no longer hidden in a second app.
- The portal is no longer read-only: an owner can add documents. The sign-in is the platform's,
  the authorization is the app's allow-list, and the write is limited by a role condition.
- Document names and run costs are public. That suits a public-audience proof of concept; a
  restricted build hides names above its audience.
- Asking the Librarian, approving its proposals and "File to wiki" from a browser are gone in this
  version. They come back, if needed, as owner actions in the drawer that use PUT.
