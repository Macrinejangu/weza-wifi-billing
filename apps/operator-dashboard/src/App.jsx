import { useState } from 'react'
import DashboardLayout from './layouts/DashboardLayout.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import CustomersPage from './pages/CustomersPage.jsx'
import PackagesPage from './pages/PackagesPage.jsx'
import PaymentsPage from './pages/PaymentsPage.jsx'
import ConnectionIssuesPage from './pages/ConnectionIssuesPage.jsx'
import SystemSettingsPage from './pages/SystemSettingsPage.jsx'
import NetworkDevicesPage from './pages/NetworkDevicesPage.jsx'
import SessionsPage from './pages/SessionsPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import { demoDataEnabled } from '../../shared/demoMode.js'
import { developmentOperator } from './operatorIdentity.js'

export default function App() {
  // This preview is for frontend review only; it does not create an authenticated session.
  const [showDashboardPreview, setShowDashboardPreview] = useState(false)
  const [activePage, setActivePage] = useState('overview')

  const [selectedIssueId, setSelectedIssueId] = useState(null)

  function navigate(page) {
    setSelectedIssueId(null)
    setActivePage(page)
  }

  function inspectIssue(issueId) {
    setSelectedIssueId(issueId)
    setActivePage('connection-issues')
  }

  if (demoDataEnabled && showDashboardPreview) {
    return (
      <DashboardLayout
        operator={developmentOperator}
        activePage={activePage}
        onNavigate={navigate}
      >
        {activePage === 'customers' ? (
          <CustomersPage />
        ) : activePage === 'packages' ? (
          <PackagesPage />
        ) : activePage === 'payments' ? (
          <PaymentsPage onInspectIssue={inspectIssue} />
        ) : activePage === 'sessions' ? (
          <SessionsPage />
        ) : activePage === 'connection-issues' ? (
          <ConnectionIssuesPage key={selectedIssueId ?? 'list'} initialIssueId={selectedIssueId} />
        ) : activePage === 'network-devices' ? (
          <NetworkDevicesPage />
        ) : activePage === 'settings' ? (
          <SystemSettingsPage />
        ) : (
          <DashboardPage operator={developmentOperator} />
        )}

        <div className="dashboard-preview-return">
          <button
            type="button"
            onClick={() => setShowDashboardPreview(false)}
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
      operator={demoDataEnabled ? developmentOperator : undefined}
      onPreviewDashboard={() => setShowDashboardPreview(true)}
    />
  )
}
