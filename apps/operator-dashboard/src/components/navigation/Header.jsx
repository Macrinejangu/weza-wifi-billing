export default function Header({
  onMenuClick,
  mobileMenuOpen,
  operator,
  onOpenProfile,
  profileActive,
  live = false,
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
          <span className="connection-label">{live ? 'Staff workspace' : 'Demo Environment'}</span>
          {!live && (
            <>
              <span className="connection-divider">/</span>
              <span className="cluster-name">Cluster KE-NBO-01</span>
            </>
          )}
        </div>
      </div>

      {live ? (
        <div className="header-actions">
          <button type="button" className="header-user header-profile-button" aria-label="Open My Profile and Security" aria-current={profileActive ? 'page' : undefined} onClick={onOpenProfile}>
            <span className="operator-avatar" aria-hidden="true">{operator.initials}</span>
            <span>{operator.displayName}</span>
          </button>
        </div>
      ) : (
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

          <button type="button" className="header-user header-profile-button" aria-label="Open My Profile and Security" aria-current={profileActive ? 'page' : undefined} onClick={onOpenProfile}>
            <span className="operator-avatar" aria-hidden="true">{operator.initials}</span>
            <span>{operator.displayName}</span>
          </button>
        </div>
      )}
    </header>
  )
}
