import { useEffect, useState } from 'react'
import { demoDataEnabled } from '../../../shared/demoMode.js'
import { getStaffSettings, StaffSessionError, updateStaffSettings } from '../api.js'
import SupportFaqSettings from './SupportFaqSettings.jsx'
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

export default function SystemSettingsPage({ accessToken, onSignOut, onOpenAuditHistory }) {
  if (accessToken) {
    return <LiveSystemSettings {...{ accessToken, onSignOut, onOpenAuditHistory }} />
  }
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

function editablePreferences(preferences) {
  return {
    name: preferences.name,
    maintenance_start: preferences.maintenance_start?.slice(0, 5) ?? '',
    maintenance_end: preferences.maintenance_end?.slice(0, 5) ?? '',
  }
}

function LiveSystemSettings({ accessToken, onSignOut, onOpenAuditHistory }) {
  const [settings, setSettings] = useState(null)
  const [draft, setDraft] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [saving, setSaving] = useState(false)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    getStaffSettings(accessToken, { signal: controller.signal }).then((result) => {
      if (controller.signal.aborted) return
      setSettings(result)
      setDraft(editablePreferences(result.preferences))
    }).catch((failure) => {
      if (controller.signal.aborted) return
      if (failure instanceof StaffSessionError) onSignOut()
      else setError(failure.message)
    })
    return () => controller.abort()
  }, [accessToken, attempt, onSignOut])

  const canEdit = settings?.role === 'admin'
  const saved = settings ? editablePreferences(settings.preferences) : null
  const dirty = Boolean(saved && draft && Object.keys(saved).some((key) => draft[key] !== saved[key]))

  function updateField(event) {
    const { name, value } = event.target
    setDraft((previous) => ({ ...previous, [name]: value }))
    setNotice('')
    setError('')
  }

  async function save(event) {
    event.preventDefault()
    if (!canEdit || !dirty || saving) return
    const { name, maintenance_start: start, maintenance_end: end } = draft
    if (!name.trim() || Boolean(start) !== Boolean(end) || (start && start === end)) {
      setError('Enter a system name and either two different maintenance times or no times.')
      return
    }
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const preferences = await updateStaffSettings(accessToken, {
        name: name.trim(),
        maintenance_start: start || null,
        maintenance_end: end || null,
      })
      setSettings((previous) => ({ ...previous, preferences }))
      setDraft(editablePreferences(preferences))
      setNotice('System preferences saved.')
    } catch (failure) {
      if (failure instanceof StaffSessionError) onSignOut()
      else setError(failure.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="system-settings-page">
      <form className="system-settings-page" onSubmit={save}>
        <header className="page-heading system-settings-heading">
          <div><h1>System Settings</h1><p>Console preferences, integration configuration, and staff access.</p></div>
          {canEdit && <div className="system-settings-actions">
            <button type="button" onClick={onOpenAuditHistory}>Audit History</button>
            <button type="submit" className="system-settings-primary" disabled={!dirty || saving}>
              {saving ? 'Saving…' : 'Save Changes'}
            </button>
          </div>}
        </header>
        {error && <p role="alert" className="system-settings-feedback">{error}</p>}
        {notice && <p role="status" className="system-settings-feedback">{notice}</p>}
        {!settings && (
          error ? <button type="button" onClick={() => { setError(''); setAttempt(attempt + 1) }}>Try again</button>
            : <p role="status">Loading system settings…</p>
        )}
        {settings && draft && <>
          <section className="system-settings-panel" aria-label="General preferences">
            <header><h2>General Preferences</h2><p>{canEdit ? 'Store the console name and maintenance window.' : 'An administrator manages these preferences.'}</p></header>
            <div className="system-settings-grid">
              <label className="system-settings-tile">
                <span>System Name</span>
                <input name="name" required maxLength={60} value={draft.name} onChange={updateField} readOnly={!canEdit || saving} />
              </label>
              <div className="system-settings-tile"><span>Timezone</span><strong>Africa/Nairobi (EAT)</strong></div>
              <div className="system-settings-tile"><span>Currency</span><strong>Kenyan Shillings (KES)</strong></div>
              <fieldset className="system-settings-tile system-maintenance" disabled={!canEdit || saving}>
                <legend>Maintenance Window (EAT)</legend>
                <label><small>Start</small><input type="time" name="maintenance_start" value={draft.maintenance_start} onChange={updateField} /></label>
                <label><small>End</small><input type="time" name="maintenance_end" value={draft.maintenance_end} onChange={updateField} /></label>
                <small>Saved schedule for staff reference.</small>
              </fieldset>
            </div>
          </section>
          <section className="system-settings-panel" aria-label="Integration configuration">
            <header><h2>Integration Configuration</h2><p>Backend settings. Service health has not been checked.</p></header>
            <div className="system-settings-grid">
              <article className="system-settings-tile"><span>Safaricom Daraja sandbox</span><strong>{settings.daraja_sandbox_enabled ? 'Enabled' : 'Disabled'}</strong></article>
              <article className="system-settings-tile"><span>Mock payments</span><strong>{settings.mock_payments_enabled ? 'Enabled' : 'Disabled'}</strong></article>
              <article className="system-settings-tile"><span>Router Mode</span><strong>{{ mock: 'Mock', mikrotik: 'MikroTik' }[settings.router_mode] ?? 'Unconfigured'}</strong></article>
              <article className="system-settings-tile"><span>SMS Notifications</span><strong>Unavailable</strong></article>
            </div>
          </section>
          <section className="system-settings-panel" aria-label="Staff access">
            <header><h2>Staff Access &amp; Operator Roles</h2><p>Signed in as {canEdit ? 'Administrator' : 'Operator'}.</p></header>
            <div className="system-settings-grid">
              <article className="system-settings-tile"><span>Administrators</span><strong>{settings.active_staff_by_role.admin} active</strong><p>Manage system preferences and review audit history.</p></article>
              <article className="system-settings-tile"><span>Operators</span><strong>{settings.active_staff_by_role.operator} active</strong><p>Review billing, sessions, and system configuration.</p></article>
            </div>
          </section>
        </>}
      </form>
      {canEdit && <SupportFaqSettings accessToken={accessToken} onSignOut={onSignOut} />}
    </div>
  )
}
