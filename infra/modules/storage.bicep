// Storage account (Entra-only), containers raw/work/releases, queues ingest/ingest-poison,
// Event Grid system topic delivering raw/ BlobCreated/BlobDeleted events to the ingest queue
// with its managed identity, and the data-plane role assignments of architecture.md §6 for
// three runtime identities: the jobs, the MCP app and the portal (least privilege per app).

import { roleIds } from 'roles.bicep'

param location string
param tags object
param storageAccountName string
param systemTopicName string

@description('Principal ID of the jobs identity (ingest and reconcile).')
param runtimePrincipalId string

@description('Principal ID of the MCP app identity.')
param mcpPrincipalId string

@description('Principal ID of the portal app identity.')
param portalPrincipalId string

@description('Object ID of the deployer; empty skips the deployer data-plane roles.')
param deployerPrincipalId string = ''

@allowed([
  'User'
  'ServicePrincipal'
  'Group'
])
param deployerPrincipalType string = 'User'

@description('Days kept for soft-deleted blobs and containers.')
param softDeleteRetentionDays int = 7

@description('Days after which previous blob versions are deleted by the lifecycle policy.')
param versionRetentionDays int = 30

@description('Secure the account with a network security perimeter instead of open public access (network-perimeter.bicep).')
param networkPerimeter bool = false

@description('Name of the network security perimeter (used when networkPerimeter is true).')
param perimeterName string = ''

@description('Public address prefixes (CIDR) of operators allowed through the perimeter.')
param allowedAddressPrefixes array = []

@description('Log Analytics workspace for the perimeter\'s denied-access logs.')
param logAnalyticsWorkspaceResourceId string = ''

var rawContainerName = 'raw'
var workContainerName = 'work'
var releasesContainerName = 'releases'
var ingestQueueName = 'ingest'
var poisonQueueName = 'ingest-poison'
var grantDeployer = !empty(deployerPrincipalId)

// Attribute-based condition on the MCP app's work/ role: it reads everything but writes only
// health reports, proposals and the domain overlay (decide_proposal, write_health_report).
var mcpWorkWriteCondition = '''
(
 (
  !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write'})
  AND
  !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action'})
  AND
  !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete'})
  AND
  !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/move/action'})
 )
 OR
 (
  @Resource[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path] StringStartsWith 'reports/'
  OR
  @Resource[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path] StringStartsWith 'proposals/'
  OR
  @Resource[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path] StringEquals 'state/overlay.yaml'
 )
)
'''

resource storage 'Microsoft.Storage/storageAccounts@2025-01-01' = {
  name: storageAccountName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    allowSharedKeyAccess: false
    allowBlobPublicAccess: false
    allowCrossTenantReplication: false
    defaultToOAuthAuthentication: true
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    // Entra-only data access over the public endpoint, or through the perimeter's rules.
    publicNetworkAccess: networkPerimeter ? 'SecuredByPerimeter' : 'Enabled'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2025-01-01' = {
  parent: storage
  name: 'default'
  properties: {
    isVersioningEnabled: true
    deleteRetentionPolicy: {
      enabled: true
      days: softDeleteRetentionDays
    }
    containerDeleteRetentionPolicy: {
      enabled: true
      days: softDeleteRetentionDays
    }
  }
}

resource rawContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-01-01' = {
  parent: blobService
  name: rawContainerName
  properties: {
    publicAccess: 'None'
  }
}

resource workContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-01-01' = {
  parent: blobService
  name: workContainerName
  properties: {
    publicAccess: 'None'
  }
}

resource releasesContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-01-01' = {
  parent: blobService
  name: releasesContainerName
  properties: {
    publicAccess: 'None'
  }
}

resource queueService 'Microsoft.Storage/storageAccounts/queueServices@2025-01-01' = {
  parent: storage
  name: 'default'
}

resource ingestQueue 'Microsoft.Storage/storageAccounts/queueServices/queues@2025-01-01' = {
  parent: queueService
  name: ingestQueueName
}

resource poisonQueue 'Microsoft.Storage/storageAccounts/queueServices/queues@2025-01-01' = {
  parent: queueService
  name: poisonQueueName
}

// Versioning keeps every overwrite of state shards and pointers; prune old versions.
resource lifecycle 'Microsoft.Storage/storageAccounts/managementPolicies@2025-01-01' = {
  parent: storage
  name: 'default'
  properties: {
    policy: {
      rules: [
        {
          name: 'prune-previous-versions'
          enabled: true
          type: 'Lifecycle'
          definition: {
            filters: {
              blobTypes: [
                'blockBlob'
              ]
            }
            actions: {
              version: {
                delete: {
                  daysAfterCreationGreaterThan: versionRetentionDays
                }
              }
            }
          }
        }
      ]
    }
  }
  dependsOn: [
    blobService
  ]
}

// ---------------------------------------------------------------------------
// Jobs identity (ingest and reconcile), architecture.md §6
// ---------------------------------------------------------------------------

resource runtimeRawReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: rawContainer
  name: guid(rawContainer.id, runtimePrincipalId, roleIds.storageBlobDataReader)
  properties: {
    principalId: runtimePrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.storageBlobDataReader)
  }
}

resource runtimeWorkContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: workContainer
  name: guid(workContainer.id, runtimePrincipalId, roleIds.storageBlobDataContributor)
  properties: {
    principalId: runtimePrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roleIds.storageBlobDataContributor
    )
  }
}

resource runtimeReleasesContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: releasesContainer
  name: guid(releasesContainer.id, runtimePrincipalId, roleIds.storageBlobDataContributor)
  properties: {
    principalId: runtimePrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roleIds.storageBlobDataContributor
    )
  }
}

// The job receives, renews (Update Message needs queues/messages/write) and deletes wake-up
// messages, and the KEDA azure-queue scaler reads the queue length (Get Queue Metadata needs
// queues/read). Storage Queue Data Contributor is the only built-in role with messages/write;
// it is scoped to the ingest queue only (messages/write also authorizes Put Message).
resource runtimeIngestContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: ingestQueue
  name: guid(ingestQueue.id, runtimePrincipalId, roleIds.storageQueueDataContributor)
  properties: {
    principalId: runtimePrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roleIds.storageQueueDataContributor
    )
  }
}

// The job moves messages dequeued more than five times to ingest-poison (Put Message only).
resource runtimePoisonSender 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: poisonQueue
  name: guid(poisonQueue.id, runtimePrincipalId, roleIds.storageQueueDataMessageSender)
  properties: {
    principalId: runtimePrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roleIds.storageQueueDataMessageSender
    )
  }
}

// ---------------------------------------------------------------------------
// MCP app identity: reads releases and work state, writes only reports, proposals and the
// overlay, enqueues ingest/recompile messages. No raw/ access, no Foundry access.
// ---------------------------------------------------------------------------

resource mcpReleasesReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: releasesContainer
  name: guid(releasesContainer.id, mcpPrincipalId, roleIds.storageBlobDataReader)
  properties: {
    principalId: mcpPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.storageBlobDataReader)
  }
}

resource mcpWorkScopedContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: workContainer
  name: guid(workContainer.id, mcpPrincipalId, roleIds.storageBlobDataContributor)
  properties: {
    principalId: mcpPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roleIds.storageBlobDataContributor
    )
    condition: mcpWorkWriteCondition
    conditionVersion: '2.0'
    description: 'DocWiki MCP app: read work/, write reports/, proposals/ and state/overlay.yaml only'
  }
}

// The operations tools (ingest_start, recompile) enqueue messages.
resource mcpIngestSender 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: ingestQueue
  name: guid(ingestQueue.id, mcpPrincipalId, roleIds.storageQueueDataMessageSender)
  properties: {
    principalId: mcpPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roleIds.storageQueueDataMessageSender
    )
  }
}

// ---------------------------------------------------------------------------
// Portal identity: reads the published sites under releases/ only.
// ---------------------------------------------------------------------------

resource portalReleasesReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: releasesContainer
  name: guid(releasesContainer.id, portalPrincipalId, roleIds.storageBlobDataReader)
  properties: {
    principalId: portalPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.storageBlobDataReader)
  }
}

// ---------------------------------------------------------------------------
// Deployer (operator): upload to raw/, inspect work/ and releases/, roll back the pointer,
// peek and re-drive queues. Owner on the resource group does not grant data-plane access.
// ---------------------------------------------------------------------------

resource deployerRawContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (grantDeployer) {
  scope: rawContainer
  name: guid(rawContainer.id, deployerPrincipalId, roleIds.storageBlobDataContributor)
  properties: {
    principalId: deployerPrincipalId
    principalType: deployerPrincipalType
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roleIds.storageBlobDataContributor
    )
  }
}

resource deployerWorkContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (grantDeployer) {
  scope: workContainer
  name: guid(workContainer.id, deployerPrincipalId, roleIds.storageBlobDataContributor)
  properties: {
    principalId: deployerPrincipalId
    principalType: deployerPrincipalType
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roleIds.storageBlobDataContributor
    )
  }
}

resource deployerReleasesContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (grantDeployer) {
  scope: releasesContainer
  name: guid(releasesContainer.id, deployerPrincipalId, roleIds.storageBlobDataContributor)
  properties: {
    principalId: deployerPrincipalId
    principalType: deployerPrincipalType
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roleIds.storageBlobDataContributor
    )
  }
}

resource deployerIngestContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (grantDeployer) {
  scope: ingestQueue
  name: guid(ingestQueue.id, deployerPrincipalId, roleIds.storageQueueDataContributor)
  properties: {
    principalId: deployerPrincipalId
    principalType: deployerPrincipalType
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roleIds.storageQueueDataContributor
    )
  }
}

resource deployerPoisonContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (grantDeployer) {
  scope: poisonQueue
  name: guid(poisonQueue.id, deployerPrincipalId, roleIds.storageQueueDataContributor)
  properties: {
    principalId: deployerPrincipalId
    principalType: deployerPrincipalType
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roleIds.storageQueueDataContributor
    )
  }
}

// ---------------------------------------------------------------------------
// Event Grid: raw/ BlobCreated + BlobDeleted -> queue "ingest" (managed identity delivery)
// ---------------------------------------------------------------------------

resource systemTopic 'Microsoft.EventGrid/systemTopics@2025-02-15' = {
  name: systemTopicName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    source: storage.id
    topicType: 'Microsoft.Storage.StorageAccounts'
  }
}

// Event Grid validates managed-identity delivery to a Storage queue against the storage
// account (the destination resource): a role assigned on the queue alone makes the event
// subscription fail with "does not have authorization to deliver to the endpoint", however
// long the assignment had to propagate. The system topic's identity is only used by Event Grid.
resource eventGridQueueSender 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, systemTopic.id, roleIds.storageQueueDataMessageSender)
  properties: {
    principalId: systemTopic.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roleIds.storageQueueDataMessageSender
    )
  }
}

// Network security perimeter (opt-in). Event Grid checks the queue destination of an event
// subscription without an identity (GetQueueMetadata), which the perimeter denies
// (NSPAccessLogs: DefaultDenyAll), so the subscription cannot be created or updated inside the
// perimeter and is only declared without one. A subscription created before the perimeter
// keeps delivering, because deliveries are authenticated with the topic's managed identity:
// provision once with DOCWIKI_NETWORK_PERIMETER=false, then turn the perimeter on. Without it,
// uploads are picked up by the reconcile schedule, a manual job start or an ingest message.
module perimeter 'network-perimeter.bicep' = if (networkPerimeter) {
  name: 'networkPerimeter'
  params: {
    location: location
    tags: tags
    perimeterName: perimeterName
    storageAccountId: storage.id
    allowedAddressPrefixes: allowedAddressPrefixes
    logAnalyticsWorkspaceResourceId: logAnalyticsWorkspaceResourceId
  }
}

resource rawToIngest 'Microsoft.EventGrid/systemTopics/eventSubscriptions@2025-02-15' = if (!networkPerimeter) {
  parent: systemTopic
  name: 'raw-to-ingest'
  properties: {
    eventDeliverySchema: 'EventGridSchema'
    filter: {
      includedEventTypes: [
        'Microsoft.Storage.BlobCreated'
        'Microsoft.Storage.BlobDeleted'
      ]
      subjectBeginsWith: '/blobServices/default/containers/${rawContainerName}/blobs/'
    }
    deliveryWithResourceIdentity: {
      identity: {
        type: 'SystemAssigned'
      }
      destination: {
        endpointType: 'StorageQueue'
        properties: {
          resourceId: storage.id
          queueName: ingestQueue.name
        }
      }
    }
    retryPolicy: {
      maxDeliveryAttempts: 30
      eventTimeToLiveInMinutes: 1440
    }
  }
  dependsOn: [
    eventGridQueueSender
  ]
}

output storageAccountName string = storage.name
output storageAccountId string = storage.id
output blobEndpoint string = storage.properties.primaryEndpoints.blob
output queueEndpoint string = storage.properties.primaryEndpoints.queue
output rawContainerName string = rawContainer.name
output workContainerName string = workContainer.name
output releasesContainerName string = releasesContainer.name
output ingestQueueName string = ingestQueue.name
output poisonQueueName string = poisonQueue.name
output systemTopicName string = systemTopic.name
