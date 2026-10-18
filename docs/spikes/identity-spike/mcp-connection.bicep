// Foundry project connection used by the MCP tool of each prompt agent, as validated by the
// identity spike. Agent Service requests an app-only token for the calling agent's own Entra
// agent identity with audience = the MCP API application ID URI.

@description('Name of the existing Foundry (AIServices) account.')
param accountName string

@description('Name of the existing Foundry project.')
param projectName string

@description('Connection name referenced by the agents (project_connection_id).')
param connectionName string = 'docwiki-mcp'

@description('MCP endpoint, for example https://<mcp-app-fqdn>/mcp.')
param mcpUrl string

@description('Application ID URI of the MCP API app registration, for example api://<client-id>.')
param mcpApiIdentifierUri string

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: accountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' existing = {
  parent: account
  name: projectName
}

resource mcpConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-10-01-preview' = {
  parent: project
  name: connectionName
  properties: {
    category: 'RemoteTool'
    // Not yet in the Bicep type definitions (warning BCP036); accepted by the resource provider.
    #disable-next-line BCP036
    authType: 'AgenticIdentityToken'
    target: mcpUrl
    audience: mcpApiIdentifierUri
    metadata: {
      type: 'generic_mcp'
    }
  }
}

output connectionId string = mcpConnection.id
