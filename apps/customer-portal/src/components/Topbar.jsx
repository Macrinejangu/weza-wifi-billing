import Logo from "./Logo.jsx"

export default function Topbar() {
  return (
    <header className="topbar">
      <div className="topbar-mobile-logo">
        <Logo />
      </div>

      <div className="connection-status">
        <span className="status-dot"></span>
        Connected
      </div>
    </header>
  )
}