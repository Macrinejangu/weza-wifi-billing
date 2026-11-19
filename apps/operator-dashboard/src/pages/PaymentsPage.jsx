import { useMemo, useState } from 'react'
import '../styles/payments.css'

const initialTransactions = [
  { id: 'PAY-00623', customer: 'Dennis Kiprono', phone: '+254 722 111 234', amount: 250, receipt: 'RJ92MN41P0', paymentStatus: 'Confirmed', provisioningStatus: 'Failed', package: 'Weekly Plus 10GB', time: '19 Nov 2026, 08:42:16', node: 'AP-NBO-014', reference: 'STK-REQ-88421' },
  { id: 'PAY-00622', customer: 'Amina Wanjiku', phone: '+254 712 345 678', amount: 900, receipt: 'QK82PL51A7', paymentStatus: 'Confirmed', provisioningStatus: 'Complete', package: 'Monthly FastTrack 50GB', time: '19 Nov 2026, 08:38:04', node: 'AP-NBO-008', reference: 'STK-REQ-88420' },
  { id: 'PAY-00621', customer: 'Kevin Omondi', phone: '+254 701 987 654', amount: 50, receipt: 'MN72TR19B4', paymentStatus: 'Confirmed', provisioningStatus: 'Complete', package: '24-Hour Day Pass', time: '19 Nov 2026, 08:31:49', node: 'AP-NBO-011', reference: 'STK-REQ-88419' },
  { id: 'PAY-00620', customer: 'Grace Mwangi', phone: '+254 734 555 666', amount: 250, receipt: 'Pending', paymentStatus: 'Pending', provisioningStatus: 'Not started', package: 'Weekly Plus 10GB', time: '19 Nov 2026, 08:26:12', node: 'AP-NBO-014', reference: 'STK-REQ-88418' },
  { id: 'PAY-00619', customer: 'Brian Kipchoge', phone: '+254 711 222 333', amount: 20, receipt: 'LK62HG81C3', paymentStatus: 'Confirmed', provisioningStatus: 'Complete', package: '1-Hour Quick Connect', time: '19 Nov 2026, 08:19:37', node: 'AP-NBO-003', reference: 'STK-REQ-88417' },
]

const filters = [
  { label: 'All transactions', value: 'all' },
  { label: 'Confirmed', value: 'Confirmed' },
  { label: 'Pending', value: 'Pending' },
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
      <span />{status}
    </span>
  )
}

function TransactionDrawer({ transaction, onClose, onRetry }) {
  if (!transaction) return null

  return (
    <div className="payment-drawer-backdrop" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose()
    }}>
      <aside className="payment-drawer" role="dialog" aria-modal="true" aria-labelledby="payment-drawer-title">
        <div className="payment-drawer-heading">
          <div>
            <p className="eyebrow">TRANSACTION INSPECTOR</p>
            <h2 id="payment-drawer-title">Payment details</h2>
            <span className="payment-reference">{transaction.id}</span>
          </div>
          <button type="button" className="payment-icon-button" aria-label="Close transaction details" onClick={onClose}>×</button>
        </div>

        <div className="payment-drawer-amount">
          <span>Transaction amount</span>
          <strong>{formatAmount(transaction.amount)}</strong>
          <span className="payment-receipt">M-PESA receipt · {transaction.receipt}</span>
        </div>

        <section className="payment-detail-section">
          <h3>Gateway and provisioning status</h3>
          <div className="payment-detail-status-row">
            <div><span><strong>Daraja STK status</strong><small>Payment settlement</small></span></div>
            <StatusPill status={transaction.paymentStatus} />
          </div>
          <div className="payment-detail-status-row">
            <div><span><strong>Router CoA status</strong><small>Subscriber access provisioning</small></span></div>
            <StatusPill status={transaction.provisioningStatus} type="provisioning" />
          </div>
          <p className="payment-detail-note">
            {transaction.provisioningStatus === 'Failed'
              ? 'Payment confirmed. Router CoA acknowledgement timed out.'
              : transaction.provisioningStatus === 'Complete'
                ? 'Payment and access provisioning completed.'
                : 'Awaiting payment confirmation callback.'}
          </p>
        </section>

        <section className="payment-detail-section">
          <h3>Customer and billing</h3>
          <dl className="payment-detail-grid">
            <div><dt>Customer</dt><dd>{transaction.customer}</dd></div>
            <div><dt>Phone number</dt><dd>{transaction.phone}</dd></div>
            <div><dt>Package</dt><dd>{transaction.package}</dd></div>
            <div><dt>Transaction time</dt><dd>{transaction.time}</dd></div>
          </dl>
        </section>

        <section className="payment-detail-section">
          <h3>Gateway telemetry</h3>
          <dl className="payment-detail-grid">
            <div><dt>Access point</dt><dd>{transaction.node}</dd></div>
            <div><dt>STK request</dt><dd>{transaction.reference}</dd></div>
            <div className="payment-detail-full">
              <dt>Event log</dt>
              <dd className="payment-event-log">
                {transaction.provisioningStatus === 'Failed'
                  ? 'CoA-ACK timeout · No acknowledgement received'
                  : transaction.provisioningStatus === 'Complete'
                    ? 'CoA-ACK received · Access policy applied'
                    : 'Waiting for payment callback · Provisioning not initiated'}
              </dd>
            </div>
          </dl>
        </section>

        <div className="payment-drawer-actions">
          {transaction.paymentStatus === 'Confirmed' && transaction.provisioningStatus === 'Failed' && (
            <button type="button" className="payment-primary-button" onClick={() => onRetry(transaction)}>
              <span className="material-symbols-outlined">refresh</span>Retry CoA push
            </button>
          )}
          <button type="button" className="payment-secondary-button" onClick={onClose}>Close details</button>
        </div>
        <p className="payment-demo-note">Demonstration record only. No live gateway request is sent from this page.</p>
      </aside>
    </div>
  )
}

export default function PaymentsPage() {
  const [transactions] = useState(initialTransactions)
  const [activeFilter, setActiveFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [selectedTransaction, setSelectedTransaction] = useState(null)
  const [notice, setNotice] = useState('')

  const visibleTransactions = useMemo(() => {
    const query = search.trim().toLowerCase()
    return transactions.filter((transaction) => {
      const matchesFilter = activeFilter === 'all' || transaction.paymentStatus === activeFilter
      const matchesSearch = !query || [
        transaction.customer, transaction.phone, transaction.receipt, transaction.id,
      ].some((value) => value.toLowerCase().includes(query))
      return matchesFilter && matchesSearch
    })
  }, [transactions, activeFilter, search])

  function exportCsv() {
    const headings = ['Transaction ID', 'Customer', 'Phone', 'Amount (KES)', 'M-PESA Receipt', 'Payment Status', 'Provisioning Status', 'Package', 'Time']
    const rows = visibleTransactions.map((item) => [
      item.id, item.customer, item.phone, item.amount, item.receipt,
      item.paymentStatus, item.provisioningStatus, item.package, item.time,
    ])
    const csv = [headings, ...rows]
      .map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(','))
      .join('\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }))
    const link = document.createElement('a')
    link.href = url
    link.download = 'weza-payment-demo-transactions.csv'
    link.click()
    URL.revokeObjectURL(url)
    setNotice('Demo transaction CSV exported.')
  }

  function retryCoa(transaction) {
    setNotice(`CoA retry is a preview only. No request was sent for ${transaction.customer}.`)
  }

  const failedProvisioning = transactions.filter((item) => item.provisioningStatus === 'Failed').length

  return (
    <main className="payments-page">
      <div className="page-heading payments-heading">
        <div>
          <p className="eyebrow">TRANSACTION OPERATIONS</p>
          <h1>Payments &amp; Vouchers</h1>
          <p className="page-description">Monitor payment confirmations and subscriber access provisioning.</p>
        </div>
        <div className="payments-heading-actions">
          <button type="button" className="payment-secondary-button" onClick={exportCsv}>
            <span className="material-symbols-outlined">download</span>Export CSV
          </button>
          <button type="button" className="payment-primary-button" onClick={() => setNotice('Gateway sync is not connected in this demonstration.')}>
            <span className="material-symbols-outlined">sync</span>Sync gateway
          </button>
        </div>
      </div>

      <div className="payments-live-strip">
        <span className="payments-live-dot" />
        <strong>LIVE STREAM</strong>
        <span>Gateway event monitor</span>
        <span className="payments-live-demo">DEMO MODE · NOT CONNECTED</span>
      </div>

      <section className="payments-overview" aria-label="Payment overview">
        <article className="payments-kpi-card">
          <div className="payments-kpi-top"><span>Today's volume</span><span className="material-symbols-outlined">payments</span></div>
          <strong>KES 84,250</strong>
          <p><span className="payments-positive">↑ 18.4%</span> vs yesterday <small>Illustrative figure</small></p>
        </article>
        <article className="payments-kpi-card">
          <div className="payments-kpi-top"><span>Successful STK</span><span className="material-symbols-outlined">verified</span></div>
          <strong>98.2%</strong>
          <p><span className="payments-positive">612 processed</span> · 11 failed <small>Illustrative figure</small></p>
        </article>
        <article className="payments-kpi-card payments-kpi-attention">
          <div className="payments-kpi-top"><span>Failed provisioning</span><span className="material-symbols-outlined">router</span></div>
          <strong>{failedProvisioning}</strong>
          <p><span className="payments-warning">Action required</span> · Payment may be settled <small>Demo records</small></p>
        </article>
      </section>

      <section className="payments-transactions-section">
        <div className="payments-section-heading">
          <div><h2>Transaction activity</h2><p>Review payment status separately from network activation.</p></div>
          <span className="payments-timezone">Today · EAT (UTC+3)</span>
        </div>

        <div className="payments-toolbar">
          <label className="payments-search">
            <span className="material-symbols-outlined">search</span>
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search customer, phone, or receipt..." aria-label="Search payments" />
          </label>
          <div className="payments-filter-group" role="group" aria-label="Filter payments by status">
            {filters.map((filter) => (
              <button key={filter.value} type="button" className={activeFilter === filter.value ? 'active' : ''} aria-pressed={activeFilter === filter.value} onClick={() => setActiveFilter(filter.value)}>
                {filter.label}
              </button>
            ))}
          </div>
        </div>

        <div className="payments-table-wrap">
          <table className="payments-table">
            <thead>
              <tr><th>Customer</th><th>Amount</th><th>M-PESA receipt</th><th>Payment status</th><th>Provisioning</th><th><span className="payments-sr-only">Actions</span></th></tr>
            </thead>
            <tbody>
              {visibleTransactions.map((transaction) => (
                <tr key={transaction.id}>
                  <td><div className="payments-customer-cell"><strong>{transaction.customer}</strong><span>{transaction.phone}</span></div></td>
                  <td className="payments-amount-cell">{formatAmount(transaction.amount)}</td>
                  <td><span className="payments-mono">{transaction.receipt}</span><small className="payments-row-time">{transaction.time.split(', ')[1]}</small></td>
                  <td><StatusPill status={transaction.paymentStatus} /></td>
                  <td><StatusPill status={transaction.provisioningStatus} type="provisioning" /></td>
                  <td><button type="button" className="payments-view-button" onClick={() => { setSelectedTransaction(transaction); setNotice('') }}>Inspect <span className="material-symbols-outlined">arrow_forward</span></button></td>
                </tr>
              ))}
              {visibleTransactions.length === 0 && <tr><td className="payments-empty" colSpan="6">No transactions match your search or selected filter.</td></tr>}
            </tbody>
          </table>
        </div>

        <div className="payments-table-footer">
          <span>Showing {visibleTransactions.length} of {transactions.length} sample transactions</span>
          <div><button type="button" disabled aria-label="Previous page">‹</button><span>1 / 1</span><button type="button" disabled aria-label="Next page">›</button></div>
          <span className="payments-sync-footnote"><span /> Local preview · No gateway sync</span>
        </div>
      </section>

      {notice && <p className="payments-notice" role="status">{notice}</p>}
      <p className="payments-page-disclaimer">Illustrative payment records and KPI figures. This page is not connected to Safaricom Daraja, a payment database, or RADIUS.</p>

      <TransactionDrawer
        transaction={selectedTransaction}
        onClose={() => setSelectedTransaction(null)}
        onRetry={retryCoa}
      />
    </main>
  )
}
