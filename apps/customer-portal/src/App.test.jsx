// @vitest-environment jsdom

import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import App from './App.jsx'
import { CheckoutProvider } from './context/CheckoutContext.jsx'

vi.hoisted(() => {
  vi.stubEnv('DEV', true)
  vi.stubEnv('VITE_USE_DEMO_DATA', 'true')
})

let container
let root

beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
  container = document.createElement('div')
  document.body.appendChild(container)
  root = createRoot(container)
})

afterEach(() => {
  act(() => root.unmount())
  container.remove()
  vi.unstubAllGlobals()
})

function renderPortal(path) {
  act(() => {
    root.render(
      <CheckoutProvider>
        <MemoryRouter initialEntries={[path]}>
          <App />
        </MemoryRouter>
      </CheckoutProvider>
    )
  })
}

function clickLink(label) {
  const link = Array.from(container.querySelectorAll('a')).find(
    (element) => element.textContent.trim() === label
  )

  expect(link).toBeDefined()
  act(() => link.click())
}

test('renders the customer portal welcome page', () => {
  renderPortal('/')

  expect(container.textContent).toContain('Weza')
})

test('shows hotspot preview status and opens the package list', () => {
  renderPortal('/hotspot-entry')

  expect(container.querySelector('h1').textContent).toBe('Welcome to Weza Wi-Fi')
  expect(container.textContent).toContain('Development preview')
  expect(container.textContent).toContain('Your connection status is unavailable.')

  clickLink('Browse Packages')

  expect(container.querySelector('h1').textContent).toBe('A little Wi-Fi. A lot of possibility.')
})

test('labels the expired subscription as demo data and opens the package list', () => {
  renderPortal('/package-expired')

  expect(container.querySelector('h1').textContent).toBe('Your package has expired')
  expect(container.textContent).toContain('Development preview · Sample subscription')
  expect(container.textContent).toContain('Daily Connect (2 GB)')

  clickLink('Browse Packages')

  expect(container.querySelector('h1').textContent).toBe('A little Wi-Fi. A lot of possibility.')
})

test('opens renewal confirmation with Daily Connect and previews payment', () => {
  renderPortal('/package-expired')

  clickLink('Renew Package (KES 50)')

  expect(container.querySelector('h1').textContent).toBe('Confirm your package')

  const phoneInput = container.querySelector('#checkout-phone')
  expect(phoneInput).not.toBeNull()

  const checkout = phoneInput.closest('section')
  expect(checkout).not.toBeNull()
  expect(checkout.querySelector('h2')?.textContent).toBe('Daily Connect')
  expect(checkout.textContent).toContain('KES 50')
  expect(checkout.textContent).toContain('2 GB')
  expect(checkout.textContent).toContain('24 hours')

  phoneInput.value = '0712345678'

  const previewButton = checkout.querySelector('button[type="submit"]')
  expect(previewButton).not.toBeNull()
  act(() => previewButton.click())

  expect(checkout.querySelector('[role="status"]')?.textContent).toBe(
    'This is a preview. No M-Pesa prompt was sent.'
  )
})

test('shows M-Pesa instructions for a pending payment preview', () => {
  renderPortal('/payment-status?preview=pending')

  expect(container.querySelector('h1').textContent).toBe('Check your phone')
  expect(container.textContent).toContain('wait for confirmation before starting another payment')

  const checkStatusButton = Array.from(container.querySelectorAll('button')).find(
    (button) => button.textContent.trim() === 'Check payment status'
  )

  expect(checkStatusButton?.disabled).toBe(true)
})

test('shows support and discourages a second payment when activation fails', () => {
  renderPortal('/connection-status?preview=failed')

  expect(container.querySelector('h1').textContent).toBe('Payment received, internet not active')
  expect(container.textContent).toContain('Please do not pay again.')
  expect(container.textContent).toContain('DEMO-RECEIPT-001')
  expect(container.textContent).not.toContain('You’re connected!')

  const supportLink = Array.from(container.querySelectorAll('a')).find(
    (link) => link.textContent.trim() === 'Get support'
  )

  expect(supportLink?.getAttribute('href')).toBe('/support')
})