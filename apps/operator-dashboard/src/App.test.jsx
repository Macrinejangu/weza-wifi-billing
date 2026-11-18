import { renderToStaticMarkup } from 'react-dom/server'
import { expect, test } from 'vitest'
import App from './App.jsx'
import DashboardLayout from './layouts/DashboardLayout.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import CustomersPage from './pages/CustomersPage.jsx'
import PackagesPage from './pages/PackagesPage.jsx'
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

test('disables navigation destinations that are not implemented', () => {
  const html = renderToStaticMarkup(
    <DashboardLayout operator={developmentOperator}>
      <DashboardPage operator={developmentOperator} />
    </DashboardLayout>
  )
  const navigation = html.match(/<nav[^>]*>[\s\S]*?<\/nav>/)?.[0] ?? ''

  expect(navigation).toContain('aria-current="page"')
  expect(navigation).toContain('Customers')
  expect((navigation.match(/disabled=""/g) ?? []).length).toBe(5)
  expect(navigation).not.toContain('href="#"')
})


test('renders the customer directory with illustrative summary data', () => {
  const html = renderToStaticMarkup(<CustomersPage />)

  expect(html).toContain('Customers')
  expect(html).toContain('1,842')
  expect(html).toContain('1,429')
  expect(html).toContain('341')
  expect(html).toContain('72')
  expect(html).toContain('94.2%')
  expect(html).toContain('Illustrative demo data')
  expect(html).toContain('Amina Wanjiku')
  expect(html).toContain('Dennis Kiprono')
  expect(html).toContain('Faith Mwangi')
  expect(html).toContain('Brian Otieno')
  expect(html).toContain('Esther Njeri')
  expect(html).not.toContain('Kevin Mutua')
})

test('renders customer search, status filters, registration and pagination controls', () => {
  const html = renderToStaticMarkup(<CustomersPage />)

  expect(html).toContain('Search customers')
  expect(html).toContain('Search by name, phone number or customer ID')
  expect(html).toContain('aria-label="Filter customers by status"')
  expect(html).toContain('aria-pressed="true"')
  expect(html).toContain('Active')
  expect(html).toContain('Expired')
  expect(html).toContain('Flagged')
  expect(html).toContain('Add customer')
  expect(html).toContain('View profile')
  expect(html).toContain('Showing 1–5 of 10 sample records')
  expect(html).toContain('aria-label="Previous page"')
  expect(html).toContain('aria-label="Next page"')
  expect(html).toContain('1 / 2')
})


test('renders the five supplied internet packages', () => {
  const html = renderToStaticMarkup(<PackagesPage />)

  expect(html).toContain('Internet Packages')
  expect(html).toContain('1-Hour Quick Connect')
  expect(html).toContain('24-Hour Day Pass')
  expect(html).toContain('Weekly Plus 10GB')
  expect(html).toContain('Monthly FastTrack 50GB')
  expect(html).toContain('Night Owl Unlimited')
  expect(html).toContain('KES 900')
  expect(html).toContain('New Package')
  expect(html).toContain('Illustrative package data')
})

test('renders package filters with the correct category counts', () => {
  const html = renderToStaticMarkup(<PackagesPage />)

  expect(html).toContain('All Tiers')
  expect(html).toContain('Hourly / Passes')
  expect(html).toContain('Weekly / Monthly')
  expect(html).toContain('aria-label="Filter packages"')
  expect(html).toContain('>5</span>')
  expect(html).toContain('>3</span>')
  expect(html).toContain('>2</span>')
})
