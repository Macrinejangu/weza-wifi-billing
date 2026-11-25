// @vitest-environment jsdom

import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import App from './App.jsx'

vi.hoisted(() => {
  vi.stubEnv('DEV', true)
  vi.stubEnv('VITE_USE_DEMO_DATA', undefined)
})

let container
let root
let request

beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
  request = vi.fn()
  vi.stubGlobal('fetch', request)
  container = document.createElement('div')
  document.body.appendChild(container)
  root = createRoot(container)
})

afterEach(() => {
  act(() => root.unmount())
  container.remove()
  vi.unstubAllGlobals()
})

async function renderPortal(pathname, search = '') {
  await act(async () => {
    root.render(
      <MemoryRouter
        initialEntries={[
          {
            pathname,
            search,
            state: { selectedPackage: { name: 'Daily Connect', price: 50 } },
          },
        ]}
      >
        <App />
      </MemoryRouter>
    )
  })
}

test.each([
  ['/dashboard', 'Sign in to check your connection.'],
  ['/payments', 'Payment history is currently unavailable.'],
  ['/usage', 'Usage history and sessions are currently unavailable.'],
  ['/profile', 'Account details are currently unavailable.'],
  ['/package-expired', 'Sign in to check your connection.'],
  ['/confirm-package', 'Live checkout is currently unavailable.'],
])('opens %s without demo records, even with stale navigation state', async (path, message) => {
  await renderPortal(path)

  expect(container.querySelector('[role="status"]').textContent).toBe(message)
  expect(container.textContent).not.toMatch(/Daily Connect|Sample|Preview|WEZA member/i)
  expect(request).not.toHaveBeenCalled()
})

test('loads active API packages and opens the selected package review', async () => {
  let resolveRequest
  request.mockReturnValue(new Promise((resolve) => { resolveRequest = resolve }))

  await renderPortal('/packages')

  expect(container.textContent).toContain('Loading internet packages')
  expect(request).toHaveBeenCalledWith('/api/packages/', {
    signal: expect.any(AbortSignal),
  })

  await act(async () => {
    resolveRequest({
      ok: true,
      json: async () => [
        {
          id: 1,
          name: 'API package',
          price: 35,
          duration_minutes: 60,
          download_speed_mbps: 10,
          upload_speed_mbps: 5,
          is_active: true,
        },
        {
          id: 2,
          name: 'Second package',
          price: 80,
          duration_minutes: 120,
          download_speed_mbps: 20,
          upload_speed_mbps: 10,
          is_active: true,
        },
        { id: 3, name: 'Inactive package', is_active: false },
      ],
    })
  })

  expect(container.textContent).toContain('API package')
  expect(container.textContent).toContain('Second package')
  expect(container.textContent).not.toMatch(/Inactive package|Daily Connect|Loading internet packages/)

  const chooseLink = container.querySelector('a[href="/packages?package=1"]')
  expect(chooseLink?.textContent.trim()).toBe('Choose API package')

  await act(async () => chooseLink.click())

  expect(container.querySelector('h1').textContent).toBe('Review your package')
  expect(container.querySelector('article h2').textContent).toBe('API package')
  expect(container.textContent).toContain('KES35')
  expect(container.textContent).toContain('60 min')
  expect(container.textContent).toContain('10 Mbps down / 5 Mbps up')
  expect(container.textContent).toContain('Live checkout is currently unavailable.')
  expect(container.textContent).not.toContain('Second package')
  expect(container.querySelector('a[href="/confirm-package"]')).toBeNull()

  const backLink = Array.from(container.querySelectorAll('a')).find(
    (link) => link.textContent.trim() === 'Back to packages'
  )
  expect(backLink).toBeDefined()

  await act(async () => backLink.click())

  expect(container.querySelector('h1').textContent).toBe('A little Wi-Fi. A lot of possibility.')
  expect(container.textContent).toContain('Second package')
})

test('shows that a selected package is unavailable when the API no longer lists it', async () => {
  request.mockResolvedValue({
    ok: true,
    json: async () => [{ id: 3, name: 'Inactive package', is_active: false }],
  })

  await renderPortal('/packages', '?package=3')

  expect(container.querySelector('[role="status"]').textContent).toBe(
    'This package is no longer available. Choose another package.'
  )
  expect(container.textContent).not.toContain('Inactive package')
})

test('shows an empty catalogue when the API returns no packages', async () => {
  request.mockResolvedValue({ ok: true, json: async () => [] })
  await renderPortal('/packages')

  expect(container.textContent).toContain('No internet packages are currently available.')
  expect(container.textContent).not.toContain('Daily Connect')
})

test('shows an error on API failure without substituting demo packages', async () => {
  request.mockResolvedValue({ ok: false })
  await renderPortal('/packages')

  expect(container.querySelector('[role="alert"]').textContent).toBe(
    'Internet packages could not load. Try again later.'
  )
  expect(container.textContent).not.toContain('Daily Connect')
})
test('creates a customer account and returns to the selected package after sign-in', async () => {
  const token = `test.${btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }))}.test`
  const profile = { id: 7, full_name: 'Test Customer', email: 'customer@example.test' }
  request.mockImplementation(async (url) => {
    const data = {
      '/api/auth/customer/register': profile,
      '/api/auth/customer/login': { access_token: token },
      '/api/auth/customer/me': profile,
      '/api/packages/': [{
        id: 8, name: 'Selected pass', is_active: true, price: 20,
        duration_minutes: 60, download_speed_mbps: 5, upload_speed_mbps: 2,
      }],
    }
    return { ok: true, json: async () => data[url] }
  })

  await act(async () => root.render(
    <MemoryRouter initialEntries={[{ pathname: '/login', state: { returnPackageId: 8 } }]}>
      <App />
    </MemoryRouter>,
  ))
  await act(async () => container.querySelector('a[href="/register"]').click())

  function submit(fields) {
    const form = container.querySelector('form')
    for (const [name, value] of Object.entries(fields)) form.elements.namedItem(name).value = value
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
  }

  await act(async () => submit({
    fullName: 'Test Customer', email: profile.email, phone: '0712345678',
    password: 'test password', confirmPassword: 'test password',
  }))
  expect(request).toHaveBeenCalledWith('/api/auth/customer/register', expect.objectContaining({
    method: 'POST',
    body: JSON.stringify({ full_name: 'Test Customer', email: profile.email, phone: '0712345678', password: 'test password' }),
  }))
  expect(container.textContent).toContain('Account created. Sign in to continue.')

  await act(async () => submit({ email: profile.email, password: 'test password' }))
  expect(container.textContent).toContain('Review your package')
  expect(container.textContent).toContain('Selected pass')
})

test('shows the saved steps when a support topic is selected', async () => {
  request.mockResolvedValue({
    ok: true,
    json: async () => [{ id: 1, question: 'Paid but offline?', steps: ['Check Connection Status.'] }],
  })
  await renderPortal('/support')
  const topic = [...container.querySelectorAll('button')].find((item) => item.textContent === 'Paid but offline?')
  expect(container.querySelector('[role="log"]').textContent).toBe('')
  await act(async () => topic.click())
  expect(topic.getAttribute('aria-pressed')).toBe('true')
  expect(container.querySelector('[role="log"]').textContent).toContain('Check Connection Status.')
})
