import { renderToStaticMarkup } from 'react-dom/server'
import { afterEach, expect, test, vi } from 'vitest'
import App from './App.jsx'

vi.hoisted(() => {
  vi.stubEnv('DEV', true)
  vi.stubEnv('VITE_USE_DEMO_DATA', undefined)
})

test('keeps the staff preview disabled by default', () => {
  const html = renderToStaticMarkup(<App />)

  expect(html).toContain('Staff sign-in is currently unavailable.')
  expect(html).not.toContain('Preview Dashboard')
  expect(html).not.toContain('Moses Lenkai')
})

afterEach(() => {
  vi.unstubAllEnvs()
})

test.each([
  [true, '', false],
  [true, 'false', false],
  [true, 'TRUE', false],
  [false, 'true', false],
  [true, 'true', true],
])('enforces the shared demo flag (DEV=%s, flag=%s)', async (dev, flag, enabled) => {
  vi.resetModules()
  vi.stubEnv('DEV', dev)
  vi.stubEnv('VITE_USE_DEMO_DATA', flag)

  const { demoDataEnabled } = await import('../../shared/demoMode.js')
  expect(demoDataEnabled).toBe(enabled)
})
