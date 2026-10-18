// Azure built-in role definition IDs used by DocWiki.
// These GUIDs are public constants, identical in every tenant, documented at
// https://learn.microsoft.com/azure/role-based-access-control/built-in-roles
// Every value is listed in tools/leakguard/allowed_guids.txt.

@export()
@description('Built-in role definition IDs (GUIDs) by role name.')
var roleIds = {
  storageBlobDataReader: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
  storageBlobDataContributor: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
  storageQueueDataReader: '19e7f393-937e-4f77-808e-94535e297925'
  storageQueueDataContributor: '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
  storageQueueDataMessageProcessor: '8a0f0c08-91a1-4084-bc3d-661d67233fed'
  storageQueueDataMessageSender: 'c6a89b2d-59bc-44d0-9896-0f6e12d7b80a'
  acrPull: '7f951dda-4ed3-4680-a7ca-43fe172d538d'
  cognitiveServicesUser: 'a97b65f3-24c7-4388-baec-2e87135dc908'
  azureAiUser: '53ca6127-db72-4b80-b1b0-d745d6d5456d'
  monitoringMetricsPublisher: '3913510d-42f4-4e42-8a64-420c390055eb'
}
