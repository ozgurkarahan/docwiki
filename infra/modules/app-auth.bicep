// Container Apps built-in authentication (Microsoft Entra ID) for one container app.
// Used by main.bicep once the app registration exists, and deployed directly by the
// postprovision hook (scripts/hooks/postprovision.py) on the first run and whenever the agent
// allowlist changes. No client secret: the MCP API only validates bearer tokens (v2 issuer,
// ADR 0003); the portal signs users in with ID tokens only (AllowAnonymous: the public portal,
// where only the owner signs in, ADR 0009).

@description('Name of an existing container app in the target resource group.')
param containerAppName string

@description('Application (client) ID of the Entra app registration.')
param clientId string

@description('Token audiences accepted by the app (application ID URI and/or client ID).')
param allowedAudiences array

@allowed([
  'Return401'
  'RedirectToLoginPage'
  'AllowAnonymous'
])
param unauthenticatedClientAction string = 'Return401'

@description('Paths served without authentication (for example a health endpoint).')
param excludedPaths array = []

@description('Client IDs allowed to call the app (defaultAuthorizationPolicy.allowedApplications). On Container Apps an empty list rejects every client except the registration itself (HTTP 403).')
param allowedApplications array = []

resource app 'Microsoft.App/containerApps@2025-01-01' existing = {
  name: containerAppName
}

resource authConfig 'Microsoft.App/containerApps/authConfigs@2025-01-01' = {
  parent: app
  name: 'current'
  properties: {
    platform: {
      enabled: true
    }
    globalValidation: {
      unauthenticatedClientAction: unauthenticatedClientAction
      redirectToProvider: unauthenticatedClientAction == 'RedirectToLoginPage' ? 'azureactivedirectory' : null
      excludedPaths: excludedPaths
    }
    identityProviders: {
      azureActiveDirectory: {
        enabled: true
        registration: {
          clientId: clientId
          openIdIssuer: '${environment().authentication.loginEndpoint}${tenant().tenantId}/v2.0'
        }
        validation: {
          allowedAudiences: allowedAudiences
          defaultAuthorizationPolicy: empty(allowedApplications)
            ? null
            : {
                allowedApplications: allowedApplications
              }
        }
      }
    }
    login: {
      tokenStore: {
        enabled: false
      }
    }
    httpSettings: {
      requireHttps: true
    }
  }
}

output unauthenticatedClientAction string = authConfig.properties.globalValidation.unauthenticatedClientAction
