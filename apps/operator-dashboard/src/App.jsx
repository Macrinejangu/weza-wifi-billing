import { useState } from 'react'
import DashboardLayout from './layouts/DashboardLayout.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import CustomersPage from './pages/CustomersPage.jsx'
import PackagesPage from './pages/PackagesPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import { developmentOperator } from './operatorIdentity.js'

export default function App() {
  // This preview is for frontend review only; it does not create an authenticated session.
  const [showDashboardPreview, setShowDashboardPreview] = useState(false)
  const [activePage, setActivePage] = useState('overview')

  if (showDashboardPreview) {
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
      operator={developmentOperator}
      onPreviewDashboard={() => setShowDashboardPreview(true)}
    />
  )
}
