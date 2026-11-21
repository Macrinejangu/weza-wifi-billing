import { useEffect, useRef, useState } from 'react'
import { demoDataEnabled } from '../../../shared/demoMode.js'
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

function EventDrawer({ event, onClose, onInspectIssue }) {
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
          <div><h2 id="audit-event-title">Event Details #{event.id}</h2><p>{recordDate} · {event.time} EAT · Demo</p></div>
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
          <section className="audit-detail-card">
            <h3>Chronological Trace</h3>
            <ol className="audit-trace">{trace.map(([time, label]) => <li key={time}><strong>{time} EAT</strong><p>{label}</p></li>)}</ol>
          </section>
          <details className="audit-detail-card">
            <summary>Sample Event Payload</summary>
            <pre>{JSON.stringify({ event_id: event.id, action: event.type, record: event.record, result: event.result, demo: true }, null, 2)}</pre>
          </details>
          <p>Ledger signature verification is unavailable in this preview.</p>
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
  if (!demoDataEnabled) return <section className="audit-page"><h1>Activity &amp; Audit History</h1><p role="status">Audit history is currently unavailable.</p></section>
  return <DemoActivityHistory {...props} />
}

function DemoActivityHistory({ onBack, onInspectIssue }) {
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState({})
  const [inspection, setInspection] = useState(null)
  const [format, setFormat] = useState('csv')
  const opener = useRef(null)
  const title = useRef(null)

  useEffect(() => { title.current?.focus() }, [])

  const term = search.trim().toLowerCase()
  const visible = events.filter((event) =>
    filterOptions.every(([key]) => !filters[key] || filters[key] === event[key])
    && fields.some((key) => event[key].toLowerCase().includes(term)),
  )

  function closeDrawer() {
    setInspection(null)
    requestAnimationFrame(() => { if (opener.current?.isConnected) opener.current.focus() })
  }

  function exportEvents() {
    const rows = visible.map((event) => ({ date: recordDate, timezone: 'EAT', ...event }))
    const quote = (value) => `"${String(value).replaceAll('"', '""')}"`
    const columns = ['date', 'timezone', ...fields]
    const content = format === 'json'
      ? JSON.stringify(rows, null, 2)
      : [columns.map(quote).join(','), ...rows.map((row) => columns.map((key) => quote(row[key])).join(','))].join('\n')
    const url = URL.createObjectURL(new Blob([content], { type: format === 'json' ? 'application/json' : 'text/csv;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `weza-demo-audit.${format}`
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 0)
  }

  return (
    <section className="audit-page">
      {onBack && <button type="button" className="audit-back" onClick={onBack}>‹ Back to System Settings</button>}
      <header className="page-heading audit-heading">
        <div><p className="audit-eyebrow">Security &amp; Operations · Demo</p><h1 ref={title} tabIndex={-1}>Activity &amp; Audit History</h1><p>Review sample operator and system actions.</p></div>
        <div className="audit-actions">
          <span>{recordDate} · EAT</span>
          <select aria-label="Audit export format" value={format} onChange={(e) => setFormat(e.target.value)}><option value="csv">CSV</option><option value="json">JSON</option></select>
          <button className="audit-primary" type="button" onClick={exportEvents} disabled={!visible.length}>Export Log</button>
        </div>
      </header>

      <section className="audit-panel audit-filters" aria-label="Audit filters">
        <div className="audit-actions audit-filter-heading"><strong>{events.length} Sample Records</strong><button type="button" onClick={() => { setSearch(''); setFilters({}) }}>Clear Filters</button></div>
        <div className="audit-actions">
          <input type="search" aria-label="Search audit history" placeholder="Search actor, event, or affected record" value={search} onChange={(e) => setSearch(e.target.value)} />
          {filterOptions.map(([key, label]) => (
            <select key={key} aria-label={label} value={filters[key] ?? ''} onChange={(e) => setFilters({ ...filters, [key]: e.target.value })}>
              <option value="">{label}</option>
              {[...new Set(events.map((event) => event[key]))].map((option) => <option key={option}>{option}</option>)}
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
                  <th scope="row">{event.time} EAT<small>{recordDate}</small></th>
                  <td>{event.actor}<small>{event.role}</small></td>
                  <td>{event.action}</td><td>{event.record}</td>
                  <td><span className="audit-result" data-result={event.result}>{event.result}</span></td>
                  <td><button type="button" aria-label={`Inspect event ${event.id}`} onClick={(e) => { opener.current = e.currentTarget; setInspection(event) }}>Inspect</button></td>
                </tr>
              ))}
              {!visible.length && <tr><td colSpan={6}>No sample events match your filters.</td></tr>}
            </tbody>
          </table>
        </div>
        <p className="audit-count" aria-live="polite">Showing {visible.length} of {events.length} sample events</p>
      </section>
      <aside className="audit-panel audit-notice"><strong>Operational Accountability</strong><p>This is a read-only sample log. Live feeds and ledger verification are unavailable.</p></aside>
      {inspection && <EventDrawer event={inspection} onClose={closeDrawer} onInspectIssue={onInspectIssue} />}
    </section>
  )
}
