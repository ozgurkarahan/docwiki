// DocWiki infrastructure (azd + Bicep), docs/spec/infra-ops-security.md §1.
// One resource group per azd environment: Microsoft Foundry (models, agents, Content
// Understanding), Blob/Queue storage with Event Grid, Container Apps (ingest + reconcile
// jobs, MCP app, optional portal), registry, one identity per workload, monitoring and a budget.
// Zero secrets: managed identities and Entra ID only; no access keys, SAS tokens or key listing.

targetScope = 'subscription'

// ---------------------------------------------------------------------------
// Environment
// ---------------------------------------------------------------------------

@minLength(1)
@maxLength(64)
@description('azd environment name (AZURE_ENV_NAME): resource group name and resource token.')
param environmentName string

@allowed([
  'swedencentral'
  'eastus2'
  'westeurope'
])
@metadata({
  azd: {
    type: 'location'
  }
})
@description('Region of every resource: one where Foundry models, agents and Content Understanding are available.')
param location string = 'swedencentral'

@description('Object ID of the deployer (azd sets AZURE_PRINCIPAL_ID); empty skips the deployer data-plane roles.')
param principalId string = ''

@allowed([
  'User'
  'ServicePrincipal'
  'Group'
])
@description('Principal type of the deployer (AZURE_PRINCIPAL_TYPE).')
param principalType string = 'User'

@description('Grant the deployer data-plane roles (upload to raw/, read releases, create agents).')
param grantDeployerDataAccess bool = true

// ---------------------------------------------------------------------------
// Models (verified by scripts/preflight.py against the region's model list and quota)
// ---------------------------------------------------------------------------

@description('Model of the `fast` deployment (classification fallback, figure descriptions, entity summaries).')
param fastModel string = 'gpt-5.4-mini'

param fastModelVersion string = '2026-03-17'

@minValue(1)
@description('Capacity of the `fast` deployment in units of 1,000 tokens per minute.')
param fastCapacity int = 100

@description('Model of the `smart` deployment (compilation, topic synthesis, agents).')
param smartModel string = 'gpt-5.5'

param smartModelVersion string = '2026-04-24'

@minValue(1)
@description('Capacity of the `smart` deployment in units of 1,000 tokens per minute.')
param smartCapacity int = 100

@allowed([
  'GlobalStandard'
  'DataZoneStandard'
])
@description('Deployment type of both model deployments: GlobalStandard (default: widest quota, lowest list price) or DataZoneStandard (processing kept in the EU or US data zone).')
param deploymentSku string = 'GlobalStandard'

// ---------------------------------------------------------------------------
// Runtime
// ---------------------------------------------------------------------------

@minValue(0)
@maxValue(3)
@description('Minimum replicas of the MCP app: 0 scales to zero after about 8.5 min idle (a cold start adds about 30 s to an agent turn); 1 for demos.')
param mcpMinReplicas int = 0

@allowed([
  'required'
  'off'
])
@description('Bearer-token validation by the MCP server behind built-in auth (DOCWIKI_MCP_TOKEN_VALIDATION). off trusts the platform principal header alone: only for a platform that does not forward the Authorization header (src/docwiki/mcp/README.md).')
param mcpTokenValidation string = 'required'

@description('Deploy the optional private portal (Entra sign-in).')
param enablePortal bool = false

@description('Wake the ingest job from the queue (KEDA); false makes it a manually started job.')
param enableEventTrigger bool = true

@description('Cron schedule (UTC) of the reconcile job.')
param reconcileCron string = '0 */6 * * *'

@allowed([
  'public'
  'internal'
  'restricted'
])
@description('Sensitivity audience of the builds (DOCWIKI_AUDIENCE).')
param audience string = 'internal'

@description('Domain pack used by the pipeline (DOCWIKI_DOMAIN).')
param domainPack string = 'wind-om'

@description('Extract with Azure Content Understanding (prebuilt-layout); false uses the local adapters.')
param contentUnderstanding bool = true

@description('Opt-in Foundry skills preview for the agents (consumed by agents/deploy.py).')
param enableFoundrySkillsPreview bool = false

@description('Deploy the optional daily Librarian routine (consumed by agents/deploy.py).')
param enableRoutine bool = false

@description('Connect Application Insights to the Foundry project for server-side agent tracing.')
param enableFoundryTracing bool = true

// ---------------------------------------------------------------------------
// Network
// ---------------------------------------------------------------------------

@description('Secure the storage account with a network security perimeter (DOCWIKI_NETWORK_PERIMETER) instead of open public access; needed where policy disables public network access on storage accounts.')
param networkPerimeter bool = false

@description('Comma-separated public CIDR ranges allowed through the perimeter, for operator uploads (DOCWIKI_ALLOWED_IP_RANGES, kept in the azd environment, never committed).')
param allowedIpRanges string = ''

// ---------------------------------------------------------------------------
// Cost
// ---------------------------------------------------------------------------

@minValue(0)
@description('Monthly budget amount (billing currency, USD by default); 0 disables the budget.')
param budgetAmount int = 50

@description('Comma-separated budget alert e-mail addresses (azd env BUDGET_CONTACT_EMAILS, never committed).')
param budgetContactEmails string = ''

@description('Budget start date: first day of the current month.')
param budgetStartDate string = '${utcNow('yyyy-MM')}-01'

// ---------------------------------------------------------------------------
// Values written by azd and the hooks (see scripts/hooks/)
// ---------------------------------------------------------------------------

@description('Client ID of the MCP API app registration (set by the postprovision hook).')
param mcpApiClientId string = ''

@description('Comma-separated client IDs of the agent identities allowed through the MCP app built-in auth and by the server itself (DOCWIKI_MCP_ALLOWED_CLIENT_IDS, written by the postprovision hook; empty rejects every agent at the built-in auth).')
param mcpAllowedClientIds string = ''

@minLength(3)
@maxLength(33)
@description('Name of the Foundry project connection used by the agents\' MCP tool (DOCWIKI_MCP_CONNECTION).')
param mcpConnectionName string = 'docwiki-mcp'

@description('Client ID of the portal sign-in app registration (set by the postprovision hook).')
param portalClientId string = ''

@description('Image of the job service (SERVICE_JOB_IMAGE_NAME, written by azd deploy).')
param jobImage string = ''

@description('Image of the mcp service (SERVICE_MCP_IMAGE_NAME, written by azd deploy).')
param mcpImage string = ''

@description('Image of the portal service (SERVICE_PORTAL_IMAGE_NAME, written by azd deploy).')
param portalImage string = ''

@description('Whether the job service resource exists (SERVICE_JOB_RESOURCE_EXISTS, set by azd).')
param jobExists bool = false

@description('Whether the mcp service resource exists (SERVICE_MCP_RESOURCE_EXISTS, set by azd).')
param mcpExists bool = false

@description('Whether the portal service resource exists (SERVICE_PORTAL_RESOURCE_EXISTS, set by azd).')
param portalExists bool = false

// ---------------------------------------------------------------------------
// Names
// ---------------------------------------------------------------------------

var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = {
  'azd-env-name': environmentName
  application: 'docwiki'
}
var names = {
  resourceGroup: 'rg-${environmentName}'
  identity: 'id-docwiki-${resourceToken}'
  mcpIdentity: 'id-docwiki-mcp-${resourceToken}'
  portalIdentity: 'id-docwiki-portal-${resourceToken}'
  logAnalytics: 'log-${resourceToken}'
  appInsights: 'appi-${resourceToken}'
  registry: 'cr${resourceToken}'
  storage: 'st${resourceToken}'
  systemTopic: 'evgt-${resourceToken}'
  perimeter: 'nsp-docwiki-${resourceToken}'
  foundry: 'aif-${resourceToken}'
  foundryProject: 'docwiki'
  environment: 'cae-${resourceToken}'
  ingestJob: 'caj-ingest-${resourceToken}'
  reconcileJob: 'caj-reconcile-${resourceToken}'
  mcpApp: 'ca-mcp-${resourceToken}'
  portalApp: 'ca-portal-${resourceToken}'
  actionGroup: 'ag-docwiki-${resourceToken}'
  budget: 'budget-docwiki-${resourceToken}'
}

// Placeholders until `azd deploy` publishes the real images: a run-to-completion sample for
// the jobs, and an HTTP sample listening on 8080 (the apps' target port).
var placeholderJobImage = 'mcr.microsoft.com/k8se/quickstart-jobs:latest'
var placeholderAppImage = 'mcr.microsoft.com/dotnet/samples:aspnetapp'

var budgetContacts = filter(map(split(budgetContactEmails, ','), email => trim(email)), email => !empty(email))
var allowedAddressPrefixes = filter(map(split(allowedIpRanges, ','), range => trim(range)), range => !empty(range))
var deployBudget = budgetAmount > 0 && !empty(budgetContacts)
var deployerPrincipalId = grantDeployerDataAccess ? principalId : ''
var portalPublic = enablePortal && !empty(portalClientId)
// Fail closed: the MCP app gets external ingress only once its built-in auth is declared here
// (mcpApiClientId set). On the first provision the postprovision hook applies and verifies the
// auth config, sets the token settings below and only then enables ingress.
var mcpPublic = !empty(mcpApiClientId)
var mcpAllowedApplications = filter(map(split(mcpAllowedClientIds, ','), id => trim(id)), id => !empty(id))

// Client-side rate limits matching the deployments: 1,000 tokens and 1 request per minute
// per capacity unit (the per-unit rate limits reported by `az cognitiveservices model list`).
var fastTokensPerMinute = fastCapacity * 1000
var smartTokensPerMinute = smartCapacity * 1000

// ---------------------------------------------------------------------------
// Resources
// ---------------------------------------------------------------------------

resource rg 'Microsoft.Resources/resourceGroups@2024-11-01' = {
  name: names.resourceGroup
  location: location
  tags: tags
}

// Three runtime identities, least privilege per workload (architecture.md §6): the jobs
// (pipeline: storage + Foundry), the MCP app (read the wiki, write proposals/reports/overlay,
// enqueue) and the portal (read the published site).
module identity 'br/public:avm/res/managed-identity/user-assigned-identity:0.6.0' = {
  name: 'identity'
  scope: rg
  params: {
    name: names.identity
    location: location
    tags: tags
    enableTelemetry: false
  }
}

module mcpIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.6.0' = {
  name: 'mcpIdentity'
  scope: rg
  params: {
    name: names.mcpIdentity
    location: location
    tags: tags
    enableTelemetry: false
  }
}

module portalIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.6.0' = {
  name: 'portalIdentity'
  scope: rg
  params: {
    name: names.portalIdentity
    location: location
    tags: tags
    enableTelemetry: false
  }
}

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  scope: rg
  params: {
    location: location
    tags: tags
    logAnalyticsName: names.logAnalytics
    appInsightsName: names.appInsights
    telemetryPrincipalIds: [
      identity.outputs.principalId
      mcpIdentity.outputs.principalId
      portalIdentity.outputs.principalId
    ]
  }
}

module registry 'br/public:avm/res/container-registry/registry:0.13.1' = {
  name: 'registry'
  scope: rg
  params: {
    name: names.registry
    location: location
    tags: tags
    acrSku: 'Basic'
    acrAdminUserEnabled: false
    anonymousPullEnabled: false
    // Keep the platform default so azd remote builds and image pulls can exchange tokens.
    azureADAuthenticationAsArmPolicyStatus: 'enabled'
    enableTelemetry: false
    roleAssignments: [
      {
        principalId: identity.outputs.principalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: 'AcrPull'
      }
      {
        principalId: mcpIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: 'AcrPull'
      }
      {
        principalId: portalIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: 'AcrPull'
      }
    ]
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  scope: rg
  params: {
    location: location
    tags: tags
    storageAccountName: names.storage
    systemTopicName: names.systemTopic
    runtimePrincipalId: identity.outputs.principalId
    mcpPrincipalId: mcpIdentity.outputs.principalId
    portalPrincipalId: portalIdentity.outputs.principalId
    deployerPrincipalId: deployerPrincipalId
    deployerPrincipalType: principalType
    networkPerimeter: networkPerimeter
    perimeterName: names.perimeter
    allowedAddressPrefixes: allowedAddressPrefixes
    logAnalyticsWorkspaceResourceId: monitoring.outputs.logAnalyticsWorkspaceResourceId
  }
}

module foundry 'modules/foundry.bicep' = {
  name: 'foundry'
  scope: rg
  params: {
    location: location
    tags: tags
    accountName: names.foundry
    projectName: names.foundryProject
    fastModel: fastModel
    fastModelVersion: fastModelVersion
    fastCapacity: fastCapacity
    smartModel: smartModel
    smartModelVersion: smartModelVersion
    smartCapacity: smartCapacity
    deploymentSku: deploymentSku
    runtimePrincipalId: identity.outputs.principalId
    deployerPrincipalId: deployerPrincipalId
    deployerPrincipalType: principalType
    enableTracing: enableFoundryTracing
    appInsightsResourceId: monitoring.outputs.appInsightsResourceId
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
  }
}

module containerAppsEnvironment 'modules/container-apps-environment.bicep' = {
  name: 'containerAppsEnvironment'
  scope: rg
  params: {
    location: location
    tags: tags
    name: names.environment
    logAnalyticsWorkspaceResourceId: monitoring.outputs.logAnalyticsWorkspaceResourceId
  }
}

module jobCurrentImage 'modules/current-image.bicep' = {
  name: 'jobCurrentImage'
  scope: rg
  params: {
    kind: 'job'
    name: names.ingestJob
    exists: jobExists
  }
}

module mcpCurrentImage 'modules/current-image.bicep' = {
  name: 'mcpCurrentImage'
  scope: rg
  params: {
    kind: 'app'
    name: names.mcpApp
    exists: mcpExists
  }
}

module portalCurrentImage 'modules/current-image.bicep' = {
  name: 'portalCurrentImage'
  scope: rg
  params: {
    kind: 'app'
    name: names.portalApp
    exists: portalExists
  }
}

var resolvedJobImage = !empty(jobImage) ? jobImage : jobCurrentImage.outputs.image
var resolvedMcpImage = !empty(mcpImage) ? mcpImage : mcpCurrentImage.outputs.image
var resolvedPortalImage = !empty(portalImage) ? portalImage : portalCurrentImage.outputs.image

var portalUrl = 'https://${names.portalApp}.${containerAppsEnvironment.outputs.defaultDomain}'
// The external FQDN the MCP app has (or gets from the hook) in this environment.
var mcpFqdn = '${names.mcpApp}.${containerAppsEnvironment.outputs.defaultDomain}'
var mcpUrl = 'https://${mcpFqdn}/mcp'

// Settings shared by every container; each container adds AZURE_CLIENT_ID of its own identity.
var sharedEnv = [
  {
    name: 'DOCWIKI_MODE'
    value: 'azure'
  }
  {
    name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
    value: monitoring.outputs.appInsightsConnectionString
  }
  {
    name: 'OTEL_RESOURCE_ATTRIBUTES'
    value: 'service.namespace=docwiki,deployment.environment=${environmentName}'
  }
  {
    name: 'DOCWIKI_STORAGE_ACCOUNT'
    value: storage.outputs.storageAccountName
  }
  {
    name: 'DOCWIKI_RAW_CONTAINER'
    value: storage.outputs.rawContainerName
  }
  {
    name: 'DOCWIKI_WORK_CONTAINER'
    value: storage.outputs.workContainerName
  }
  {
    name: 'DOCWIKI_RELEASES_CONTAINER'
    value: storage.outputs.releasesContainerName
  }
  {
    name: 'DOCWIKI_QUEUE_NAME'
    value: storage.outputs.ingestQueueName
  }
  {
    name: 'DOCWIKI_POISON_QUEUE_NAME'
    value: storage.outputs.poisonQueueName
  }
  {
    name: 'DOCWIKI_AUDIENCE'
    value: audience
  }
  {
    name: 'DOCWIKI_DOMAIN'
    value: domainPack
  }
]

var pipelineEnv = concat(
  sharedEnv,
  [
    {
      name: 'AZURE_CLIENT_ID'
      value: identity.outputs.clientId
    }
    {
      name: 'DOCWIKI_FOUNDRY_PROJECT_ENDPOINT'
      value: foundry.outputs.projectEndpoint
    }
    {
      name: 'DOCWIKI_FAST_DEPLOYMENT'
      value: foundry.outputs.fastDeploymentName
    }
    {
      name: 'DOCWIKI_SMART_DEPLOYMENT'
      value: foundry.outputs.smartDeploymentName
    }
    {
      name: 'DOCWIKI_FAST_MODEL'
      value: fastModel
    }
    {
      name: 'DOCWIKI_SMART_MODEL'
      value: smartModel
    }
    {
      name: 'DOCWIKI_FAST_TPM'
      value: string(fastTokensPerMinute)
    }
    {
      name: 'DOCWIKI_SMART_TPM'
      value: string(smartTokensPerMinute)
    }
    {
      name: 'DOCWIKI_FAST_RPM'
      value: string(fastCapacity)
    }
    {
      name: 'DOCWIKI_SMART_RPM'
      value: string(smartCapacity)
    }
    {
      name: 'DOCWIKI_CONTENT_UNDERSTANDING'
      value: contentUnderstanding ? 'true' : 'false'
    }
  ],
  enablePortal
    ? [
        {
          name: 'DOCWIKI_SITE_BASE_URL'
          value: portalUrl
        }
      ]
    : []
)

module ingestJob 'modules/container-apps-job.bicep' = {
  name: 'ingestJob'
  scope: rg
  params: {
    location: location
    tags: union(tags, {
      'azd-service-name': 'job'
    })
    name: names.ingestJob
    containerName: 'ingest'
    environmentId: containerAppsEnvironment.outputs.id
    workloadProfileName: containerAppsEnvironment.outputs.workloadProfileName
    identityResourceId: identity.outputs.resourceId
    registryServer: registry.outputs.loginServer
    image: !empty(resolvedJobImage) ? resolvedJobImage : placeholderJobImage
    args: !empty(resolvedJobImage) ? ['worker'] : []
    env: concat(pipelineEnv, [
      {
        name: 'OTEL_SERVICE_NAME'
        value: 'docwiki-ingest'
      }
    ])
    triggerType: enableEventTrigger ? 'Event' : 'Manual'
    queueAccountName: storage.outputs.storageAccountName
    queueName: storage.outputs.ingestQueueName
    pollingIntervalSeconds: 30
    replicaTimeoutSeconds: 3600
    replicaRetryLimit: 1
  }
}

// Same image as the ingest job; the postdeploy hook keeps it in sync after `azd deploy`.
module reconcileJob 'modules/container-apps-job.bicep' = {
  name: 'reconcileJob'
  scope: rg
  params: {
    location: location
    tags: tags
    name: names.reconcileJob
    containerName: 'reconcile'
    environmentId: containerAppsEnvironment.outputs.id
    workloadProfileName: containerAppsEnvironment.outputs.workloadProfileName
    identityResourceId: identity.outputs.resourceId
    registryServer: registry.outputs.loginServer
    image: !empty(resolvedJobImage) ? resolvedJobImage : placeholderJobImage
    args: !empty(resolvedJobImage) ? ['reconcile'] : []
    env: concat(pipelineEnv, [
      {
        name: 'OTEL_SERVICE_NAME'
        value: 'docwiki-reconcile'
      }
    ])
    triggerType: 'Schedule'
    cronExpression: reconcileCron
    replicaTimeoutSeconds: 3600
    replicaRetryLimit: 1
  }
}

module mcpApp 'modules/container-app.bicep' = {
  name: 'mcpApp'
  scope: rg
  params: {
    location: location
    tags: union(tags, {
      'azd-service-name': 'mcp'
    })
    name: names.mcpApp
    containerName: 'mcp'
    environmentId: containerAppsEnvironment.outputs.id
    workloadProfileName: containerAppsEnvironment.outputs.workloadProfileName
    identityResourceId: mcpIdentity.outputs.resourceId
    registryServer: registry.outputs.loginServer
    image: !empty(resolvedMcpImage) ? resolvedMcpImage : placeholderAppImage
    // The server validates the bearer token forwarded by built-in auth (tenant, audience and
    // caller allowlist below); without DOCWIKI_MCP_AUDIENCE it refuses to start (fail closed).
    env: concat(
      sharedEnv,
      [
        {
          name: 'AZURE_CLIENT_ID'
          value: mcpIdentity.outputs.clientId
        }
        {
          name: 'DOCWIKI_AUTH_MODE'
          value: 'easyauth'
        }
        {
          name: 'DOCWIKI_MCP_TENANT_ID'
          value: tenant().tenantId
        }
        {
          name: 'DOCWIKI_MCP_TOKEN_VALIDATION'
          value: mcpTokenValidation
        }
        {
          name: 'OTEL_SERVICE_NAME'
          value: 'docwiki-mcp'
        }
      ],
      mcpPublic
        ? [
            {
              name: 'DOCWIKI_MCP_AUDIENCE'
              value: 'api://${mcpApiClientId},${mcpApiClientId}'
            }
          ]
        : [],
      empty(mcpAllowedApplications)
        ? []
        : [
            {
              name: 'DOCWIKI_MCP_ALLOWED_CLIENT_IDS'
              value: join(mcpAllowedApplications, ',')
            }
          ]
    )
    cpu: '0.5'
    memory: '1Gi'
    minReplicas: mcpMinReplicas
    maxReplicas: 3
    ingressMode: mcpPublic ? 'external' : 'none'
    targetPort: 8080
    // TCP probes only: /healthz answers 503 until the first release is published, so an HTTP
    // probe would restart a healthy server on a fresh environment. The explicit startup probe
    // tolerates slow cold starts without logging a failure every second.
    tcpProbes: true
  }
}

// The portal app always exists so that `azd deploy` can publish its image; it gets ingress
// only when enabled AND its Entra sign-in is configured (fail closed). Disabled, it is dormant
// (zero replicas). Enabled but not yet public (first provision), it has no scale rule so the
// HTTP default applies once the postprovision hook turns its ingress on.
module portalApp 'modules/container-app.bicep' = {
  name: 'portalApp'
  scope: rg
  params: {
    location: location
    tags: union(tags, {
      'azd-service-name': 'portal'
    })
    name: names.portalApp
    containerName: 'portal'
    environmentId: containerAppsEnvironment.outputs.id
    workloadProfileName: containerAppsEnvironment.outputs.workloadProfileName
    identityResourceId: portalIdentity.outputs.resourceId
    registryServer: registry.outputs.loginServer
    image: !empty(resolvedPortalImage) ? resolvedPortalImage : placeholderAppImage
    env: concat(sharedEnv, [
      {
        name: 'AZURE_CLIENT_ID'
        value: portalIdentity.outputs.clientId
      }
      {
        name: 'OTEL_SERVICE_NAME'
        value: 'docwiki-portal'
      }
    ])
    cpu: '0.25'
    memory: '0.5Gi'
    minReplicas: 0
    maxReplicas: 1
    ingressMode: portalPublic ? 'external' : 'none'
    dormant: !enablePortal
    targetPort: 8080
  }
}

module mcpAuth 'modules/app-auth.bicep' = if (!empty(mcpApiClientId)) {
  name: 'mcpAuth'
  scope: rg
  params: {
    containerAppName: mcpApp.outputs.name
    clientId: mcpApiClientId
    // v2 access tokens carry the client ID as `aud`, which is accepted implicitly (ADR 0003).
    allowedAudiences: [
      'api://${mcpApiClientId}'
    ]
    unauthenticatedClientAction: 'Return401'
    excludedPaths: [
      '/healthz'
    ]
    // The agents' identity client IDs, recorded by the postprovision hook after agents/deploy.py.
    allowedApplications: mcpAllowedApplications
  }
}

// Created by the postprovision hook on the first run (the audience needs the app registration).
module mcpConnection 'modules/mcp-connection.bicep' = if (!empty(mcpApiClientId)) {
  name: 'mcpConnection'
  scope: rg
  params: {
    accountName: foundry.outputs.accountName
    projectName: foundry.outputs.projectName
    connectionName: mcpConnectionName
    mcpUrl: mcpUrl
    audience: 'api://${mcpApiClientId}'
  }
}

module portalAuth 'modules/app-auth.bicep' = if (portalPublic) {
  name: 'portalAuth'
  scope: rg
  params: {
    containerAppName: portalApp.outputs.name
    clientId: portalClientId
    allowedAudiences: [
      portalClientId
    ]
    unauthenticatedClientAction: 'RedirectToLoginPage'
  }
}

module budget 'modules/budget.bicep' = if (deployBudget) {
  name: 'budget'
  scope: rg
  params: {
    tags: tags
    budgetName: names.budget
    actionGroupName: names.actionGroup
    amount: max(1, budgetAmount)
    contactEmails: budgetContacts
    startDate: budgetStartDate
  }
}

// ---------------------------------------------------------------------------
// Outputs (azd writes them to .azure/<env>/.env; the hooks and BOOTSTRAP.md read them)
// ---------------------------------------------------------------------------

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = registry.outputs.loginServer
output AZURE_CONTAINER_REGISTRY_NAME string = registry.outputs.name
output AZURE_CONTAINER_APPS_ENVIRONMENT_NAME string = containerAppsEnvironment.outputs.name
output AZURE_CONTAINER_APPS_ENVIRONMENT_ID string = containerAppsEnvironment.outputs.id

output DOCWIKI_RESOURCE_TOKEN string = resourceToken
output DOCWIKI_RUNTIME_IDENTITY_NAME string = identity.outputs.name
output DOCWIKI_RUNTIME_IDENTITY_CLIENT_ID string = identity.outputs.clientId
output DOCWIKI_RUNTIME_IDENTITY_PRINCIPAL_ID string = identity.outputs.principalId
output DOCWIKI_MCP_IDENTITY_NAME string = mcpIdentity.outputs.name
output DOCWIKI_MCP_IDENTITY_CLIENT_ID string = mcpIdentity.outputs.clientId
output DOCWIKI_MCP_IDENTITY_PRINCIPAL_ID string = mcpIdentity.outputs.principalId
output DOCWIKI_PORTAL_IDENTITY_NAME string = portalIdentity.outputs.name
output DOCWIKI_PORTAL_IDENTITY_CLIENT_ID string = portalIdentity.outputs.clientId
output DOCWIKI_PORTAL_IDENTITY_PRINCIPAL_ID string = portalIdentity.outputs.principalId

output DOCWIKI_FOUNDRY_ACCOUNT_NAME string = foundry.outputs.accountName
output DOCWIKI_FOUNDRY_ACCOUNT_ENDPOINT string = foundry.outputs.accountEndpoint
output DOCWIKI_FOUNDRY_PROJECT_NAME string = foundry.outputs.projectName
output DOCWIKI_FOUNDRY_PROJECT_ENDPOINT string = foundry.outputs.projectEndpoint
output DOCWIKI_FOUNDRY_PROJECT_PRINCIPAL_ID string = foundry.outputs.projectPrincipalId
output DOCWIKI_FAST_DEPLOYMENT string = foundry.outputs.fastDeploymentName
output DOCWIKI_SMART_DEPLOYMENT string = foundry.outputs.smartDeploymentName
// The deployed model settings are echoed so that the azd environment pins them: a newer
// template default never switches the models of an existing environment silently.
output DOCWIKI_FAST_MODEL string = fastModel
output DOCWIKI_FAST_MODEL_VERSION string = fastModelVersion
output DOCWIKI_FAST_CAPACITY int = fastCapacity
output DOCWIKI_SMART_MODEL string = smartModel
output DOCWIKI_SMART_MODEL_VERSION string = smartModelVersion
output DOCWIKI_SMART_CAPACITY int = smartCapacity
output DOCWIKI_DEPLOYMENT_SKU string = deploymentSku
output DOCWIKI_ENABLE_ROUTINE bool = enableRoutine
output DOCWIKI_ENABLE_FOUNDRY_SKILLS_PREVIEW bool = enableFoundrySkillsPreview

output DOCWIKI_STORAGE_ACCOUNT string = storage.outputs.storageAccountName
output DOCWIKI_RAW_CONTAINER string = storage.outputs.rawContainerName
output DOCWIKI_WORK_CONTAINER string = storage.outputs.workContainerName
output DOCWIKI_RELEASES_CONTAINER string = storage.outputs.releasesContainerName
output DOCWIKI_QUEUE_NAME string = storage.outputs.ingestQueueName
output DOCWIKI_POISON_QUEUE_NAME string = storage.outputs.poisonQueueName
output DOCWIKI_EVENT_GRID_SYSTEM_TOPIC string = storage.outputs.systemTopicName
output DOCWIKI_NETWORK_PERIMETER bool = networkPerimeter
output DOCWIKI_DOMAIN string = domainPack
output DOCWIKI_AUDIENCE string = audience

output DOCWIKI_INGEST_JOB_NAME string = ingestJob.outputs.name
output DOCWIKI_RECONCILE_JOB_NAME string = reconcileJob.outputs.name
output DOCWIKI_MCP_APP_NAME string = mcpApp.outputs.name
output DOCWIKI_MCP_FQDN string = mcpFqdn
output DOCWIKI_MCP_URL string = mcpUrl
output DOCWIKI_MCP_CONNECTION string = mcpConnectionName
output DOCWIKI_PORTAL_APP_NAME string = portalApp.outputs.name
output DOCWIKI_ENABLE_PORTAL bool = enablePortal
output DOCWIKI_PORTAL_URL string = enablePortal ? portalUrl : ''
output DOCWIKI_CONTAINER_APPS_DEFAULT_DOMAIN string = containerAppsEnvironment.outputs.defaultDomain

output DOCWIKI_LOG_ANALYTICS_WORKSPACE_ID string = monitoring.outputs.logAnalyticsWorkspaceCustomerId
output DOCWIKI_LOG_ANALYTICS_WORKSPACE_NAME string = monitoring.outputs.logAnalyticsWorkspaceName
output DOCWIKI_APPINSIGHTS_NAME string = monitoring.outputs.appInsightsName
output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitoring.outputs.appInsightsConnectionString
output DOCWIKI_BUDGET_ENABLED bool = deployBudget
