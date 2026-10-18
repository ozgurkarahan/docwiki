// Optional network security perimeter (NSP) around the storage account
// (DOCWIKI_NETWORK_PERIMETER=true). Some tenants enforce a policy that turns public network
// access off on every storage account unless it is secured by a perimeter
// (publicNetworkAccess = SecuredByPerimeter); without a perimeter the jobs, the MCP app and
// the KEDA queue scaler then lose access to the account.
//
// The perimeter denies all public inbound traffic except:
// - callers authenticated with a managed identity of this subscription (the jobs, the MCP
//   app, the portal and the KEDA queue scaler): subscription rule;
// - the operator address ranges in `allowedAddressPrefixes` (uploads to raw/ from a
//   workstation; keep them in the azd environment, never in the repository). The address
//   Azure sees can differ from what public "my IP" services report (secure-access clients
//   tunnel Microsoft traffic): read SourceIpAddress in the NSPAccessLogs table.
// Event Grid cannot create its subscription inside the perimeter (see storage.bicep). Data
// access still requires the Entra roles granted in storage.bicep.

param location string
param tags object
param perimeterName string

@description('Resource ID of the storage account to associate with the perimeter.')
param storageAccountId string

@description('Public address prefixes (CIDR) allowed to reach the storage account.')
param allowedAddressPrefixes array = []

@description('Log Analytics workspace receiving the perimeter\'s denied-access logs; empty skips them.')
param logAnalyticsWorkspaceResourceId string = ''

resource perimeter 'Microsoft.Network/networkSecurityPerimeters@2024-07-01' = {
  name: perimeterName
  location: location
  tags: tags
}

resource profile 'Microsoft.Network/networkSecurityPerimeters/profiles@2024-07-01' = {
  parent: perimeter
  name: 'docwiki'
}

resource allowSubscription 'Microsoft.Network/networkSecurityPerimeters/profiles/accessRules@2024-07-01' = {
  parent: profile
  name: 'allow-subscription-identities'
  properties: {
    direction: 'Inbound'
    subscriptions: [
      {
        id: subscription().id
      }
    ]
  }
}

resource allowOperators 'Microsoft.Network/networkSecurityPerimeters/profiles/accessRules@2024-07-01' = if (!empty(allowedAddressPrefixes)) {
  parent: profile
  name: 'allow-operator-addresses'
  properties: {
    direction: 'Inbound'
    addressPrefixes: allowedAddressPrefixes
  }
}

resource storageAssociation 'Microsoft.Network/networkSecurityPerimeters/resourceAssociations@2024-07-01' = {
  parent: perimeter
  name: 'storage'
  properties: {
    privateLinkResource: {
      id: storageAccountId
    }
    profile: {
      id: profile.id
    }
    accessMode: 'Enforced'
  }
  dependsOn: [
    allowSubscription
    allowOperators
  ]
}

// Denied requests only (allowed-request logs would record every storage call).
resource deniedAccessLogs 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (!empty(logAnalyticsWorkspaceResourceId)) {
  scope: perimeter
  name: 'denied-access'
  properties: {
    workspaceId: logAnalyticsWorkspaceResourceId
    logs: [
      for category in [
        'NspPublicInboundPerimeterRulesDenied'
        'NspPublicInboundResourceRulesDenied'
        'NspPublicOutboundPerimeterRulesDenied'
        'NspPublicOutboundResourceRulesDenied'
      ]: {
        category: category
        enabled: true
      }
    ]
  }
}

output perimeterId string = perimeter.id
output associationName string = storageAssociation.name
