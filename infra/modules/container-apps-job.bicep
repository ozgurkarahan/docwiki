// Container Apps job (event-, schedule- or manually triggered) running as the runtime
// user-assigned identity and pulling from the registry with that identity.

param location string
param tags object
param name string
param containerName string
param environmentId string
param workloadProfileName string
param identityResourceId string
param registryServer string
param image string

@description('Container arguments (the image entrypoint is `docwiki`); empty keeps the image default.')
param args array = []

param env array = []
param cpu string = '2.0'
param memory string = '4Gi'

@allowed([
  'Event'
  'Schedule'
  'Manual'
])
param triggerType string

@description('Cron expression (UTC) for Schedule jobs.')
param cronExpression string = ''

@description('Storage account holding the wake-up queue (Event jobs).')
param queueAccountName string = ''

@description('Wake-up queue watched by the KEDA azure-queue scaler (Event jobs).')
param queueName string = ''

param pollingIntervalSeconds int = 30
param replicaTimeoutSeconds int = 3600
param replicaRetryLimit int = 1

var singleExecution = {
  parallelism: 1
  replicaCompletionCount: 1
}

resource job 'Microsoft.App/jobs@2025-01-01' = {
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
      triggerType: triggerType
      replicaTimeout: replicaTimeoutSeconds
      replicaRetryLimit: replicaRetryLimit
      registries: [
        {
          server: registryServer
          identity: identityResourceId
        }
      ]
      eventTriggerConfig: triggerType == 'Event'
        ? union(singleExecution, {
            scale: {
              minExecutions: 0
              maxExecutions: 1
              pollingInterval: pollingIntervalSeconds
              rules: [
                {
                  name: 'ingest-queue'
                  type: 'azure-queue'
                  metadata: {
                    accountName: queueAccountName
                    queueName: queueName
                    queueLength: '1'
                    cloud: 'AzurePublicCloud'
                  }
                  identity: identityResourceId
                }
              ]
            }
          })
        : null
      scheduleTriggerConfig: triggerType == 'Schedule'
        ? union(singleExecution, {
            cronExpression: cronExpression
          })
        : null
      manualTriggerConfig: triggerType == 'Manual' ? singleExecution : null
    }
    template: {
      containers: [
        {
          name: containerName
          image: image
          args: empty(args) ? null : args
          env: env
          resources: {
            cpu: json(cpu)
            memory: memory
          }
        }
      ]
    }
  }
}

output name string = job.name
output id string = job.id
