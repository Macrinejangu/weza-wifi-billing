import { useEffect, useMemo, useRef, useState } from 'react'
import '../styles/sessions.css'

const initialSessions = [
  {
    id: 'SES-DEMO-001',
    name: 'Amina Wanjiku',
    phone: '+254 712 345 678',
    ip: '10.140.22.8',
    mac: 'A4:5E:60:21:8B:10',
    package: 'Weekly Plus 10GB',
    remaining: '5h 18m',
    type: 'Voucher',
    node: 'Nairobi Central AP-01',
    status: 'Active',
    expiry: '20:30 EAT',
    started: '08:42 EAT',
    uptime: '2h 18m',
    download: '1.42 GB',
    upload: '184 MB',
  },
  {
    id: 'SES-DEMO-002',
    name: 'John Kariuki',
    phone: '+254 722 890 123',
    ip: '10.140.18.91',
    mac: 'B8:27:EB:91:3A:42',
    package: 'Daily Unlimited',
    remaining: 'CoA failed',
    type: 'Voucher',
    node: 'Nairobi West AP-03',
    status: 'Disconnected',
    expiry: 'Pending lease',
    started: '06:15 EAT',
    uptime: '4h 45m',
    download: '3.18 GB',
    upload: '392 MB',
  },
  {
    id: 'SES-DEMO-003',
    name: 'Brenda Mutua',
    phone: '+254 733 441 902',
    ip: '10.140.34.12',
    mac: 'D0:37:45:AC:19:62',
    package: '3-Hour Quick Boost',
    remaining: '8m',
    type: 'Voucher',
    node: 'Eastlands AP-02',
    status: 'Expiring',
    expiry: '12:40 EAT',
    started: '10:10 EAT',
    uptime: '2h 15m',
    download: '842 MB',
    upload: '96 MB',
  },
  {
    id: 'SES-DEMO-004',
    name: 'David Kipchirchir',
    phone: '+254 701 554 719',
    ip: '10.140.05.44',
    mac: 'F4:8C:50:72:0D:11',
    package: 'Monthly SME 50GB',
    remaining: '14d',
    type: 'Monthly / SME',
    node: 'Industrial Area AP-04',
    status: 'Grace Period',
    expiry: 'In 14 days',
    started: 'Yesterday, 16:20 EAT',
    uptime: '18h 37m',
    download: '8.64 GB',
    upload: '1.12 GB',
  },
  {
    id: 'SES-DEMO-005',
    name: 'Esther Kemboi',
    phone: '+254 798 112 004',
    ip: '10.140.29.63',
    mac: '70:4D:7B:2C:91:05',
    package: 'Weekly Plus 10GB',
    remaining: '1d 4h',
    type: 'Voucher',
    node: 'Kilimani AP-02',
    status: 'Active',
    expiry: 'Tomorrow, 23:05 EAT',
    started: 'Yesterday, 21:05 EAT',
    uptime: '13h 52m',
    download: '2.06 GB',
    upload: '278 MB',
  },
]

const summary = [
  { label: 'Active Sessions', value: '1,248', detail: 'Hotspot and GPON fiber online', icon: 'devices', tone: 'purple' },
  { label: 'Expiring Soon', value: '18', detail: 'Less than 15 minutes remaining', icon: 'timer', tone: 'lime' },
  { label: 'Failed Activations', value: '2', detail: 'Paid subscribers awaiting a lease', icon: 'warning', tone: 'danger' },
]

const packageTypes = ['Voucher', 'Monthly / SME']
const sessionStatuses = ['All', 'Active', 'Expiring', 'Grace Period']

function initials(name) {
  return name.split(' ').map((part) => part[0]).slice(0, 2).join('').toUpperCase()
}

function escapeCsv(value) {
  return `"${String(value ?? '').replaceAll('"', '""')}"`
}

function SessionDetails({ session, opener, onClose }) {
  const closeButtonRef = useRef(null)
  const footerButtonRef = useRef(null)

  useEffect(() => {
    closeButtonRef.current.focus()

    return () => {
      if (opener?.isConnected) opener.focus()
    }
  }, [opener])

  function handleKeyDown(event) {
    if (event.key === 'Escape') {
      event.preventDefault()
      onClose()
      return
    }

    if (event.key !== 'Tab') return

    const firstButton = closeButtonRef.current
    const lastButton = footerButtonRef.current
    const boundaryButton = event.shiftKey ? firstButton : lastButton

    if (event.target === boundaryButton) {
      event.preventDefault()
      const nextButton = event.shiftKey ? lastButton : firstButton
      nextButton.focus()
    }
  }

  const [view, setView] = useState('overview')
  const featuredSample = session.id === 'SES-DEMO-001'
  const status = session.status === 'Active' ? 'Active Lease' : session.status

  return (
    <div
      className="session-modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <section
        className="session-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="session-detail-title"
        onKeyDown={handleKeyDown}
      >
        <header className="session-drawer-header">
          <div className="session-modal-heading">
            <div>
              <h2 id="session-detail-title">Session Details</h2>
              <p>Session ID #{session.id} · {session.name} · Demo</p>
            </div>
            <button ref={closeButtonRef} type="button" className="session-icon-button" aria-label="Close session details" onClick={onClose}>×</button>
          </div>
          <div className="session-drawer-switch" role="group" aria-label="Session detail view">
            <button type="button" aria-pressed={view === 'overview'} onClick={() => setView('overview')}>Overview</button>
            <button type="button" aria-pressed={view === 'technical'} onClick={() => setView('technical')}>Technical Details</button>
          </div>
        </header>

        <div className="session-drawer-body">
          {view === 'overview' ? (
            <>
              <section className="session-detail-section session-auth-card">
                <div className="session-drawer-card-heading">
                  <h3>Authentication State</h3>
                  <span className="session-connection-badge" data-status={session.status}>{status}</span>
                </div>
                <div className="session-drawer-person">
                  <span className="session-avatar" aria-hidden="true">{initials(session.name)}</span>
                  <div><strong>{session.name}</strong><p>{session.phone}</p></div>
                </div>
                <dl className="session-detail-grid">
                  <div><dt>Package</dt><dd>{session.package}</dd></div>
                  <div><dt>Applied speeds</dt><dd>{featuredSample ? '10 Mbps / 5 Mbps' : 'Unavailable'}</dd></div>
                </dl>
              </section>

              <section className="session-detail-section">
                <div className="session-drawer-card-heading">
                  <h3>Quota Consumption</h3>
                  {featuredSample && <span className="session-drawer-chip">34% consumed</span>}
                </div>
                {featuredSample ? (
                  <>
                    <div className="session-quota-numbers"><strong>3.42 GB</strong><span>Total cap: 10.00 GB</span></div>
                    <progress aria-label="Sample quota consumption" value={3.42} max={10} />
                    <p>6.58 GB available · Sample quota</p>
                  </>
                ) : <p>Quota and remaining allowance are unavailable for this sample session.</p>}
              </section>

              <section className="session-detail-section">
                <div className="session-drawer-card-heading"><h3>Lease Timeline</h3><span className="session-drawer-chip">Fixed sample</span></div>
                <dl className="session-drawer-rows">
                  <div><dt>Start time</dt><dd>{session.started}</dd></div>
                  <div><dt>Expiry time</dt><dd>{session.expiry}</dd></div>
                  <div><dt>Remaining duration</dt><dd>{session.remaining}</dd></div>
                </dl>
              </section>

              <section className="session-detail-section">
                <h3>Device &amp; Location</h3>
                <dl className="session-drawer-rows session-device-rows">
                  <div><dt>Client device</dt><dd>{featuredSample ? 'iPhone 15 Pro' : 'Unavailable'}</dd></div>
                  <div><dt>Client MAC</dt><dd>{session.mac}</dd></div>
                  <div><dt>Access point</dt><dd>{session.node}</dd></div>
                </dl>
              </section>
            </>
          ) : (
            <>
              <section className="session-detail-section">
                <h3>Network Identifiers</h3>
                <dl className="session-drawer-rows">
                  <div><dt>Session ID</dt><dd>{session.id}</dd></div>
                  <div><dt>IP address</dt><dd>{session.ip}</dd></div>
                  <div><dt>Client MAC</dt><dd>{session.mac}</dd></div>
                  <div><dt>Access point</dt><dd>{session.node}</dd></div>
                </dl>
              </section>
              <section className="session-detail-section">
                <h3>Sample Traffic</h3>
                <dl className="session-drawer-rows">
                  <div><dt>Download</dt><dd>{session.download}</dd></div>
                  <div><dt>Upload</dt><dd>{session.upload}</dd></div>
                  <div><dt>Uptime</dt><dd>{session.uptime}</dd></div>
                </dl>
              </section>
            </>
          )}
        </div>

        <footer className="session-drawer-footer">
          <div className="session-drawer-footer-row">
            <button type="button" className="session-secondary-button" disabled>Send Renewal STK</button>
            <button ref={footerButtonRef} type="button" className="session-secondary-button" onClick={onClose}>Close details</button>
          </div>
          <button type="button" className="session-drawer-disconnect" disabled>Terminate Session (Disconnect RADIUS)</button>
          <p>Demo mode. Renewal and disconnect are unavailable.</p>
        </footer>
      </section>
    </div>
  )
}

export default function SessionsPage() {
  const [search, setSearch] = useState('')
  const [activeFilter, setActiveFilter] = useState('All')
  const [selectedStatus, setSelectedStatus] = useState('All')
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false)
  const [selectedNode, setSelectedNode] = useState('All')
  const [details, setDetails] = useState(null)
  const [notice, setNotice] = useState('')

  const filteredSessions = useMemo(() => {
    const term = search.trim().toLowerCase()

    return initialSessions.filter((session) => {
      const matchesType = activeFilter === 'All' || session.type === activeFilter
      const matchesStatus = selectedStatus === 'All' || session.status === selectedStatus
      const matchesNode = selectedNode === 'All' || session.node === selectedNode
      const matchesSearch = !term || [
        session.name,
        session.phone,
        session.ip,
        session.mac,
        session.package,
        session.id,
      ].some((value) => value.toLowerCase().includes(term))

      return matchesType && matchesStatus && matchesNode && matchesSearch
    })
  }, [search, activeFilter, selectedStatus, selectedNode])

  function exportSessions() {
    const headers = ['Session ID', 'Customer', 'Phone', 'IP Address', 'MAC Address', 'Package', 'Session Type', 'Access Point', 'Uptime', 'Remaining', 'Connection Status', 'Sample Expiry']
    const rows = filteredSessions.map((session) => [
      session.id,
      session.name,
      session.phone,
      session.ip,
      session.mac,
      session.package,
      session.type,
      session.node,
      session.uptime,
      session.remaining,
      session.status,
      session.expiry,
    ])

    const csv = [headers, ...rows].map((row) => row.map(escapeCsv).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'weza-session-demo-records.csv'
    anchor.click()
    URL.revokeObjectURL(url)
    setNotice(`Exported ${filteredSessions.length} illustrative session records.`)
  }

  function clearFilters() {
    setSearch('')
    setActiveFilter('All')
    setSelectedStatus('All')
    setSelectedNode('All')
    setNotice('')
  }

  return (
    <section className="sessions-page">
      <div className="page-heading sessions-heading">
        <div>
          <p className="session-eyebrow">SESSIONS &amp; TELEMETRY / RADIUS ACCOUNTING</p>
          <h1>Sessions</h1>
          <p className="sessions-description">Monitor customer internet access and session status across access points.</p>
        </div>
        <div className="sessions-heading-actions">
          <button
            type="button"
            className="session-secondary-button"
            aria-expanded={showAdvancedFilters}
            aria-controls="sessions-filter-actions"
            onClick={() => setShowAdvancedFilters((current) => !current)}
          >
            <span className="material-symbols-outlined">filter_list</span>
            Filter Telemetry
          </button>
          <button type="button" className="session-primary-button session-export-button" onClick={exportSessions}>
            <span className="material-symbols-outlined">download</span>
            Export Active Sessions
          </button>
        </div>
      </div>

      <div className="sessions-demo-notice">
        <span className="material-symbols-outlined">info</span>
        <span><strong>DEMO MODE · NOT CONNECTED</strong>. Summary metrics are illustrative fleet totals, separate from the five sample rows. Session start times, uptime, and remaining time are fixed sample values.</span>
      </div>

      <section className="sessions-summary-grid" aria-label="Illustrative session metrics">
        {summary.map((item) => (
          <article className="sessions-summary-card" key={item.label}>
            <div className={`sessions-summary-icon tone-${item.tone}`}>
              <span className="material-symbols-outlined">{item.icon}</span>
            </div>
            <div>
              <p>{item.label}</p>
              <strong>{item.value}</strong>
              <span>{item.detail}</span>
            </div>
          </article>
        ))}
      </section>

      <section className="sessions-list-panel sessions-filters-panel" aria-label="Session filters">
        <div className="sessions-toolbar">
          <label className="sessions-search">
            <span className="material-symbols-outlined">search</span>
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search by phone, IP, MAC or customer"
              aria-label="Search sessions"
            />
          </label>
          <div className="sessions-filter-controls">
            <div className="sessions-filter-pills" role="group" aria-label="Filter sessions by connection status">
              {sessionStatuses.map((status) => (
                <button
                  key={status}
                  type="button"
                  className={selectedStatus === status ? 'active' : ''}
                  aria-pressed={selectedStatus === status}
                  onClick={() => setSelectedStatus(status)}
                >
                  {status}
                </button>
              ))}
            </div>
            <select aria-label="Filter sessions by package type" value={activeFilter} onChange={(event) => setActiveFilter(event.target.value)}>
              <option value="All">All Packages</option>
              {packageTypes.map((type) => <option key={type}>{type}</option>)}
            </select>
            <select aria-label="Access point" id="session-node-filter" value={selectedNode} onChange={(event) => setSelectedNode(event.target.value)}>
              <option value="All">All Nodes</option>
              {[...new Set(initialSessions.map((session) => session.node))].map((node) => (
                <option key={node}>{node}</option>
              ))}
            </select>
            <span className="sessions-refresh-label">Fixed snapshot</span>
          </div>
        </div>

        <div id="sessions-filter-actions" hidden={!showAdvancedFilters}>
          <div className="sessions-advanced-filter">
            <button type="button" onClick={clearFilters}>Clear filters</button>
          </div>
        </div>
      </section>

      <section className="sessions-list-panel" aria-label="Session records">
        <div className="sessions-list-heading">
          <div>
            <h2>Active Authentications</h2>
            <p>Review the illustrative session records below.</p>
          </div>
          <span className="sessions-record-count">{filteredSessions.length} demo records</span>
        </div>

        <div className="sessions-table-scroll" role="region" aria-label="Active authentications" tabIndex={0}>
          <table className="sessions-table">
            <thead>
              <tr>
                <th scope="col">Customer / Device</th>
                <th scope="col">Package</th>
                <th scope="col">Connection status</th>
                <th scope="col">Start time</th>
                <th scope="col">Expiry time</th>
                <th scope="col">Remaining</th>
                <th scope="col">Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredSessions.map((session) => (
                <tr className="session-table-row" key={session.id}>
                  <th scope="row">
                    <div className="session-card-identity">
                      <span className="session-avatar" aria-hidden="true">{initials(session.name)}</span>
                      <div>
                        <strong>{session.name}</strong>
                        <span>{session.phone}</span>
                        <span className="session-mono">{session.ip} / {session.mac}</span>
                        <span>{session.node}</span>
                      </div>
                    </div>
                  </th>
                  <td>
                    <strong>{session.package}</strong>
                    <span className="session-table-secondary">{session.type}</span>
                  </td>
                  <td>
                    <span className="session-connection-badge" data-status={session.status}>{session.status}</span>
                  </td>
                  <td>{session.started}</td>
                  <td>{session.expiry}</td>
                  <td>{session.remaining}</td>
                  <td>
                    <button
                      type="button"
                      className="session-view-button"
                      aria-label={`Inspect session for ${session.name}`}
                      onClick={(event) => setDetails({ session, opener: event.currentTarget })}
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
              {filteredSessions.length === 0 && (
                <tr>
                  <td colSpan={7}>
                    <div className="sessions-empty">
                      <span className="material-symbols-outlined" aria-hidden="true">search_off</span>
                      <strong>No matching demo sessions</strong>
                      <span>Try another search term or clear the selected filters.</span>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="sessions-list-footer">
          <span>Showing {filteredSessions.length} of {initialSessions.length} demo records</span>
          <span>Page 1 of 1</span>
        </div>
      </section>

      {notice && <p className="sessions-notice" role="status">{notice}</p>}

      <p className="sessions-disclaimer">
        Illustrative interface and sample records only. No live subscriber leases, bandwidth telemetry, RADIUS accounting, or Change of Authorization (CoA) operations are being queried or performed.
      </p>

      {details && (
        <SessionDetails
          session={details.session}
          opener={details.opener}
          onClose={() => setDetails(null)}
        />
      )}
    </section>
  )
}
