import { useEffect, useRef, useState } from 'react'
import { getStaffPayment, listStaffPayments, StaffSessionError } from '../api.js'
import '../styles/payments.css'

const summaryCards = [
  { label: 'Collected Today', icon: 'payments' },
  { label: 'Pending Payments', icon: 'hourglass_top' },
  { label: 'Failed Payments', icon: 'error' },
]

const pageSize = 50
const statusFilters = [
  { value: '', label: 'All' },
  { value: 'successful', label: 'Successful' },
  { value: 'pending', label: 'Pending' },
  { value: 'failed', label: 'Failed' },
]
const statusColors = { successful: 'payment-success', pending: 'payment-pending', failed: 'payment-failed' }
const currency = new Intl.NumberFormat('en-KE', { style: 'currency', currency: 'KES' })
const dateTime = new Intl.DateTimeFormat('en-KE', {
  dateStyle: 'medium',
  timeStyle: 'short',
  timeZone: 'Africa/Nairobi',
})

function formatDate(value) {
  return value ? dateTime.format(new Date(value)) : 'Unavailable'
}

function formatStatus(status) {
  return status.charAt(0).toUpperCase() + status.slice(1)
}

function StatusPill({ status }) {
  return (
    <span className={`payment-status-pill ${statusColors[status] ?? ''}`}>
      <span aria-hidden="true" />
      {formatStatus(status)}
    </span>
  )
}

function PaymentDrawer({ detail, onClose }) {
  const closeButton = useRef(null)
  const drawer = useRef(null)
  const { trigger, record: payment } = detail

  useEffect(() => {
    const dialog = drawer.current
    function keepFocus(event) {
      if (!dialog.contains(event.target)) closeButton.current?.focus()
    }

    document.addEventListener('focusin', keepFocus)
    closeButton.current?.focus()
    return () => {
      document.removeEventListener('focusin', keepFocus)
      if (trigger?.isConnected) trigger.focus()
    }
  }, [trigger])

  function onKeyDown(event) {
    if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      onClose()
    }
    if (event.key === 'Tab') {
      event.preventDefault()
      closeButton.current?.focus()
    }
  }

  return (
    <div className="payment-drawer-backdrop" onMouseDown={(event) => {
      if (event.target === event.currentTarget) {
        event.preventDefault()
        onClose()
      }
    }}>
      <aside
        ref={drawer}
        className="payment-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="staff-payment-detail-title"
        onKeyDown={onKeyDown}
      >
        <header className="payment-drawer-heading">
          <div>
            <h2 id="staff-payment-detail-title">Payment details</h2>
            <p className="payment-reference">Payment #{detail.id}</p>
          </div>
          <button ref={closeButton} className="payment-icon-button" type="button" aria-label="Close details" onClick={onClose}>
            ×
          </button>
        </header>
        <div className="payment-drawer-body">
          {detail.error && <p role="alert">{detail.error}</p>}
          {!detail.error && !payment && <p role="status">Loading payment details…</p>}
          {payment && (
            <>
              <div className="payment-drawer-summary">
                <section className="payment-detail-section">
                  <h3>Amount</h3>
                  <strong className="payment-drawer-total">{currency.format(payment.amount)}</strong>
                </section>
                <section className="payment-detail-section">
                  <h3>Payment status</h3>
                  <StatusPill status={payment.status} />
                </section>
              </div>
              {payment.failure_reason && (
                <section className="payment-detail-section">
                  <h3>Failure reason</h3>
                  <p>{payment.failure_reason}</p>
                </section>
              )}
              <section className="payment-detail-section">
                <h3>Transaction details</h3>
                <dl className="payment-detail-grid">
                  <div><dt>Purchase ID</dt><dd>{payment.purchase_id}</dd></div>
                  <div><dt>Phone</dt><dd>{payment.phone_number}</dd></div>
                  <div><dt>M-Pesa receipt</dt><dd>{payment.mpesa_receipt_number || 'Unavailable'}</dd></div>
                  <div><dt>Checkout request ID</dt><dd>{payment.checkout_request_id || 'Unavailable'}</dd></div>
                  <div><dt>Created (EAT)</dt><dd>{formatDate(payment.created_at)}</dd></div>
                  {payment.paid_at && <div><dt>Paid (EAT)</dt><dd>{formatDate(payment.paid_at)}</dd></div>}
                </dl>
              </section>
            </>
          )}
        </div>
      </aside>
    </div>
  )
}

export default function StaffPaymentsPage({ accessToken, onSignOut }) {
  const [page, setPage] = useState(0)
  const [status, setStatus] = useState('')
  const [list, setList] = useState({ loading: true, records: [] })
  const [detail, setDetail] = useState(null)
  const [reload, setReload] = useState(0)
  const paymentId = detail?.id

  useEffect(() => {
    const controller = new AbortController()
    const { signal } = controller

    async function loadPayments() {
      try {
        const records = await listStaffPayments(accessToken, {
          limit: pageSize + 1,
          offset: page * pageSize,
          status,
          signal,
        })
        if (!signal.aborted) {
          if (!Array.isArray(records)) throw new Error('Invalid payment list')
          setList({ records: records.slice(0, pageSize), hasNext: records.length > pageSize })
        }
      } catch (error) {
        if (signal.aborted) return
        if (error instanceof StaffSessionError) {
          onSignOut()
        } else {
          setList({ records: [], error: 'Could not load payments. Please try again.' })
        }
      }
    }

    loadPayments()
    return () => controller.abort()
  }, [accessToken, onSignOut, page, reload, status])

  useEffect(() => {
    if (paymentId == null) return undefined
    const controller = new AbortController()
    const { signal } = controller

    async function loadPayment() {
      try {
        const record = await getStaffPayment(accessToken, paymentId, { signal })
        if (!signal.aborted) setDetail((current) => current?.id === paymentId ? { ...current, record } : current)
      } catch (error) {
        if (signal.aborted) return
        if (error instanceof StaffSessionError) {
          onSignOut()
        } else {
          setDetail((current) => current?.id === paymentId
            ? { ...current, error: 'Could not load this payment. Reopen the payment to try again.' }
            : current)
        }
      }
    }

    loadPayment()
    return () => controller.abort()
  }, [accessToken, onSignOut, paymentId])

  function changePage(nextPage) {
    setDetail(null)
    setList({ loading: true, records: [] })
    setPage(nextPage)
  }

  function changeStatus(nextStatus) {
    if (nextStatus === status) return
    changePage(0)
    setStatus(nextStatus)
  }

  function refresh() {
    setDetail(null)
    setList({ loading: true, records: [] })
    setReload((attempt) => attempt + 1)
  }

  return (
    <section className="payment-monitor-page" aria-labelledby="staff-payments-title">
      <header className="page-heading payment-monitor-heading">
        <div>
          <h1 id="staff-payments-title">Payments</h1>
          <p className="page-description">Review customer payment records.</p>
        </div>
        <div className="payment-monitor-heading-actions">
          <button className="payment-secondary-button" type="button" onClick={refresh} disabled={list.loading}>
            Refresh
          </button>
        </div>
      </header>

      <section className="payment-monitor-overview" aria-label="Payment summary">
        {summaryCards.map(({ label, icon }) => (
          <article key={label} className={`payment-monitor-kpi-card${icon === 'error' ? ' payment-monitor-kpi-attention' : ''}`}>
            <div className="payment-monitor-kpi-top">
              <span>{label}</span>
              <span className="material-symbols-outlined" aria-hidden="true">{icon}</span>
            </div>
            <strong>Unavailable</strong>
          </article>
        ))}
      </section>

      <section className="payment-monitor-filters" aria-label="Payment filters">
        <div className="payment-monitor-toolbar">
          <div className="payment-monitor-filter-group" role="group" aria-label="Filter payments by status">
            {statusFilters.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                className={status === value ? 'active' : undefined}
                aria-pressed={status === value}
                onClick={() => changeStatus(value)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {list.loading && <p role="status">Loading payments…</p>}
      {list.error && <p role="alert">{list.error}</p>}
      {!list.loading && !list.error && list.records.length === 0 && (
        <p role="status">{status ? 'No payments match this status.' : 'No payment records on this page.'}</p>
      )}

      {list.records.length > 0 && (
        <div className="payment-monitor-transactions-section">
          <div className="payment-monitor-table-wrap" role="region" aria-label="Payment records" tabIndex={0}>
            <table className="payment-monitor-table">
              <thead>
                <tr>
                  {['Transaction ref', 'Purchase ID', 'Phone', 'Amount', 'Created (EAT)', 'Payment status', 'Action'].map((title) => (
                    <th scope="col" key={title}>{title}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {list.records.map((record) => (
                  <tr
                    key={record.id}
                    style={paymentId === record.id ? { backgroundColor: '#f0edf6' } : undefined}
                  >
                    <th
                      scope="row"
                      className="payment-monitor-reference-cell"
                      style={paymentId === record.id ? { boxShadow: 'inset 3px 0 #62568c' } : undefined}
                    >
                      {record.mpesa_receipt_number || record.checkout_request_id || `Payment #${record.id}`}
                    </th>
                    <td>{record.purchase_id}</td>
                    <td>{record.phone_number}</td>
                    <td>{currency.format(record.amount)}</td>
                    <td>{formatDate(record.created_at)}</td>
                    <td><StatusPill status={record.status} /></td>
                    <td>
                      <button
                        type="button"
                        className="payment-monitor-view-button"
                        aria-label={`Inspect payment ${record.id}`}
                        aria-expanded={paymentId === record.id}
                        onClick={(event) => setDetail({ id: record.id, trigger: event.currentTarget })}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {(page > 0 || list.hasNext) && (
        <nav className="payment-monitor-table-footer" aria-label="Payment pages">
          <button className="payment-secondary-button" type="button" disabled={page === 0 || list.loading} onClick={() => changePage(page - 1)}>
            Previous
          </button>
          <span>Page {page + 1}</span>
          <button className="payment-secondary-button" type="button" disabled={!list.hasNext || list.loading} onClick={() => changePage(page + 1)}>
            Next
          </button>
        </nav>
      )}

      {detail && <PaymentDrawer detail={detail} onClose={() => setDetail(null)} />}
    </section>
  )
}
