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