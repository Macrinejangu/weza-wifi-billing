// @vitest-environment jsdom
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import App from '../App.jsx'

vi.hoisted(() => {
  vi.stubEnv('DEV', true)
  vi.stubEnv('VITE_USE_DEMO_DATA', 'true')
})

let root
let container

beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
  container = document.createElement('div')
  document.body.append(container)
  root = createRoot(container)
  act(() => root.render(<App />))
  click('Preview Dashboard (Development Only)')
  click('Payments')
})

afterEach(() => {
  act(() => root.unmount())
  container.remove()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

function findButton(label, scope = container) {
  return [...scope.querySelectorAll('button')].find((button) => {
    const copy = button.cloneNode(true)
    copy.querySelectorAll('[aria-hidden="true"]').forEach((icon) => icon.remove())
    return (button.getAttribute('aria-label') ?? copy.textContent.trim()) === label
  })
}

function click(label, scope = container) {
  const button = findButton(label, scope)
  expect(button, label).toBeDefined()
  act(() => button.click())
  return button
}

function searchFor(value) {
  const input = container.querySelector('input[aria-label="Search payments"]')
  const setValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set

  act(() => {
    setValue.call(input, value)
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })

  return input
}

function customerNames() {
  return [...container.querySelectorAll('.payments-customer-cell strong')].map(
    (name) => name.textContent,
  )
}

function pressKey(element, key, options = {}) {
  act(() => element.dispatchEvent(new KeyboardEvent('keydown', {
    key,
    bubbles: true,
    cancelable: true,
    ...options,
  })))
}

function readBlob(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => reject(reader.error)
    reader.readAsText(blob)
  })
}

test('searches by name, phone, receipt, and transaction ID and shows an empty result', () => {
  expect(customerNames()).toHaveLength(6)

  searchFor('  dennis  ')
  expect(customerNames()).toEqual(['Dennis Kiprono'])

  searchFor('712 345 678')
  expect(customerNames()).toEqual(['Amina Wanjiku'])

  searchFor('rj92mn41p0')
  expect(customerNames()).toEqual(['Dennis Kiprono'])

  searchFor('pay-00620')
  expect(customerNames()).toEqual(['Grace Mwangi'])

  searchFor('no matching customer')
  expect(customerNames()).toEqual([])
  expect(container.textContent).toContain('No transactions match your search or selected filter.')
  expect(container.textContent).toContain('Showing 0 of 6 sample transactions')
})

test('filters by payment status, including a failed payment with no provisioning', () => {
  const filters = container.querySelector('[aria-label="Filter payments by status"]')

  const failed = click('Failed', filters)
  expect(failed.getAttribute('aria-pressed')).toBe('true')
  expect(customerNames()).toEqual(['Esther Njeri'])

  searchFor('Dennis')
  expect(customerNames()).toEqual([])
  expect(container.textContent).toContain('No transactions match your search or selected filter.')

  const confirmed = click('Confirmed', filters)
  expect(failed.getAttribute('aria-pressed')).toBe('false')
  expect(confirmed.getAttribute('aria-pressed')).toBe('true')
  expect(customerNames()).toEqual(['Dennis Kiprono'])

  searchFor('')
  click('Pending', filters)
  expect(customerNames()).toEqual(['Grace Mwangi'])

  click('All transactions', filters)
  expect(customerNames()).toHaveLength(6)
})

test('opens the selected transaction, wraps keyboard focus, and restores focus on Escape', () => {
  const search = searchFor('')
  const trigger = click('Inspect payment for Dennis Kiprono')
  const dialog = container.querySelector('[role="dialog"]')
  const close = findButton('Close transaction details', dialog)
  const last = findButton('Close details', dialog)

  expect(dialog.getAttribute('aria-modal')).toBe('true')
  expect(dialog.textContent).toContain('PAY-00623')
  expect(dialog.textContent).toContain('19 Nov 2026, 08:42:16 EAT')
  expect(document.activeElement).toBe(close)

  pressKey(close, 'Tab', { shiftKey: true })
  expect(document.activeElement).toBe(last)
  pressKey(last, 'Tab')
  expect(document.activeElement).toBe(close)

  search.focus()
  expect(document.activeElement).toBe(close)

  pressKey(close, 'Escape')
  expect(container.querySelector('[role="dialog"]')).toBeNull()
  expect(document.activeElement).toBe(trigger)
})

test('keeps retry local and offers it only for a confirmed payment with failed provisioning', () => {
  const fetch = vi.fn()
  vi.stubGlobal('fetch', fetch)
  const trigger = click('Inspect payment for Dennis Kiprono')
  let dialog = container.querySelector('[role="dialog"]')

  click('Retry CoA push', dialog)
  expect(dialog.querySelector('[role="status"]').textContent).toContain(
    'No request was sent for Dennis Kiprono.',
  )
  expect([...dialog.querySelectorAll('.payment-status-pill')].map(
    (pill) => pill.textContent,
  )).toEqual(['Confirmed', 'Failed'])
  expect(fetch).not.toHaveBeenCalled()

  click('Close details', dialog)
  expect(document.activeElement).toBe(trigger)

  click('Inspect payment for Esther Njeri')
  dialog = container.querySelector('[role="dialog"]')
  expect(dialog.textContent).toContain('Payment failed. Access provisioning did not start.')
  expect(findButton('Retry CoA push', dialog)).toBeUndefined()
})

test('exports the visible transactions with separate payment and provisioning columns', async () => {
  const createObjectURL = vi.fn(() => 'blob:payments-test')
  const revokeObjectURL = vi.fn()
  vi.stubGlobal('URL', class extends URL {
    static createObjectURL = createObjectURL
    static revokeObjectURL = revokeObjectURL
  })
  const download = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

  click('Failed')
  click('Export CSV')

  expect(createObjectURL).toHaveBeenCalledTimes(1)
  expect(download).toHaveBeenCalledTimes(1)
  expect(download.mock.contexts[0].download).toBe('weza-payment-demo-transactions.csv')
  expect(revokeObjectURL).toHaveBeenCalledWith('blob:payments-test')
  expect(container.querySelector('[role="status"]').textContent).toBe(
    'Demo transaction CSV exported.',
  )

  const blob = createObjectURL.mock.calls[0][0]
  const csv = await readBlob(blob)
  const lines = csv.split('\n')
  expect(lines).toHaveLength(2)
  expect(lines[0]).toContain('"Payment Status","Provisioning Status"')
  expect(lines[1]).toContain('"PAY-00618","Esther Njeri"')
  expect(lines[1]).toContain('"Failed","Not started"')
})