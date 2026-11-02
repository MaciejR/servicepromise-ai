// Deploys the frontend only; already provisioned through Azure Portal.
// React can call a separately hosted API using VITE_API_BASE_URL and strict CORS.
param location string = 'westeurope'
param siteName string = 'swa-servicepromise-ai'

resource site 'Microsoft.Web/staticSites@2023-12-01' = {
  name: siteName
  location: location
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {
    allowConfigFileUpdates: true
    stagingEnvironmentPolicy: 'Enabled'
  }
}

output url string = 'https://${site.properties.defaultHostname}'
