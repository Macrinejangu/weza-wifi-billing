
import { Outlet } from 'react-router-dom'
import Sidebar from '../Sidebar'
import Topbar from '../Topbar'
import { NavigationLinks } from './Navigation'

export default function CustomerLayout() {
  return (
    <div className="customer-layout">
      <Sidebar />

      <main className="main-content">
        <Topbar />

        <div className="mobile-navigation-wrapper">
          <NavigationLinks mobile />
        </div>

        <div className="page-container">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

