import { useEffect, useState } from 'react'
import '../styles/dashboard.css'
import Sidebar from '../components/navigation/Sidebar.jsx'
import Header from '../components/navigation/Header.jsx'

export default function DashboardLayout({ children, operator, activePage = 'overview', onNavigate = () => {}, onSignOut }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  // Allow the mobile navigation drawer to close with the Escape key.
  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        setMobileMenuOpen(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  return (
    <div className="dashboard-layout">
      <Sidebar
        operator={operator}
        mobileMenuOpen={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
        activePage={activePage}
        onNavigate={onNavigate}
        onSignOut={onSignOut}
      />

      {mobileMenuOpen && (
        <button
          className="mobile-menu-backdrop"
          aria-label="Close navigation menu"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      <div className="dashboard-main">
        <Header
          operator={operator}
          onMenuClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          mobileMenuOpen={mobileMenuOpen}
          onOpenProfile={() => onNavigate('staff-profile')}
          live={Boolean(onSignOut)}
          profileActive={activePage === 'staff-profile'}
        />

        <main className="dashboard-content">
          {children}
        </main>
      </div>
    </div>
  )
}
