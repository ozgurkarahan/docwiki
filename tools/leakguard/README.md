# Leak guard (publication safety)

DocWiki is published as a public open-source repository. The leak guard scans everything that
could be published and fails when it finds private identifiers, secrets, real-world names or
revealing metadata. It implements `docs/spec/infra-ops-security.md` §5 and the closed-world rule
of `docs/spec/domain-and-corpus.md` §2.

```powershell
uv sync --all-extras --no-extra evals          # once (Linux/x64: uv sync --all-extras)
$env:DOCWIKI_DENYLIST = "<path outside the repository>"
uv run python tools/leakguard/leakguard.py scan --root . --strict
uv run python tools/leakguard/leakguard.py scan --root . --history --strict   # before publishing
```

## Command line

```text
leakguard.py scan [--root DIR] [--history] [--commits-from FILE|-] [--include-untracked]
                  [--site DIR]... [--site-vendor FILE] [--denylist FILE] [--allowlist FILE]
                  [--ignore-file FILE] [--strict] [--format text|json] [--redact | --no-redact]
leakguard.py denylist-ids [--denylist FILE]
```

| Option | Meaning |
|---|---|
| `--root` | Repository to scan (default `.`). The default file set is `git ls-files`. |
| `--include-untracked` | Also scan untracked files that are not ignored (`git ls-files --others --exclude-standard`). |
| `--history` | Also scan every commit of every ref: added lines, commit messages, author/committer names and e-mails, annotated tags, and every historical version of binary files. |
| `--commits-from FILE` | Scan only the listed commits (one SHA per line, `-` = stdin); used by the pre-push hook. |
| `--site DIR` | Scan a built site or generated wiki folder (all files, not only tracked ones). Repeatable. |
| `--site-vendor FILE` | Reviewed exemptions for third-party bundles inside `--site` folders (default: `tools/leakguard/site_vendor.txt`). |
| `--denylist FILE` | Private deny-list (default: the `DOCWIKI_DENYLIST` environment variable). |
| `--allowlist FILE` | Fiction allowlist (default: `samples/fiction/allowlist.txt`; optional while it does not exist). |
| `--ignore-file FILE` | Reviewed false positives (default: `tools/leakguard/ignore.txt`). |
| `--strict` | Warnings fail the scan too, and a missing deny-list becomes an error. |
| `--format json` | Machine-readable report (`findings`, `notices`, `summary`, `stats`), ASCII-only (non-ASCII as `\uXXXX`) so it stays valid in any console or pipe encoding. |
| `--redact` / `--no-redact` | Redact matched text. On by default when the environment variable `CI` is `true`. |

`denylist-ids` prints the rule id (`deny:<hash>`) of every deny-list line, so that the owner can
map a redacted CI finding back to a line of the private file.

Exit codes: **0** clean, **1** findings (errors; warnings only with `--strict`), **2** configuration
error (not a git work tree, unreadable or invalid configuration file, deny-list inside the
repository...).

Every finding has an `id` (stable fingerprint `LG-xxxxxxxxxx` of rule + file + matched text), a
`severity` (`error` or `warning`), a `file` (`path`, or `path@commit` for history), a `line` and/or
`location` (page, sheet cell, XML part, table row...), a `rule` and a `message`. Repeated matches are
merged (`count`).

## What is extracted

| Content | Extraction |
|---|---|
| Text files | Every line. Python: string literals and comments feed the proper-noun check (code does not). Markdown: fenced code is excluded from the proper-noun check. HTML/SVG/XML: visible text and `alt`/`title`/`content` attributes. Lines written with string escapes (`\u00fc`, `\n`, `\\`, as in JSON) are also checked decoded, without reporting a match twice. |
| DOCX, XLSX, PPTX (and macro/template variants) | Every XML part: paragraphs (including deleted text of tracked changes, comments, headers, footers, notes, charts), sheet cells (by cell reference, formulas separately), hyperlink targets, comment authors, `docProps/core.xml` (creator, lastModifiedBy, title...), `docProps/app.xml` (company, manager...), `docProps/custom.xml`; embedded images and files recursively. Template boilerplate (themes, styles, fonts, masters, layouts, shape names) is checked for identifiers but not for proper nouns; table style references (`tableStyleId`, built-in Office constants) are not scanned. |
| PDF (pypdfium2) | Page text, Info dictionary (Author, Creator, Producer...), XMP packets, link URIs, bookmarks, embedded files; pages without a text layer are reported as notices (no OCR). |
| Images (Pillow) | EXIF presence, PNG text chunks, comments and XMP. Pixels are not OCR-scanned (notice). |
| E-mail (`.eml`) | Decoded headers and bodies; attachments recursively. |
| SQLite | Schema and every text value of every table. |
| Parquet | Rows and key-value metadata through `duckdb` (the `mcp` extra); without duckdb, or for historical versions, an "unscanned" notice is reported. |
| ZIP archives | Entry names and entries recursively. |
| Other binaries | Printable ASCII/UTF-16 strings, plus an `unscanned-binary` warning. Fonts are string-scanned without warning. |
| Git history (`--history`) | `git log --all -p --raw` (added lines with their line numbers, file paths), commit messages, author/committer identities, annotated tags; binary blobs changed by any commit are extracted like working-tree files. History findings already present in the working tree are not repeated. Tool-generated commit trailers whose value is a random identifier (`Copilot-Session:`, `Change-Id:`) are skipped. Proper nouns are judged against every historical version of the word lists (see "Closed-world check"). |

## Rules

| Rule | Severity | Detects |
|---|---|---|
| `deny:<hash>` | error | A line of the private deny-list (case-insensitive regex) matched. `<hash>` is `sha256(pattern)[:8]`. |
| `denylist-missing` | warning (error with `--strict`) | No deny-list configured, or the file has no pattern. |
| `guid` | error | Any GUID not listed in `allowed_guids.txt` (subscription, tenant, object, client IDs...). |
| `azure-resource-id` | error | `/subscriptions/<guid>/...` resource IDs. |
| `email` | error | E-mail addresses except `*@users.noreply.github.com`, `example.com`, `example.org` and `allowed_domains.txt`. |
| `home-path` | error | Windows (`<drive>:\Users\<name>`) and Unix/macOS (`/home/<name>`, `/Users/<name>`) home paths; generic names (`runner`, `Public`, placeholders) are accepted. |
| `private-key` | error | PEM/OpenSSH/PGP private key blocks, PuTTY keys. |
| `secret-github-token`, `secret-token` | error | GitHub tokens and other well-known token formats, npm registry credentials. |
| `secret-azure-key`, `secret-azure-sas` | error | `AccountKey=`/`SharedAccessKey=` values and SAS signatures (`sig=`). |
| `secret-jwt` | error | JSON Web Tokens. |
| `secret-assignment` | error | Literal values assigned to `api_key`, `client_secret`, `password`, `*_TOKEN`... (placeholders such as `<...>`, `${...}`, `changeme` are ignored). |
| `secret-url-credentials` | error | URLs with an embedded user name and password before the host. |
| `internal-host` | error | Internal-looking host names: `*.internal`, `*.lan`, `*.corp`, `*.corp.*`, `intranet` labels, `.local`/single-label hosts in URLs and UNC paths. Reserved test domains (`.example`, `.test`...) and well-known names (`localhost`, `host.docker.internal`) are accepted. |
| `package-mirror` | error | URLs of package indexes or mirrors other than `pypi.org`, `files.pythonhosted.org` and `registry.npmjs.org` (Artifactory, Nexus, Azure Artifacts feeds, `/simple/` indexes, URLs right after an `index-url`/`registry` setting...). |
| `lockfile-mirror` | error | Lock and registry files (`uv.lock`, `package-lock.json`, `requirements*.txt`, `.npmrc`, `pip.conf`...) resolving from any non-public host. |
| `policy-file` | error | Files that must never be committed: lock files (`uv.lock`, `package-lock.json`, `yarn.lock`...), `.env*`, key/certificate containers and credential files, and any tracked file matching `.gitignore` (in history too). |
| `closed-world` | error in `samples/`, warning in `evals/golden/` and `--site` folders | Capitalised names not in the fiction allowlist, the technology allowlist or the common words (see below). |
| `metadata-office-author` | error in `samples/`, warning elsewhere | Office `creator`/`lastModifiedBy` must be `DocWiki sample generator` or empty in `samples/`; elsewhere any value that is not a known tool name is reported. |
| `metadata-pdf` | error in `samples/`, warning elsewhere | PDF `Author` must be `DocWiki sample generator` or empty in `samples/`; `Creator`/`Producer` must not contain personal or user names. |
| `metadata-exif` | error | Any EXIF block, in any image (also images embedded in Office files and PDFs). |
| `scan-error` | warning | A file could not be fully extracted (corrupt file, missing extraction library...). |
| `unscanned-binary` | warning | Unknown binary format: only printable strings were scanned. |

### Closed-world check

In sample content (`samples/`, `evals/golden/`, `--site` folders) the scanner extracts candidate
proper nouns: runs of capitalised words (with connectors such as "of", "de", "&"), camel-case or
brand-like tokens (`iThing`, `ThingView`), acronyms. Text written with unicode escapes (`\u00fc`,
common in JSON and YAML) is decoded first, for every rule. These are not candidates:

- a single capitalised word that only starts a sentence, or that opens a phrase (start of a cell,
  a line or a double-quoted value, or after a colon) **and** is followed by lower-case prose
  ("Deliver the windows", `"summary": "Curated syntheses"`). A capitalised word standing alone
  ("Supplier: Zorblax", a cell holding "Zorblax"), parentheses and Markdown headings are always
  checked;
- fragments of alphanumeric identifiers: compounds containing a digit or an underscore, such as
  release ids (`20260401T090000Z-7ce99a3f`), ISO timestamps, source ids (`src-c6436ec50050`),
  locators (`p0003`, `b0042`), delivery note numbers (`BL-2026-0391`), document numbers
  (`DEV-2026-014`) and code identifiers (`FIXTURE_DIR`). Product or model codes containing digits
  are therefore not checked: real ones belong in the private deny-list;
- format placeholders made of one repeated capital letter (`BC-2026-NNN`, `YYYY-MM-DD`).

A candidate is accepted when every word is known:

1. `samples/fiction/allowlist.txt` (generated from `samples/fiction/bible.yaml`);
2. `tools/leakguard/tech_allowlist.txt` (public technology, standard, unit and currency names);
3. `tools/leakguard/common_words.txt` (curated English, French and German words);
4. words that the scanned sample content itself writes in lower case in prose.

Inflected forms of known words (plurals, possessives, "-ed", "-ing", "-ly", "-ment", "-ness") are
known; agent nouns ("-er") are not inflected on purpose because many surnames would become common
words. Camel-case compounds made only of known words (`ReleaseReader`, `PDFContext`) are treated as
code identifiers; tokens with an unknown or one-letter hump (`ZorbView`, `iZorb`) stay candidates.

History is judged against every version of the word lists it contains. A candidate found in
history (`--history`, `--commits-from`) is accepted when the current lists know it, or when any
version of `samples/fiction/allowlist.txt`, `tools/leakguard/common_words.txt` or
`tools/leakguard/tech_allowlist.txt` in the scanned history (the scanned commits, their ancestors
and `HEAD`) knew it. A sample world that has been replaced therefore does not turn into errors in
the old commits that describe it: the names that were valid in their time stay valid there. The
working tree and the `--site` folders are always judged against the current lists, so a retired
name that is still used in a current file is still reported. A version of a list that cannot be
parsed is skipped with a `config` notice.

The check is a heuristic safety net, not a guarantee: a real name made only of common words, or a
name opening a sentence or a value, is not detected. Real names that must never appear belong in
the private deny-list.

## Configuration files

| File | Format |
|---|---|
| Private deny-list (`DOCWIKI_DENYLIST`, never in the repository) | One case-insensitive Python regex per line; full-line `#` comments; surrounding blanks ignored. The scanner refuses a deny-list inside the repository. |
| `samples/fiction/allowlist.txt` | One term per line (multi-word terms allowed, every word becomes known); `#` comments; `re:<regex>` lines are full-matched against words and names (useful for document-number schemes). Owned by the corpus lane, generated from the bible. |
| `tech_allowlist.txt`, `common_words.txt` | Same format as the allowlist. Public technology names only, never fictional or real organisations. |
| `allowed_guids.txt` | `<guid>  # why it is public`; the comment is mandatory. Only documented public constants (Azure built-in role definition IDs, RFC 9562 namespaces). |
| `allowed_domains.txt` | `domain.tld` (and subdomains), `.suffix`, or `user@domain` per line. Use the reserved `.example` TLD for fictional domains. |
| `ignore.txt` | `LG-xxxxxxxxxx  # reason` per line; the reason is mandatory. Deny-list findings cannot be ignored. |
| `site_vendor.txt` | Vendor bundles of a built site: `file <glob>` lines (path inside the site folder, `**/` = any folders) and `allow <rule> re:<regex>  # reason` or `allow <rule> sha256:<hex>  # reason` lines. Only listed findings are dropped, and only inside files matching a glob; content pages, other findings and deny-list matches stay reported. Use `sha256:` (prefix of the hash of the exact matched text) for personal data such as a licence-header address, so the data itself is never committed. Review with `--site-vendor <empty file>`. |

## Redaction and CI

With `--redact` (default when `CI=true`) the output never contains matched text, extracted values,
document locations or deny-list patterns: deny-list findings print only
`rule=deny:<sha256(pattern)[:8]>` and `file:line`; other findings print rule, file, line, message
and id. Secrets (tokens, keys) are always masked, even without `--redact`.

`.github/workflows/leakguard.yml` runs `scan --history --strict --redact` on pushes to `main` and on
manual dispatch, never on pull requests, and only when the repository variable
`DOCWIKI_PRIVATE_REPO` equals `<owner>/<name>` of the running repository (so it never runs on the
public repository). Setup in the private repository:

1. Repository variable `DOCWIKI_PRIVATE_REPO` = `<owner>/<name>` of the private repository.
2. Repository secret `DOCWIKI_DENYLIST_CONTENT` = the deny-list content (the job fails if it is
   empty). The workflow writes it to `$RUNNER_TEMP`, exports `DOCWIKI_DENYLIST` and deletes it.

## Pre-push hook

`.githooks/pre-push` runs `scan --root . --strict` on the tracked files and blocks the push on any
finding. It fails closed: a missing `uv`, a missing scanner or a configuration error also blocks
the push. Install it once per clone:

```powershell
git config core.hooksPath .githooks
```

Export `DOCWIKI_DENYLIST` in your shell profile, otherwise the strict scan reports
`denylist-missing` and blocks the push. Set `LEAKGUARD_PRE_PUSH_HISTORY=1` to also scan the commits
being pushed (useful when a leak was committed and then removed from the working tree).

## Handling false positives

In order of preference:

1. **Fix the content** (use a fictional name from the bible, a reserved `.example` domain, a
   placeholder such as `<subscription-id>`, strip the metadata).
2. **Extend the right list**: a fictional name goes into `samples/fiction/bible.yaml` (then
   regenerate `allowlist.txt`); a public technology or standard name into `tech_allowlist.txt`; an
   ordinary word into `common_words.txt`; a documented public GUID into `allowed_guids.txt` with its
   justification; a fictional mail domain into `allowed_domains.txt`.
3. **Record a reviewed exception**: add the finding id to `ignore.txt` with the reason. The id is
   bound to the rule, the file and the matched text, so it covers that text in that file only.

Never weaken a rule to silence one finding, and never ignore a deny-list finding: fix the content
or, if the pattern itself is too broad, fix the private deny-list.

## Notes for sample generators

- `python-docx` and `python-pptx` templates embed `docProps/thumbnail.jpeg` with an EXIF block:
  remove the thumbnail part (and its relationship) or the scan reports `metadata-exif`.
- The `python-pptx` template sets `lastModifiedBy` to a real person: set `creator` to
  `DocWiki sample generator` and `lastModifiedBy` to the same value or empty.
- Keep PDF `Author` to `DocWiki sample generator` (or empty); tool names in `Creator`/`Producer`
  are fine.

## Tests

`uv run pytest tests/leakguard` builds every fixture (Office files, PDFs, images with and without
EXIF, SQLite, Parquet, e-mail, temporary git repositories, a fake deny-list) at test time.
Sensitive-looking test values are assembled at run time so that the test sources stay clean.
