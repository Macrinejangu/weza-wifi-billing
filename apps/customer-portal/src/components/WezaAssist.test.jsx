// @vitest-environment jsdom
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { expect, test, vi } from 'vitest'
import WezaAssist from './WezaAssist.jsx'

test('opens the independent assistant and offers verified contact links after a handoff', async () => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
  const request = vi.fn(async () => ({
    ok: true,
    json: async () => ({ answer: 'Please contact Weza Support.', sources: [], handoff: true }),
  }))
  vi.stubGlobal('fetch', request)
  const container = document.body.appendChild(document.createElement('div'))
  const root = createRoot(container)
  try {
    await act(async () => root.render(<WezaAssist />))
    await act(async () => container.querySelector('[aria-label="Open Weza Assist chat"]').click())
    const input = container.querySelector('input')
    expect(document.activeElement).toBe(input)
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
      setter.call(input, 'I need support')
      input.dispatchEvent(new Event('input', { bubbles: true }))
    })
    await act(async () => container.querySelector('[aria-label="Send message"]').click())
    expect(request).toHaveBeenCalledWith('/api/support/assist', expect.objectContaining({ method: 'POST' }))
    expect([...container.querySelectorAll('[role="log"] a')].map((link) => link.getAttribute('href'))).toEqual([
      'mailto:support@wezawifi.co.ke', 'tel:+254710268735', 'https://wa.me/254710268735',
    ])
  } finally {
    act(() => root.unmount())
    container.remove()
    vi.unstubAllGlobals()
  }
})
