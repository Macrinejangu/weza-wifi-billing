import { useState } from 'react'
import DashboardLayout from './layouts/DashboardLayout.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import CustomersPage from './pages/CustomersPage.jsx'
import PackagesPage from './pages/PackagesPage.jsx'
import PaymentsPage from './pages/PaymentsPage.jsx'
import SessionsPage from './pages/SessionsPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import { demoDataEnabled } from '../../shared/demoMode.js'
import { developmentOperator } from './operatorIdentity.js'

export default function App() {
  // This preview is for frontend review only; it does not create an authenticated session.
  const [showDashboardPreview, setShowDashboardPreview] = useState(false)
  const [activePage, setActivePage] = useState('overview')

  if (demoDataEnabled && showDashboardPreview) {
    return (
      <DashboardLayout
        operator={developmentOperator}
        activePage={activePage}
        onNavigate={setActivePage}
      >
        {activePage === 'customers' ? (
          <CustomersPage />
        ) : activePage === 'packages' ? (
          <PackagesPage />
        ) : activePage === 'payments' ? (
          <PaymentsPage />
        ) : activePage === 'sessions' ? (
          <SessionsPage />
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
