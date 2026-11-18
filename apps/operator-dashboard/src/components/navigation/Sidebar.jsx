const navigationItems = [
  { id: 'overview', label: 'Overview', icon: 'dashboard', enabled: true },
  { id: 'customers', label: 'Customers', icon: 'group', enabled: true },
  { id: 'packages', label: 'Packages', icon: 'inventory_2', enabled: true },
  { id: 'payments', label: 'Payments', icon: 'payments' },
  { id: 'sessions', label: 'Sessions', icon: 'wifi' },
  { id: 'connection-issues', label: 'Connection Issues', icon: 'warning', badge: '3' },
  { id: 'network-devices', label: 'Network & Devices', icon: 'router' },
  { id: 'settings', label: 'Settings', icon: 'settings' },
]

export default function Sidebar({ mobileMenuOpen, onClose, operator, activePage = 'overview', onNavigate = () => {} }) {
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
          <button
            key={item.label}
            type="button"
            className={`navigation-item ${activePage === item.id ? 'active' : ''}`}
            aria-current={activePage === item.id ? 'page' : undefined}
            onClick={item.enabled ? () => {
              onNavigate(item.id)
              onClose()
            } : undefined}
            disabled={!item.enabled}
            title={item.enabled ? undefined : "Available in a future release"}
          >
            <span className="material-symbols-outlined">
              {item.icon}
            </span>

            <span className="navigation-text">{item.label}</span>

            {item.badge && (
              <span className="navigation-badge">{item.badge}</span>
            )}
          </button>
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
