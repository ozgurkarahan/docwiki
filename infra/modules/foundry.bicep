// Microsoft Foundry: AIServices account (Entra-only, custom subdomain, project management), the
// `docwiki` project (pipeline calls and both agents, each agent with its own Entra agent
// identity, ADR 0003), the `fast`, `smart` and optional `embed` model deployments, the
// Application Insights tracing connection and the Foundry role assignments of architecture.md §6.

import { roleIds } from 'roles.bicep'

param location string
param tags object
param accountName string

@description('Name of the project hosting the pipeline calls and both agents.')
param projectName string

param fastModel string
param fastModelVersion string
param fastCapacity int
param smartModel string
param smartModelVersion string
param smartCapacity int

@description('Model of the `embed` deployment (hybrid retrieval, ADR 0014).')
param embedModel string = 'text-embedding-3-small'
param embedModelVersion string = '1'

@minValue(0)
@description('Capacity of the `embed` deployment in units of 1,000 tokens per minute: the hard daily cost bound of ADR 0014; 0 = no embedding deployment.')
param embedCapacity int = 0

@allowed([
  'DataZoneStandard'
  'GlobalStandard'
])
param deploymentSku string

@description('Principal ID of the runtime user-assigned identity.')
param runtimePrincipalId string

@description('Object ID of the deployer; empty skips the deployer roles.')
param deployerPrincipalId string = ''

@allowed([
  'User'
  'ServicePrincipal'
  'Group'
])
param deployerPrincipalType string = 'User'

param enableTracing bool = true
param appInsightsResourceId string

@description('Application Insights connection string used by the Foundry tracing connection.')
@secure()
param appInsightsConnectionString string

var fastDeploymentName = 'fast'
var smartDeploymentName = 'smart'
var embedDeploymentName = 'embed'
var deployEmbed = embedCapacity > 0
var grantDeployer = !empty(deployerPrincipalId)

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: accountName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: accountName
    disableLocalAuth: true
    allowProjectManagement: true
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}

// The account's default project (the account cannot be deleted while it exists, see
// docs/spikes/identity-spike.md F13 and scripts/teardown.py).
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: account
  name: projectName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: 'DocWiki'
    description: 'DocWiki pipeline and agents'
  }
}

// Operations on one account are serialised to avoid "another operation is in progress".
resource fastDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: fastDeploymentName
  sku: {
    name: deploymentSku
    capacity: fastCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: fastModel
      version: fastModelVersion
    }
    // Pinned version; upgraded only when it retires (run reports record the served version).
    versionUpgradeOption: 'OnceCurrentVersionExpired'
  }
  dependsOn: [
    project
  ]
}

resource smartDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: smartDeploymentName
  sku: {
    name: deploymentSku
    capacity: smartCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: smartModel
      version: smartModelVersion
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
  }
  dependsOn: [
    fastDeployment
  ]
}

// Embeddings for hybrid retrieval (ADR 0014). The low explicit capacity is the hard Azure bound
// on embedding spend; it is not created when the capacity is 0.
resource embedDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = if (deployEmbed) {
  parent: account
  name: embedDeploymentName
  sku: {
    name: deploymentSku
    capacity: embedCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: embedModel
      version: embedModelVersion
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
  }
  dependsOn: [
    smartDeployment
  ]
}

// Server-side tracing of the agents: Application Insights connection of the project.
resource tracingConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01' = if (enableTracing) {
  parent: project
  name: 'appinsights'
  properties: {
    category: 'AppInsights'
    target: appInsightsResourceId
    authType: 'ApiKey'
    isSharedToAll: true
    credentials: {
      key: appInsightsConnectionString
    }
    metadata: {
      ApiType: 'Azure'
      ResourceId: appInsightsResourceId
    }
  }
  dependsOn: [
    smartDeployment
  ]
}

resource runtimeCognitiveServicesUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: account
  name: guid(account.id, runtimePrincipalId, roleIds.cognitiveServicesUser)
  properties: {
    principalId: runtimePrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.cognitiveServicesUser)
  }
}

resource runtimeAzureAiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: account
  name: guid(account.id, runtimePrincipalId, roleIds.azureAiUser)
  properties: {
    principalId: runtimePrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.azureAiUser)
  }
}

// The deployer creates agents (agents/deploy.py) and sets Content Understanding defaults;
// both are data-plane operations that Owner on the resource group does not grant.
resource deployerCognitiveServicesUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (grantDeployer) {
  scope: account
  name: guid(account.id, deployerPrincipalId, roleIds.cognitiveServicesUser)
  properties: {
    principalId: deployerPrincipalId
    principalType: deployerPrincipalType
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.cognitiveServicesUser)
  }
}

resource deployerAzureAiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (grantDeployer) {
  scope: account
  name: guid(account.id, deployerPrincipalId, roleIds.azureAiUser)
  properties: {
    principalId: deployerPrincipalId
    principalType: deployerPrincipalType
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.azureAiUser)
  }
}

// Endpoints reported by the service, with the documented URL shape as a fallback.
var accountFoundryEndpoint = account.properties.?endpoints[?'AI Foundry API'] ?? 'https://${accountName}.services.ai.azure.com/'
var accountFoundryBase = endsWith(accountFoundryEndpoint, '/') ? accountFoundryEndpoint : '${accountFoundryEndpoint}/'
var foundryProjectEndpoint = project.properties.?endpoints[?'AI Foundry API'] ?? '${accountFoundryBase}api/projects/${projectName}'

output accountName string = account.name
output accountId string = account.id
@description('Foundry account endpoint (also the Content Understanding endpoint).')
output accountEndpoint string = accountFoundryEndpoint
output projectName string = project.name
output projectEndpoint string = foundryProjectEndpoint
output projectPrincipalId string = project.identity.principalId
output fastDeploymentName string = fastDeployment.name
output smartDeploymentName string = smartDeployment.name
output embedDeploymentName string = deployEmbed ? embedDeploymentName : ''
