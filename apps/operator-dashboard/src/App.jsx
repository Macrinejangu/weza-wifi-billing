import { useCallback, useEffect, useState } from 'react'
import { getStaffProfile, signInStaff } from './api.js'
import DashboardLayout from './layouts/DashboardLayout.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import CustomersPage, { initialCustomers } from './pages/CustomersPage.jsx'
import CustomerProfilePage from './pages/CustomerProfilePage.jsx'
import PackagesPage from './pages/PackagesPage.jsx'
import PaymentsPage from './pages/PaymentsPage.jsx'
import ConnectionIssuesPage from './pages/ConnectionIssuesPage.jsx'
import ActivityHistoryPage from './pages/ActivityHistoryPage.jsx'
import SystemSettingsPage from './pages/SystemSettingsPage.jsx'
import NetworkDevicesPage from './pages/NetworkDevicesPage.jsx'
import SessionsPage from './pages/SessionsPage.jsx'
import StaffProfilePage from './pages/StaffProfilePage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import { demoDataEnabled } from '../../shared/demoMode.js'
import { developmentOperator } from './operatorIdentity.js'

function getTokenExpiry(accessToken) {
  try {
    const payload = accessToken.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const { exp } = JSON.parse(atob(payload))
    return Number.isFinite(exp) ? exp * 1000 : 0
  } catch {
    return 0
  }
}

export default function App() {
  const [staffSession, setStaffSession] = useState(null)
  const [staffPage, setStaffPage] = useState('payments')
  const expiresAt = staffSession?.expiresAt
  const signOut = useCallback(() => setStaffSession(null), [])

  useEffect(() => {
    if (!expiresAt) return undefined

    const timeout = window.setTimeout(signOut, Math.max(0, expiresAt - Date.now()))
    return () => window.clearTimeout(timeout)
  }, [expiresAt, signOut])

  async function handleSignIn(email, password) {
    const accessToken = await signInStaff(email, password)
    const staff = await getStaffProfile(accessToken)
    const expiry = getTokenExpiry(accessToken)

    if (expiry <= Date.now()) {
      throw new Error('Your staff session is unavailable. Please sign in again.')
    }

    setStaffPage('payments')
    setStaffSession({ accessToken, staff, expiresAt: expiry })
  }

  // This preview is for frontend review only; it does not create an authenticated session.
  const [showDashboardPreview, setShowDashboardPreview] = useState(false)
  const [activePage, setActivePage] = useState('overview')

  const [selectedIssueId, setSelectedIssueId] = useState(null)

  const [profile, setProfile] = useState(null)

  function navigate(page) {
    setProfile(null)
    setSelectedIssueId(null)
    setActivePage(page)
  }

  function openCustomerProfile(customer) {
    setProfile({ customer, from: 'customers' })
    setActivePage('customer-profile')
  }

  function openPaymentProfile(payment) {
    const phoneDigits = (phone) => phone.replace(/\D/g, '')
    const match = initialCustomers.find((customer) =>
      customer.name === payment.customer && phoneDigits(customer.phone) === phoneDigits(payment.phone),
    )
    const customer = match ?? { name: payment.customer, phone: payment.phone, plan: payment.package }
    setProfile({ customer: { ...customer, payment }, from: 'payments' })
    setActivePage('customer-profile')
  }

  function inspectIssue(issueId) {
    setSelectedIssueId(issueId)
    setActivePage('connection-issues')
  }

  function closePreview() {
    navigate('overview')
    setShowDashboardPreview(false)
  }

  if (staffSession) {
    const { staff, accessToken } = staffSession
    const names = staff.full_name.trim().split(/\s+/)
    const operator = {
      fullName: staff.full_name,
      displayName: names[0],
      initials: names.slice(0, 2).map((name) => name.charAt(0)).join('').toUpperCase(),
      role: staff.role === 'admin' ? 'Administrator' : 'Operator',
    }

    return (
      <DashboardLayout operator={operator} activePage={staffPage} onNavigate={setStaffPage} onSignOut={signOut}>
        {staffPage === 'overview' ? (
          <DashboardPage
            operator={operator}
            accessToken={accessToken}
            onSignOut={signOut}
            onOpenIssues={() => setStaffPage('connection-issues')}
          />
        ) : staffPage === 'sessions' ? (
          <SessionsPage accessToken={accessToken} onSignOut={signOut} />
        ) : staffPage === 'packages' ? (
          <PackagesPage live />
        ) : staffPage === 'customers' ? (
          <CustomersPage accessToken={accessToken} onSignOut={signOut} />
        ) : staffPage === 'network-devices' ? (
          <NetworkDevicesPage accessToken={accessToken} onSignOut={signOut} />
        ) : staffPage === 'connection-issues' ? (
          <ConnectionIssuesPage accessToken={accessToken} onSignOut={signOut} />
        ) : staffPage === 'staff-profile' ? (
          <StaffProfilePage operator={operator} staff={staff} onSignOut={signOut} />
        ) : (
          <PaymentsPage accessToken={accessToken} onSignOut={signOut} />
        )}
      </DashboardLayout>
    )
  }

  if (demoDataEnabled && showDashboardPreview) {
    return (
      <DashboardLayout
        operator={developmentOperator}
        activePage={activePage === 'audit-history' ? 'settings' : activePage === 'customer-profile' ? profile?.from : activePage}
        onNavigate={navigate}
      >
        {activePage === 'customers' ? (
          <CustomersPage onOpenProfile={openCustomerProfile} />
        ) : activePage === 'customer-profile' ? (
          <CustomerProfilePage
            customer={profile?.customer}
            backLabel={profile?.from === 'payments' ? 'Payments' : 'Customers Directory'}
            onBack={() => navigate(profile?.from ?? 'customers')}
          />
        ) : activePage === 'packages' ? (
          <PackagesPage />
        ) : activePage === 'payments' ? (
          <PaymentsPage onInspectIssue={inspectIssue} onOpenProfile={openPaymentProfile} />
        ) : activePage === 'sessions' ? (
          <SessionsPage />
        ) : activePage === 'connection-issues' ? (
          <ConnectionIssuesPage key={selectedIssueId ?? 'list'} initialIssueId={selectedIssueId} />
        ) : activePage === 'network-devices' ? (
          <NetworkDevicesPage />
        ) : activePage === 'settings' ? (
          <SystemSettingsPage onOpenAuditHistory={() => navigate('audit-history')} />
        ) : activePage === 'audit-history' ? (
          <ActivityHistoryPage onBack={() => navigate('settings')} onInspectIssue={inspectIssue} />
        ) : activePage === 'staff-profile' ? (
          <StaffProfilePage operator={developmentOperator} onSignOut={closePreview} />
        ) : (
          <DashboardPage operator={developmentOperator} />
        )}

        <div className="dashboard-preview-return">
          <button
            type="button"
            onClick={closePreview}
          >
            Return to Staff Login
          </button>
          <span>Demonstration preview only · No authentication performed</span>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <LoginPage
      onSignIn={handleSignIn}
      operator={demoDataEnabled ? developmentOperator : undefined}
      onPreviewDashboard={() => setShowDashboardPreview(true)}
    />
  )
}
