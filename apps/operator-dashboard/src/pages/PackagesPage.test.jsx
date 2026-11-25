// @vitest-environment jsdom
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import App from '../App.jsx'
import PackagesPage from './PackagesPage.jsx'
import SupportFaqSettings from './SupportFaqSettings.jsx'

vi.hoisted(() => {
  vi.stubEnv('DEV', true)
  vi.stubEnv('VITE_USE_DEMO_DATA', 'true')
})

let root
let container

beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
  // jsdom does not implement the native modal lifecycle.
  if (!HTMLDialogElement.prototype.showModal) {
    HTMLDialogElement.prototype.showModal = function () { this.open = true }
    HTMLDialogElement.prototype.close = function () { this.open = false }
  }
  container = document.createElement('div')
  document.body.append(container)
  root = createRoot(container)
  act(() => root.render(<App />))
  click('Preview Dashboard (Development Only)')
  click('Packages')
})

afterEach(() => {
  act(() => root.unmount())
  container.remove()
  vi.unstubAllGlobals()
})

function click(label, scope = container) {
  const button = [...scope.querySelectorAll('button')].find((item) => {
    const copy = item.cloneNode(true)
    copy.querySelectorAll('[aria-hidden="true"]').forEach((node) => node.remove())
    return (item.getAttribute('aria-label') ?? copy.textContent.trim()) === label
  })
  expect(button, label).toBeDefined()
  act(() => button.click())
  return button
}

function enter(field, value) {
  act(() => {
    const setValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
    setValue.call(field, value)
    field.dispatchEvent(new Event('input', { bubbles: true }))
  })
}

function packageNames() {
  return [...container.querySelectorAll('.package-name strong')].map((heading) => heading.textContent)
}

test('combines name, ID, speed and price search with status and type filters', () => {
  expect(packageNames()).toHaveLength(6)
  const search = container.querySelector('.package-search input')

  enter(search, 'night owl')
  expect(packageNames()).toEqual(['Night Owl 12h'])
  enter(search, '  PKG-003  ')
  expect(packageNames()).toEqual(['Weekly Plus'])
  enter(search, '10 Mbps / 5 Mbps')
  expect(packageNames()).toEqual(['Weekly Plus', 'Monthly Max'])
  click('Home Fiber')
  expect(packageNames()).toEqual(['Monthly Max'])
  enter(search, '900')
  expect(packageNames()).toEqual(['Monthly Max'])
  const filter = click('Inactive (1)')
  expect(filter.getAttribute('aria-pressed')).toBe('true')
  expect(packageNames()).toEqual([])
  expect(container.textContent).toContain('No matching packages')
  click('All Types')
  enter(search, '')
  expect(packageNames()).toEqual(['Night Owl 12h'])
})

test('rejects invalid values and creates a package with trimmed text', () => {
  const trigger = click('Add Package')
  const dialog = container.querySelector('dialog')
  const name = dialog.querySelector('input')
  const price = dialog.querySelector('input[type="number"]')
  const [speed] = dialog.querySelectorAll('.package-form-grid input')
  expect(dialog.open).toBe(true)
  expect(document.activeElement).toBe(name)

  enter(name, '   ')
  enter(price, '-1')
  click('Create package', dialog)
  expect(price.validity.rangeUnderflow).toBe(true)
  enter(price, '2.5')
  click('Create package', dialog)
  expect(price.validity.stepMismatch).toBe(true)
  enter(price, '75')
  enter(speed, '   ')
  click('Create package', dialog)
  expect(name.validity.customError).toBe(true)
  expect(speed.validity.customError).toBe(true)
  expect(packageNames()).toHaveLength(6)

  enter(name, '  Weekend Pass  ')
  enter(speed, '  8 Mbps  ')
  click('Create package', dialog)
  expect(packageNames()).toContain('Weekend Pass')
  expect(container.querySelector('dialog')).toBeNull()
  expect(document.activeElement).toBe(trigger)
})

test('prefills edit fields, discards cancelled changes, and saves an edit in place', () => {
  const trigger = click('Edit package: Weekly Plus')
  let dialog = container.querySelector('dialog')
  expect(dialog.querySelector('input').value).toBe('Weekly Plus')
  enter(dialog.querySelector('input'), 'Unsaved name')
  click('Cancel', dialog)
  expect(document.activeElement).toBe(trigger)
  expect(packageNames()).toContain('Weekly Plus')

  click('Edit package: Weekly Plus')
  dialog = container.querySelector('dialog')
  expect(dialog.querySelector('input[type="number"]').value).toBe('250')
  enter(dialog.querySelector('input'), 'Weekly Plus Revised')
  click('Save changes', dialog)
  expect(packageNames()).toHaveLength(6)
  expect(packageNames()).toContain('Weekly Plus Revised')
  expect(document.activeElement).toBe(trigger)
})

test('dismisses the dialog on native Escape cancellation and restores focus', () => {
  const trigger = click('Add Package')
  const dialog = container.querySelector('dialog')
  act(() => dialog.dispatchEvent(new Event('cancel', { cancelable: true })))
  expect(container.querySelector('dialog')).toBeNull()
  expect(document.activeElement).toBe(trigger)
})

test('admins save live packages through the API and operators get read-only controls', async () => {
  const saved = {
    id: 7, name: 'Live pilot pass', service_type: 'hotspot', is_active: true, price: 20,
    duration_minutes: 60, download_speed_mbps: 5, upload_speed_mbps: 2, description: null,
  }
  const fetcher = vi.fn(async (url) => ({
    ok: true,
    json: async () => url === '/api/packages/staff' ? [] : saved,
  }))
  vi.stubGlobal('fetch', fetcher)
  await act(async () => root.render(<PackagesPage live accessToken="admin-token" canManage />))
  click('Add Package')
  const dialog = container.querySelector('dialog')
  enter(dialog.querySelector('[name="name"]'), saved.name)
  for (const name of ['price', 'duration_minutes', 'download_speed_mbps', 'upload_speed_mbps']) {
    enter(dialog.querySelector(`[name="${name}"]`), String(saved[name]))
  }
  await act(async () => dialog.querySelector('[type="submit"]').click())
  const { id, is_active: active, ...fields } = saved
  expect(fetcher).toHaveBeenCalledWith('/api/packages/', expect.objectContaining({
    method: 'POST',
    body: JSON.stringify({
      name: fields.name, service_type: fields.service_type, description: fields.description,
      price: fields.price, duration_minutes: fields.duration_minutes,
      download_speed_mbps: fields.download_speed_mbps, upload_speed_mbps: fields.upload_speed_mbps,
    }),
    headers: expect.objectContaining({ Authorization: 'Bearer admin-token' }),
  }))
  expect(id).toBe(7)
  expect(active).toBe(true)
  expect(packageNames()).toEqual(['Live pilot pass'])
  await act(async () => root.render(<PackagesPage live accessToken="operator-token" />))
  expect(click('Add Package').disabled).toBe(true)
})

test('saves a guided support answer under the staff account', async () => {
  const faq = { id: 1, question: 'Can I get help?', steps: ['Check Connection Status.'] }
  const fetcher = vi.fn(async (url) => ({
    ok: true, json: async () => url === '/api/support/faqs' ? [faq] : { ...faq, question: 'Paid but offline?' },
  }))
  vi.stubGlobal('fetch', fetcher)
  await act(async () => root.render(<SupportFaqSettings accessToken="admin-token" onSignOut={vi.fn()} />))
  enter(container.querySelector('input'), 'Paid but offline?')
  await act(async () => container.querySelector('button[type="submit"]').click())
  expect(fetcher).toHaveBeenCalledWith('/api/support/faqs/1', expect.objectContaining({
    method: 'PUT',
    body: JSON.stringify({ question: 'Paid but offline?', steps: faq.steps }),
  }))
  expect(container.textContent).toContain('Support answer saved.')
})
