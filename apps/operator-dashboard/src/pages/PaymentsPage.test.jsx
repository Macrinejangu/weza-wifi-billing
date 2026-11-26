// @vitest-environment jsdom

import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { expect, test, vi } from 'vitest'
import PaymentsPage from './PaymentsPage.jsx'

test('shows separate payment and access states on the staff list and details', async () => {
  const container = document.createElement('div')
  document.body.append(container)
  const root = createRoot(container)
  const base = { amount: 20, phone_number: '254712345678', created_at: '2026-11-25T14:30:00Z' }
  const payments = [
    { ...base, id: 4, purchase_id: 14, status: 'successful', access_status: 'active', session_id: 24 },
    { ...base, id: 3, purchase_id: 13, status: 'successful', access_status: 'activating', session_id: null },
    { ...base, id: 2, purchase_id: 12, status: 'successful', access_status: 'failed', session_id: 22 },
    { ...base, id: 1, purchase_id: 11, status: 'pending', access_status: 'unconfirmed', session_id: null },
  ]
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
  vi.stubGlobal('fetch', vi.fn(async (url) => ({
    ok: true,
    json: async () => url.startsWith('/api/payments?') ? payments : payments[2],
  })))

  try {
    await act(async () => root.render(<PaymentsPage accessToken="staff-token" />))
    const rows = [...container.querySelectorAll('tbody tr')].map((row) =>
      [...row.querySelectorAll('.payment-status-pill')].map((pill) => pill.textContent),
    )
    expect(rows).toEqual([
      ['Confirmed', 'Active'], ['Confirmed', 'Awaiting activation'],
      ['Confirmed', 'Activation Failed'], ['Pending', 'Not Requested'],
    ])
    await act(async () => container.querySelector('[aria-label="Inspect payment 2"]').click())
    const details = container.querySelector('[role="dialog"]')
    expect(details.textContent).toContain('Payment statusConfirmed')
    expect(details.textContent).toContain('Internet accessActivation Failed')
    expect(details.textContent).toContain('Session ID22')
    expect(container.textContent).not.toContain('Manual STK')
  } finally {
    act(() => root.unmount())
    container.remove()
    vi.unstubAllGlobals()
  }
})
