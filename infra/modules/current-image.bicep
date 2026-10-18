// Returns the image currently deployed on an existing container app or job, so that
// `azd provision` never resets a deployed image back to the placeholder.

@allowed([
  'app'
  'job'
])
param kind string
param name string
param exists bool

resource app 'Microsoft.App/containerApps@2025-01-01' existing = if (exists && kind == 'app') {
  name: name
}

resource job 'Microsoft.App/jobs@2025-01-01' existing = if (exists && kind == 'job') {
  name: name
}

// ARM evaluates only the selected branch, so the existing resources are read only when they exist.
output image string = exists
  ? (kind == 'app' ? app!.properties.template.containers[0].image : job!.properties.template.containers[0].image)
  : ''
