const navigationItems = [
  { label: 'Overview', icon: 'dashboard', active: true },
  { label: 'Customers', icon: 'group' },
  { label: 'Packages', icon: 'inventory_2' },
  { label: 'Payments', icon: 'payments' },
  { label: 'Sessions', icon: 'wifi' },
  { label: 'Connection Issues', icon: 'warning', badge: '3' },
  { label: 'Network & Devices', icon: 'router' },
  { label: 'Settings', icon: 'settings' },
]

export default function Sidebar({ mobileMenuOpen, onClose, operator }) {
  return (
    <aside
      id="operator-sidebar"
      className={`sidebar ${mobileMenuOpen ? 'is-open' : ''}`}
    >
      <div className="sidebar-brand">
        <div className="brand-mark">W</div>
        <div>
          <h1>Weza</h1>
          <p>Operator Console</p>
        </div>
        <span className="version-badge">v2.4</span>
      </div>

      <nav className="sidebar-navigation" aria-label="Main navigation">
        <p className="navigation-label">WORKSPACE</p>

        {navigationItems.map((item) => (
          <a
            key={item.label}
            href="#"
            className={`navigation-item ${item.active ? 'active' : ''}`}
            aria-current={item.active ? 'page' : undefined}
            onClick={onClose}
          >
            <span className="material-symbols-outlined">
              {item.icon}
            </span>

            <span className="navigation-text">{item.label}</span>

            {item.badge && (
              <span className="navigation-badge">{item.badge}</span>
            )}
          </a>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <div className="support-card">
          <span className="material-symbols-outlined">support_agent</span>
          <div>
            <strong>Operational Support</strong>
            <p>Available 24/7</p>
          </div>
        </div>

        <div className="operator-profile">
          <div className="operator-avatar">{operator.initials}</div>
          <div className="operator-details">
            <strong>{operator.fullName}</strong>
            <p>{operator.role}</p>
          </div>
          <button className="icon-button" aria-label="Sign out">
            <span className="material-symbols-outlined">logout</span>
          </button>
        </div>
      </div>
    </aside>
  )
}
