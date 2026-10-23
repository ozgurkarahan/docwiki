# ADR 0011 — A company-wide wiki: scopes and three classification axes

- Status: Accepted 2026-10-23
- Supersedes: goal G8's "one client, one chantier" sample; amends the wiki layout of
  [`wiki-contract.md`](../spec/wiki-contract.md) §1 (new folders) and supersession (keyed by scope)
- Spec: v1.7

## Context

The sample wiki covers one job of one client. A building-trade expert reviewed it (2026-10-22):
a real entreprise de bâtiment runs several chantiers at once, at different phases and under
different contract types, with suppliers and subcontractors shared between them. What a
dirigeant or a conducteur de travaux asks is mostly *across* chantiers: which réception dates a
supplier's delay puts at risk, the financial position of every chantier, the open réserves, the
expired compliance documents, the crews booked twice. And the first thing a professional
distrusts is an LLM adding up invoices.

Today the engine knows no chantier: classification looks at the file name and the text only,
supersession groups documents by number alone (two chantiers both have a "DPGF indice B"), topics
are one page per catalog entry for the whole corpus, and the home page has no table.

## Decision

The engine stays generic; the domain pack names things.

1. **One scope dimension per pack, from the raw path.** An optional pack file `scopes.yaml`
   names the scope (`chantier`, plural `chantiers`), the default for documents outside any scope
   (`entreprise`), and an ordered list of path regexes with named groups `scope`, `phase`,
   `type` and `lot`. The first regex that matches a document's raw path decides; no match means
   the default scope. **Scope and axes never come from the LLM.**
2. **Three classification axes, deterministic:**
   - **phase** from the path (the pack lists them: 0 commercial · 1 marché · 2 préparation ·
     3 exécution · 4 réception · 5 garantie);
   - **type** = the pack's closed list of document types: a path segment that names a type
     decides it, before the rules and the LLM fallback;
   - **lot** from the path or a file-name regex of the pack.
   They are recorded on the classification, in the source frontmatter (`scope`, `phase`, `lot`)
   and in the catalog.
3. **Supersession is keyed by (scope, document number):** two chantiers' "DPGF indice B" never
   supersede each other.
4. **The wiki layout grows, the existing paths stay:**
   - `<plural>/<code>.md` (`chantiers/moreau.md`): one **hub** page per scope value, a new page
     type built by code from the pack's registry entry for that scope (client, contract type,
     maître d'œuvre, conducteur) and from the documents, topics, entities, contradictions and
     last document of that scope; `<plural>/index.md` lists them;
   - `index.md` becomes the **company dashboard**: a table of the scopes (phase, client,
     documents, last document received, open contradictions, and the computed figures of
     decision 5) before the existing sections;
   - topics marked `per_scope` in the topic catalog are written once per scope that has
     sources for them, at `topics/<scope>/<slug>.md`; the others stay company topics at
     `topics/<slug>.md`;
   - entity pages stay at `entities/<type>/<key>.md`; the site groups them as "Entreprise".
5. **Cross-scope figures are computed by code from tables, every row cited.** An optional pack
   file `views.yaml` declares views: a read-only SQL query (the existing locked-down DuckDB) over
   the tables of the documents of given types, unioned by column name. Each result row keeps
   the source and row it came from and is rendered with a footnote to that row's evidence. A
   view page lists the rows; the dashboard shows the per-scope totals the pack asks for. The LLM
   never adds numbers.
6. **Search and agents:** the search index records each page's scope; MCP `search` and
   `get_index` take an optional `within` filter (a scope value, or the default scope). The
   Researcher names the chantier in its answers and asks which one when a question is
   ambiguous ("When are the windows delivered?" with two chantiers ordering windows).
7. **Access stays tier-only** (public, internal, restricted). Per-scope rights are out of scope
   for the proof of concept, and the site says so.

## Consequences

- A pack without `scopes.yaml` behaves exactly as before (one implicit scope, no hubs, no
  dashboard table).
- The batiment sample moves its documents under `chantiers/<code>/<phase>/<type>/` and
  `entreprise/<type>/` (slice F); until then its pack declares no scopes.
- Hubs, the dashboard and views are deterministic: they cost nothing to rebuild and can be
  trusted line by line; topics stay LLM syntheses with citations.
- More page types and folders: the contracts, the release validator, the MCP tool descriptions
  and the site's explorer learn them.
