const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '')

export async function fetchActivePackages(signal) {
  const response = await fetch(`${apiBaseUrl}/api/packages/`, { signal })
  if (!response.ok) throw new Error('Package request failed')

  const packages = await response.json()
  if (!Array.isArray(packages)) throw new Error('Invalid package response')

  return packages
    .filter((item) => item.is_active === true)
    .map((item) => ({
      id: item.id,
      name: item.name,
      price: item.price,
      duration: `${item.duration_minutes} min`,
      speed: `${item.download_speed_mbps} Mbps down / ${item.upload_speed_mbps} Mbps up`,
      description: item.description,
    }))
}

async function apiRequest(endpoint, options = {}) {
  const response = await fetch(`${apiBaseUrl}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    }
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(data.detail || 'Unable to connect to WEZA server')
  }

  return data
}

export function getConnectionStatus() {
  return apiRequest('/api/network/status')
}

export function getMySubscription() {
  return apiRequest('/api/subscriptions/me')
}
