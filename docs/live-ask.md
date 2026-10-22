# Live ask: visitors ask the Researcher in the wiki

The "Ask this wiki" drawer can let an anonymous visitor ask the Researcher agent a question. The
answer appears in the drawer with its numbered citations, and is shown as verified only when every
citation opens an evidence page of the wiki being served. The design is
[ADR 0008](adr/0008-one-experience-live-agent-in-the-wiki.md); this page is the setup.

```text
browser ──/api/ask──> portal ──(managed identity token + X-Visitor-IP)──> API Management ──> Foundry
   drawer               guards, gate before display        per-visitor and global limits      Researcher
```

Everything is off by default. Without the setting below the portal behaves as before, the drawer
lists the filed answers only, and a static host (no portal) never shows the Ask form.

## What you need

- The portal deployed (`DOCWIKI_ENABLE_PORTAL=true`) with a public-audience build
  (`DOCWIKI_AUDIENCE=public`, `DOCWIKI_PORTAL_ACCESS=public`).
- An **existing, shared** API Management instance on a v2 tier (or any tier that has the
  `llm-token-limit` policy). DocWiki never creates one and the repository never contains its name
  or URL.
- The Researcher deployed in the Foundry project (`uv run python agents/deploy.py`).

## 1. API Management

Placeholders in angle brackets are yours; keep the real values out of the repository.

```bash
APIM=<apim-name>; RG=<apim-resource-group>; SUB=<subscription-id>
ACCOUNT_URL=https://<foundry-account>.services.ai.azure.com   # the Foundry account, no path
TENANT_ID=<tenant-id>
PORTAL_CLIENT_ID=<portal-identity-client-id>   # azd env: DOCWIKI_PORTAL_IDENTITY_CLIENT_ID

# The gateway signs in to Foundry with its own identity.
az apim update --name $APIM --resource-group $RG --set identity.type=SystemAssigned
PRINCIPAL=$(az apim show --name $APIM --resource-group $RG --query identity.principalId -o tsv)

# An API whose paths mirror the Foundry project endpoint; callers authenticate with an Entra token,
# not an API Management subscription key.
az apim api create --service-name $APIM --resource-group $RG --api-id docwiki-live-ask \
  --path docwiki-live-ask --display-name "DocWiki live ask" --protocols https \
  --service-url $ACCOUNT_URL --subscription-required false
for METHOD in GET POST; do
  az apim api operation create --service-name $APIM --resource-group $RG --api-id docwiki-live-ask \
    --operation-id "any-$METHOD" --display-name "$METHOD *" --method $METHOD --url-template "/*"
done

# The policy: copy the template, fill the three placeholders, apply it. Do not commit the result.
sed -e "s|{{TENANT_ID}}|$TENANT_ID|" -e "s|{{PORTAL_CLIENT_ID}}|$PORTAL_CLIENT_ID|" \
    -e "s|{{FOUNDRY_ACCOUNT_URL}}|$ACCOUNT_URL|" infra/apim/docwiki-live-ask-policy.xml \
  | jq -Rs '{properties: {format: "rawxml", value: .}}' > /tmp/policy-body.json
az rest --method put \
  --uri "https://management.azure.com/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.ApiManagement/service/$APIM/apis/docwiki-live-ask/policies/policy?api-version=2022-08-01" \
  --body @/tmp/policy-body.json
```

`llm-emit-token-metric` needs an Application Insights logger on the instance (Azure portal: API
Management → Application Insights; the logger must be enabled for the API's diagnostics).

## 2. Foundry: the role of the gateway

The gateway's identity needs **Azure AI User** on the Foundry account (the project inherits it):

```bash
az role assignment create --assignee-object-id $PRINCIPAL --assignee-principal-type ServicePrincipal \
  --role "Azure AI User" \
  --scope /subscriptions/$SUB/resourceGroups/<foundry-resource-group>/providers/Microsoft.CognitiveServices/accounts/<foundry-account>
```

The portal's identity needs no role on Foundry: it only calls the gateway, which accepts that one
client ID (`validate-azure-ad-token`).

## 3. The portal

The endpoint is the gateway URL followed by the Foundry project path:

```bash
azd env set DOCWIKI_ENABLE_LIVE_ASK true
azd env set DOCWIKI_LIVE_ASK_ENDPOINT https://<apim-gateway-host>/docwiki-live-ask/api/projects/<project>
azd provision
```

The Bicep parameters `enableLiveAsk` and `liveAskEndpoint` give the portal app
`DOCWIKI_LIVE_ASK=1`, `DOCWIKI_FOUNDRY_PROJECT_ENDPOINT=<endpoint>` and its existing
`AZURE_CLIENT_ID`. Check it: `GET /api/ask/status` answers `{"enabled": true}`, and the drawer shows
the Ask form.

## Limits

| Layer | Limit | Default | Set by |
|---|---|---|---|
| Portal | request body | 4 KB | `DOCWIKI_LIVE_ASK_MAX_BODY_BYTES` |
| Portal | question length (after trimming) | 3 to 500 characters | `DOCWIKI_LIVE_ASK_MIN_QUESTION_CHARS`, `DOCWIKI_LIVE_ASK_MAX_QUESTION_CHARS` |
| Portal | running questions per visitor / in total | 1 / 3 | `DOCWIKI_LIVE_ASK_MAX_RUNNING` (total) |
| Portal | questions per visitor and window | 3 per 300 s | `DOCWIKI_LIVE_ASK_QUESTIONS_PER_IP`, `DOCWIKI_LIVE_ASK_IP_WINDOW_SECONDS` |
| Portal | time to answer | 200 s | `DOCWIKI_LIVE_ASK_TIMEOUT_SECONDS` |
| Portal | a finished job stays readable | 900 s | `DOCWIKI_LIVE_ASK_RESULT_TTL_SECONDS` |
| Gateway | questions per visitor | 3 per 300 s (`rate-limit-by-key`; 300 s is the longest window the v2 tiers accept) | policy |
| Gateway | tokens per visitor | 20,000 per minute, 60,000 per day | policy |
| Gateway | tokens for everyone | 1,500,000 per day: the daily cost cut-off | policy |

The portal's limits are in memory (a restart forgets them, and each replica counts alone); the
gateway's are the ones that hold. The portal also requires `Content-Type: application/json` and,
when the browser sends an `Origin`, that it is the request's own host. A visitor is the first entry
of `X-Forwarded-For` (else the client address), logged only as a salted hash. Questions are not
logged above DEBUG.

When a limit is reached the gateway answers 429 (the policy turns an exhausted token quota, which
API Management reports as 403, into 429 too), and the drawer says "The live agent has reached its
limit for now. The answers below were reviewed and filed." The filed answers keep working.

## What a visitor sees

- A **verified** answer: its text, numbered citations that open the evidence beside the drawer,
  the agent's steps and the banner "Live answer from the Researcher agent — not reviewed by the
  owner." The citation badges never say "quote verified": the live quote is not checked.
- An **unverified** answer (a citation is missing from the source list, is not an evidence path, or
  has no page in this site): the text with its citations removed and "This answer could not be
  checked against the sources, so it is not shown as verified."
- No "Open as a page" link: live answers are not filed. The owner can ask the same question with
  `docwiki file-answer`, review it and file it ([agents](agents.md#filing-an-answer-into-the-wiki)).

## Turn it off

Fastest, no deployment: remove the policy or the API's operations in API Management (the drawer then
shows the portal's generic error and keeps the filed answers), or set the token quotas to 0.

Properly: `azd env set DOCWIKI_ENABLE_LIVE_ASK false` and `azd provision`. The portal restarts
without the three settings, `GET /api/ask/status` answers `{"enabled": false}`, the Ask form and
(on a build without filed answers) the button disappear.

## Known limits

- The visitor key can be forged when the ingress does not overwrite `X-Forwarded-For`; the gateway's
  global daily quota is what bounds the spend either way.
- The citation gate proves that each cited evidence page exists in the site, not that the quoted
  text is in it. Filed answers go through quote verification before they are published.
- The Researcher's MCP connection and its model deployment are the ones of the owner's agent: size
  the global quota with the cost of one answer in mind (about 0.12 USD, [cost.md](cost.md)).
