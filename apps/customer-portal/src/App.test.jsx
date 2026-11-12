import { renderToStaticMarkup } from 'react-dom/server'
import { expect, test } from 'vitest'
import App from './App.jsx'

test('renders the starter page heading', () => {
  expect(renderToStaticMarkup(<App />)).toContain('<h1>Weza Customer Portal</h1>')
})
