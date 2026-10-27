# Use a wiki with your coding agent

The DocWiki MCP server runs locally over stdio, serves a release read-only (from a folder, or from
the Blob storage of your own deployment), and works with any MCP client. This page gives the exact
configuration for GitHub Copilot (VS Code and CLI), Claude Code and Codex.

## Prerequisites

```bash
git clone https://github.com/ozgurkarahan/docwiki
cd docwiki
uv sync --all-extras        # Windows ARM64: uv sync --all-extras --no-extra evals
```

Check the server once by hand (it waits for an MCP client on stdin; stop it with Ctrl+C):

```bash
uv run --extra mcp python -m docwiki.mcp.server --stdio --release samples/fixtures/mock-release
```

> **Which release?** The committed VS Code and Claude Code configurations serve
> `samples/fixtures/mock-release`, a small hand-made release (three sources, one topic, three
> entities) with the same contract, so they work without Azure. To read the current release of
> your own deployment instead, sign in with `az login`, set `DOCWIKI_MODE=azure` and
> `DOCWIKI_STORAGE_ACCOUNT` to your storage account, and replace `--release ...` with
> `--storage blob`. `--release` also accepts a release folder, a `releases/` folder with
> `current.json`, or a folder that contains `releases/current.json`, so a release you compiled
> yourself works too (`--release .local/releases`).

In local mode the server exposes the **read tools only**: `answer_context`, `search`,
`read_page`, `get_index`, `get_links`, `glossary`, `get_evidence`, `query_table`, `get_skill`,
`list_skills` and `recent_changes`. The operations tools need `--allow-ops` and a work folder (development only).

## GitHub Copilot in VS Code

The repository ships [`.vscode/mcp.json`](../.vscode/mcp.json):

```json
{
  "servers": {
    "docwiki": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--extra",
        "mcp",
        "python",
        "-m",
        "docwiki.mcp.server",
        "--stdio",
        "--storage",
        "blob"
      ],
      "env": {
        "DOCWIKI_MODE": "azure",
        "DOCWIKI_STORAGE_ACCOUNT": "${env:DOCWIKI_STORAGE_ACCOUNT}"
      },
      "cwd": "${workspaceFolder}"
    }
  }
}
```

Open the repository folder, start the `docwiki` server from the MCP view or the prompt to trust
it, then use Copilot Chat in **agent mode** and enable the DocWiki tools in the tools picker.

## Claude Code

The repository ships [`.mcp.json`](../.mcp.json), a project-scoped server definition:

```json
{
  "mcpServers": {
    "docwiki": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--extra",
        "mcp",
        "python",
        "-m",
        "docwiki.mcp.server",
        "--stdio",
        "--storage",
        "blob"
      ],
      "env": {
        "DOCWIKI_MODE": "azure",
        "DOCWIKI_STORAGE_ACCOUNT": "${DOCWIKI_STORAGE_ACCOUNT}"
      }
    }
  }
}
```

Run `claude` from the repository root and approve the project server when Claude Code asks;
`/mcp` shows its status and tools.

## GitHub Copilot CLI

Copilot CLI reads its servers from the user configuration (`~/.copilot/mcp-config.json`, or
`/mcp add` inside the CLI). Add this entry and run the CLI from the repository root:

```json
{
  "mcpServers": {
    "docwiki": {
      "type": "local",
      "command": "uv",
      "args": ["run", "--extra", "mcp", "python", "-m", "docwiki.mcp.server", "--stdio",
               "--release", "samples/fixtures/mock-release"],
      "tools": ["*"]
    }
  }
}
```

## Codex

Codex reads MCP servers from `config.toml` (`~/.codex/config.toml`, or a project-scoped
`.codex/config.toml` in trusted projects). This configuration is not shipped in the repository;
set `cwd` to your clone and allow the first `uv` start some time:

```toml
[mcp_servers.docwiki]
command = "uv"
args = ["run", "--extra", "mcp", "python", "-m", "docwiki.mcp.server", "--stdio",
        "--release", "samples/fixtures/mock-release"]
cwd = "<path to your docwiki clone>"
startup_timeout_sec = 60
```

The CLI equivalent is `codex mcp add docwiki -- uv run --extra mcp python -m docwiki.mcp.server --stdio --release samples/fixtures/mock-release`
(run Codex from the repository root then). Check your Codex version's MCP documentation if an
option is not recognised.

## Skills

A wiki carries its Agent Skills in three identical folders (`.agents/skills`,
`.claude/skills`, `.github/skills`; see [skills](skills.md)). Two ways to use them:

- **Through MCP, from the repository root:** ask the agent to call `list_skills` and `get_skill`,
  for example *"Read the docwiki `deep-research` skill, then follow it"*.
- **As native skills:** open the wiki folder of the release (for example
  `samples/fixtures/mock-release/releases/20260401T090000Z-8a41b109/wiki/`) as the project or
  working directory, so that the client discovers the skill folder it supports. Plain file reads
  then work too: `AGENTS.md`, `index.md` and the topic pages are ordinary Markdown.

## Prompts to try

On a release compiled from the full sample corpus:

- *"Use the docwiki tools: which delivery date applies to the windows, and why do the documents
  disagree? Cite the evidence."* The topic page reports a contradiction between the planning and
  the window maker's e-mail; a good answer gives both claims and the resolution rule.
- *"What did indice A of quote DEV-2026-014 say about the bay window, and what replaced it?"*
  (supersession)
- *"Query the Achats sheet of the planning workbook: how much has been ordered, and how much
  invoiced to date?"* (`query_table` with row ids)
- *"What does 'retenue de garantie' mean, and what is it called in English?"* (glossary
  synonyms)

The mock release holds only three sources (two revisions of the planning and the minutes of site
meeting n°3). The questions above are written for a release of the full sample corpus and mostly get "not found"
on the mock (the Achats one works). Try these on the mock instead:

- *"Use the docwiki tools: when are the windows delivered, and what was the date before?"* The
  answer is 2026-04-20 (indice B of the planning, minutes ¶ 11); indice A, now superseded, gave
  2026-03-30.
- *"How far along are the walls? Do the documents agree?"* The topic page reports a
  contradiction, 100 % in indice B and 70 % in the minutes of 2026-03-24, and the minutes prevail
  (authority 7 against 4).
- *"What is an 'indice', in English?"* (glossary synonyms: "revision")

The answers should end with sources in the Researcher's format,
`[n] <source title> — <locator label> (<provenance>) — <sidecar path>`, and every sidecar path
should open the exact paragraph, page or rows.

## Troubleshooting

| Symptom | Fix |
|---|---|
| The server does not start | Run the command above by hand from the repository root; `uv sync --all-extras` installs the `mcp` extra |
| `not_found` or `unavailable` results | The release path is wrong or not generated yet: use `samples/fixtures/mock-release` |
| Tools are listed but never called | Use agent mode (VS Code) and name the tools in the prompt ("use the docwiki tools") |
| A slow first start | `uv` resolves the environment on the first launch; later starts are fast |
| Paths printed in answers start with `../` | Footnote targets are relative to the page; `get_evidence` returns the canonical `evidence/<source_id>/<locator_key>.md` path |
