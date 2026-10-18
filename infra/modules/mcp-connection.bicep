// Foundry project connection of the agents' MCP tool (ADR 0003, docs/spikes/identity-spike.md
// section 4.3). Agent Service requests an app-only token for the calling agent's own Entra agent
// identity (AgenticIdentityToken) with audience = the MCP API application ID URI, and sends the
// tool calls to `target`. Declared by main.bicep once the MCP API app registration exists; the
// postprovision hook creates it with the same properties on the first run
// (scripts/hooks/postprovision.py, `connection_body`).

@description('Name of the existing Foundry (AIServices) account.')
param accountName string

@description('Name of the existing Foundry project hosting the agents.')
param projectName string

@description('Connection name referenced by the agents (DOCWIKI_MCP_CONNECTION).')
param connectionName string = 'docwiki-mcp'

@description('MCP endpoint (https://<mcp app FQDN>/mcp).')
param mcpUrl string

@description('Application ID URI of the MCP API app registration (api://<client id>).')
param audience string

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: accountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' existing = {
  parent: account
  name: projectName
}

// AgenticIdentityToken is only accepted by preview API versions and is not in the Bicep types yet
// (validated against the resource provider by the identity spike).
resource connection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-10-01-preview' = {
  parent: project
  name: connectionName
  properties: {
    category: 'RemoteTool'
    #disable-next-line BCP036
    authType: 'AgenticIdentityToken'
    target: mcpUrl
    audience: audience
    metadata: {
      type: 'generic_mcp'
    }
  }
}

output name string = connection.name
