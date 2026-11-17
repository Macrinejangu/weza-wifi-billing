
import { renderToStaticMarkup } from 'react-dom/server'
import { expect, test } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import App from './App.jsx'

test('renders the customer portal', () => {
  const html = renderToStaticMarkup(
    <MemoryRouter initialEntries={['/']}>
      <App />
    </MemoryRouter>
  )

  expect(html).toContain('Weza')
})
