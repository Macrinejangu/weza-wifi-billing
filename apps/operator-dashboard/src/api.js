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

async function readStaffData(path, accessToken, { signal, errorMessage, notFoundMessage, method, body }) {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: 'no-store',
    signal,
    ...(method ? { method, body, headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    } } : {}),
  })

  if (response.status === 401 || (response.status === 403 && !method)) {
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


export function listStaffCustomers(accessToken, { limit = 50, offset = 0, status, query, registeredOn, signal } = {}) {
  const params = new URLSearchParams({ limit, offset })
  if (status) params.set('status', status)
  if (query) params.set('q', query)
  if (registeredOn) params.set('registered_on', registeredOn)
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

export function retryStaffActivation(accessToken, paymentId) {
  return readStaffData(`/api/connection-issues/${paymentId}/retry`, accessToken, {
    method: 'POST',
    errorMessage: 'Could not retry this activation. Check the package and payment status.',
  })
}

export function getStaffSettings(accessToken, { signal } = {}) {
  return readStaffData('/api/staff/settings', accessToken, {
    signal,
    errorMessage: 'Could not load system settings.',
  })
}

export function updateStaffSettings(accessToken, preferences) {
  return readStaffData('/api/staff/settings', accessToken, {
    method: 'PUT',
    body: JSON.stringify(preferences),
    errorMessage: 'Could not save system settings.',
  })
}

export function getStaffAuditHistory(accessToken, { signal, offset = 0, limit = 50 } = {}) {
  const query = new URLSearchParams({ limit, offset })
  return readStaffData(`/api/staff/settings/audit?${query}`, accessToken, {
    signal,
    errorMessage: 'Could not load the audit history.',
  })
}

export function listStaffPackages(accessToken, { signal } = {}) {
  return readStaffData('/api/packages/staff', accessToken, {
    signal, errorMessage: 'Could not load packages. Please try again.',
  })
}

export function saveStaffPackage(accessToken, packageId, fields) {
  const path = packageId ? `/api/packages/${packageId}` : '/api/packages/'
  return readStaffData(path, accessToken, {
    method: packageId ? 'PUT' : 'POST',
    body: JSON.stringify(fields),
    errorMessage: 'Could not save the package. Check the details and try again.',
  })
}

export function deactivateStaffPackage(accessToken, packageId) {
  return readStaffData(`/api/packages/${packageId}`, accessToken, {
    method: 'DELETE',
    errorMessage: 'Could not deactivate the package. Please try again.',
  })
}

export function listSupportFaqs(accessToken, { signal } = {}) {
  return readStaffData('/api/support/faqs', accessToken, {
    signal, errorMessage: 'Could not load support answers. Please try again.',
  })
}

export function updateSupportFaq(accessToken, id, fields) {
  return readStaffData(`/api/support/faqs/${id}`, accessToken, {
    method: 'PUT',
    body: JSON.stringify(fields),
    errorMessage: 'Could not save the support answer. Please try again.',
  })
}

export function saveStaffCustomer(accessToken, id, fields) {
  return readStaffData(id ? `/api/customers/${id}` : '/api/customers', accessToken, {
    method: id ? 'PUT' : 'POST',
    body: JSON.stringify(fields),
    errorMessage: 'Could not save the customer. Check the details and whether the email or number is already used.',
  })
}

export function disconnectStaffSession(accessToken, id) {
  return readStaffData(`/api/sessions/${id}/disconnect`, accessToken, {
    method: 'POST',
    errorMessage: 'Could not disconnect this session. Check its status and router connection.',
  })
}
