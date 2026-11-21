import { useState } from 'react'
import { demoDataEnabled } from '../../../shared/demoMode.js'
import '../styles/system-settings.css'

const sections = [
  ['settings-general', 'General Settings'],
  ['settings-integrations', 'Integration Status'],
  ['settings-staff', 'Staff Access & Tiers'],
]

const defaultPreferences = { name: 'Weza Wi-Fi Core', maintenanceStart: '03:00', maintenanceEnd: '04:00' }

const integrations = [
  { category: 'Billing Gateway', name: 'Safaricom Daraja C2B/STK', details: [['Latency', '418 ms'], ['Last verified', '2 min before snapshot']] },
  { category: 'Authentication', name: 'Network AAA Integration', details: [['Router fleet', '6 sample routers'], ['Last ping', '30 sec before snapshot']] },
  { category: 'Notifications', name: "Africa’s Talking SMS Gateway", details: [['Balance', '42,850 sample SMS'], ['Last dispatched', '5 min before snapshot']] },
]

const staffTiers = [
  { name: 'Desk Support', accounts: 4, description: 'Voucher lookups, session status queries, and payment reconciliation assistance.' },
  { name: 'Network Operator', accounts: 2, description: 'Router monitoring, subscriber session inspection, and access point telemetry.' },
  { name: 'System Administrator', accounts: 1, description: 'System preferences, integration configuration, and audit access.' },
]

export default function SystemSettingsPage({ onOpenAuditHistory }) {
  if (!demoDataEnabled) {
    return (
      <section className="system-settings-page">
        <h1>System Settings</h1>
        <p role="status">System settings are currently unavailable.</p>
      </section>
    )
  }

  return <DemoSystemSettings onOpenAuditHistory={onOpenAuditHistory} />
}

function DemoSystemSettings({ onOpenAuditHistory }) {
  const [saved, setSaved] = useState(defaultPreferences)
  const [draft, setDraft] = useState(defaultPreferences)
  const [feedback, setFeedback] = useState('')
  const [activeSection, setActiveSection] = useState(sections[0][0])

  const dirty = Object.keys(saved).some((key) => saved[key] !== draft[key])

  function updateField(event) {
    const { name, value } = event.target
    setDraft((current) => ({ ...current, [name]: value }))
    setFeedback('')
  }

  function savePreferences(event) {
    event.preventDefault()
    const name = draft.name.trim()
    if (!name || draft.maintenanceStart === draft.maintenanceEnd) {
      setFeedback('Enter a system name and choose different maintenance start and end times.')
      return
    }

    const preferences = { ...draft, name }
    setSaved(preferences)
    setDraft(preferences)
    setFeedback('Demo preferences saved for this visit.')
  }

  return (
    <form className="system-settings-page" onSubmit={savePreferences}>
      <header className="page-heading system-settings-heading">
        <div>
          <p className="system-settings-eyebrow">Pilot Cluster · KE-NBO-01 · Demo</p>
          <h1>System Settings</h1>
          <p>Manage console preferences and review integrations and staff access.</p>
        </div>
        <div className="system-settings-actions">
          <button type="button" onClick={onOpenAuditHistory} disabled={!onOpenAuditHistory}>Audit History</button>
          <button type="submit" className="system-settings-primary" disabled={!dirty}>Save Changes</button>
        </div>
      </header>

      <aside className="system-settings-health">
        <div>
          <span>Pilot Node · Nairobi Central</span>
          <h2>Core System Status: Operational</h2>
          <p>Illustrative billing, authentication, and notification health.</p>
        </div>
        <strong>3 of 3 Sample Services Healthy</strong>
      </aside>
      {feedback && <p className="system-settings-feedback" role="status">{feedback}</p>}

      <nav className="system-settings-nav" aria-label="Settings sections">
        {sections.map(([id, label]) => (
          <a key={id} href={`#${id}`} aria-current={activeSection === id ? 'location' : undefined} onClick={(event) => {
            event.preventDefault()
            const target = document.getElementById(id)
            target?.scrollIntoView({ block: 'start' })
            target?.focus({ preventScroll: true })
            setActiveSection(id)
          }}>{label}</a>
        ))}
      </nav>

      <section className="system-settings-panel" id="settings-general" aria-labelledby="settings-general-heading" tabIndex={-1}>
        <header><h2 id="settings-general-heading">Section 1: General Preferences</h2><p>Console name, localization, and maintenance schedule.</p></header>
        <div className="system-settings-grid">
          <label className="system-settings-tile"><span>System Name</span><input name="name" required maxLength={60} value={draft.name} onChange={updateField} /></label>
          <div className="system-settings-tile"><span>Timezone</span><strong>Africa/Nairobi (EAT)</strong><small>UTC+03:00</small></div>
          <div className="system-settings-tile"><span>Currency</span><strong>Kenyan Shillings (KES)</strong><small>M-Pesa billing currency</small></div>
          <fieldset className="system-settings-tile system-maintenance">
            <legend>Maintenance Window (EAT)</legend>
            <label><small>Start</small><input type="time" name="maintenanceStart" required value={draft.maintenanceStart} onChange={updateField} /></label>
            <label><small>End</small><input type="time" name="maintenanceEnd" required value={draft.maintenanceEnd} onChange={updateField} /></label>
          </fieldset>
        </div>
      </section>

      <section className="system-settings-panel" id="settings-integrations" aria-labelledby="settings-integrations-heading" tabIndex={-1}>
        <header><h2 id="settings-integrations-heading">Section 2: Integration Status</h2><p>Fixed health snapshots for billing, authentication, and notifications.</p></header>
        <div className="system-settings-grid">
          {integrations.map(({ category, name, details }) => (
            <article key={category} className="system-settings-tile">
              <div className="system-settings-tile-heading"><span>{category}</span><small className="system-settings-badge">Sample active</small></div>
              <strong>{name}</strong>
              <dl>
                {details.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
              </dl>
            </article>
          ))}
        </div>
      </section>

      <section className="system-settings-panel" id="settings-staff" aria-labelledby="settings-staff-heading" tabIndex={-1}>
        <header><h2 id="settings-staff-heading">Section 3: Staff Access &amp; Operator Roles</h2><p>Sample access tiers and permission summaries.</p></header>
        <div className="system-settings-grid">
          {staffTiers.map(({ name, accounts, description }, index) => (
            <article key={name} className="system-settings-tile">
              <div className="system-settings-tile-heading"><span>Tier {index + 1}</span><small>{accounts} sample accounts</small></div>
              <strong>{name}</strong><p>{description}</p>
            </article>
          ))}
        </div>
      </section>
    </form>
  )
}
