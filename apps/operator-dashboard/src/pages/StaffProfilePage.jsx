import { useEffect, useRef, useState } from 'react'
import { demoDataEnabled } from '../../../shared/demoMode.js'
import '../styles/staff-profile.css'

const sampleSessions = [
  { id: 'current', name: 'Chrome on macOS', location: 'Nairobi, Kenya', status: 'Current device · Active now' },
  { id: 'other', name: 'Safari on iOS', location: 'Westlands Office Hub', status: 'Last active 4 hours before snapshot' },
]

export default function StaffProfilePage({ operator, onSignOut, staff }) {
  if (!staff && !demoDataEnabled) return <section className="staff-profile-page"><h1>My Profile &amp; Security</h1><p role="status">Operator profile is currently unavailable.</p></section>
  return <ProfileView key={staff?.id ?? 'demo'} operator={operator} onSignOut={onSignOut} staff={staff} />
}

function ProfileView({ operator, onSignOut, staff }) {
  const live = Boolean(staff)
  const [saved, setSaved] = useState(() => ({
    name: live ? staff.full_name : operator.fullName,
    email: live ? staff.email : 'operator@example.com',
    phone: '',
    timezone: 'Africa/Nairobi',
  }))
  const [draft, setDraft] = useState(saved)
  const [sessions, setSessions] = useState(() => live ? [] : sampleSessions)
  const [profileNotice, setProfileNotice] = useState('')
  const [sessionNotice, setSessionNotice] = useState('')
  const title = useRef(null)

  useEffect(() => { title.current?.focus() }, [])

  const dirty = Object.keys(saved).some((key) => saved[key] !== draft[key])
  const otherSessions = sessions.filter((session) => session.id !== 'current')

  function update(event) {
    const { name, value } = event.target
    setDraft((current) => ({ ...current, [name]: value }))
    setProfileNotice('')
  }

  function save(event) {
    event.preventDefault()
    if (live) return
    const name = draft.name.trim()
    if (!name) {
      setProfileNotice('Enter a name before saving.')
      return
    }
    const preferences = { ...draft, name, email: draft.email.trim(), phone: draft.phone.trim() }
    setSaved(preferences)
    setDraft(preferences)
    setProfileNotice('Demo profile changes saved for this visit.')
  }

  return (
    <section className="staff-profile-page">
      <header className="page-heading staff-profile-heading">
        <div><h1 ref={title} tabIndex={-1}>My Profile &amp; Security</h1><p>Review operator preferences, security settings, and console sessions.</p></div>
        <span className="staff-profile-chip">{live ? 'Read-only profile' : 'Demo profile'}</span>
      </header>
      <div className="staff-profile-columns">
        <div className="staff-profile-stack">
          <form className="staff-profile-card" onSubmit={save}>
            <div className="staff-profile-identity">
              <span className="staff-profile-avatar" aria-hidden="true">{operator.initials}</span>
              <div><h2>{saved.name}</h2><p>{operator.role}{!live && ' · Sample operator'}</p></div>
            </div>
            <div className="staff-profile-fields">
              <label className="staff-profile-wide">Full Name<input name="name" readOnly={live} required maxLength={60} value={draft.name} onChange={update} /></label>
              <label>Work Email<input name="email" type="email" readOnly={live} required value={draft.email} onChange={update} /></label>
              <label>Direct Mobile<input name="phone" type="tel" disabled={live} placeholder={live ? 'Unavailable' : 'Sample number only'} value={draft.phone} onChange={update} /></label>
              <label className="staff-profile-wide">Primary Timezone &amp; Dispatch Locale
                <select name="timezone" disabled={live} value={draft.timezone} onChange={update}>
                  <option value="Africa/Nairobi">{live ? 'Unavailable' : 'East Africa Time · Nairobi'}</option>
                  <option value="UTC">Coordinated Universal Time</option>
                </select>
              </label>
            </div>
            {profileNotice && <p role="status">{profileNotice}</p>}
            {live ? <p>Staff profile details are read-only.</p> : (
              <div className="staff-profile-actions">
                <button type="button" disabled={!dirty} onClick={() => { setDraft(saved); setProfileNotice('') }}>Cancel</button>
                <button type="submit" disabled={!dirty} className="staff-profile-primary">Save Changes</button>
              </div>
            )}
          </form>

          <section className="staff-profile-card">
            <div className="staff-profile-card-heading"><h2>Active Console Sessions</h2><span className="staff-profile-chip">{live ? 'Unavailable' : `${sessions.length} sample sessions`}</span></div>
            <p>{live ? 'Other console sessions are unavailable.' : 'Review devices in this demo session list.'}</p>
            <ul className="staff-session-list">
              {sessions.map((session) => (
                <li key={session.id}><div><strong>{session.name}</strong><p>{session.location} · {session.status}</p></div>
                  {session.id !== 'current' && <button type="button" onClick={() => {
                    setSessions((current) => current.filter((item) => item.id !== session.id))
                    setSessionNotice('Sample session removed from this view.')
                  }}>Revoke</button>}
                </li>
              ))}
            </ul>
            {sessionNotice && <p role="status">{sessionNotice}</p>}
            {!live && <div className="staff-profile-actions">
              <button type="button" className="staff-profile-danger" disabled={!otherSessions.length} onClick={() => {
                setSessions((current) => current.filter((session) => session.id === 'current'))
                setSessionNotice('Other sample sessions removed from this view.')
              }}>Sign Out of Other Sessions</button>
            </div>}
          </section>
        </div>

        <div className="staff-profile-stack">
          <section className="staff-profile-card">
            <div className="staff-profile-card-heading"><h2>Password &amp; Key</h2><span className="staff-profile-chip">Unavailable</span></div>
            {!live && <div className="staff-profile-fields">
              <label className="staff-profile-wide">Current Password<input type="password" disabled autoComplete="off" /></label>
              <label className="staff-profile-wide">New Password<input type="password" disabled autoComplete="off" /></label>
              <label className="staff-profile-wide">Confirm New Password<input type="password" disabled autoComplete="off" /></label>
            </div>}
            <p>{live ? 'Password changes are currently unavailable.' : 'Password changes require an authenticated staff account.'}</p>
            {!live && <div className="staff-profile-actions"><button type="button" disabled>Update Password</button></div>}
          </section>

          <section className="staff-profile-card">
            <div className="staff-profile-card-heading"><h2>Two-Factor Auth</h2><span className="staff-profile-chip">{live ? 'Unavailable' : 'Demo'}</span></div>
            <div className="staff-profile-security-tile"><strong>Authenticator App</strong><p>{live ? 'Authenticator setup is currently unavailable.' : 'Sample enrollment. Verification and recovery are unavailable in the preview.'}</p></div>
            {!live && <div className="staff-profile-actions"><button type="button" disabled>Manage 2FA</button></div>}
          </section>

          <section className="staff-profile-card staff-profile-card-heading">
            <div><h2>Operator Sign Out</h2><p>Return to the staff login screen.</p></div>
            <button type="button" disabled={!onSignOut} onClick={onSignOut}>Sign Out</button>
          </section>
        </div>
      </div>
    </section>
  )
}
