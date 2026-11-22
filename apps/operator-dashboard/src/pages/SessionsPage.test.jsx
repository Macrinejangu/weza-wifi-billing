// @vitest-environment jsdom

import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import SessionsPage from './SessionsPage.jsx'

let container
let root

beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
  container = document.createElement('div')
  document.body.append(container)
  root = createRoot(container)
  act(() => root.render(<SessionsPage />))
})

afterEach(() => {
  act(() => root.unmount())
  container.remove()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

function button(label, scope = container) {
  const result = [...scope.querySelectorAll('button')].find(
    (candidate) => (candidate.getAttribute('aria-label') ?? candidate.textContent.trim()) === label,
  )
  expect(result, `Expected button "${label}"`).toBeDefined()
  return result
}

function click(element) {
  act(() => element.click())
}

function searchFor(value) {
  const input = container.querySelector('input[type="search"]')
  const setValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
  act(() => {
    setValue.call(input, value)
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })
}

function visibleSubscribers() {
  return [...container.querySelectorAll('.sessions-table tbody th[scope="row"] strong')].map(
    (name) => name.textContent,
  )
}

function pressKey(element, key, shiftKey = false) {
  const event = new KeyboardEvent('keydown', {
    key,
    shiftKey,
    bubbles: true,
    cancelable: true,
  })
  act(() => element.dispatchEvent(event))
  return event
}

function readBlob(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => reject(reader.error)
    reader.readAsText(blob)
  })
}

test('searches by IP and reports when no session matches', () => {
  searchFor(' 10.140.22.8 ')
  expect(visibleSubscribers()).toEqual(['Amina Wanjiku'])

  searchFor('no matching subscriber')
  expect(visibleSubscribers()).toEqual([])
  expect(container.textContent).toContain('No matching demo sessions')
})

function selectOption(select, value) {
  act(() => {
    select.value = value
    select.dispatchEvent(new Event('change', { bubbles: true }))
  })
}

function packageTypeFilter() {
  return container.querySelector('select[aria-label="Filter sessions by package type"]')
}

test('combines search, status, package type, and access point, then clears them', () => {
  const packageType = packageTypeFilter()
  const accessPoint = container.querySelector('#session-node-filter')

  selectOption(packageType, 'Monthly / SME')
  expect(visibleSubscribers()).toEqual(['David Kipchirchir'])

  selectOption(accessPoint, 'Nairobi Central AP-01')
  expect(visibleSubscribers()).toEqual([])

  selectOption(packageType, 'Voucher')
  expect(visibleSubscribers()).toEqual(['Amina Wanjiku'])

  click(button('Expiring'))
  expect(button('Expiring').getAttribute('aria-pressed')).toBe('true')
  expect(visibleSubscribers()).toEqual([])

  click(button('Active'))
  expect(visibleSubscribers()).toEqual(['Amina Wanjiku'])

  searchFor('John')
  expect(visibleSubscribers()).toEqual([])

  click(container.querySelector('button[aria-controls="sessions-filter-actions"]'))
  click(button('Clear filters'))
  expect(accessPoint.value).toBe('All')
  expect(packageType.value).toBe('All')
  expect(container.querySelector('input[type="search"]').value).toBe('')
  expect(button('All').getAttribute('aria-pressed')).toBe('true')
  expect(visibleSubscribers()).toEqual([
    'Amina Wanjiku',
    'John Kariuki',
    'Brenda Mutua',
    'David Kipchirchir',
    'Esther Kemboi',
  ])
})

test('focuses the drawer, wraps Tab, and restores focus after Escape or Close', () => {
  const opener = button('Inspect session for John Kariuki')

  click(opener)
  const dialog = container.querySelector('[role="dialog"]')
  const closeIcon = button('Close session details', dialog)
  const closeFooter = button('Close details', dialog)

  expect(dialog.textContent).toContain('John Kariuki')
  expect(dialog.textContent).toContain('SES-DEMO-002')
  expect(document.activeElement).toBe(closeIcon)

  expect(pressKey(closeIcon, 'Tab', true).defaultPrevented).toBe(true)
  expect(document.activeElement).toBe(closeFooter)
  expect(pressKey(closeFooter, 'Tab').defaultPrevented).toBe(true)
  expect(document.activeElement).toBe(closeIcon)

  pressKey(closeIcon, 'Escape')
  expect(container.querySelector('[role="dialog"]')).toBeNull()
  expect(document.activeElement).toBe(opener)

  click(opener)
  click(button('Close details', container.querySelector('[role="dialog"]')))
  expect(container.querySelector('[role="dialog"]')).toBeNull()
  expect(document.activeElement).toBe(opener)
})

test('exports only matching rows to the demo CSV', async () => {
  const objectUrl = 'blob:weza-session-test'
  const createObjectURL = vi.fn(() => objectUrl)
  const revokeObjectURL = vi.fn()
  const BrowserURL = window.URL

  vi.stubGlobal('URL', class extends BrowserURL {
    static createObjectURL = createObjectURL
    static revokeObjectURL = revokeObjectURL
  })

  let download
  const anchorClick = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () {
    download = { filename: this.download, href: this.href }
  })

  selectOption(packageTypeFilter(), 'Monthly / SME')
  click(container.querySelector('.session-export-button'))

  expect(createObjectURL).toHaveBeenCalledTimes(1)
  expect(anchorClick).toHaveBeenCalledTimes(1)
  expect(download).toEqual({
    filename: 'weza-session-demo-records.csv',
    href: objectUrl,
  })
  expect(revokeObjectURL).toHaveBeenCalledWith(objectUrl)

  const [blob] = createObjectURL.mock.calls[0]
  expect(blob.type).toBe('text/csv;charset=utf-8;')
  const rows = (await readBlob(blob)).split('\n')
  expect(rows).toHaveLength(2)
  expect(rows[0]).toContain('"Session ID","Customer"')
  expect(rows[0]).toContain('"Connection Status","Sample Expiry"')
  expect(rows[1]).toContain('"SES-DEMO-004","David Kipchirchir"')
  expect(container.querySelector('[role="status"]').textContent).toContain('Exported 1')
})
