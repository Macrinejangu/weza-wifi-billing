import { useEffect, useRef, useState } from 'react'
import '../styles/login.css'

export default function LoginPage({ onPreviewDashboard, operator }) {
  const [staffId, setStaffId] = useState('')
  const [password, setPassword] = useState('')
  const [passwordVisible, setPasswordVisible] = useState(false)
  const [supportOpen, setSupportOpen] = useState(false)
  const [message, setMessage] = useState('')

  // Keep references so keyboard focus can enter the dialog and return to its trigger.
  const supportTriggerRef = useRef(null)
  const supportDialogRef = useRef(null)

  // Manage dialog focus, contain keyboard navigation, and support Escape to close.
  useEffect(() => {
    if (!supportOpen) {
      supportTriggerRef.current?.focus()
      return undefined
    }

    const dialog = supportDialogRef.current
    const focusableSelector =
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

    const focusableElements = dialog?.querySelectorAll(focusableSelector)
    const firstElement = focusableElements?.[0]
    const lastElement = focusableElements?.[focusableElements.length - 1]

    firstElement?.focus()

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        setSupportOpen(false)
        return
      }

      if (event.key === 'Tab' && firstElement && lastElement) {
        const focusOutsideDialog = !dialog.contains(document.activeElement)

        if (
          event.shiftKey &&
          (document.activeElement === firstElement || focusOutsideDialog)
        ) {
          event.preventDefault()
          lastElement.focus()
        } else if (
          !event.shiftKey &&
          (document.activeElement === lastElement || focusOutsideDialog)
        ) {
          event.preventDefault()
          firstElement.focus()
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [supportOpen])

  // Authentication is intentionally pending backend integration; credentials are not sent.
  function handleSubmit(event) {
    event.preventDefault()
    setMessage(
      'The authentication service is not connected yet. Your credentials have not been submitted.',
    )
  }

  return (
    <main className="login-page">
      <section className="login-panel" aria-labelledby="login-title">
        <div className="login-cluster">
          <div className="cluster-details">
            <span className="cluster-label">CLUSTER KE-NBO-01</span>
            <span className="cluster-location">Nairobi East</span>
          </div>

          <span className="cluster-status">
            <span className="status-indicator" />
            Online
          </span>
        </div>

        <div className="login-brand" aria-label="Weza">
          <div className="brand-emblem" aria-hidden="true">
            <svg viewBox="0 0 64 64" role="presentation">
              <circle cx="32" cy="32" r="5" />
              <path d="M19 32a13 13 0 0 1 26 0" />
              <path d="M12 32a20 20 0 0 1 40 0" />
              <path d="M5 32a27 27 0 0 1 54 0" />
            </svg>
          </div>
          <span className="brand-name">WEZA</span>
        </div>

        <header className="login-heading">
          <h1 id="login-title">Staff Login</h1>
          <p>Weza Wi-Fi Operator Console &amp; Billing NOC</p>
        </header>

        <form className="login-form" onSubmit={handleSubmit}>
          <div className="login-field">
            <label htmlFor="staff-identity">Staff Phone Number or ID</label>
            <input
              id="staff-identity"
              name="staffIdentity"
              type="text"
              autoComplete="username"
              placeholder="e.g. +254 7XX XXX XXX or #STF-XXXX"
              value={staffId}
              onChange={(event) => setStaffId(event.target.value)}
              required
            />
            <span className="field-assurance">
              <span className="material-symbols-outlined" aria-hidden="true">
                verified_user
              </span>
              NOC Verified
            </span>
          </div>

          <div className="login-field">
            <label htmlFor="staff-password">Password</label>
            <div className="password-input-wrap">
              <input
                id="staff-password"
                name="password"
                type={passwordVisible ? 'text' : 'password'}
                autoComplete="current-password"
                placeholder="Enter your password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
              <button
                className="password-toggle"
                type="button"
                onClick={() => setPasswordVisible((visible) => !visible)}
                aria-label={passwordVisible ? 'Hide password' : 'Show password'}
                aria-pressed={passwordVisible}
              >
                <span className="material-symbols-outlined" aria-hidden="true">
                  {passwordVisible ? 'visibility_off' : 'visibility'}
                </span>
              </button>
            </div>
            <span className="field-assurance">
              <span className="material-symbols-outlined" aria-hidden="true">
                security
              </span>
              2FA Ready
            </span>
          </div>

          <div className="login-restriction">
            <span className="material-symbols-outlined" aria-hidden="true">
              admin_panel_settings
            </span>
            <p>
              Restricted access. This console is for authorized Weza network
              engineers, field technicians, and billing NOC dispatchers only.
            </p>
          </div>

          <button className="login-submit" type="submit">
            <span>Sign In </span>
            <span className="material-symbols-outlined" aria-hidden="true">
              arrow_forward
            </span>
          </button>

          {message && (
            <p className="login-feedback" role="status">
              {message}
            </p>
          )}
        </form>

        <button
          ref={supportTriggerRef}
          className="support-link"
          type="button"
          onClick={() => setSupportOpen(true)}
        >
          Forgot Password or Need Access?
          <span className="material-symbols-outlined" aria-hidden="true">
            arrow_outward
          </span>
        </button>

        <button
          className="dashboard-preview-link"
          type="button"
          onClick={onPreviewDashboard}
        >
          Preview Dashboard (Development Only)
        </button>

        <footer className="login-footer">
          <p>
            <span className="material-symbols-outlined" aria-hidden="true">
              enhanced_encryption
            </span>
            Protected by Hardware Security Key &amp; 2FA
          </p>
          <p>Kenya Data Protection Act 2019 Compliant · Version 4.18.2</p>
        </footer>
      </section>

      {supportOpen && (
        <div
          className="support-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setSupportOpen(false)
            }
          }}
        >
          <section
            ref={supportDialogRef}
            className="support-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="support-title"
            aria-describedby="support-description"
          >
            <button
              className="support-close"
              type="button"
              onClick={() => setSupportOpen(false)}
              aria-label="Close support information"
            >
              <span className="material-symbols-outlined" aria-hidden="true">
                close
              </span>
            </button>

            <span className="support-icon material-symbols-outlined" aria-hidden="true">
              support_agent
            </span>
            <p className="support-eyebrow">ACCESS &amp; ACCOUNT SUPPORT</p>
            <h2 id="support-title">NOC Lead Desk</h2>
            <p id="support-description" className="support-description">
              Staff credentials and physical YubiKeys are provisioned by your
              Regional NOC Operations Lead.
            </p>

            <div className="support-detail">
              <span className="material-symbols-outlined" aria-hidden="true">
                call
              </span>
              <div>
                <span>Dispatch extension</span>
                <strong>#402 · Nairobi NOC</strong>
              </div>
            </div>

            <div className="support-detail">
              <span className="material-symbols-outlined" aria-hidden="true">
                badge
              </span>
              <div>
                <span>Shift Duty Officer</span>
                <strong>{operator.fullName} · Lead</strong>
              </div>
            </div>

            <button
              className="support-dismiss"
              type="button"
              onClick={() => setSupportOpen(false)}
            >
              Close
            </button>
          </section>
        </div>
      )}
    </main>
  )
}
