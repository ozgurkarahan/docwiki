# DocWiki Studio

DocWiki Studio is the visible application around the pipeline and the two agents: one signed-in
page where you add documents, watch the ingest job compile them into a new release, and ask the
Researcher and the Librarian. It runs as its own Azure Container App next to the wiki portal and
reuses everything else unchanged: the upload is the same `raw/` drop that triggers the pipeline,
and the questions go to the same Foundry agents through the project's Responses API.

> **Status: demo / proof of concept**, like the rest of DocWiki. One replica, questions kept in
> memory, owner-only access.

![DocWiki Studio: the documents with their pipeline status, and a Researcher answer whose citations open the exact page, spreadsheet rows and e-mail lines](assets/screenshots/studio.png)

## What you can do

| Panel | What it shows | What it does |
|---|---|---|
| **Documents** | Every file in `raw/` with its pipeline status (`new`, `pending`, `done`, `failed`, `quarantined`, `deleted`), the failing stage and error, and a link to its wiki page | Upload files (drag and drop) into a folder of `raw/`; replacing a file starts a new revision |
| **Pipeline** | The served release (sources, pages, link to the wiki), the ingest queue, and the last ten run reports: stages, quality gates, counts and the cost receipt | Read only |
| **Ask** | The **Researcher**: cited answers whose `[n]` markers open the exact page, sheet rows, slide or transcript cue. The **Librarian**: run status, sources, quality, proposals | Every Librarian call that changes something (`ingest_start`, `recompile`, `decide_proposal`) waits for **Approve** or **Deny** in the page. A Researcher answer can be **filed to the wiki** after a preview (see below) |

Each answer ends with a receipt (agent version, tool calls, tokens, latency) and a collapsible
"How the agent worked" trace of its tool calls.

![The Librarian asks for approval before it starts an ingest run: the tool name, its arguments and Approve / Deny buttons](assets/screenshots/studio-approval.png)

## File an answer to the wiki

A good Researcher answer can become a page of the wiki, so that visitors find it in the wiki's
**Ask this wiki** panel and agents can read and search it ([ADR 0007](adr/0007-answers-in-the-wiki.md)).
Under each completed Researcher answer, **File to wiki** opens a preview in the page:

- **The page**: its path (`queries/<yyyy-mm-dd>-<question>.md`), the sensitivity (the highest
  tier among the cited sources), the number of cited sources, the release it is built from, and
  the full Markdown to read before it becomes public. Citations become footnotes to the evidence
  sidecars of the **current** release, with their provenance badge; a "How this answer was
  produced" section records the agent and its version, the dates, the release and the tool
  steps, and that the owner reviewed it (`approved_by: owner`, never a name).
- **The warnings** to review: numbers of a cited sentence that the cited evidence does not
  contain (often a computed or rounded value), sources listed but never cited, content removed by
  the safety rules.
- An honest "Not found in the wiki." answer files too, without sources.

**File it** writes the page to the answers inbox `work/inbox/queries/` (nothing is written
before). Event Grid turns the new blob into an `ingest` message, and the next run merges the
inbox into `queries/` with the same citation and safety checks as every query page, then
publishes: about three minutes and no model cost, because every model output is cached. The
Studio then says "Filed as queries/…; it appears after the next run".

| Case | What happens |
|---|---|
| A Librarian answer, a question still running or failed | Nothing to file: the button only appears under completed Researcher answers, and the API refuses the others |
| An answer without citations (other than "Not found in the wiki."), a citation that is not an evidence sidecar of the current release, a question over 300 characters | The preview says why it cannot be filed (HTTP 422); ask again |
| A new release or a new day between the preview and **File it** | Refused (HTTP 409) and the new page is shown for another review: you file exactly what you read |
| The same question filed again the same day | Same inbox key: an unchanged page is not written twice; a changed one replaces it. A question longer than the page-name limit (60 characters of slug) gets a short hash in its page name, so two long questions that start alike never share a page |
| Filed answers later | They are snapshots: every later release re-checks their citations ([agents](agents.md#filing-an-answer-into-the-wiki)); filing again refreshes them |

`docwiki file-answer` does the same from the command line with the deployer's data role.

## How it works

```mermaid
flowchart LR
  browser["Browser"] -->|"Entra sign-in<br/>(owner only)"| auth["Container Apps<br/>built-in auth"]
  auth --> studio["Container App: Studio<br/>own managed identity"]
  studio -->|"upload"| raw[("Blob raw/")]
  studio -->|"File to wiki"| inbox[("Blob work/<br/>inbox/queries/")]
  raw -->|"Event Grid, queue"| job["Ingest job"]
  inbox -->|"Event Grid, queue"| job
  job --> releases[("Blob releases/")]
  studio -->|"read: states, run reports,<br/>current release, queue"| work[("Blob work/, releases/,<br/>queue ingest")]
  studio -->|"Responses API,<br/>agent_reference"| agents["Foundry agents<br/>Researcher, Librarian"]
  agents -->|"MCP, own identities"| mcp["MCP server"]
  releases --> portal["Wiki portal"]
```

- **Uploads take the pipeline's normal path.** The Studio writes `raw/<folder>/<file>`; Event Grid
  turns the new blob into a queue message and KEDA starts the ingest job. Expect about a minute
  before the run starts (queue polling and the debounce window), then the per-document status
  moves from `new` to `pending` to `done`.
- **Filed answers take the same path.** The Studio writes `work/inbox/queries/<date>-<slug>.md`;
  the Event Grid subscription `inbox-to-ingest` turns it into an `ingest` message. The job is
  level-triggered: whatever woke it, it reads the whole inbox.
- **Questions run in the background.** `POST /api/ask` returns at once with a question ID; the page
  polls it every two seconds. Long answers never hit the 240-second request limit of Container
  Apps ingress.
- **Approvals pause the agent.** When the Librarian calls a mutating tool, Foundry returns an
  `mcp_approval_request`; the Studio parks it until you decide, then continues the response with
  your `mcp_approval_response`. Without a decision within ten minutes the call is denied.

## Access and safety

The Studio can write to `raw/` and to the answers inbox and spend model tokens, so it is built to
fail closed.

| Layer | Protection |
|---|---|
| Network | External ingress only once its sign-in is declared and verified (Bicep and the postprovision hook); disabled, the app is dormant at zero replicas |
| Sign-in | Container Apps built-in authentication with a single-tenant Entra app registration: ID tokens only, **no client secret**, assignment required, the deployer assigned. Unauthenticated requests are redirected to sign-in; only `/livez` and `/healthz` (static liveness answers) are excluded |
| Application | Every `/api` call needs the principal headers injected by the platform **and** an object ID listed in `DOCWIKI_STUDIO_ALLOWED_PRINCIPALS` (written by the hook: the deployer). An empty list lets nobody in |
| Requests | Writes (uploads, questions, approvals, filings) need the `X-DocWiki-Studio: 1` header and a same-origin request (`Origin`, `Sec-Fetch-Site`); there is no CORS. Uploads accept only the pipeline's file types, safe relative paths and 50 MB. Filing takes only completed Researcher answers and writes only the page the owner previewed |
| Browser | `Content-Security-Policy: script-src 'self'` (no inline script or style, no third party), `frame-ancestors 'none'`. Model output, including the page preview and its warnings, is rendered as text; links are built only from validated wiki paths |
| Identity | `id-docwiki-studio-*`: Storage Blob Data Contributor on `raw` **with a condition that denies deletes**; on `work`, the custom role "DocWiki Studio inbox writer" (blob read, write and create only: no delete or move, and no action on the container itself, which a condition could not restrict) **with a condition: reads everything, writes and creates blobs only under `inbox/queries/`** (the jobs identity consumes the inbox); Storage Blob Data Reader on `releases`, Storage Queue Data Reader on `ingest`, Azure AI User on the Foundry account. Creating the custom role needs `Microsoft.Authorization/roleDefinitions/write` on the resource group (Owner or User Access Administrator) |
| Trigger | The Event Grid subscription `inbox-to-ingest` delivers only `BlobCreated` events under `work/inbox/queries/` to the `ingest` queue, with the system topic's identity like `raw-to-ingest`; the job's own deletes in the inbox never wake it. The run checks every filed page again (citations, safety gates) before it publishes it |
| Cost | One question at a time, 100 questions, 10 uploads and 20 filings per day, a 20-minute deadline per question, and a confirmation before each upload and each filing: a new or changed document starts a pipeline run that spends model tokens (see [cost](cost.md)); a filed answer starts one too, without model cost (about three minutes) |

## Enable it on Azure

```bash
azd env set DOCWIKI_ENABLE_STUDIO true
azd provision          # identity, roles and the app (no ingress); the hook then registers the
                       # sign-in app, assigns you, writes the allow-list, applies auth, opens ingress
azd deploy studio      # builds the image in the registry and rolls it out
azd env get-value DOCWIKI_STUDIO_URL
```

Open the URL and sign in with the account that ran `azd provision`. The hook prints
`studio ready at <DOCWIKI_STUDIO_URL> (Entra sign-in, owner only)` when it is done.

| Setting (azd environment) | Default | Effect |
|---|---|---|
| `DOCWIKI_ENABLE_STUDIO` | `false` | Deploy the Studio |
| `DOCWIKI_STUDIO_ALLOWED_PRINCIPALS` | the deployer (set by the hook) | Comma-separated Entra object IDs allowed in |
| `DOCWIKI_STUDIO_MIN_REPLICAS` | `1` | `1` keeps questions and approval waits in memory and avoids cold starts (about 0.5 vCPU idle); `0` scales to zero |
| `DOCWIKI_GRAPH_TOKEN_SOURCE` | unset | `azd`: when the Azure CLI token is refused by Microsoft Graph (continuous access evaluation), the hook uses the azd sign-in for Graph, after checking it is the same account and tenant |

The question, upload and filing limits are container settings with defaults
(`DOCWIKI_STUDIO_DAILY_QUESTIONS`, `DOCWIKI_STUDIO_DAILY_UPLOADS`, `DOCWIKI_STUDIO_DAILY_FILINGS`
(20), `DOCWIKI_STUDIO_MAX_UPLOAD_MB`, `DOCWIKI_STUDIO_APPROVAL_TIMEOUT_SECONDS`,
`DOCWIKI_STUDIO_QUESTION_TIMEOUT_SECONDS`).

**Add someone.** Assign them to the enterprise application `docwiki-studio-<env>` in Microsoft
Entra ID, append their object ID to `DOCWIKI_STUDIO_ALLOWED_PRINCIPALS`, then run `azd provision`.

**Turn it off.** `azd env set DOCWIKI_ENABLE_STUDIO false` and `azd provision`: the app loses its
ingress and stays dormant at zero replicas. `azd down` deletes the app registration with the rest.

## Run it on your workstation

`docwiki studio --local` serves the same app on `http://127.0.0.1:8090` with your `az login`
instead of a managed identity; `--local` skips the sign-in checks and only binds the loopback
interface (the CSRF checks stay on). Point it at a deployed environment:

```powershell
$env:DOCWIKI_MODE = "azure"
$env:DOCWIKI_STORAGE_ACCOUNT = azd env get-value DOCWIKI_STORAGE_ACCOUNT
$env:DOCWIKI_FOUNDRY_PROJECT_ENDPOINT = azd env get-value DOCWIKI_FOUNDRY_PROJECT_ENDPOINT
$env:DOCWIKI_STUDIO_WIKI_URL = azd env get-value DOCWIKI_PORTAL_URL
uv run docwiki studio --local
```

Your account needs the deployer's data roles (granted by Bicep when `grantDeployerDataAccess` is
on) and, with a network perimeter, your IP in `DOCWIKI_ALLOWED_IP_RANGES`.

Without Azure, `uv run python tests/studio/studio_preview.py` serves the Studio on seeded data
with canned agent answers at `http://127.0.0.1:8091`; **File to wiki** works there too (its canned
answer shows one number warning) and writes into the temporary folder it prints.

## A five-minute demo

1. **Before the audience arrives**, open the portal and the Studio and ask one question: it wakes
   the MCP server and the portal (each can take about 30 seconds from zero).
2. **Documents**: every source compiled, each one opening its wiki page.
3. **Ask the Researcher** "Which delivery date applies to the windows, and why do the documents
   disagree?": the answer gives both dates, from the planning and from the window maker's e-mail,
   and the wiki's resolution rule; its citations open the spreadsheet rows and the e-mail lines.
   Expand "How the agent worked" to show the search, page reads and evidence checks.
4. **File to wiki**: open the preview to show the page, its warnings and its Markdown, then cancel.
   Filing publishes the answer at the next run; on the public sample, file only questions
   screened against the golden set ([ADR 0007](adr/0007-answers-in-the-wiki.md)).
5. **Ask the Librarian** "Start an ingest run for the uploads/ folder": it asks for approval. Deny
   it, or approve it: with nothing changed the run is a no-op that costs nothing.
6. **Pipeline**: the run timeline, the quality gates and the cost receipt of the last compilation.

### Time travel (optional)

The sample keeps one document out of the deployed corpus: a later revision of the planning, in
`samples/corpus/held-back/planning/`, whose new delivery date for the windows matches the e-mail.
To show a new revision taking effect, upload it from the Documents panel (confirm the upload) and
follow the run in the Pipeline panel. A run takes a while, so start it before the audience
arrives, or come back to it at the end. When the run is `done`, ask the question of step 3 again:
the first planning is now `superseded` and the contradiction is gone.

## Check a deployment (three minutes, as the owner)

Without signing in, check that the Studio's managed identity reaches the storage and the agents:

```bash
az containerapp exec --name $(azd env get-value DOCWIKI_STUDIO_APP_NAME) \
  --resource-group $(azd env get-value AZURE_RESOURCE_GROUP) \
  --command "python -m docwiki.studio --check"
# {"storage": true, "agents": true, "queue_readable": true, "ok": true}
```

Then, as the owner:

1. Open the Studio URL in a private window: you are sent to Microsoft Entra sign-in.
2. Sign in as the owner: the page loads, the documents and the served release appear.
3. Ask the Researcher a sample question: an answer with linked citations comes back.
4. Ask the Librarian for the last run's status: it answers without asking for approval.
5. Sign in with another account (or remove yourself from the allow-list): access is refused.

## Limits

- One replica keeps the questions in memory: a restart forgets questions in flight (the page says
  so and you ask again), and which answers it filed (the inbox and the wiki keep the pages).
- Answers are not streamed: they appear when the agent is done (the page shows the elapsed time).
- The Studio cannot delete documents: delete them in the storage account (the pipeline then
  withdraws them from the wiki). It cannot delete a filed answer either: until the next run, the
  deployer can delete it from `work/inbox/queries/`.
- With a network perimeter (`DOCWIKI_NETWORK_PERIMETER=true`) Event Grid cannot create the
  `inbox-to-ingest` subscription inside it: filed answers then wait for the reconcile schedule, a
  manual job start or an ingest message, like uploads.
- The agents and the pipeline share the `smart` model deployment: a question asked during a run is
  slower and may be throttled.
