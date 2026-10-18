# Security policy

## Reporting a vulnerability

Please **do not open a public issue** for a security problem. Report it privately through GitHub:
open the repository's **Security** tab and choose **Report a vulnerability** (private
vulnerability reporting). Include:

- what is affected (component, file, version or commit);
- how to reproduce it, with a minimal example;
- the impact you expect, and any idea of a fix.

Never include real secrets, tokens, personal data or private documents in a report: describe them
or use placeholders. If you have found a secret committed to this repository, report its location
privately and do not reuse it.

DocWiki is an independent open-source project maintained on a best-effort basis. Reports are
acknowledged as soon as possible and valid issues are fixed on the default branch; tell us in the
report whether you want to be credited.

## Supported versions

DocWiki is pre-release. Security fixes are made on the default branch (`main`); there are no
maintained release branches.

## Scope

In scope: the code and configuration in this repository, in particular

- the MCP server's authentication and authorization (`src/docwiki/mcp/`): role enforcement,
  principal handling, tool argument validation, the read-only SQL guard of `query_table`;
- content safety: sanitisation of compiled Markdown, evidence sidecars and the built site,
  injection handling, canary gates, template-only skills;
- sensitivity tiers and audience filtering (content of a higher tier reaching a lower-tier build);
- the infrastructure templates and hooks (`infra/`, `scripts/`, `docker/`): identities, role
  assignments, network exposure, secrets handling;
- the Foundry agent definitions (`agents/`): tool lists, approvals, identity strategy;
- the leak guard (`tools/leakguard/`) and the pre-push hook: bypasses or false negatives.

Out of scope:

- vulnerabilities in Azure, Microsoft Foundry, GitHub or other third-party services and libraries
  (report them to their vendors; tell us if DocWiki should mitigate or upgrade);
- the factual content of the sample corpus, which is **fictional — not for operational use**;
- deployments operated by third parties;
- model behaviour that DocWiki already documents as a limitation (for example a heuristic
  injection detector that misses a novel phrasing), unless it bypasses a control described in
  [docs/security.md](docs/security.md).

## No secrets by design

DocWiki is built so that there is nothing to leak:

- every Azure call uses managed identities or Entra sign-in through `DefaultAzureCredential`;
  there are no API keys, connection strings, SAS tokens or `listKeys()` in code or templates;
- Foundry local authentication, storage shared keys and the registry admin user are disabled;
- the MCP server validates Entra tokens through Container Apps built-in authentication, without a
  client secret;
- environment values (subscription, tenant and object IDs, e-mail addresses) stay in local,
  git-ignored files and are never committed;
- CI runs a secret scanner and the leak guard on every pull request.

A change that introduces a secret, a key-based connection or a private identifier is a security
bug: please report it the same way.

The threat model and controls are described in [docs/security.md](docs/security.md).
