import { useEffect, useMemo, useRef, useState } from 'react'
import { demoDataEnabled } from '../../../shared/demoMode.js'
import { getStaffPayment, listStaffPayments, StaffSessionError } from '../api.js'
import '../styles/payments.css'
import ManualStkDialog from './ManualStkDialog.jsx'

const pageSize = 50
const paymentDate = new Intl.DateTimeFormat('en-KE', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Africa/Nairobi' })
const paymentStatuses = { all: '', Confirmed: 'successful', Pending: 'pending', Failed: 'failed' }
const accessStatuses = {
  unconfirmed: 'Not started', activating: 'Awaiting activation',
  active: 'Complete', failed: 'Failed', expired: 'Expired', ended: 'Ended',
}

function toTransaction(record) {
  return {
    id: record.id,
    purchaseId: record.purchase_id,
    phone: record.phone_number,
    amount: record.amount,
    receipt: record.mpesa_receipt_number,
    reference: record.checkout_request_id,
    paymentStatus: { successful: 'Confirmed', pending: 'Pending', failed: 'Failed' }[record.status] ?? record.status,
    provisioningStatus: accessStatuses[record.access_status] ?? 'Unavailable',
    sessionId: record.session_id,
    time: record.created_at ? paymentDate.format(new Date(record.created_at)) : 'Unavailable',
    paidAt: record.paid_at ? paymentDate.format(new Date(record.paid_at)) : 'Unavailable',
    failureReason: record.failure_reason,
  }
}

const sampleDate = '19 Nov 2026'

const initialTransactions = [
  { id: 'PAY-DEMO-001', customer: 'Amina Wanjiku', phone: '+254 712 345 678', amount: 250, receipt: 'RJ92MN41P0', paymentStatus: 'Confirmed', provisioningStatus: 'Complete', package: 'Weekly Plus 10GB', time: `${sampleDate}, 14:45`, node: 'AP-DEMO-01', reference: 'STK-DEMO-001' },
  { id: 'PAY-DEMO-002', customer: 'Dennis Kiprono', phone: '+254 722 890 123', amount: 100, receipt: 'RJ92MN38X2', paymentStatus: 'Confirmed', provisioningStatus: 'Failed', package: 'Daily Unlimited', time: `${sampleDate}, 14:41`, node: 'AP-DEMO-02', reference: 'STK-DEMO-002' },
  { id: 'PAY-DEMO-003', customer: 'Faith Muthoni', phone: '+254 705 441 902', amount: 35, receipt: 'STK_PEND_884', paymentStatus: 'Pending', provisioningStatus: 'Not started', package: '3-Hour Study Pass', time: `${sampleDate}, 14:39`, node: 'AP-DEMO-03', reference: 'STK-DEMO-003' },
  { id: 'PAY-DEMO-004', customer: 'Kevin Ombati', phone: '+254 791 204 558', amount: 1200, receipt: 'RJ92MN11K9', paymentStatus: 'Confirmed', provisioningStatus: 'Complete', package: 'Monthly Kiosk', time: `${sampleDate}, 14:32`, node: 'AP-DEMO-04', reference: 'STK-DEMO-004' },
  { id: 'PAY-DEMO-005', customer: 'Lilian Cherotich', phone: '+254 748 119 023', amount: 50, receipt: 'RJ92MN09H4', paymentStatus: 'Confirmed', provisioningStatus: 'Complete', package: 'Daily Connect', time: `${sampleDate}, 14:18`, node: 'AP-DEMO-05', reference: 'STK-DEMO-005' },
  { id: 'PAY-DEMO-006', customer: 'Brian Otieno', phone: '+254 719 332 108', amount: 250, receipt: 'RJ91ZZ77L1', paymentStatus: 'Failed', provisioningStatus: 'Not started', package: 'Weekly Plus 10GB', time: `${sampleDate}, 13:54`, node: 'AP-DEMO-06', reference: 'STK-DEMO-006' },
]

const filters = [
  { label: 'All', value: 'all' },
  { label: 'Confirmed', value: 'Confirmed' },
  { label: 'Pending', value: 'Pending' },
  { label: 'Failed', value: 'Failed' },
]

function formatAmount(amount) {
  return `KES ${amount.toLocaleString('en-KE')}`
}

function StatusPill({ status, type = 'payment' }) {
  if (status === 'Unavailable') return <span className="payment-status-pill">Unavailable</span>
  const tone = ['Confirmed', 'Complete'].includes(status)
    ? 'success'
    : ['Pending', 'Not started', 'Awaiting activation'].includes(status) ? 'pending' : status === 'Failed' ? 'failed' : 'neutral'

  return (
    <span className={`payment-status-pill ${type}-${tone}`}>
      <span />{type === 'provisioning'
        ? (({ Complete: 'Active', Failed: 'Activation Failed', 'Not started': 'Not Requested' })[status] ?? status)
        : status}
    </span>
  )
}

function TransactionDrawer({ transaction, trigger, onClose, onInspectIssue, onOpenProfile, accessToken, onSignOut }) {
  const [liveDetail, setLiveDetail] = useState({ loading: true })
  const paymentId = transaction.id
  const live = Boolean(accessToken)

  useEffect(() => {
    if (!accessToken) return undefined
    const controller = new AbortController()
    const { signal } = controller
    getStaffPayment(accessToken, paymentId, { signal }).then((record) => {
      if (!signal.aborted) setLiveDetail({ record: toTransaction(record) })
    }).catch((error) => {
      if (signal.aborted) return
      if (error instanceof StaffSessionError) onSignOut?.()
      else setLiveDetail({ error: 'Could not load payment details. Close and reopen to retry.' })
    })
    return () => controller.abort()
  }, [accessToken, onSignOut, paymentId])
  const drawerRef = useRef(null)
  const closeButtonRef = useRef(null)
  const [drawerNotice, setDrawerNotice] = useState('')

  useEffect(() => {
    const drawer = drawerRef.current
    const closeButton = closeButtonRef.current
    const ownerDocument = drawer.ownerDocument

    function keepFocusInDrawer(event) {
      if (!drawer.contains(event.target)) closeButton.focus()
    }

    ownerDocument.addEventListener('focusin', keepFocusInDrawer)
    closeButton.focus()

    return () => {
      ownerDocument.removeEventListener('focusin', keepFocusInDrawer)
      if (trigger?.isConnected) trigger.focus()
    }
  }, [trigger])

  function handleKeyDown(event) {
    if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      onClose()
      return
    }

    if (event.key !== 'Tab') return

    const buttons = event.currentTarget.querySelectorAll('button:not(:disabled)')
    const first = buttons[0]
    const last = buttons[buttons.length - 1]

    if (event.shiftKey && event.target === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && event.target === last) {
      event.preventDefault()
      first.focus()
    }
  }

  const confirmed = transaction.paymentStatus === 'Confirmed'
  const activationFailed = transaction.provisioningStatus === 'Failed'
  const issueId = activationFailed ? '#ISS-4091' : null
  const initials = live ? '' : transaction.customer.split(' ').slice(0, 2).map((part) => part[0]).join('')
  const sampleTime = transaction.time.split(', ')[1]
  const events = live ? [] : issueId
    ? [
        ['14:41:02', 'Customer STK prompt accepted', 'Sample Daraja callback received', 'success'],
        ['14:41:03', 'Payment verified and receipt generated', 'Ledger balanced (+KES 100)', 'success'],
        ['14:41:04', 'Activation request dispatched', 'Sample router provisioning request', 'dispatch'],
        ['14:41:08', 'Router CoA socket timeout', 'ERR_ROUTER_COA_TIMEOUT', 'failure'],
        ['14:41:10', `Incident ${issueId} opened`, 'Flagged for operator review', 'neutral'],
      ]
    : [
        [sampleTime, 'Payment attempt recorded', 'Illustrative transaction event', 'neutral'],
        [sampleTime, `Payment ${transaction.paymentStatus.toLowerCase()}`,
          confirmed ? 'Internet access active in this sample record' : 'Internet activation was not requested',
          confirmed ? 'success' : transaction.paymentStatus === 'Failed' ? 'failure' : 'neutral'],
      ]

  function inspectRelatedIssue() {
    if (onInspectIssue) {
      onInspectIssue(issueId.slice(1))
    } else {
      setDrawerNotice(`${issueId} is a sample incident. Issue navigation is unavailable.`)
    }
  }

  return (
    <div
      className="payment-drawer-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          event.preventDefault()
          onClose()
        }
      }}
    >
      <aside
        ref={drawerRef}
        className="payment-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="payment-drawer-title"
        onKeyDown={handleKeyDown}
      >
        <header className="payment-drawer-heading">
          <div>
            {!live && <p className="payment-drawer-context"><span>Daraja STK</span> Cluster KE-NBO-01 · Demo</p>}
            <h2 id="payment-drawer-title">Payment Details</h2>
            <p className="payment-reference">{live ? `Payment #${paymentId}` : `Daraja transaction #${transaction.receipt}`}</p>
          </div>
          <button ref={closeButtonRef} type="button" className="payment-icon-button" aria-label="Close transaction details" onClick={onClose}>×</button>
        </header>

        <div className="payment-drawer-body">
          {live ? (
            <>
              {liveDetail.loading && <p role="status">Loading payment details…</p>}
              {liveDetail.error && <p role="alert">{liveDetail.error}</p>}
              {liveDetail.record && (
                <>
                  <div className="payment-drawer-summary">
                    <section className="payment-detail-section">
                      <h3>Amount</h3>
                      <strong className="payment-drawer-total">{formatAmount(liveDetail.record.amount)}</strong>
                    </section>
                    <section className="payment-detail-section">
                      <h3>Purchased plan</h3>
                      <p>Unavailable</p>
                    </section>
                  </div>
                  <section className="payment-detail-section">
                    <h3>Payment and access</h3>
                    <div className="payment-detail-status-row"><strong>Payment status</strong><StatusPill status={liveDetail.record.paymentStatus} /></div>
                    <div className="payment-detail-status-row"><strong>Internet access</strong><StatusPill status={liveDetail.record.provisioningStatus} type="provisioning" /></div>
                  </section>
                  {liveDetail.record.failureReason && (
                    <section className="payment-detail-section"><h3>Failure reason</h3><p>{liveDetail.record.failureReason}</p></section>
                  )}
                  <section className="payment-detail-section">
                    <h3>Transaction metadata</h3>
                    <dl className="payment-detail-grid">
                      <div><dt>Purchase ID</dt><dd>{liveDetail.record.purchaseId}</dd></div>
                      {liveDetail.record.sessionId != null && <div><dt>Session ID</dt><dd>{liveDetail.record.sessionId}</dd></div>}
                      <div><dt>Phone</dt><dd>{liveDetail.record.phone}</dd></div>
                      <div><dt>M-Pesa receipt</dt><dd>{liveDetail.record.receipt || 'Unavailable'}</dd></div>
                      <div><dt>Checkout request ID</dt><dd>{liveDetail.record.reference || 'Unavailable'}</dd></div>
                      <div><dt>Created (EAT)</dt><dd>{liveDetail.record.time}</dd></div>
                      <div><dt>Paid (EAT)</dt><dd>{liveDetail.record.paidAt}</dd></div>
                    </dl>
                  </section>
                </>
              )}
            </>
          ) : (
            <>
              <div className="payment-drawer-summary">
                <section className="payment-detail-section">
                  <h3>{confirmed ? 'Settled amount' : 'Requested amount'}</h3>
                  <strong className="payment-drawer-total">{formatAmount(transaction.amount)}</strong>
                  <p>{confirmed ? 'Exact match (no balance)' : 'Settlement unconfirmed'}</p>
                </section>
                <section className="payment-detail-section">
                  <h3>{confirmed ? 'Purchased plan' : 'Selected plan'}</h3>
                  <strong>{transaction.package}</strong>
                  {issueId && <p>24h / 5 Mbps cap</p>}
                </section>
              </div>

              <section className="payment-detail-section">
                <h3>Reconciliation dual-state</h3>
                <div className="payment-detail-status-row">
                  <div><strong>Payment Status</strong><small>Safaricom Daraja STK Push</small></div>
                  <StatusPill status={transaction.paymentStatus} />
                </div>
                <div className="payment-detail-status-row">
                  <div><strong>Internet Activation</strong><small>Router CoA provisioning</small></div>
                  <StatusPill status={transaction.provisioningStatus} type="provisioning" />
                </div>
              </section>

              {issueId && (
                <section className="payment-detail-section payment-related-issue">
                  <span className="material-symbols-outlined" aria-hidden="true">warning</span>
                  <div>
                    <h3>Active Issue: {issueId}</h3>
                    <p>Router CoA timed out after payment confirmation. Internet access stayed inactive.</p>
                    <button type="button" className="payment-drawer-link" onClick={inspectRelatedIssue}>Inspect Issue Details <span aria-hidden="true">→</span></button>
                  </div>
                </section>
              )}

              <section className="payment-detail-section">
                <div className="payment-detail-heading">
                  <h3>Subscriber details</h3>
                  <button type="button" className="payment-drawer-link" onClick={() => onOpenProfile ? onOpenProfile(transaction) : setDrawerNotice('Subscriber details are shown below.')}>View Profile <span aria-hidden="true">→</span></button>
                </div>
                <div className="payment-subscriber">
                  <span className="payment-subscriber-avatar" aria-hidden="true">{initials}</span>
                  <div><strong>{transaction.customer}</strong><p>{transaction.phone}</p></div>
                </div>
              </section>

              <section className="payment-detail-section">
                <h3>Transaction metadata</h3>
                <dl className="payment-detail-grid">
                  <div><dt>Payment channel</dt><dd>Daraja STK Push</dd></div>
                  <div><dt>{confirmed ? 'M-Pesa receipt' : 'Transaction reference'}</dt><dd>{transaction.receipt}</dd></div>
                  <div><dt>{confirmed ? 'Paid at' : 'Attempted at'}</dt><dd>{transaction.time} EAT</dd></div>
                  <div><dt>Network node</dt><dd>{transaction.node}</dd></div>
                </dl>
              </section>

              <section className="payment-detail-section">
                <div className="payment-detail-heading"><h3>Audit &amp; dispatch timeline</h3><small>{events.length} sample events</small></div>
                <ol className="payment-audit-timeline">
                  {events.map(([time, title, detail, tone]) => (
                    <li key={title} data-tone={tone}>
                      <small>{time} EAT</small>
                      <strong>{title}</strong>
                      <p>{detail}</p>
                    </li>
                  ))}
                </ol>
              </section>
            </>
          )}
        </div>

        <footer className="payment-drawer-footer">
          {!live && <p className="payment-demo-note" role="status">{drawerNotice || 'Illustrative transaction and audit events.'}</p>}
          <div className="payment-drawer-actions">
            <button type="button" className="payment-secondary-button" onClick={onClose}>Close Drawer</button>
            {issueId && <button type="button" className="payment-primary-button" onClick={inspectRelatedIssue}>View Issue {issueId}</button>}
          </div>
        </footer>
      </aside>
    </div>
  )
}

export default function PaymentsPage({ accessToken, onSignOut, onInspectIssue, onOpenProfile, isAdmin = false }) {
  return accessToken || demoDataEnabled ? (
    <PaymentsView accessToken={accessToken} onSignOut={onSignOut} onInspectIssue={onInspectIssue} onOpenProfile={onOpenProfile} isAdmin={isAdmin} />
  ) : (
    <section className="payment-monitor-page">
      <h1>Payments</h1>
      <p role="status">Payment records are currently unavailable.</p>
    </section>
  )
}

function PaymentsView({ accessToken, onSignOut, onInspectIssue, onOpenProfile, isAdmin }) {
  const live = Boolean(accessToken)
  const [page, setPage] = useState(0)
  const [reload, setReload] = useState(0)
  const [liveList, setLiveList] = useState({ records: [], loading: true })
  const [activeFilter, setActiveFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [selectedPackage, setSelectedPackage] = useState('')
  const [showFilterRules, setShowFilterRules] = useState(false)
  const [inspection, setInspection] = useState(null)
  const [notice, setNotice] = useState('')
  const [manualStk, setManualStk] = useState(false)

  useEffect(() => {
    if (!accessToken) return undefined
    const controller = new AbortController()
    const { signal } = controller
    listStaffPayments(accessToken, {
      status: paymentStatuses[activeFilter], limit: pageSize + 1, offset: page * pageSize, signal,
    }).then((records) => {
      if (!signal.aborted) setLiveList({ records: records.slice(0, pageSize).map(toTransaction), hasNext: records.length > pageSize })
    }).catch((error) => {
      if (signal.aborted) return
      if (error instanceof StaffSessionError) onSignOut?.()
      else setLiveList({ records: [], error: 'Could not load payments. Please try again.' })
    })
    return () => controller.abort()
  }, [accessToken, activeFilter, onSignOut, page, reload])

  function changeList(nextPage, nextFilter = activeFilter) {
    setInspection(null)
    setLiveList({ records: [], loading: true })
    setPage(nextPage)
    setActiveFilter(nextFilter)
    setReload((attempt) => attempt + 1)
  }

  const visibleTransactions = useMemo(() => {
    const query = search.trim().toLowerCase()

    const records = live ? liveList.records : initialTransactions
    return records.filter((transaction) => {
      const matchesFilter = live || activeFilter === 'all' || transaction.paymentStatus === activeFilter
      const matchesPackage = !selectedPackage || transaction.package === selectedPackage
      const matchesSearch = !query || [
        transaction.customer, transaction.phone, transaction.receipt, transaction.reference, transaction.id, transaction.purchaseId,
      ].some((value) => String(value ?? '').toLowerCase().includes(query))

      return matchesFilter && matchesPackage && matchesSearch
    })
  }, [activeFilter, search, selectedPackage, live, liveList.records])

  function exportCsv() {
    const headings = ['Transaction ID', 'Customer', 'Phone', 'Amount (KES)', 'M-PESA Receipt', 'Payment Status', 'Provisioning Status', 'Package', 'Time']
    const rows = visibleTransactions.map((item) => [
      item.id, item.customer, item.phone, item.amount, item.receipt,
      item.paymentStatus, item.provisioningStatus, item.package, item.time,
    ])
    const csv = [headings, ...rows]
      .map((row) => row.map((value) => `"${String(typeof value === 'string' && /^[\s\uFEFF]*[=+@\-]|^[\t\r\n]/.test(value) ? "'" + value : (value ?? '')).replaceAll('"', '""')}"`).join(','))
      .join('\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }))
    const link = document.createElement('a')
    link.href = url
    link.download = live ? 'weza-payments-page.csv' : 'weza-payment-demo-transactions.csv'
    link.click()
    URL.revokeObjectURL(url)
    setNotice(live ? 'Payments on this page exported.' : 'Demo transaction CSV exported.')
  }

  const packages = [...new Set(initialTransactions.map((item) => item.package))]
  const metrics = [
    { label: 'Collected Today', value: 'KES 142,850', note: '814 confirmed receipts', icon: 'payments' },
    { label: 'Pending Payments', value: '3', note: 'Awaiting M-Pesa confirmation', icon: 'hourglass_top' },
    { label: 'Failed Payments', value: '4', note: 'Cancelled or timed out', icon: 'error' },
  ]

  return (
    <section className="payment-monitor-page">
      <div className="page-heading payment-monitor-heading">
        <div>
          <p className="eyebrow">BILLING &amp; SETTLEMENT / M-PESA DARAJA GATEWAY</p>
          <h1>Payments</h1>
          <p className="page-description">Monitor and verify customer payments.</p>
        </div>
        <div className="payment-monitor-heading-actions">
          {live && <button type="button" className="payment-secondary-button" disabled={liveList.loading} onClick={() => changeList(page)}>Refresh</button>}
          {live && isAdmin && <button type="button" className="payment-secondary-button" onClick={() => setManualStk(true)}>Manual STK</button>}
          {!live && <button type="button" className="payment-secondary-button" onClick={() => setNotice('Manual STK is a preview only. No payment prompt was sent.')}>
            <span className="material-symbols-outlined" aria-hidden="true">sensors</span>Manual STK
          </button>}
          <button type="button" className="payment-secondary-button" aria-expanded={showFilterRules} aria-controls="payment-filter-rules" onClick={() => setShowFilterRules(!showFilterRules)}>
            <span className="material-symbols-outlined" aria-hidden="true">tune</span>Filter Rules
          </button>
          <button type="button" className="payment-secondary-button" onClick={exportCsv} disabled={(live && !isAdmin) || !visibleTransactions.length}>
            <span className="material-symbols-outlined" aria-hidden="true">download</span>{live ? 'Export this page' : 'Export CSV'}
          </button>
        </div>
      </div>

      {!live && <p className="payment-monitor-demo-banner"><strong>Demo data</strong> · KPI figures are illustrative. The table shows six sample transactions for {sampleDate}.</p>}
      {notice && <p className="payment-monitor-notice" role="status">{notice}</p>}

      <section className="payment-monitor-overview" aria-label={live ? 'Payment summary' : 'Illustrative payment metrics'}>
        {metrics.map(({ label, value, note, icon }) => (
          <article key={label} className={`payment-monitor-kpi-card ${icon === 'error' ? 'payment-monitor-kpi-attention' : ''}`}>
            <div className="payment-monitor-kpi-top">
              <span>{label}</span>
              <span className="material-symbols-outlined" aria-hidden="true">{icon}</span>
            </div>
            <strong>{live ? 'Unavailable' : value}</strong>
            {!live && <p>{note}</p>}
          </article>
        ))}
      </section>

      <section className="payment-monitor-filters" aria-label="Payment filters">
        <div className="payment-monitor-toolbar">
          <div className="payment-monitor-filter-group" role="group" aria-label="Filter payments by status">
            {filters.map(({ label, value }) => (
              <button key={value} type="button" className={activeFilter === value ? 'active' : ''} aria-pressed={activeFilter === value} onClick={() => live ? value !== activeFilter && changeList(0, value) : setActiveFilter(value)}>
                {label} {!live && <span>{initialTransactions.filter((item) => value === 'all' || item.paymentStatus === value).length}</span>}
              </button>
            ))}
          </div>
          <div className="payment-monitor-filter-fields">
            <label className="payment-monitor-search">
              <span className="material-symbols-outlined" aria-hidden="true">search</span>
              <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder={live ? 'Search this page by reference, phone or ID' : 'Search receipt, phone, or customer'} aria-label="Search payments" />
            </label>
            {!live && <span className="payment-monitor-date">{sampleDate} · EAT</span>}
            {!live && <select value={selectedPackage} onChange={(event) => setSelectedPackage(event.target.value)} aria-label="Filter payments by package">
              <option value="">All Packages</option>
              {!live && packages.map((name) => <option key={name}>{name}</option>)}
            </select>}
          </div>
        </div>
        <div className="payment-monitor-filter-rules" id="payment-filter-rules" hidden={!showFilterRules}>
          <p>{live ? 'Status filters apply to all records. Search applies to this page.' : 'Search, payment status, and package filters apply together. CSV export uses the matching rows.'}</p>
          <button type="button" className="payment-secondary-button" onClick={() => {
            if (live) changeList(0, 'all')
            else setActiveFilter('all')
            setSearch('')
            setSelectedPackage('')
            setNotice('')
          }}>Clear filters</button>
        </div>
      </section>

      <section className="payment-monitor-transactions-section" aria-label="Payment transactions">
        <div className="payment-monitor-table-wrap" role="region" aria-label="Scrollable transaction table" tabIndex={0}>
          <table className="payment-monitor-table">
            <thead>
              <tr>
                {['Transaction ref', (live ? 'Purchase & phone' : 'Customer & phone'), 'Package', 'Amount', 'Time (EAT)', 'Payment status', 'Internet access', 'Action'].map((title) => (
                  <th key={title} scope="col">{title}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visibleTransactions.map((transaction) => (
                <tr key={transaction.id} style={live && inspection?.transaction.id === transaction.id ? { backgroundColor: '#f0edf6' } : undefined}>
                  <th scope="row" className="payment-monitor-reference-cell">{transaction.receipt || transaction.reference || `Payment #${transaction.id}`}</th>
                  <td><div className="payment-monitor-customer-cell"><strong>{live ? `Purchase #${transaction.purchaseId}` : transaction.customer}</strong><span>{transaction.phone}</span></div></td>
                  <td><span className="payment-monitor-package">{live ? 'Unavailable' : transaction.package}</span></td>
                  <td className="payment-monitor-amount-cell">{formatAmount(transaction.amount)}</td>
                  <td>{live ? transaction.time : transaction.time.split(', ')[1]}</td>
                  <td><StatusPill status={transaction.paymentStatus} /></td>
                  <td><StatusPill status={transaction.provisioningStatus} type="provisioning" /></td>
                  <td>
                    <button
                      type="button"
                      className="payment-monitor-view-button"
                      aria-label={live ? `Inspect payment ${transaction.id}` : `Inspect payment for ${transaction.customer}`}
                      onClick={(event) => {
                        setInspection({ transaction, trigger: event.currentTarget })
                        setNotice('')
                      }}
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
              {visibleTransactions.length === 0 && <tr><td className="payment-monitor-empty" colSpan={8}>{live ? liveList.error ? <span role="alert">{liveList.error}</span> : <span role="status">{liveList.loading ? 'Loading payments…' : 'No matching payments.'}</span> : 'No transactions match your search or selected filter.'}</td></tr>}
            </tbody>
          </table>
        </div>

        <div className="payment-monitor-table-footer">
          {live ? (
            <>
              <span aria-live="polite">Page {page + 1} · {visibleTransactions.length} records</span>
              <div role="group" aria-label="Payment pages">
                <button type="button" disabled={page === 0 || liveList.loading} onClick={() => changeList(page - 1)}>Previous</button>
                <button type="button" disabled={!liveList.hasNext || liveList.loading} onClick={() => changeList(page + 1)}>Next</button>
              </div>
            </>
          ) : (
            <>
              <span aria-live="polite">Showing {visibleTransactions.length} of {initialTransactions.length} sample transactions</span>
              <span className="payment-monitor-sync-footnote"><span /> Local preview · No gateway sync</span>
            </>
          )}
        </div>
      </section>

      {!live && <p className="payment-monitor-page-disclaimer">Illustrative payment records and KPI figures. This page is not connected to Safaricom Daraja, a payment database, or RADIUS.</p>}

      {inspection && (
        <TransactionDrawer
          key={inspection.transaction.id}
          transaction={inspection.transaction}
          accessToken={accessToken}
          onSignOut={onSignOut}
          trigger={inspection.trigger}
          onInspectIssue={onInspectIssue}
          onOpenProfile={onOpenProfile}
          onClose={() => setInspection(null)}
        />
      )}
      {manualStk && isAdmin && <ManualStkDialog accessToken={accessToken} onClose={() => setManualStk(false)}
        onSignOut={onSignOut} onSent={(result) => {
          setManualStk(false)
          changeList(0, 'Pending')
          setNotice(result.simulated
            ? 'Prompt simulated. No message was sent. Payment is pending.'
            : 'Daraja accepted the test prompt. Payment is pending.')
        }} />}
    </section>
  )
}
