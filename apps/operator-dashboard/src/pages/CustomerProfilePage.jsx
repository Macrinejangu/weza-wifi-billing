import { useEffect, useRef, useState } from 'react'
import { demoDataEnabled } from '../../../shared/demoMode.js'
import '../styles/customer-profile.css'

const sections = ['Overview', 'Subscriptions & Packages', 'Payment History', 'Devices & Sessions', 'Activity & Audit Log']

const aminaSnapshot = {
  device: 'iPhone 15 Pro',
  node: 'AP-Westlands-02',
  ip: '192.0.2.118',
  mac: '02:00:00:00:00:18',
  session: 'SES-DEMO-001',
  receipt: 'RJ92MN41P0',
  amount: 250,
}

function Details({ rows }) {
  return <dl className="subscriber-details">{rows.map(([label, value]) => (
    <div key={label}><dt>{label}</dt><dd>{value ?? 'Unavailable'}</dd></div>
  ))}</dl>
}

export default function CustomerProfilePage({ customer, onBack, backLabel = 'Customers Directory' }) {
  if (!demoDataEnabled || !customer) return <section className="subscriber-page"><h1>Customer Profile</h1><p role="status">Customer details are currently unavailable.</p></section>
  return <DemoCustomerProfile customer={customer} onBack={onBack} backLabel={backLabel} />
}

function DemoCustomerProfile({ customer, onBack, backLabel }) {
  const [section, setSection] = useState(sections[0])
  const heading = useRef(null)
  useEffect(() => { heading.current?.focus() }, [])

  const snapshot = customer.id === 'CUS-001842' ? aminaSnapshot : null
  const payment = customer.payment
  const plan = customer.plan
  const hasQuota = typeof customer.quota === 'number' && customer.quota > 0 && typeof customer.used === 'number'
  const remaining = hasQuota ? Math.max(0, customer.quota - customer.used) : null
  const initials = customer.name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()

  const subscription = (
    <section className="subscriber-card">
      <div className="subscriber-card-heading">
        <div><p className="subscriber-eyebrow">Sample Subscription</p><h2>{plan ?? 'Package unavailable'}</h2></div>
        <span className="subscriber-badge">{customer.status ?? 'Status unavailable'}</span>
      </div>
      {hasQuota ? (
        <div className="subscriber-quota">
          <strong>{remaining.toLocaleString('en-KE', { maximumFractionDigits: 1 })} GB</strong> remaining of {customer.quota} GB
          <progress aria-label="Sample data balance remaining" value={remaining} max={customer.quota} />
        </div>
      ) : <p>Quota details are unavailable for this record.</p>}
      <Details rows={[[ 'Sample expiry', customer.expiresOn ], [ 'Package amount', customer.price == null ? null : `KES ${customer.price.toLocaleString('en-KE')}` ]]} />
    </section>
  )

  const connection = (
    <section className="subscriber-card">
      <div className="subscriber-card-heading"><h2>Connection Summary</h2><span className="subscriber-badge">{customer.connection ?? 'Unavailable'}</span></div>
      <Details rows={[
        ['Current device', snapshot?.device], ['Access point', snapshot?.node],
        ['Session ID', snapshot?.session], ['Sample IP / MAC', snapshot ? `${snapshot.ip} / ${snapshot.mac}` : null],
      ]} />
    </section>
  )

  return (
    <section className="subscriber-page">
      <div className="subscriber-breadcrumb">
        <button type="button" onClick={onBack}>‹ Back to {backLabel}</button>
        <span>Customers / {customer.name}</span>
      </div>
      <header className="subscriber-card subscriber-hero">
        <span className="subscriber-avatar" aria-hidden="true">{initials}</span>
        <div>
          <p className="subscriber-eyebrow">Customer Profile · Demo</p>
          <h1 ref={heading} tabIndex={-1}>{customer.name}</h1>
          <div className="subscriber-actions">
            {customer.status && <span className="subscriber-badge">{customer.status}</span>}
            {customer.mpesaVerified && <span className="subscriber-chip">M-Pesa Verified · Sample</span>}
          </div>
          <p>{customer.phone}</p>
          {customer.id && <p>{customer.id} · Registered {customer.registeredOn}</p>}
        </div>
        <div className="subscriber-actions subscriber-hero-actions">
          <button type="button" disabled>Edit Customer Info</button>
          <button type="button" disabled>Send SMS Notice</button>
          <button type="button" className="subscriber-primary" disabled>Send M-Pesa Renewal STK</button>
        </div>
      </header>
      <p className="subscriber-note">Sample records only. Customer edits, SMS, and renewal requests are unavailable.</p>
      <nav className="subscriber-tabs" aria-label="Customer profile sections">
        {sections.map((label) => <button type="button" aria-pressed={section === label} key={label} onClick={() => setSection(label)}>{label}</button>)}
      </nav>
      {section === 'Overview' && (
        <div className="subscriber-columns">
          <div className="subscriber-stack">{subscription}{connection}</div>
          <aside className="subscriber-card">
            <h2>Customer Information</h2>
            <Details rows={[[ 'Full name', customer.name ], [ 'Phone', customer.phone ], [ 'Email address', snapshot ? 'amina@example.com' : null ], [ 'Registration date', customer.registeredOn ]]} />
            {snapshot && <div className="subscriber-spend"><span>Illustrative lifetime spend</span><strong>KES 14,200</strong></div>}
            {!customer.id && <p>This profile shows information from the selected demo transaction.</p>}
          </aside>
        </div>
      )}
      {section === 'Subscriptions & Packages' && subscription}
      {section === 'Devices & Sessions' && connection}
      {section === 'Payment History' && (
        <section className="subscriber-card"><h2>Payment History</h2>
          {payment || snapshot
            ? <Details rows={[[ 'Sample reference', payment?.receipt ?? snapshot.receipt ], [ 'Amount', `KES ${(payment?.amount ?? snapshot.amount).toLocaleString('en-KE')}` ], [ 'Payment status', payment?.paymentStatus ?? 'Confirmed' ], [ 'Date', payment?.time ]]} />
            : <p>No sample payments are linked to this customer.</p>}
        </section>
      )}
      {section === 'Activity & Audit Log' && (
        <section className="subscriber-card"><h2>Activity &amp; Audit Log</h2>
          {snapshot ? <p>Sample lease SES-DEMO-001 appears in the dashboard snapshot.</p> : <p>No sample audit events are linked to this record.</p>}
        </section>
      )}
    </section>
  )
}
