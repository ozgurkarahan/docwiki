// Built-in authentication (Easy Auth) for the MCP container app, as validated by the identity spike.
// Bearer-token validation only: no client secret, no token store, 401 for anonymous calls.
// ACA returns 403 for tokens whose client (azp/appid) is not in allowedApplications, so the agent
// identities' client IDs must be listed (see docs/spikes/identity-spike.md, finding F1).

@description('Name of the existing MCP container app.')
param containerAppName string

@description('Application (client) ID of the MCP API app registration.')
param mcpApiClientId string

@description('Application ID URI of the MCP API app registration, for example api://<client-id>.')
param mcpApiIdentifierUri string

@description('Client IDs (instance_identity.client_id) of the agents allowed to call the server.')
param allowedClientIds array

resource app 'Microsoft.App/containerApps@2024-03-01' existing = {
  name: containerAppName
}

resource auth 'Microsoft.App/containerApps/authConfigs@2024-03-01' = {
  parent: app
  name: 'current'
  properties: {
    platform: {
      enabled: true
    }
    globalValidation: {
      unauthenticatedClientAction: 'Return401'
      excludedPaths: [
        '/healthz'
      ]
    }
    identityProviders: {
      azureActiveDirectory: {
        enabled: true
        registration: {
          clientId: mcpApiClientId
          openIdIssuer: '${environment().authentication.loginEndpoint}${tenant().tenantId}/v2.0'
        }
        validation: {
          // The client ID is accepted implicitly; v2 tokens carry it as `aud`.
          allowedAudiences: [
            mcpApiIdentifierUri
          ]
          defaultAuthorizationPolicy: {
            allowedApplications: allowedClientIds
          }
        }
      }
    }
    login: {
      tokenStore: {
        enabled: false
      }
    }
  }
}
