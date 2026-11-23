const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '')

export async function signInStaff(email, password) {
  const response = await fetch(`${apiBaseUrl}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: email.trim(), password }),
  })

  if (response.status === 401) {
    throw new Error('Invalid email or password.')
  }

  if (!response.ok) {
    throw new Error('Staff sign-in is unavailable. Please try again.')
  }

  const { access_token: accessToken } = await response.json()

  if (typeof accessToken !== 'string' || !accessToken) {
    throw new Error('Staff sign-in returned an invalid response.')
  }

  return accessToken
}

export async function getStaffProfile(accessToken) {
  const response = await fetch(`${apiBaseUrl}/api/auth/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })

  if (response.status === 401 || response.status === 403) {
    throw new Error('Your staff session is unavailable. Please sign in again.')
  }

  if (!response.ok) {
    throw new Error('Could not load your staff profile. Please try again.')
  }

  return response.json()
}

export class StaffSessionError extends Error {
  constructor() {
    super('Your staff session is unavailable. Please sign in again.')
    this.name = 'StaffSessionError'
  }
}

async function readStaffData(path, accessToken, { signal, errorMessage, notFoundMessage }) {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: 'no-store',
    signal,
  })

  if (response.status === 401 || response.status === 403) {
    throw new StaffSessionError()
  }

  if (response.status === 404 && notFoundMessage) {
    throw new Error(notFoundMessage)
  }

  if (!response.ok) {
    throw new Error(errorMessage)
  }

  return response.json()
}

export function listStaffPayments(accessToken, { limit = 50, offset = 0, status, signal } = {}) {
  const query = new URLSearchParams({ limit, offset })
  if (status) query.set('status', status)
  return readStaffData(`/api/payments?${query}`, accessToken, {
    signal,
    errorMessage: 'Could not load payment records. Please try again.',
  })
}

export function getStaffPayment(accessToken, paymentId, { signal } = {}) {
  return readStaffData(`/api/payments/${encodeURIComponent(paymentId)}`, accessToken, {
    signal,
    errorMessage: 'Could not load payment records. Please try again.',
    notFoundMessage: 'This payment could not be found.',
  })
}

export function listStaffSessions(accessToken, { limit = 50, offset = 0, status, signal } = {}) {
  const query = new URLSearchParams({ limit, offset })
  if (status) query.set('status', status)
  return readStaffData(`/api/sessions?${query}`, accessToken, {
    signal,
    errorMessage: 'Could not load session records. Please try again.',
  })
}

export async function listActivePackages({ signal } = {}) {
  const response = await fetch(`${apiBaseUrl}/api/packages/`, {
    cache: 'no-store',
    signal,
  })

  if (!response.ok) {
    throw new Error('Could not load packages. Please try again.')
  }

  const packages = await response.json()
  if (!Array.isArray(packages)) {
    throw new Error('The package catalog returned an invalid response.')
  }

  return packages
}


export function listStaffCustomers(accessToken, { limit = 50, offset = 0, status, query, signal } = {}) {
  const params = new URLSearchParams({ limit, offset })
  if (status) params.set('status', status)
  if (query) params.set('q', query)
  return readStaffData(`/api/customers?${params}`, accessToken, {
    signal,
    errorMessage: 'Could not load customers. Please try again.',
  })
}


export function getStaffOverview(accessToken, { signal } = {}) {
  return readStaffData('/api/overview', accessToken, {
    signal,
    errorMessage: 'Could not load overview totals. Please try again.',
  })
}


export function getStaffNetworkInventory(accessToken, { signal } = {}) {
  return readStaffData('/api/network/devices', accessToken, {
    signal,
    errorMessage: 'Could not load device inventory. Please try again.',
  })
}


export function listStaffConnectionIssues(accessToken, { limit = 50, offset = 0, signal } = {}) {
  const params = new URLSearchParams({ limit, offset })
  return readStaffData(`/api/connection-issues?${params}`, accessToken, {
    signal,
    errorMessage: 'Could not load connection issues. Please try again.',
  })
}
