import { useEffect, useRef, useState } from 'react'
import { demoDataEnabled } from '../../../shared/demoMode.js'
import { listStaffConnectionIssues, retryStaffActivation, StaffSessionError } from '../api.js'
import '../styles/connection-issues.css'

const pageSize = 25
const dateTime = new Intl.DateTimeFormat('en-KE', {
  dateStyle: 'medium', timeStyle: 'short', timeZone: 'Africa/Nairobi',
})

function toIssue(record) {
  const failed = record.activation_status === 'failed'
  return {
    id: record.session_id ? `Session #${record.session_id}` : `Payment #${record.payment_id}`,
    title: failed ? 'Activation failed' : 'Awaiting activation',
    customer: `Customer #${record.customer_id}`,
    receipt: record.payment_reference || `Payment #${record.payment_id}`,
    paymentId: record.payment_id,
    purchaseId: record.purchase_id,
    time: dateTime.format(new Date(record.updated_at)),
    status: failed ? 'Activation Failed' : 'Awaiting activation',
    payment: 'Successful',
    description: record.failure_reason,
  }
}

const sampleIssues = [
  { id: 'ISS-4091', title: 'Router CoA Timeout', customer: 'Dennis Kiprono', receipt: 'RJ92MN38X2', node: 'KE-NBO-01', time: '14:41 EAT', severity: 'High', status: 'Investigating', payment: 'Confirmed', retryable: true, description: 'The payment was confirmed. The router timed out before acknowledging the request to activate internet access.' },
  { id: 'ISS-4088', title: 'Authentication Failure', customer: 'Grace Muthoni', receipt: 'Sample reference', node: 'KE-NBO-01', time: '14:10 EAT', severity: 'Medium', status: 'Investigating', payment: 'Confirmed', retryable: false, description: 'The access point rejected the subscriber authentication request.' },
  { id: 'ISS-4082', title: 'Payment Confirmation Delayed', customer: 'Faith Muthoni', receipt: 'STK_PEND_884', node: 'KE-NBO-01', time: '13:46 EAT', severity: 'Medium', status: 'New', payment: 'Pending', retryable: false, description: 'The sample payment is still awaiting confirmation. Internet activation has not started.' },
  { id: 'ISS-4075', title: 'Router Unreachable', customer: 'Samuel Mwangi', receipt: 'Sample reference', node: 'KE-NBO-02', time: '12:20 EAT', severity: 'Low', status: 'Resolved', payment: 'Confirmed', retryable: false, description: 'The node responded after the sample connectivity check.' },
]

const statusFilters = ['All', 'New', 'Investigating', 'Resolved']
const resolutionCategories = ['Router connectivity restored', 'Access policy corrected', 'Payment status verified', 'Other']

function IssueBadge({ value }) {
  return <span className="connection-issue-badge" data-value={value}>{value}</span>
}

function IssueConfirmation({ action, issue, reason, onClose, onConfirm }) {
  const dialogRef = useRef(null)
  const [category, setCategory] = useState('')
  const [note, setNote] = useState(reason)
  const [verified, setVerified] = useState(false)
  const retry = action === 'retry'
  const ready = retry || Boolean(category && note.trim() && verified)

  useEffect(() => {
    const dialog = dialogRef.current
    dialog.showModal()
    return () => dialog.close()
  }, [])

  return (
    <dialog
      ref={dialogRef}
      className="connection-issue-dialog"
      aria-labelledby="connection-confirmation-title"
      onCancel={(event) => {
        event.preventDefault()
        onClose()
      }}
    >
      <form onSubmit={(event) => {
        event.preventDefault()
        if (ready) onConfirm({ category, note: note.trim() })
      }}>
        <header className="connection-issue-dialog-header">
          <div><h2 id="connection-confirmation-title">{retry ? 'Confirm Safe Activation Retry' : 'Mark Issue as Resolved'}</h2>
          <p>{issue.id} · {issue.customer}</p></div>
          <button type="button" aria-label="Close confirmation" onClick={onClose}>×</button>
        </header>
        <p>{retry
          ? `Record a simulated activation retry for ${issue.id}. No router command or payment prompt will be sent.`
          : `Record how ${issue.id} was resolved in this preview. The change only lasts until the page is refreshed or left.`}</p>
        {retry && (
          <aside className="connection-issue-callout">
            <strong>Safe retry preview</strong>
            <p>Gateway {issue.node} · Existing payment {issue.receipt} · {issue.payment}. This records a sample attempt without another charge.</p>
          </aside>
        )}
        {!retry && (
          <>
            <label>Resolution category
              <select required value={category} onChange={(event) => setCategory(event.target.value)}>
                <option value="">Select a category</option>
                {resolutionCategories.map((item) => <option key={item}>{item}</option>)}
              </select>
            </label>
            <label>Resolution notes
              <textarea rows={4} required value={note} onChange={(event) => setNote(event.target.value)} />
            </label>
            <label className="connection-issue-verify">
              <input type="checkbox" checked={verified} onChange={(event) => setVerified(event.target.checked)} />
              I confirm the resolution details for this sample incident.
            </label>
          </>
        )}
        <div className="connection-issue-actions">
          <button type="button" onClick={onClose}>Cancel</button>
          <button type="submit" className="connection-issue-primary" disabled={!ready}>
            {retry ? 'Simulate Retry' : 'Confirm Resolution'}
          </button>
        </div>
      </form>
    </dialog>
  )
}

export default function ConnectionIssuesPage({ initialIssueId = null, accessToken, onSignOut } = {}) {
  return accessToken || demoDataEnabled ? <ConnectionIssuesView initialIssueId={initialIssueId} accessToken={accessToken} onSignOut={onSignOut} /> : (
    <section className="connection-issues-page">
      <h1>Connection Issues</h1>
      <p role="status">Connection incidents are currently unavailable.</p>
    </section>
  )
}

function ConnectionIssuesView({ initialIssueId, accessToken, onSignOut }) {
  const live = Boolean(accessToken)
  const [issues, setIssues] = useState(() => live ? [] : sampleIssues)
  const [request, setRequest] = useState({ loading: live })
  const [page, setPage] = useState(0)
  const [reload, setReload] = useState(0)

  useEffect(() => {
    if (!accessToken) return undefined
    const controller = new AbortController()
    const { signal } = controller
    listStaffConnectionIssues(accessToken, { limit: pageSize + 1, offset: page * pageSize, signal }).then((records) => {
      if (signal.aborted) return
      setIssues(records.slice(0, pageSize).map(toIssue))
      setRequest({ hasNext: records.length > pageSize })
    }).catch((error) => {
      if (signal.aborted) return
      if (error instanceof StaffSessionError) onSignOut?.()
      else setRequest({ error: 'Could not load connection issues. Please try again.' })
    })
    return () => controller.abort()
  }, [accessToken, onSignOut, page, reload])

  function changePage(nextPage) {
    setIssues([])
    setRequest({ loading: true })
    setPage(nextPage)
    setReload((attempt) => attempt + 1)
  }
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('All')
  const [severity, setSeverity] = useState('All')
  const [selectedId, setSelectedId] = useState(initialIssueId)
  const [detailSection, setDetailSection] = useState('Overview')
  const [resolutionReason, setResolutionReason] = useState('')
  const [action, setAction] = useState(null)
  const [notice, setNotice] = useState('')
  const [retrying, setRetrying] = useState(false)
  const detailTitleRef = useRef(null)
  const listTitleRef = useRef(null)
  const returnIssueRef = useRef(null)
  const actionTriggerRef = useRef(null)

  const selected = issues.find((issue) => issue.id === selectedId)
  const query = search.trim().toLowerCase()
  const visible = issues.filter((issue) =>
    (status === 'All' || issue.status === status)
    && (severity === 'All' || issue.severity === severity)
    && [issue.id, issue.customer, issue.receipt, issue.title, issue.node, issue.paymentId].some((value) => String(value ?? '').toLowerCase().includes(query)),
  )
  const unresolved = issues.filter((issue) => issue.status !== 'Resolved')
  const metrics = live ? [
    ['Unresolved Issues', request.loading || request.error ? 'Unavailable' : issues.length, 'Paid cases on this page'],
    ['Failed Activations', request.loading || request.error ? 'Unavailable' : issues.filter((issue) => issue.status === 'Activation Failed').length, 'Paid failures on this page'],
    ['Activation Pending', request.loading || request.error ? 'Unavailable' : issues.filter((issue) => issue.status === 'Awaiting activation').length, 'Waiting cases on this page'],
    ['Resolved', 'Unavailable', 'Resolution records unavailable'],
  ] : [
    ['Unresolved Issues', unresolved.length, 'Require operator review'],
    ['Failed Activations', unresolved.filter((issue) => issue.retryable).length, 'Confirmed payments awaiting access'],
    ['Activation Pending', unresolved.filter((issue) => issue.payment === 'Pending').length, 'Awaiting payment confirmation'],
    ['Resolved', issues.length - unresolved.length, 'Closed in this demo'],
  ]

  useEffect(() => {
    if (selectedId) {
      detailTitleRef.current?.focus()
    } else if (returnIssueRef.current) {
      const opener = document.getElementById(`inspect-${returnIssueRef.current}`)
      const destination = opener ?? listTitleRef.current
      destination?.focus()
      returnIssueRef.current = null
    }
  }, [selectedId])

  function openConfirmation(event, nextAction) {
    actionTriggerRef.current = event.currentTarget
    setAction(nextAction)
  }

  function closeConfirmation() {
    setAction(null)
    requestAnimationFrame(() => {
      const trigger = actionTriggerRef.current
      if (trigger?.isConnected) trigger.focus()
      else detailTitleRef.current?.focus()
    })
  }

  function confirmAction({ category, note }) {
    const resolving = action === 'resolve'
    setIssues((current) => current.map((issue) => issue.id !== selectedId ? issue : {
      ...issue,
      ...(resolving
        ? { status: 'Resolved', resolution: { category, note } }
        : { retryCount: (issue.retryCount ?? 0) + 1 }),
    }))
    setNotice(resolving ? 'Issue resolved in this demo.' : 'Simulated retry recorded. Internet access status is unchanged.')
    closeConfirmation()
  }

  async function retryActivation() {
    if (!selected || retrying) return
    setRetrying(true)
    setNotice('')
    try {
      const result = await retryStaffActivation(accessToken, selected.paymentId)
      if (result.outcome === 'activated') {
        setSelectedId(null)
        changePage(page)
        setNotice('Access confirmed. No new payment was requested.')
      } else {
        setNotice('Access is still unconfirmed. The payment remains recorded.')
      }
    } catch (error) {
      if (error instanceof StaffSessionError) onSignOut?.()
      else setNotice('Could not retry access. Check the payment and package status.')
    } finally {
      setRetrying(false)
    }
  }

  if (selected) {
    return (
      <section className="connection-issues-page">
        <button type="button" onClick={() => { setSelectedId(null); setNotice(''); setDetailSection('Overview'); setResolutionReason('') }}>‹ Back to Connection Issues</button>
        <header className="connection-issue-panel connection-issue-detail-header">
          <div>
            <p className="connection-issue-eyebrow">{selected.id}{!live && ' · Demo issue'}</p>
            <h1 ref={detailTitleRef} tabIndex={-1}>{selected.title}</h1>
            <p>{selected.description}</p>
            <IssueBadge value={selected.status} /> {!live && <IssueBadge value={selected.severity} />}
          </div>
          {live && (
            <button type="button" className="connection-issue-primary"
              disabled={retrying} onClick={retryActivation}>
              {retrying ? 'Checking access…' : 'Retry access'}
            </button>
          )}
          {!live && selected.retryable && selected.status !== 'Resolved' && (
            <button type="button" className="connection-issue-primary" onClick={(event) => openConfirmation(event, 'retry')}>Retry Activation Handshake</button>
          )}
        </header>

        <nav className="connection-issue-actions" aria-label="Issue detail sections">
          {['Overview', 'Event Timeline', 'Technical Diagnostics'].map((section) => (
            <button type="button" key={section} aria-pressed={detailSection === section} onClick={() => setDetailSection(section)}>{section}</button>
          ))}
        </nav>

        {detailSection === 'Overview' && (
          <div className="connection-issue-detail-grid">
            <div className="connection-issue-stack">
              <section className="connection-issue-panel">
                <h2>Problem Summary</h2>
                <div className="connection-issue-problem"><p>{selected.description}</p></div>
                {selected.retryable && <div className="connection-issue-callout"><strong>Recommended Next Action</strong><p>Verify gateway reachability, then review the activation retry.</p></div>}
              </section>
              <section className="connection-issue-panel">
                <h2>Incident Key Metadata</h2>
                <dl className="connection-issue-metadata">
                  {[
                    ['Customer', selected.customer], ['Linked payment', selected.receipt],
                    ['Payment status', selected.payment],
                    ['Activation status', live ? selected.status : selected.retryable ? 'Activation Failed' : selected.payment === 'Pending' ? 'Not Requested' : 'See incident summary'],
                    ...(live ? [['Payment ID', selected.paymentId], ['Purchase ID', selected.purchaseId]] : []),
                    [live ? 'Last updated (EAT)' : 'Reported time', selected.time], ['Current status', selected.status],
                  ].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
                </dl>
              </section>
              <section className="connection-issue-panel">
                <h2>Resolution &amp; Closure</h2>
                {selected.resolution && <><strong>{selected.resolution.category}</strong><p>{selected.resolution.note}</p></>}
                {live && <button type="button" className="connection-issue-primary" disabled>Mark as Resolved</button>}
                {!live && selected.status !== 'Resolved' && (
                  <div className="connection-issue-stack">
                    <label>Recorded Resolution Reason
                      <textarea value={resolutionReason} onChange={(event) => setResolutionReason(event.target.value)} rows={3} placeholder="Explain what resolved this incident" />
                    </label>
                    <button type="button" className="connection-issue-primary" onClick={(event) => openConfirmation(event, 'resolve')}>Mark as Resolved</button>
                  </div>
                )}
              </section>
            </div>
            <aside className="connection-issue-stack">
              <section className="connection-issue-panel">
                <h2>Customer Details</h2>
                <strong>{selected.customer}</strong>
                {selected.id === 'ISS-4091' && <p>+254 722 890 123</p>}
              </section>
              <section className="connection-issue-panel">
                <h2>{selected.payment === 'Confirmed' ? 'Verified Payment' : 'Linked Payment'}</h2>
                <p>{selected.receipt}</p>
                <IssueBadge value={selected.payment} />
                {selected.id === 'ISS-4091' && <p>KES 100 · Daraja · {selected.time}</p>}
              </section>
            </aside>
          </div>
        )}

        {detailSection === 'Event Timeline' && (
          <section className="connection-issue-panel">
            <h2>Event Timeline</h2>
            <ol>
              <li>{selected.time} · {live ? 'Last session update (EAT)' : 'Sample incident reported'}</li>
              {selected.retryable && <li>Payment verified, activation requested, and router acknowledgement timed out.</li>}
              {selected.retryCount > 0 && <li>{selected.retryCount} simulated activation {selected.retryCount === 1 ? 'retry' : 'retries'} recorded</li>}
              {selected.resolution && <li>Resolved in preview: {selected.resolution.category}. {selected.resolution.note}</li>}
            </ol>
          </section>
        )}

        {detailSection === 'Technical Diagnostics' && (
          <section className="connection-issue-panel">
            <h2>Technical Diagnostics</h2>
            {live ? <p>{selected.description}</p> : <p>Gateway {selected.node} · Sample incident {selected.id}</p>}
            {selected.retryable && <p>Router CoA acknowledgement timed out. The paid session timer has yet to start.</p>}
            <p>{live ? 'Live gateway diagnostics are unavailable.' : 'Live gateway diagnostics are unavailable in this preview.'}</p>
          </section>
        )}

        {notice && <p role="status">{notice}</p>}
        {action && <IssueConfirmation action={action} issue={selected} reason={resolutionReason} onClose={closeConfirmation} onConfirm={confirmAction} />}
      </section>
    )
  }

  return (
    <section className="connection-issues-page">
      <header>
        <p className="connection-issue-eyebrow">Network Operations / Incident Queue</p>
        <h1 ref={listTitleRef} tabIndex={-1}>Connection Issues</h1>
        <p>{live ? 'Review sessions where payment succeeded and activation failed.' : 'Review subscriber access failures and network incidents.'}</p>
      </header>
      {!live && <p className="connection-issue-demo"><strong>Demo data.</strong> Incident actions are simulated.</p>}

      <section className="connection-issue-metrics" aria-label="Incident summary">
        {metrics.map(([label, value, description]) => (
          <article className="connection-issue-panel" key={label}>
            <h2>{label}</h2><strong>{value}</strong><p>{description}</p>
          </article>
        ))}
      </section>

      {!live && <aside className="connection-issue-problem connection-issue-alert">
        <span><strong>Sample system incident</strong> · Westlands gateway CoA queue delay</span>
        <button type="button" onClick={() => { returnIssueRef.current = 'ISS-4091'; setSelectedId('ISS-4091') }}>View Details</button>
      </aside>}

      <section className="connection-issue-panel connection-issue-filters" aria-label="Filter incidents">
        <input type="search" aria-label="Search connection issues" placeholder={live ? 'Search this page by session, customer or payment' : 'Search incident, customer, receipt, or node'} value={search} onChange={(event) => setSearch(event.target.value)} />
        {live ? (
          <button type="button" disabled={request.loading} onClick={() => changePage(page)}>Refresh</button>
        ) : (
          <>
          <div className="connection-issue-actions" role="group" aria-label="Filter by status">
            {statusFilters.map((item) => <button type="button" key={item} aria-pressed={status === item} onClick={() => setStatus(item)}>{item}</button>)}
          </div>
          <select aria-label="Filter by severity" value={severity} onChange={(event) => setSeverity(event.target.value)}>
            <option value="All">All Severities</option>
            {['High', 'Medium', 'Low'].map((item) => <option key={item}>{item}</option>)}
          </select>
          </>
        )}
      </section>

      <section className="connection-issue-table-panel" aria-label="Incident results">
        <div className="connection-issue-table-scroll" role="region" aria-label="Scrollable incident table" tabIndex={0}>
          <table>
            <thead><tr>{[live ? 'Session reference' : 'Issue reference', 'Customer', live ? 'Payment reference' : 'M-Pesa receipt', 'Issue type', live ? 'Last updated (EAT)' : 'Reported', 'Status', 'Action'].map((item) => <th scope="col" key={item}>{item}</th>)}</tr></thead>
            <tbody>
              {visible.map((issue) => (
                <tr key={issue.id}>
                  <th scope="row">{issue.id}{!live && <small>{issue.severity} priority</small>}</th>
                  <td>{issue.customer}</td>
                  <td>{issue.receipt}</td>
                  <td>{issue.title}</td>
                  <td>{issue.time}</td>
                  <td><IssueBadge value={issue.status} /></td>
                  <td><button id={`inspect-${issue.id}`} type="button" aria-label={`View details for ${issue.id}`} onClick={() => {
                    returnIssueRef.current = issue.id
                    setSelectedId(issue.id)
                  }}>View Details</button></td>
                </tr>
              ))}
              {!visible.length && <tr><td colSpan={7}>
                {live ? request.error ? <span role="alert">{request.error}</span>
                  : <span role="status">{request.loading ? 'Loading connection issues…' : issues.length ? 'No records match your search.' : 'No paid customers are waiting for activation.'}</span>
                  : 'No sample incidents match your filters.'}
              </td></tr>}
            </tbody>
          </table>
        </div>
        <p className="connection-issue-results" aria-live="polite">{live ? !request.error && !request.loading && `${visible.length} of ${issues.length} records on this page` : `Showing ${visible.length} of ${issues.length} sample incidents`}</p>
        {live && (page > 0 || request.hasNext) && (
          <nav className="connection-issue-actions" aria-label="Connection issue pages">
            <button type="button" disabled={!page || request.loading} onClick={() => changePage(page - 1)}>Previous</button>
            <span>Page {page + 1}</span>
            <button type="button" disabled={!request.hasNext || request.loading} onClick={() => changePage(page + 1)}>Next</button>
          </nav>
        )}
      </section>

      <aside className="connection-issue-panel">
        <strong>Operational Guardrail</strong>
        <p>{live ? 'Retry and resolution are unavailable in this view.' : 'Retrying activation uses the existing payment. Paid time begins when the network confirms access.'}</p>
      </aside>
    </section>
  )
}
