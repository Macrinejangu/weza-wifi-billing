import { renderToStaticMarkup } from 'react-dom/server'
import { expect, test } from 'vitest'
import App from './App.jsx'
import DashboardLayout from './layouts/DashboardLayout.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import { developmentOperator } from './operatorIdentity.js'

test('renders the operator dashboard shell', () => {
  const html = renderToStaticMarkup(<DashboardLayout operator={developmentOperator}><DashboardPage operator={developmentOperator} /></DashboardLayout>)

  expect(html).toContain('Weza')
  expect(html).toContain('Operator Console')
  expect(html).toContain('Overview')
  expect(html).toContain('Customers')
  expect(html).toContain('Payments')
  expect(html).toContain('Network &amp; Devices')
})

test('renders operator and cluster information', () => {
  const html = renderToStaticMarkup(<DashboardLayout operator={developmentOperator}><DashboardPage operator={developmentOperator} /></DashboardLayout>)

  expect(html).toContain('Moses Lenkai')
  expect(html).toContain('Good morning, Moses.')
  expect(html).toContain('Network Lead')
  expect(html).toContain('Cluster KE-NBO-01')
  expect(html).toContain('Demo environment')
  expect(html).toContain('DEMONSTRATION DASHBOARD')
})

test('renders the four KPI cards with demo data', () => {
  const html = renderToStaticMarkup(<DashboardLayout operator={developmentOperator}><DashboardPage operator={developmentOperator} /></DashboardLayout>)

  expect(html).toContain('Network &amp; Billing Overview')
  expect(html).toContain('DEMO DATA')
  expect(html).toContain('KES 142,850')
  expect(html).toContain('1,248')
  expect(html).toContain('Awaiting M-Pesa callback')
  expect(html).toContain('Paid subscribers awaiting access')
})

test('renders the activity chart and its metric controls', () => {
  const html = renderToStaticMarkup(<DashboardLayout operator={developmentOperator}><DashboardPage operator={developmentOperator} /></DashboardLayout>)

  expect(html).toContain('Revenue &amp; Session Activity')
  expect(html).toContain('Revenue (KES)')
  expect(html).toContain('Active Sessions')
  expect(html).toContain('Last 7 Days')
  expect(html).toContain('Illustrative figures only')
})

test('renders operational issues with their priority levels', () => {
  const html = renderToStaticMarkup(<DashboardLayout operator={developmentOperator}><DashboardPage operator={developmentOperator} /></DashboardLayout>)

  expect(html).toContain('Requires Attention')
  expect(html).toContain('ISS-4091')
  expect(html).toContain('Router CoA Timeout')
  expect(html).toContain('ISS-4088')
  expect(html).toContain('Activation Pending')
  expect(html).toContain('ISS-4085')
  expect(html).toContain('Telco Delay')
  expect(html).toContain('High')
  expect(html).toContain('Medium')
  expect(html).toContain('Low')
})

test('renders recent payments with separate payment and activation statuses', () => {
  const html = renderToStaticMarkup(<DashboardLayout operator={developmentOperator}><DashboardPage operator={developmentOperator} /></DashboardLayout>)

  expect(html).toContain('Recent Payments')
  expect(html).toContain('Amina Wanjiku')
  expect(html).toContain('Dennis Kiprono')
  expect(html).toContain('Faith Muthoni')
  expect(html).toContain('Kevin Ombati')
  expect(html).toContain('Lilian Cherotich')
  expect(html).toContain('RJ92MN41P0')
  expect(html).toContain('STK_PEND_884')
  expect(html).toContain('Activation Failed')
  expect(html).toContain('Activation Pending')
  expect(html).toContain('Illustrative transactions only')
})


test('shows the staff login page by default', () => {
  const html = renderToStaticMarkup(<App />)

  expect(html).toContain('Staff Login')
  expect(html).toContain('Staff Phone Number or ID')
  expect(html).toContain('Sign In')
  expect(html).toContain('Forgot Password or Need Access?')
})

test('provides a development-only dashboard preview link', () => {
  const html = renderToStaticMarkup(<App />)

  expect(html).toContain('Preview Dashboard (Development Only)')
  expect(html).toContain('Forgot Password or Need Access?')
})

test('provides an accessible control for opening NOC support', () => {
  const html = renderToStaticMarkup(<App />)

  expect(html).toContain('Forgot Password or Need Access?')
  expect(html).toContain('type="button"')
})
