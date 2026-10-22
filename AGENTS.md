# DocWiki - instructions for coding agents and contributors

DocWiki compiles a folder of messy documents (PDF, Word, Excel, CSV, PowerPoint, email, scans,
transcripts) into a Karpathy-style Markdown wiki that humans can browse and agents can trust:
every claim is cited back to the original page, sheet or row. It runs on Azure Container Apps with
Microsoft Foundry models and two Foundry agents (Librarian and Researcher).

**The authoritative design is the frozen spec in `docs/spec/`. Read `docs/spec/README.md` first.**
If code and spec disagree, the spec wins; propose spec changes in your summary instead of
silently diverging.

## Owner decisions (2026-10-21 and 2026-10-22, apply now; they win over older spec text until the spec is updated)

DocWiki is a **public proof of concept**. Its job is to show one pattern clearly: messy documents
become a cited wiki that is served on Azure Container Apps, with Microsoft Foundry agents working
*inside* that wiki. It must be easy to understand and easy to present.

1. **One site, one app (ADR 0009, 0010).** The wiki, the process and the agents are one website
   served by the portal, told as three tabs: ① Documents · ② Pipeline · ③ Wiki. Everyone reads
   the wiki, asks the Researcher in the drawer and follows the process on the `pipeline` page
   (each document's status, the runs, the release). Only the
   owner, signed in on the same site, uploads documents. Asking never writes to the wiki in this
   version: answers show their citations and the wiki pages they used.
2. **A public LLM endpoint is allowed.** The old invariant "no public endpoint calls an LLM"
   (`docs/spec/architecture.md` §8, D13) is dropped (ADR 0008, live since 2026-10-21). It is
   replaced by: per-IP rate limits, a token budget and a daily cost cut-off that falls back to the
   filed answers. Limits run in an existing,
   shared Azure API Management instance, passed in as a deployment parameter; never create a new
   one, and never commit its name or URL. Live answers go through the same quote verification and
   leak checks as filed answers before they are shown.
3. **One public repository, no GitHub Pages.** This repository is the only one. The demo is served
   from Azure at https://docwiki.ozgurkarahan.com; there is no Pages site or committed
   `samples/wiki`. Only push `main` or branches created from it: local branches or worktrees whose
   history predates the public snapshot (the old private repository) must never be pushed here.
4. **GlobalStandard model deployments are the default.** This PoC has no data-residency requirement.
5. **The standalone Studio is removed (2026-10-22, ADR 0009).** On Azure, built-in authentication
   refuses every browser POST that carries its session cookie, so owner calls use GET and PUT only
   and the public `POST /api/ask` is excluded from authentication. Do not reintroduce a second app.
6. **Small, reviewable steps.** Prefer short slices and small pull requests over long runs.
7. **Decisions live here.** When the owner makes a new decision, record it in this section (and in
   an ADR when it changes the design), so every coding agent, including GitHub Copilot sessions,
   works from the same facts.

## Hard rules (non-negotiable)

1. **Closed world.** Every organisation, person, product, brand, site, asset and place name in
   code, docs, samples, tests or generated content MUST come from `samples/fiction/bible.yaml`
   (or be a public technology name such as Azure, Python, Quartz, GitHub). Never use a real
   company, person, site or brand in sample content. When unsure, use a name from the bible.
2. **Only public inputs.** Work only inside this repository and with public documentation.
   Never read, copy or paraphrase files from other folders on this machine.
3. **Zero secrets and no private identifiers.** Use managed identity / `DefaultAzureCredential`.
   Never commit keys, connection strings, SAS tokens, `listKeys()`, subscription / tenant /
   object IDs, e-mail addresses, internal URLs or local machine paths.
4. **Documents are untrusted data.** Document text never becomes instructions, skills, raw HTML,
   or links to unknown hosts. LLM calls that read document text use structured outputs and no tools.
5. **Evidence first.** Generated wiki content is source-grounded and cited. Never invent
   procedures, parameters, safety rules or facts.
6. **Fictional safety content.** Every procedure-like sample document carries the stamp
   "FICTIONAL - NOT FOR OPERATIONAL USE".

## Engineering conventions

- Python 3.12+, type hints everywhere, `pathlib`, `encoding="utf-8"` for all text I/O.
- Environment: `uv sync --all-extras` then `uv run ...`. Do not add dependencies casually; if a
  lane needs a new one, add it to the matching extra in `pyproject.toml` and say so in your summary.
- Lint and test: `uv run ruff check .` and `uv run pytest` (tests needing Azure are marked
  `@pytest.mark.live` and excluded by default).
- LLM calls only through `docwiki.llm`; tests use the fake/replay client, never the network.
- Deterministic first: anything derivable from structure (paths, IDs, links, indexes, tables)
  is computed by code, not by an LLM.
- Errors surface; no silent fallbacks that hide failed extraction, compilation or Azure calls.
- LF line endings, ruff line length 100.
- Never commit lock files produced on a developer machine (`uv.lock`, `package-lock.json`): they may
  embed private package-mirror URLs. CI resolves dependencies against the public registries.
- On Windows ARM64, sync with `uv sync --all-extras --no-extra evals` (`azure-ai-evaluation`
  pulls `pandas`, which has no ARM64 wheel); run evaluations on Linux CI or an x64 Python.

## Repository map and ownership (parallel lanes)

| Path | Owner lane | Purpose |
|---|---|---|
| `docs/spec/` | main (frozen) | Authoritative design |
| `src/docwiki/contracts/`, `src/docwiki/domain/`, `src/docwiki/search/`, `src/docwiki/release/` | contracts | Schemas, domain-pack loader, search index, release snapshot I/O |
| `samples/fixtures/mock-release/` | contracts | Hand-made release used by other lanes |
| `samples/fiction/`, `samples/generators/`, `samples/corpus/`, `domains/`, `evals/golden/` | corpus | Fictional world, corpus, domain packs, golden questions |
| `src/docwiki/llm/` | llm | Foundry model client, fake/replay client, cost receipts |
| `src/docwiki/extract/`, `src/docwiki/stages/`, `src/docwiki/orchestration/`, `src/docwiki/storage/`, `src/docwiki/cli.py`, `skills/templates/` | engine | Extraction, pipeline stages, workflow, CLI, skill templates |
| `src/docwiki/mcp/` | mcp | MCP server and tools |
| `agents/` | agents | Foundry agent definitions and deploy scripts |
| `site/`, `src/docwiki/portal/` | site | Quartz site and optional portal |
| `infra/`, `azure.yaml`, `docker/`, `BOOTSTRAP.md` | infra | Azure infrastructure and runbook |
| `tools/leakguard/`, `.githooks/` | leakguard | Leak prevention |
| `evals/` (except `golden/`) | evals | Evaluation runner and baselines |
| `.github/` | main | CI workflows |

Stay inside your lane's paths. Shared files (`pyproject.toml`, `README.md`, `AGENTS.md`) are edited
by the main agent; describe needed changes in your summary.

## Validation

```powershell
git config core.hooksPath .githooks        # once per clone: enables the fail-closed pre-push leak guard
uv sync --all-extras --no-extra evals
uv run ruff check .
uv run pytest
uv run python tools/leakguard/leakguard.py scan --root . --strict   # set DOCWIKI_DENYLIST to a private deny-list file
```

The private deny-list file lives outside the repository; its path is given by the
`DOCWIKI_DENYLIST` environment variable (see `tools/leakguard/README.md`).
