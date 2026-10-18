# DocWiki - instructions for coding agents and contributors

DocWiki compiles a folder of messy documents (PDF, Word, Excel, CSV, PowerPoint, email, scans,
transcripts) into a Karpathy-style Markdown wiki that humans can browse and agents can trust:
every claim is cited back to the original page, sheet or row. It runs on Azure Container Apps with
Microsoft Foundry models and two Foundry agents (Librarian and Researcher).

**The authoritative design is the frozen spec in `docs/spec/`. Read `docs/spec/README.md` first.**
If code and spec disagree, the spec wins; propose spec changes in your summary instead of
silently diverging.

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
