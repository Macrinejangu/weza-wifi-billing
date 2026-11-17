export default function Header({
  onMenuClick,
  mobileMenuOpen,
  operator,
}) {
  return (
    <header className="dashboard-header">
      <div className="header-leading">
        <button
          className="icon-button mobile-menu-button"
          aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
          aria-controls="operator-sidebar"
          aria-expanded={mobileMenuOpen}
          onClick={onMenuClick}
        >
          <span className="material-symbols-outlined">
            {mobileMenuOpen ? 'close' : 'menu'}
          </span>
        </button>

        <div className="connection-status">
          <span className="connection-dot" />
          <span className="connection-label">Demo Environment</span>
          <span className="connection-divider">/</span>
          <span className="cluster-name">Cluster KE-NBO-01</span>
        </div>
      </div>

      <div className="header-actions">
        <label className="search-box">
          <span className="material-symbols-outlined">search</span>
          <input
            type="search"
            placeholder="Search unavailable in preview"
            aria-label="Search unavailable in preview"
            disabled
          />
          <span className="search-shortcut">⌘ K</span>
        </label>

        <button
          className="icon-button notification-button"
          aria-label="Notifications unavailable in preview"
          title="Notifications unavailable in preview"
          disabled
        >
          <span className="material-symbols-outlined">notifications</span>
        </button>

        <div className="header-user">
          <div className="operator-avatar">{operator.initials}</div>
          <span>{operator.displayName}</span>
        </div>
      </div>
    </header>
  )
}
