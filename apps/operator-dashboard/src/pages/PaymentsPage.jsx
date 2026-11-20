import { useEffect, useMemo, useRef, useState } from 'react'
import { demoDataEnabled } from '../../../shared/demoMode.js'
import '../styles/payments.css'

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
  const tone = ['Confirmed', 'Complete'].includes(status)
    ? 'success'
    : ['Pending', 'Not started'].includes(status) ? 'pending' : 'failed'

  return (
    <span className={`payment-status-pill ${type}-${tone}`}>
      <span />{type === 'provisioning'
        ? ({ Complete: 'Active', Failed: 'Activation Failed', 'Not started': 'Not Requested' })[status]
        : status}
    </span>
  )
}

function TransactionDrawer({ transaction, trigger, onClose, onInspectIssue }) {
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
  const initials = transaction.customer.split(' ').slice(0, 2).map((part) => part[0]).join('')
  const sampleTime = transaction.time.split(', ')[1]
  const events = issueId
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
            <p className="payment-drawer-context"><span>Daraja STK</span> Cluster KE-NBO-01 · Demo</p>
            <h2 id="payment-drawer-title">Payment Details</h2>
            <p className="payment-reference">Daraja transaction #{transaction.receipt}</p>
          </div>
          <button ref={closeButtonRef} type="button" className="payment-icon-button" aria-label="Close transaction details" onClick={onClose}>×</button>
        </header>

        <div className="payment-drawer-body">
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
              <button type="button" className="payment-drawer-link" onClick={() => setDrawerNotice('The full Customer Profile screen is pending. Subscriber details are shown below.')}>View Profile <span aria-hidden="true">→</span></button>
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
        </div>

        <footer className="payment-drawer-footer">
          <p className="payment-demo-note" role="status">{drawerNotice || 'Illustrative transaction and audit events.'}</p>
          <div className="payment-drawer-actions">
            <button type="button" className="payment-secondary-button" onClick={onClose}>Close Drawer</button>
            {issueId && <button type="button" className="payment-primary-button" onClick={inspectRelatedIssue}>View Issue {issueId}</button>}
          </div>
        </footer>
      </aside>
    </div>
  )
}

export default function PaymentsPage({ onInspectIssue }) {
  return demoDataEnabled ? <DemoPaymentsPage onInspectIssue={onInspectIssue} /> : (
    <section className="payment-monitor-page">
      <h1>Payments</h1>
      <p role="status">Payment records are currently unavailable.</p>
    </section>
  )
}

function DemoPaymentsPage({ onInspectIssue }) {
  const [activeFilter, setActiveFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [selectedPackage, setSelectedPackage] = useState('')
  const [showFilterRules, setShowFilterRules] = useState(false)
  const [inspection, setInspection] = useState(null)
  const [notice, setNotice] = useState('')

  const visibleTransactions = useMemo(() => {
    const query = search.trim().toLowerCase()

    return initialTransactions.filter((transaction) => {
      const matchesFilter = activeFilter === 'all' || transaction.paymentStatus === activeFilter
      const matchesPackage = !selectedPackage || transaction.package === selectedPackage
      const matchesSearch = !query || [
        transaction.customer, transaction.phone, transaction.receipt, transaction.id,
      ].some((value) => value.toLowerCase().includes(query))

      return matchesFilter && matchesPackage && matchesSearch
    })
  }, [activeFilter, search, selectedPackage])

  function exportCsv() {
    const headings = ['Transaction ID', 'Customer', 'Phone', 'Amount (KES)', 'M-PESA Receipt', 'Payment Status', 'Provisioning Status', 'Package', 'Time']
    const rows = visibleTransactions.map((item) => [
      item.id, item.customer, item.phone, item.amount, item.receipt,
      item.paymentStatus, item.provisioningStatus, item.package, item.time,
    ])
    const csv = [headings, ...rows]
      .map((row) => row.map((value) => `"${String(typeof value === 'string' && /^[=+@\-]/.test(value) ? "'" + value : value).replaceAll('"', '""')}"`).join(','))
      .join('\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }))
    const link = document.createElement('a')
    link.href = url
    link.download = 'weza-payment-demo-transactions.csv'
    link.click()
    URL.revokeObjectURL(url)
    setNotice('Demo transaction CSV exported.')
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
          <button type="button" className="payment-secondary-button" onClick={() => setNotice('Manual STK is a preview only. No payment prompt was sent.')}>
            <span className="material-symbols-outlined" aria-hidden="true">sensors</span>Manual STK
          </button>
          <button type="button" className="payment-secondary-button" aria-expanded={showFilterRules} aria-controls="payment-filter-rules" onClick={() => setShowFilterRules(!showFilterRules)}>
            <span className="material-symbols-outlined" aria-hidden="true">tune</span>Filter Rules
          </button>
          <button type="button" className="payment-secondary-button" onClick={exportCsv} disabled={!visibleTransactions.length}>
            <span className="material-symbols-outlined" aria-hidden="true">download</span>Export CSV
          </button>
        </div>
      </div>

      <p className="payment-monitor-demo-banner"><strong>Demo data</strong> · KPI figures are illustrative. The table shows six sample transactions for {sampleDate}.</p>
      {notice && <p className="payment-monitor-notice" role="status">{notice}</p>}

      <section className="payment-monitor-overview" aria-label="Illustrative payment metrics">
        {metrics.map(({ label, value, note, icon }) => (
          <article key={label} className={`payment-monitor-kpi-card ${icon === 'error' ? 'payment-monitor-kpi-attention' : ''}`}>
            <div className="payment-monitor-kpi-top">
              <span>{label}</span>
              <span className="material-symbols-outlined" aria-hidden="true">{icon}</span>
            </div>
            <strong>{value}</strong>
            <p>{note}</p>
          </article>
        ))}
      </section>

      <section className="payment-monitor-filters" aria-label="Payment filters">
        <div className="payment-monitor-toolbar">
          <div className="payment-monitor-filter-group" role="group" aria-label="Filter payments by status">
            {filters.map(({ label, value }) => (
              <button key={value} type="button" className={activeFilter === value ? 'active' : ''} aria-pressed={activeFilter === value} onClick={() => setActiveFilter(value)}>
                {label} <span>{initialTransactions.filter((item) => value === 'all' || item.paymentStatus === value).length}</span>
              </button>
            ))}
          </div>
          <div className="payment-monitor-filter-fields">
            <label className="payment-monitor-search">
              <span className="material-symbols-outlined" aria-hidden="true">search</span>
              <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search receipt, phone, or customer" aria-label="Search payments" />
            </label>
            <span className="payment-monitor-date">{sampleDate} · EAT</span>
            <select value={selectedPackage} onChange={(event) => setSelectedPackage(event.target.value)} aria-label="Filter payments by package">
              <option value="">All Packages</option>
              {packages.map((name) => <option key={name}>{name}</option>)}
            </select>
          </div>
        </div>
        <div className="payment-monitor-filter-rules" id="payment-filter-rules" hidden={!showFilterRules}>
          <p>Search, payment status, and package filters apply together. CSV export uses the matching rows.</p>
          <button type="button" className="payment-secondary-button" onClick={() => {
            setActiveFilter('all')
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
                {['Transaction ref', 'Customer & phone', 'Package', 'Amount', 'Time (EAT)', 'Payment status', 'Internet access', 'Action'].map((title) => (
                  <th key={title} scope="col">{title}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visibleTransactions.map((transaction) => (
                <tr key={transaction.id}>
                  <th scope="row" className="payment-monitor-reference-cell">{transaction.receipt}</th>
                  <td><div className="payment-monitor-customer-cell"><strong>{transaction.customer}</strong><span>{transaction.phone}</span></div></td>
                  <td><span className="payment-monitor-package">{transaction.package}</span></td>
                  <td className="payment-monitor-amount-cell">{formatAmount(transaction.amount)}</td>
                  <td>{transaction.time.split(', ')[1]}</td>
                  <td><StatusPill status={transaction.paymentStatus} /></td>
                  <td><StatusPill status={transaction.provisioningStatus} type="provisioning" /></td>
                  <td>
                    <button
                      type="button"
                      className="payment-monitor-view-button"
                      aria-label={`Inspect payment for ${transaction.customer}`}
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
              {visibleTransactions.length === 0 && <tr><td className="payment-monitor-empty" colSpan={8}>No transactions match your search or selected filter.</td></tr>}
            </tbody>
          </table>
        </div>

        <div className="payment-monitor-table-footer">
          <span aria-live="polite">Showing {visibleTransactions.length} of {initialTransactions.length} sample transactions</span>
          <span className="payment-monitor-sync-footnote"><span /> Local preview · No gateway sync</span>
        </div>
      </section>

      <p className="payment-monitor-page-disclaimer">Illustrative payment records and KPI figures. This page is not connected to Safaricom Daraja, a payment database, or RADIUS.</p>

      {inspection && (
        <TransactionDrawer
          transaction={inspection.transaction}
          trigger={inspection.trigger}
          onInspectIssue={onInspectIssue}
          onClose={() => setInspection(null)}
        />
      )}
    </section>
  )
}
