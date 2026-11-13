import { useEffect, useState } from 'react'
import '../styles/dashboard.css'
import Sidebar from '../components/navigation/Sidebar.jsx'
import Header from '../components/navigation/Header.jsx'

export default function DashboardLayout({ children, operator }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

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
        />

        <main className="dashboard-content">
          {children}
        </main>
      </div>
    </div>
  )
}
