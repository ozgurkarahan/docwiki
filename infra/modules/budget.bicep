// Monthly cost budget on the resource group with 50/80/100 % notifications delivered by an
// action group. Contact e-mail addresses come from the azd environment (BUDGET_CONTACT_EMAILS)
// and are never committed.

param tags object
param budgetName string
param actionGroupName string

@minValue(1)
@description('Monthly amount in the billing currency of the subscription.')
param amount int

@minLength(1)
param contactEmails array

@description('First day of the current month (yyyy-MM-dd).')
param startDate string

param thresholds array = [
  50
  80
  100
]

module actionGroup 'br/public:avm/res/insights/action-group:0.8.0' = {
  name: 'budgetActionGroup'
  params: {
    name: actionGroupName
    groupShortName: 'docwiki'
    location: 'global'
    tags: tags
    enabled: true
    enableTelemetry: false
    emailReceivers: [
      for (email, i) in contactEmails: {
        name: 'budget-contact-${i}'
        emailAddress: email
        useCommonAlertSchema: true
      }
    ]
  }
}

resource budget 'Microsoft.Consumption/budgets@2024-08-01' = {
  name: budgetName
  properties: {
    category: 'Cost'
    amount: amount
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: startDate
    }
    notifications: toObject(
      thresholds,
      threshold => 'actual-${threshold}-percent',
      threshold => {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: threshold
        thresholdType: 'Actual'
        contactEmails: []
        contactGroups: [
          actionGroup.outputs.resourceId
        ]
      }
    )
  }
}

output budgetName string = budget.name
output actionGroupId string = actionGroup.outputs.resourceId
