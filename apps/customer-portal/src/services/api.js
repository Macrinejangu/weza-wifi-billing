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
      ...options.headers,
    },
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    const message = typeof data?.detail === 'string'
      ? data.detail
      : 'Unable to complete the request'

    const error = new Error(message)
    error.status = response.status
    error.code = data?.code
    error.paymentId = data?.payment_id
    throw error
  }

  return data
}

export function getCheckoutDeviceReference({ accessToken, packageId, idempotencyKey }) {
  return apiRequest('/api/customer/checkout/device-reference', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify({ package_id: packageId }),
  })
}

export function createCustomerPurchase({ accessToken, packageId, idempotencyKey, deviceReference }) {
  return apiRequest('/api/customer/purchases', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify({ package_id: packageId, device_reference: deviceReference }),
  })
}

export function submitMockPayment({ accessToken, purchaseId, phoneNumber }) {
  return apiRequest('/api/customer/payments/mock', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ purchase_id: purchaseId, phone_number: phoneNumber }),
  })
}

export function startMpesaPayment({ accessToken, purchaseId, phoneNumber }) {
  return apiRequest('/api/payments', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({
      purchase_id: purchaseId,
      phone_number: phoneNumber,
    }),
  })
}

export function getCustomerPayment({ accessToken, paymentId, signal }) {
  return apiRequest(`/api/customer/payments/${paymentId}`, {
    cache: 'no-store',
    signal,
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

export function getMyConnection({ accessToken, paymentId, signal }) {
  const query = paymentId ? `?payment_id=${encodeURIComponent(paymentId)}` : ''
  return apiRequest(`/api/customer/connection${query}`, {
    cache: 'no-store',
    signal,
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}


export function loginCustomer({ email, password }) {
  return apiRequest('/api/auth/customer/login', {
    method: 'POST',
    cache: 'no-store',
    body: JSON.stringify({ email: email.trim(), password }),
  })
}

export function getCustomerProfile(accessToken) {
  return apiRequest('/api/auth/customer/me', {
    cache: 'no-store',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}
