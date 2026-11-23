// @vitest-environment jsdom

import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import App from './App.jsx'

vi.hoisted(() => {
  vi.stubEnv('DEV', true)
  vi.stubEnv('VITE_USE_DEMO_DATA', 'false')
  vi.stubEnv('VITE_ENABLE_SANDBOX_CHECKOUT', 'true')
  vi.stubEnv('VITE_SANDBOX_PACKAGE_ID', '1')
  vi.stubEnv('VITE_SANDBOX_PURCHASE_ID', '42')
  vi.stubEnv('VITE_API_BASE_URL', '')
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

async function openCheckout() {
  request.mockResolvedValueOnce({
    ok: true,
    json: async () => [
      {
        id: 1,
        name: 'Local Test Package',
        price: 35,
        duration_minutes: 60,
        download_speed_mbps: 10,
        upload_speed_mbps: 5,
        is_active: true,
      },
    ],
  })

  await act(async () => {
    root.render(
      <MemoryRouter initialEntries={['/packages']}>
        <App />
      </MemoryRouter>
    )
  })

  const choosePackage = container.querySelector('a[href="/packages?package=1"]')
  expect(choosePackage).not.toBeNull()
  await act(async () => choosePackage.click())

  const continueToCheckout = container.querySelector('a[href="/confirm-package"]')
  expect(continueToCheckout).not.toBeNull()
  await act(async () => continueToCheckout.click())

  expect(container.querySelector('h1')?.textContent).toBe('Confirm your package')
  const checkout = container.querySelector('#checkout-phone')?.closest('section')
  expect(checkout?.querySelector('h2')?.textContent).toBe('Local Test Package')
}

async function submitPhone(number) {
  const phone = container.querySelector('#checkout-phone')
  const submit = container.querySelector('button[type="submit"]')
  expect(phone).not.toBeNull()
  expect(submit).not.toBeNull()

  phone.value = number
  await act(async () => submit.click())
}

test('rejects an invalid number before requesting payment', async () => {
  await openCheckout()
  await submitPhone('12345')

  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    'Enter a Kenyan mobile number'
  )
  expect(request).toHaveBeenCalledTimes(1)
})

test('sends a normalized number for the pending purchase and locks submission', async () => {
  await openCheckout()

  request.mockResolvedValueOnce({
    ok: true,
    status: 201,
    json: async () => ({
      payment_id: 7,
      purchase_id: 42,
      amount: 35,
      status: 'pending',
    }),
  })

  await submitPhone('0712 345 678')

  expect(request).toHaveBeenNthCalledWith(2, '/api/payments', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      purchase_id: 42,
      phone_number: '254712345678',
    }),
  })
  expect(container.querySelector('[role="status"]')?.textContent).toContain(
    'Your payment is pending confirmation.'
  )
  expect(container.querySelector('button[type="submit"]')?.disabled).toBe(true)

  await act(async () => container.querySelector('button[type="submit"]').click())
  expect(request).toHaveBeenCalledTimes(2)
})

test('locks submission when the backend cannot confirm whether it sent the prompt', async () => {
  await openCheckout()

  request.mockResolvedValueOnce({
    ok: false,
    status: 504,
    json: async () => ({
      code: 'outcome_unknown',
      detail: 'Payment outcome unknown.',
      payment_id: 7,
    }),
  })

  await submitPhone('0712345678')

  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    'We could not confirm whether the M-Pesa prompt was sent.'
  )
  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    'Payment reference: 7.'
  )
  expect(container.querySelector('button[type="submit"]')?.disabled).toBe(true)
})