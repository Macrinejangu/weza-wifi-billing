import { renderToStaticMarkup } from 'react-dom/server'
import { expect, test, vi } from 'vitest'
import App from './App.jsx'
import DashboardLayout from './layouts/DashboardLayout.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import CustomersPage from './pages/CustomersPage.jsx'
import PackagesPage from './pages/PackagesPage.jsx'
import PaymentsPage from './pages/PaymentsPage.jsx'
import ConnectionIssuesPage from './pages/ConnectionIssuesPage.jsx'
import ActivityHistoryPage from './pages/ActivityHistoryPage.jsx'
import SystemSettingsPage from './pages/SystemSettingsPage.jsx'
import NetworkDevicesPage from './pages/NetworkDevicesPage.jsx'
import SessionsPage from './pages/SessionsPage.jsx'
import { developmentOperator } from './operatorIdentity.js'

vi.hoisted(() => {
  vi.stubEnv('DEV', true)
  vi.stubEnv('VITE_USE_DEMO_DATA', 'true')
})

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

test('renders enabled dashboard destinations', () => {
  const html = renderToStaticMarkup(
    <DashboardLayout operator={developmentOperator}>
      <DashboardPage operator={developmentOperator} />
    </DashboardLayout>
  )
  const navigation = html.match(/<nav[^>]*>[\s\S]*?<\/nav>/)?.[0] ?? ''

  expect(navigation).toContain('aria-current="page"')
  expect(navigation).toContain('Customers')
  expect(navigation).toContain('Settings')
  expect(navigation).not.toContain('disabled=""')
  expect(navigation).not.toContain('href="#"')
})


test('renders the customer directory with illustrative summary data', () => {
  const html = renderToStaticMarkup(<CustomersPage />)

  expect(html).toContain('Customers')
  expect(html).toContain('Total Registered')
  expect(html).toContain('<strong>10</strong>')
  expect(html).toContain('Active Online')
  expect(html).toContain('<strong>4</strong>')
  expect(html).toContain('Suspended / Inactive')
  expect(html).toContain('<strong>2</strong>')
  expect((html.match(/scope="col"/g) ?? []).length).toBe(7)
  expect((html.match(/scope="row"/g) ?? []).length).toBe(7)
  expect(html).toContain('Illustrative demo data')
  expect(html).toContain('Amina Wanjiku')
  expect(html).toContain('Dennis Kiprono')
  expect(html).toContain('Faith Mwangi')
  expect(html).toContain('Brian Otieno')
  expect(html).toContain('Esther Njeri')
  expect(html).toContain('Grace Achieng')
  expect(html).not.toContain('Samuel Kariuki')
})

test('renders customer search, status filters, registration and pagination controls', () => {
  const html = renderToStaticMarkup(<CustomersPage />)

  expect(html).toContain('Search customers')
  expect(html).toContain('Search name, phone or customer ID')
  expect(html).toContain('aria-label="Filter customers by status"')
  expect(html).toContain('aria-pressed="true"')
  expect(html).toContain('Active')
  expect(html).toContain('Expired')
  expect(html).toContain('Flagged')
  expect(html).toContain('Register customer')
  expect(html).toContain('View profile for Amina Wanjiku')
  expect(html).toContain('Filter by package')
  expect(html).toContain('Showing 1–7 of 10 sample records')
  expect(html).toContain('aria-label="Previous page"')
  expect(html).toContain('aria-label="Next page"')
  expect(html).toContain('1 / 2')
})


test('renders the six demo internet packages', () => {
  const html = renderToStaticMarkup(<PackagesPage />)

  expect(html).toContain('>Packages</h1>')
  expect(html).toContain('Quick Connect')
  expect(html).toContain('Daily Connect')
  expect(html).toContain('Weekly Plus')
  expect(html).toContain('Monthly Max')
  expect(html).toContain('Night Owl 12h')
  expect(html).toContain('Unlimited 24h')
  expect(html).toContain('Add Package')
  expect(html).toContain('Demo data')
})

test('renders package status and type filters with counts derived from the demo rows', () => {
  const html = renderToStaticMarkup(<PackagesPage />)

  expect(html).toContain('Filter packages by status')
  expect(html).toContain('Filter packages by type')
  expect(html).toContain('All (6)')
  expect(html).toContain('Active (5)')
  expect(html).toContain('Inactive (1)')
  expect(html).toContain('Hotspot Captive')
  expect(html).toContain('Home Fiber')
})

test('renders active session monitoring with illustrative KPI data', () => {
  const html = renderToStaticMarkup(<SessionsPage />)

  expect(html).toContain('Active Sessions')
  expect(html).toContain('DEMO MODE')
  expect(html).toContain('NOT CONNECTED')
  expect(html).toContain('Expiring Soon')
  expect(html).toContain('Failed Activations')
  expect(html).toContain('<strong>1,248</strong>')
  expect(html).toContain('<strong>18</strong>')
  expect(html).toContain('<strong>2</strong>')
  expect(html).toContain('Amina Wanjiku')
  expect(html).toContain('John Kariuki')
  expect(html).toContain('Brenda Mutua')
  expect(html).toContain('David Kipchirchir')
  expect(html).toContain('Esther Kemboi')
  expect(html).toContain('Illustrative')
})

test('renders session search, filters and inspection controls', () => {
  const html = renderToStaticMarkup(<SessionsPage />)

  expect(html).toContain('Search sessions')
  expect(html).toContain('Voucher')
  expect(html).toContain('Monthly / SME')
  expect(html).toContain('Active Authentications')
  expect(html).toContain('Connection status')
  expect(html).toContain('Expiry time')
  expect(html).toContain('Fixed snapshot')
  expect(html).toContain('aria-label="Inspect session for Amina Wanjiku"')
  expect(html).toContain('Page 1 of 1')
})


test('renders the Payments preview with separate settlement and access statuses', () => {
  const html = renderToStaticMarkup(<PaymentsPage />)

  expect(html).toContain('KES 142,850')
  expect(html).toContain('Demo data')
  expect(html).toContain('Search payments')
  expect(html).toContain('Filter payments by package')

  const transaction = html.match(/<tr><th[^>]*>RJ92MN38X2<\/th>[\s\S]*?<\/tr>/)?.[0]
  expect(transaction).toContain('Confirmed')
  expect(transaction).toContain('Activation Failed')
  expect(transaction).toContain('Inspect payment for Dennis Kiprono')
})


test('renders the demo incident list and opens the linked payment incident by ID', () => {
  const list = renderToStaticMarkup(<ConnectionIssuesPage />)
  const detail = renderToStaticMarkup(<ConnectionIssuesPage initialIssueId="ISS-4091" />)

  expect(list).toContain('Search connection issues')
  expect(list).toContain('ISS-4091')
  expect(detail).toContain('Router CoA Timeout')
  expect(detail).toContain('RJ92MN38X2')
  expect(detail).toContain('Activation Failed')
})


test('renders the demo equipment inventory and named device inspection controls', () => {
  const html = renderToStaticMarkup(<NetworkDevicesPage />)

  expect(html).toContain('Equipment Inventory')
  expect(html).toContain('Filter by sector')
  expect(html).toContain('Needs Attention First')
  expect(html).toContain('aria-label="View device AP-Westlands-02"')
})


test('renders the demo settings sections and local save control', () => {
  const html = renderToStaticMarkup(<SystemSettingsPage />)

  expect(html).toContain('General Preferences')
  expect(html).toContain('Integration Status')
  expect(html).toContain('Staff Access &amp; Operator Roles')
  expect(html).toContain('Save Changes')
})


test('renders the demo audit log with filters and named event inspection controls', () => {
  const html = renderToStaticMarkup(<ActivityHistoryPage />)

  expect(html).toContain('Activity &amp; Audit History')
  expect(html).toContain('Search audit history')
  expect(html).toContain('Inspect event EVT-89210')
  expect(html).toContain('Pending Router Response')
})
