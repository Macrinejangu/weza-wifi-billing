

import { Headset, ArrowUpRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import Logo from './Logo.jsx'
import { NavigationLinks } from './Navigations'

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <Logo />

      <p className="sidebar-label">CUSTOMER PORTAL</p>

      <NavigationLinks />

      <div className="support-card">
        <div className="support-icon">
          <Headset size={21} />
        </div>

        <h3>A little help?</h3>

        <p>
          We're here to keep you connected.
          Reach out whenever you need us.
        </p>

        <Link to="/support" className="support-button">
          Get support <ArrowUpRight size={15} />
        </Link>
      </div>

      <div className="sidebar-customer">
        <div className="customer-avatar">EM</div>

        <div>
          <h4>Customer</h4>
          <p>WEZA member</p>
        </div>
      </div>
    </aside>
  )
}
