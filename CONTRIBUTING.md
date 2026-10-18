# Contributing to DocWiki

Thank you for your interest in DocWiki. Contributions of all sizes are welcome: bug reports,
fixes with tests, domain packs for other industries, documentation, and evaluation work.

Before you start, read [`AGENTS.md`](AGENTS.md). It is the single instruction file for coding
agents **and** humans in this repository (`CLAUDE.md` and `.github/copilot-instructions.md` point
to it), and the design it refers to, [`docs/spec/`](docs/spec/README.md), is authoritative.

## Ground rules

These are non-negotiable, for every file, test and sample:

1. **Closed world.** Every organisation, person, product, brand, site, asset and place name in
   code, docs, samples, tests or generated content comes from
   [`samples/fiction/bible.yaml`](samples/fiction/bible.yaml), or is a public technology name
   (Azure, Python, Quartz, GitHub…). Never use a real company, person, site or brand in sample
   content.
2. **Only public inputs.** Work from this repository and public documentation. Never copy or
   paraphrase private material.
3. **Zero secrets and no private identifiers.** Use managed identity and `DefaultAzureCredential`.
   Never commit keys, connection strings, SAS tokens, `listKeys()`, subscription, tenant or object
   IDs, e-mail addresses, internal URLs or local machine paths.
4. **Documents are untrusted data.** Document text never becomes instructions, skills, raw HTML or
   links to unknown hosts. Model calls that read document text use structured outputs and no tools.
5. **Evidence first.** Generated content is source-grounded and cited; never invent procedures,
   parameters, safety rules or facts.
6. **Fictional safety content.** Every procedure-like sample document carries the stamp
   "FICTIONAL - NOT FOR OPERATIONAL USE".

## Development setup

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/) and git. Node 22+ only for site
builds; Azure CLI and azd only for live work.

```bash
git clone https://github.com/ozgurkarahan/docwiki
cd docwiki
uv sync --all-extras                  # Windows ARM64: uv sync --all-extras --no-extra evals
uv run docwiki version
```

| Extra | Pulls in |
|---|---|
| `extract` | PDF, Office and image parsers (pypdfium2, python-docx, openpyxl, python-pptx, Pillow) |
| `azure` | Azure SDKs: identity, Blob and Queue storage, Foundry projects, OpenTelemetry |
| `mcp` | The MCP SDK, DuckDB and the HTTP server |
| `workflow` | Microsoft Agent Framework (the pipeline orchestrator) |
| `portal` | The private portal's web server |
| `evals` | `azure-ai-evaluation` (no Windows ARM64 wheels; use Linux or x64 Python) |
| `gen` | Sample corpus generators (fpdf2, matplotlib, Office libraries, Pillow) |

`azure-ai-evaluation` pulls packages without Windows ARM64 wheels, hence `--no-extra evals` on
that platform. Do not commit lock files produced on your machine (`uv.lock`, `package-lock.json`):
they may embed private package-mirror URLs. CI resolves dependencies against the public registries.

## Lint and test

```bash
uv run ruff check .
uv run pytest                                   # the offline suite; tests marked live are excluded
uv run pytest tests/mcp                         # one area
DOCWIKI_SITE_BUILD=1 uv run pytest tests/site   # also builds the mock release site (Node 22+, git)
uv run pytest -m live                           # needs Azure resources and DOCWIKI_* settings
```

In PowerShell, set the variable first: `$env:DOCWIKI_SITE_BUILD = "1"`.

- Tests never touch the network. Model calls go through `docwiki.llm` and use the fake or replay
  client; Content Understanding responses are recorded and replayed. Record fixtures only from
  public sample content: they contain prompt and document text.
- Ruff enforces line length 100 and the rule set in `pyproject.toml`; most files also follow
  `ruff format`, so keep the formatting of the code around you.
- CI runs lint and tests, the leak guard with public rules, a gitleaks secret scan, a Bicep build
  and a site build of the mock release.

## Leak guard

The repository is public, so publication safety is part of every change:

```bash
uv run python tools/leakguard/leakguard.py scan --root .     # public rules, exactly as CI runs them
```

Maintainers also run the strict scan with a private deny-list kept outside the repository
(`DOCWIKI_DENYLIST`), and install the fail-closed pre-push hook with
`git config core.hooksPath .githooks`. The hook runs the strict scan, so it blocks pushes until a
deny-list is configured; if you do not hold one, skip the hook and run the public scan before you
open a pull request.

When the scanner reports a finding, in this order of preference: fix the content (use a name from
the bible, a reserved `.example` domain, a placeholder such as `<subscription-id>`, strip the
metadata); extend the right list (a new fictional name goes into the bible, a public technology
name into `tools/leakguard/tech_allowlist.txt`); or record a reviewed exception in
`tools/leakguard/ignore.txt` with its reason. Never weaken a rule to silence one finding. Details:
[`tools/leakguard/README.md`](tools/leakguard/README.md).

## Engineering conventions

- Python 3.12+, type hints everywhere, `pathlib`, `encoding="utf-8"` for all text I/O, LF line
  endings.
- Deterministic first: anything derivable from structure (paths, IDs, links, indexes, tables) is
  computed by code, not by a model.
- All model calls go through `docwiki.llm`; prompts are versioned files under
  `src/docwiki/stages/prompts/` with a `PROMPT_VERSION` that feeds the cache keys.
- Errors surface: no silent fallbacks that hide a failed extraction, compilation or Azure call.
- Do not add dependencies casually. When one is needed, add it to the matching extra in
  `pyproject.toml` and explain why in the pull request.
- Contracts are code: models live in `src/docwiki/contracts/`, documented in
  [`CONTRACT.md`](src/docwiki/contracts/CONTRACT.md). After changing one, regenerate the JSON
  Schemas with `uv run python -m docwiki.contracts.export_schemas` (a test fails when they are
  stale).

## Sample content and the closed world

- New names go into [`samples/fiction/bible.yaml`](samples/fiction/bible.yaml) first. Prefer
  Microsoft's documented fictitious brand names for organisations, and check every new name on
  the web so that it does not match a real company, product, site or person in the domain. Then
  regenerate the allowlist: `uv run python samples/generators/allowlist.py`.
- Generators are deterministic (fixed seeds) and write neutral metadata (author "DocWiki sample
  generator", no EXIF): `uv run python samples/generators/build.py --out samples/corpus`.
- The corpus is frozen and the golden set is **sealed** against it. A justified change to either
  goes through `evals/golden/author.py`, which re-verifies every citation and re-seals; the commit
  message explains why the seal changed. Never edit `evals/golden/dev.jsonl` by hand, never read
  or commit the private holdout, and never tune prompts on holdout results.

## Proposing spec changes

The v1 spec in [`docs/spec/`](docs/spec/README.md) is frozen. If code and spec disagree, the spec
wins until a change is accepted.

1. Open an issue that states the problem, the proposed change, and the contracts, gates or tests it
   affects.
2. Clarifications that do not change the design are recorded in
   [`docs/spec/CHANGELOG.md`](docs/spec/CHANGELOG.md); interface details go into `CONTRACT.md`.
3. Decisions with alternatives and consequences get an ADR in [`docs/adr/`](docs/adr/README.md).
   Back risky assumptions with a spike first, as the identity spike did for ADR 0003.
4. Update the code, the contracts, the JSON Schemas and the guides in the same pull request.

## Commits and pull requests

- Use [Conventional Commits](https://www.conventionalcommits.org/): `feat(mcp): …`,
  `fix(engine): …`, `docs: …`, `test(extract): …`, `build: …`, `ci: …`.
- Keep pull requests focused, and describe what changed, why, and how you tested it.
- Checklist: `ruff check` clean, tests pass, the public leak-guard scan is clean, docs updated,
  no secrets, only fictional names in samples.

## Documentation and images

Guides live in [`docs/`](docs/README.md). The architecture diagram and the social preview are
generated by scripts in [`scripts/docs/`](scripts/docs); regenerate them rather than editing the
files by hand:

```bash
uv run python scripts/docs/architecture_svg.py
uv run --extra gen python scripts/docs/social_preview.py
```

## Security

Do not open public issues for vulnerabilities: follow [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions are licensed under the licenses of this
repository: [MIT](LICENSE) for code and [CC BY 4.0](LICENSE-CONTENT.md) for sample content,
images and diagrams.
