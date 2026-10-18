// Log Analytics workspace (30-day retention) and workspace-based Application Insights.
// The workspace is a plain resource: the AVM workspace module lists the workspace shared keys
// in its outputs, and DocWiki never reads keys.

import { roleIds } from 'roles.bicep'

param location string
param tags object
param logAnalyticsName string
param appInsightsName string

@description('Principal IDs of the runtime identities (Monitoring Metrics Publisher for Entra-authenticated telemetry).')
param telemetryPrincipalIds array

@description('Log retention in days.')
param retentionInDays int = 30

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2025-02-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: retentionInDays
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

module appInsights 'br/public:avm/res/insights/component:0.8.0' = {
  name: 'appInsights'
  params: {
    name: appInsightsName
    location: location
    tags: tags
    workspaceResourceId: logAnalytics.id
    applicationType: 'web'
    kind: 'web'
    retentionInDays: retentionInDays
    disableIpMasking: false
    enableTelemetry: false
    roleAssignments: [
      for principalId in telemetryPrincipalIds: {
        principalId: principalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: subscriptionResourceId(
          'Microsoft.Authorization/roleDefinitions',
          roleIds.monitoringMetricsPublisher
        )
      }
    ]
  }
}

output logAnalyticsWorkspaceResourceId string = logAnalytics.id
output logAnalyticsWorkspaceName string = logAnalytics.name
@description('Workspace (customer) ID used by `az monitor log-analytics query --workspace`.')
output logAnalyticsWorkspaceCustomerId string = logAnalytics.properties.customerId
output appInsightsResourceId string = appInsights.outputs.resourceId
output appInsightsName string = appInsights.outputs.name
@description('Application Insights connection string (an ingestion endpoint, not a credential).')
output appInsightsConnectionString string = appInsights.outputs.connectionString
