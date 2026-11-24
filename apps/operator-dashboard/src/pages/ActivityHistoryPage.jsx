import { useEffect, useRef, useState } from 'react'
import { demoDataEnabled } from '../../../shared/demoMode.js'
import { getStaffAuditHistory, StaffSessionError } from '../api.js'
import '../styles/activity-history.css'

const events = [
  { id: 'EVT-89210', time: '14:52:08', actor: 'Moses Lenkai', role: 'Network Lead', type: 'Network', action: 'Manual Activation Retry Dispatched', record: 'ISS-4091', result: 'Pending Router Response' },
  { id: 'EVT-89209', time: '14:45:21', actor: 'FreeRADIUS Daemon', role: 'System', type: 'Network', action: 'CoA Handshake Timeout Logged', record: 'ISS-4091', result: 'Failed' },
  { id: 'EVT-89208', time: '14:41:18', actor: 'Samuel K.', role: 'Field Technician', type: 'Customer', action: 'Customer Note Appended', record: 'WZ-88219', result: 'Logged' },
  { id: 'EVT-89207', time: '12:15:30', actor: 'Safaricom Daraja', role: 'External Gateway', type: 'Payment', action: 'STK Push Callback Confirmed', record: 'RJ92MN38X2', result: 'Success' },
  { id: 'EVT-89206', time: '10:30:00', actor: 'Moses Lenkai', role: 'Network Lead', type: 'Network', action: 'Access Override Authorized', record: 'SES-DEMO-001', result: 'Authorized' },
  { id: 'EVT-89205', time: '08:30:14', actor: 'Moses Lenkai', role: 'Network Lead', type: 'Staff access', action: 'Staff Console Sign In', record: 'SEC-AUTH-09', result: 'Verified' },
]

const recordDate = '19 Nov 2026'
const fields = ['id', 'time', 'actor', 'role', 'type', 'action', 'record', 'result']
const filterOptions = [
  ['actor', 'All Actors'],
  ['type', 'All Action Types'],
  ['result', 'All Results'],
]

function EventDrawer({ event, onClose, onInspectIssue, live }) {
  const dialogRef = useRef(null)

  useEffect(() => {
    const dialog = dialogRef.current
    dialog.showModal()
    return () => dialog.close()
  }, [])

  const retry = event.id === 'EVT-89210'
  const trace = retry ? [
    ['14:52:08', 'Operator initiated a sample activation retry.'],
    ['14:52:09', 'The record shows verification of the existing payment RJ92MN38X2.'],
    ['14:52:10', 'A sample activation request was prepared.'],
    ['14:52:11', 'The snapshot shows the router acknowledgement as pending.'],
  ] : [[event.time, 'Event recorded in the sample audit history.']]

  return (
    <dialog className="audit-drawer" ref={dialogRef} aria-labelledby="audit-event-title" onCancel={(e) => { e.preventDefault(); onClose() }}>
      <div className="audit-drawer-layout">
        <header>
          <div><h2 id="audit-event-title">Event Details #{event.id}</h2><p>{event.date ?? recordDate} · {event.time} EAT{!live && ' · Demo'}</p></div>
          <button type="button" aria-label="Close event details" onClick={onClose}>×</button>
        </header>
        <div className="audit-drawer-body">
          <section className="audit-detail-card">
            <h3>Event Summary</h3>
            <dl>
              <div><dt>Action Type</dt><dd>{event.action}</dd></div>
              <div><dt>Triggered By</dt><dd>{event.actor}</dd></div>
              <div><dt>Affected Record</dt><dd>{event.record}</dd></div>
              <div><dt>Result</dt><dd><span className="audit-result" data-result={event.result}>{event.result}</span></dd></div>
            </dl>
          </section>
          {!live && <>
          <section className="audit-detail-card">
            <h3>Chronological Trace</h3>
            <ol className="audit-trace">{trace.map(([time, label]) => <li key={time}><strong>{time} EAT</strong><p>{label}</p></li>)}</ol>
          </section>
          <details className="audit-detail-card">
            <summary>Sample Event Payload</summary>
            <pre>{JSON.stringify({ event_id: event.id, action: event.type, record: event.record, result: event.result, demo: true }, null, 2)}</pre>
          </details>
          <p>Ledger signature verification is unavailable in this preview.</p>
          </>}
        </div>
        <footer>
          <button type="button" onClick={onClose}>Close Inspector</button>
          {event.record === 'ISS-4091' && onInspectIssue && <button className="audit-primary" type="button" onClick={() => onInspectIssue(event.record)}>View Related Issue #ISS-4091</button>}
        </footer>
      </div>
    </dialog>
  )
}

export default function ActivityHistoryPage(props) {
  if (props.accessToken) return <LiveActivityHistory {...props} />
  if (!demoDataEnabled) return <section className="audit-page"><h1>Activity &amp; Audit History</h1><p role="status">Audit history is currently unavailable.</p></section>
  return <ActivityHistory {...props} entries={events} />
}

const auditPageSize = 50
const auditDate = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeZone: 'Africa/Nairobi' })
const auditTime = new Intl.DateTimeFormat('en-GB', { timeStyle: 'medium', timeZone: 'Africa/Nairobi' })

function LiveActivityHistory({ accessToken, onSignOut, onBack }) {
  const [offset, setOffset] = useState(0)
  const [attempt, setAttempt] = useState(0)
  const [result, setResult] = useState(null)

  useEffect(() => {
    const controller = new AbortController()
    getStaffAuditHistory(accessToken, { offset, limit: auditPageSize, signal: controller.signal })
      .then((records) => {
        if (!controller.signal.aborted) setResult({ offset, attempt, records })
      }).catch((error) => {
        if (controller.signal.aborted) return
        if (error instanceof StaffSessionError) onSignOut()
        else setResult({ offset, attempt, error: error.message })
      })
    return () => controller.abort()
  }, [accessToken, offset, attempt, onSignOut])

  const current = result?.offset === offset && result?.attempt === attempt ? result : null
  const entries = (current?.records ?? []).map((record) => ({
    id: String(record.id),
    date: auditDate.format(new Date(record.created_at)),
    time: auditTime.format(new Date(record.created_at)),
    actor: record.actor ?? 'System',
    role: '',
    type: record.entity_type,
    action: record.action,
    record: record.entity_id == null ? record.entity_type : `${record.entity_type} #${record.entity_id}`,
    result: 'Recorded',
  }))

  return (
    <ActivityHistory
      key={offset}
      entries={entries}
      live
      onBack={onBack}
      loading={!current}
      error={current?.error}
      onRetry={() => setAttempt(attempt + 1)}
      onPrevious={offset > 0 ? () => setOffset(offset - auditPageSize) : undefined}
      onNext={entries.length === auditPageSize ? () => setOffset(offset + auditPageSize) : undefined}
    />
  )
}

function ActivityHistory({
  onBack, onInspectIssue, entries, live, loading, error, onRetry, onPrevious, onNext,
}) {
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState({})
  const [inspection, setInspection] = useState(null)
  const [format, setFormat] = useState('csv')
  const opener = useRef(null)
  const title = useRef(null)

  useEffect(() => { title.current?.focus() }, [])

  const term = search.trim().toLowerCase()
  const visible = entries.filter((event) =>
    filterOptions.every(([key]) => !filters[key] || filters[key] === event[key])
    && fields.some((key) => event[key].toLowerCase().includes(term)),
  )

  function closeDrawer() {
    setInspection(null)
    requestAnimationFrame(() => { if (opener.current?.isConnected) opener.current.focus() })
  }

  function exportEvents() {
    const rows = visible.map((event) => ({ date: event.date ?? recordDate, timezone: 'EAT', ...event }))
    const quote = (value) => {
      const text = String(value)
      const escaped = /^[\s]*[=+@-]|^[\t\r\n]/.test(text) ? `'${text}` : text
      return `"${escaped.replaceAll('"', '""')}"`
    }
    const columns = ['date', 'timezone', ...fields]
    const content = format === 'json'
      ? JSON.stringify(rows, null, 2)
      : [columns.map(quote).join(','), ...rows.map((row) => columns.map((key) => quote(row[key])).join(','))].join('\n')
    const url = URL.createObjectURL(new Blob([content], { type: format === 'json' ? 'application/json' : 'text/csv;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `weza-${live ? '' : 'demo-'}audit.${format}`
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 0)
  }

  return (
    <section className="audit-page">
      {onBack && <button type="button" className="audit-back" onClick={onBack}>‹ Back to System Settings</button>}
      <header className="page-heading audit-heading">
        <div><p className="audit-eyebrow">Security &amp; Operations{!live && ' · Demo'}</p><h1 ref={title} tabIndex={-1}>Activity &amp; Audit History</h1><p>{live ? 'Review recorded administrative actions.' : 'Review sample operator and system actions.'}</p></div>
        <div className="audit-actions">
          <span>{!live && `${recordDate} · `}EAT</span>
          <select aria-label="Audit export format" value={format} onChange={(e) => setFormat(e.target.value)}><option value="csv">CSV</option><option value="json">JSON</option></select>
          <button className="audit-primary" type="button" onClick={exportEvents} disabled={!visible.length}>Export Log</button>
        </div>
      </header>

      <section className="audit-panel audit-filters" aria-label="Audit filters">
        <div className="audit-actions audit-filter-heading"><strong>{entries.length} {live ? 'Records on this page' : 'Sample Records'}</strong><button type="button" onClick={() => { setSearch(''); setFilters({}) }}>Clear Filters</button></div>
        <div className="audit-actions">
          <input type="search" aria-label="Search audit history" placeholder="Search actor, event, or affected record" value={search} onChange={(e) => setSearch(e.target.value)} />
          {filterOptions.map(([key, label]) => (
            <select key={key} aria-label={label} value={filters[key] ?? ''} onChange={(e) => setFilters({ ...filters, [key]: e.target.value })}>
              <option value="">{label}</option>
              {[...new Set(entries.map((event) => event[key]))].map((option) => <option key={option}>{option}</option>)}
            </select>
          ))}
        </div>
      </section>

      <section className="audit-panel audit-table-panel" aria-label="Audit log">
        <div className="audit-table-scroll" role="region" aria-label="Scrollable audit log" tabIndex={0}>
          <table>
            <thead><tr>{['Date and Time', 'Actor', 'Action', 'Affected Record', 'Result', 'Details'].map((label) => <th key={label} scope="col">{label}</th>)}</tr></thead>
            <tbody>
              {visible.map((event) => (
                <tr key={event.id}>
                  <th scope="row">{event.time} EAT<small>{event.date ?? recordDate}</small></th>
                  <td>{event.actor}<small>{event.role}</small></td>
                  <td>{event.action}</td><td>{event.record}</td>
                  <td><span className="audit-result" data-result={event.result}>{event.result}</span></td>
                  <td><button type="button" aria-label={`Inspect event ${event.id}`} onClick={(e) => { opener.current = e.currentTarget; setInspection(event) }}>Inspect</button></td>
                </tr>
              ))}
              {!visible.length && <tr><td colSpan={6}>
                {loading ? 'Loading audit history…' : error ? <span role="alert">{error}</span>
                  : live ? 'No recorded events match your filters.' : 'No sample events match your filters.'}
              </td></tr>}
            </tbody>
          </table>
        </div>
        <p className="audit-count" aria-live="polite">Showing {visible.length} of {entries.length} {live ? 'events on this page' : 'sample events'}</p>
      </section>
      {error && <button type="button" onClick={onRetry}>Try again</button>}
      {live && (onPrevious || onNext) && <div className="audit-actions">
        <button type="button" onClick={onPrevious} disabled={!onPrevious}>Previous</button>
        <button type="button" onClick={onNext} disabled={!onNext}>Next</button>
      </div>}
      {!live && <aside className="audit-panel audit-notice"><strong>Operational Accountability</strong><p>This is a read-only sample log. Live feeds and ledger verification are unavailable.</p></aside>}
      {inspection && <EventDrawer live={live} event={inspection} onClose={closeDrawer} onInspectIssue={onInspectIssue} />}
    </section>
  )
}
