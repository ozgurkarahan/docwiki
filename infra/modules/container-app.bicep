// Container app running as its own user-assigned identity. Ingress is optional
// (`ingressMode: 'none'` keeps the app private); `dormant: true` keeps it at zero replicas.

param location string
param tags object
param name string
param containerName string
param environmentId string
param workloadProfileName string
param identityResourceId string
param registryServer string
param image string
param env array = []
param cpu string = '0.5'
param memory string = '1Gi'
param minReplicas int = 0
param maxReplicas int = 2

@allowed([
  'external'
  'none'
])
param ingressMode string = 'external'

param targetPort int = 8080

@description('HTTP path probed for liveness/readiness; empty uses the platform default TCP probe.')
param healthPath string = ''

@description('Explicit TCP probes on targetPort (startup allowing about two minutes, liveness, readiness); ignored when healthPath is set.')
param tcpProbes bool = false

@description('Concurrent HTTP requests per replica before scaling out.')
param concurrentRequests int = 20

@description('Deployed (azd can publish its image) but never running: zero replicas, no ingress.')
param dormant bool = false

// With no ingress and no scale rule the platform leaves the first replica of every revision
// running (KEDA has no trigger to scale it in). A cron rule whose one-minute window falls on
// 29 February gives KEDA a trigger that is never active, so the revision scales to zero after
// the cooldown period.
var dormantRule = {
  name: 'dormant'
  custom: {
    type: 'cron'
    metadata: {
      timezone: 'Etc/UTC'
      start: '0 0 29 2 *'
      end: '1 0 29 2 *'
      desiredReplicas: '1'
    }
  }
}

var httpProbes = [
  {
    type: 'Liveness'
    httpGet: {
      path: healthPath
      port: targetPort
    }
    initialDelaySeconds: 5
    periodSeconds: 30
    failureThreshold: 3
  }
  {
    type: 'Readiness'
    httpGet: {
      path: healthPath
      port: targetPort
    }
    initialDelaySeconds: 3
    periodSeconds: 10
    failureThreshold: 3
  }
]

// TCP probes (tcpProbes): the startup probe gives a cold replica about two minutes to open the
// port (10 s, then 10 attempts every 11 s; the API caps failureThreshold at 10) and probes
// rarely enough that a normal cold start logs at most one failed attempt, where the platform
// default probes every second. Liveness and readiness only run once the startup probe passed.
var tcpProbeSet = [
  {
    type: 'Startup'
    tcpSocket: {
      port: targetPort
    }
    initialDelaySeconds: 10
    periodSeconds: 11
    timeoutSeconds: 3
    failureThreshold: 10
  }
  {
    type: 'Liveness'
    tcpSocket: {
      port: targetPort
    }
    periodSeconds: 30
    timeoutSeconds: 5
    failureThreshold: 3
  }
  {
    type: 'Readiness'
    tcpSocket: {
      port: targetPort
    }
    periodSeconds: 5
    timeoutSeconds: 3
    failureThreshold: 3
  }
]

var probes = !empty(healthPath) ? httpProbes : tcpProbes ? tcpProbeSet : []

resource app 'Microsoft.App/containerApps@2025-01-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityResourceId}': {}
    }
  }
  properties: {
    environmentId: environmentId
    workloadProfileName: workloadProfileName
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: ingressMode == 'external'
        ? {
            external: true
            targetPort: targetPort
            transport: 'auto'
            allowInsecure: false
            traffic: [
              {
                latestRevision: true
                weight: 100
              }
            ]
          }
        : null
      registries: [
        {
          server: registryServer
          identity: identityResourceId
        }
      ]
    }
    template: {
      containers: [
        {
          name: containerName
          image: image
          env: env
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          probes: probes
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: ingressMode == 'external'
          ? [
              {
                name: 'http'
                http: {
                  metadata: {
                    concurrentRequests: string(concurrentRequests)
                  }
                }
              }
            ]
          : dormant ? [dormantRule] : []
      }
    }
  }
}

output name string = app.name
output id string = app.id
output fqdn string = ingressMode == 'external' ? app.properties.configuration.ingress.fqdn : ''
