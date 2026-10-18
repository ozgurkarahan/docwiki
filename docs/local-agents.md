# Use the sample wiki with your coding agent

You do not need Azure to explore DocWiki with an agent. The DocWiki MCP server runs locally over
stdio, serves a release folder read-only, and works with any MCP client. This page gives the exact
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

> **Which release?** The committed configurations serve `samples/wiki/`, the sample release of the
> fictional wind farm compiled on Azure (37 sources, 165 pages), committed as a portable wiki
> folder. For a quicker smoke test, `samples/fixtures/mock-release` is a small hand-made release
> (three sources, one topic, three entities) with the same contract.
> `--release` accepts a release folder, a `releases/` folder with `current.json`, or a folder that
> contains `releases/current.json`, so a release you compiled yourself works too
> (`--release .local/releases`).

In local mode the server exposes the **read tools only**: `search`, `read_page`, `get_index`,
`get_links`, `glossary`, `get_evidence`, `query_table`, `get_skill`, `list_skills` and
`recent_changes`. The operations tools need `--allow-ops` and a work folder (development only).

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
        "--release",
        "samples/wiki"
      ],
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
        "--release",
        "samples/wiki"
      ]
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
               "--release", "samples/wiki"],
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
        "--release", "samples/wiki"]
cwd = "<path to your docwiki clone>"
startup_timeout_sec = 60
```

The CLI equivalent is `codex mcp add docwiki -- uv run --extra mcp python -m docwiki.mcp.server --stdio --release samples/wiki`
(run Codex from the repository root then). Check your Codex version's MCP documentation if an
option is not recognised.

## Skills

The sample wiki carries its Agent Skills in three identical folders (`.agents/skills`,
`.claude/skills`, `.github/skills`; see [skills](skills.md)). Two ways to use them:

- **Through MCP, from the repository root:** ask the agent to call `list_skills` and `get_skill`,
  for example *"Read the docwiki `deep-research` skill, then follow it"*.
- **As native skills:** open the wiki folder of the release (for example
  `samples/fixtures/mock-release/releases/20260215T090000Z-decd4b59/wiki/`) as the project or
  working directory, so that the client discovers the skill folder it supports. Plain file reads
  then work too: `AGENTS.md`, `index.md` and the topic pages are ordinary Markdown.

## Prompts to try

On the mock release:

- *"Use the docwiki tools: which gearbox oil grade applies to WTG-07 in winter? Cite the
  evidence."* The topic page reports a contradiction between the current procedure and the 2026
  maintenance plan; a good answer gives both claims and the resolution rule.
- *"What did revision A of the gearbox oil change SOP say, and what replaced it?"* (supersession)
- *"Query the maintenance plan table: which turbines have a gearbox oil change planned, and
  when?"* (`query_table` with row ids)
- *"What does WTG mean, and how is it called in French?"* (glossary synonyms)

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
