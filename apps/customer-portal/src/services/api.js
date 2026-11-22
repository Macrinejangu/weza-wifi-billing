

const API_URL = import.meta.env.VITE_API_BASE_URL

async function apiRequest(endpoint, options = {}) {
  const response = await fetch(`${API_URL}${endpoint}`, {
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
