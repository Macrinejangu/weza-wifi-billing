import { useEffect, useRef, useState } from 'react'
import { demoDataEnabled } from '../../../shared/demoMode.js'
import '../styles/customers.css'

const initialCustomers = demoDataEnabled ? [
  { id: 'CUS-001842', name: 'Amina Wanjiku', phone: '+254 712 345 678', mpesaVerified: true, status: 'Active', plan: 'Premium Plan', price: 2500, used: 18.4, quota: 50 },
  { id: 'CUS-001841', name: 'Dennis Kiprono', phone: '+254 722 111 234', mpesaVerified: true, status: 'Active', plan: 'Basic Plan', price: 1000, used: 4.2, quota: 10 },
  { id: 'CUS-001840', name: 'Faith Mwangi', phone: '+254 733 456 789', mpesaVerified: false, status: 'Expired', plan: 'Standard Plan', price: 1500, used: 10, quota: 10 },
  { id: 'CUS-001839', name: 'Brian Otieno', phone: '+254 701 987 654', mpesaVerified: true, status: 'Active', plan: 'Premium Plan', price: 2500, used: 32.1, quota: 50 },
  { id: 'CUS-001838', name: 'Esther Njeri', phone: '+254 711 222 333', mpesaVerified: true, status: 'Active', plan: 'Basic Plan', price: 1000, used: 6.8, quota: 10 },
  { id: 'CUS-001837', name: 'Kevin Mutua', phone: '+254 720 444 555', mpesaVerified: false, status: 'Flagged', plan: 'Standard Plan', price: 1500, used: 8.6, quota: 20 },
  { id: 'CUS-001836', name: 'Grace Achieng', phone: '+254 734 555 666', mpesaVerified: true, status: 'Expired', plan: 'Basic Plan', price: 1000, used: 10, quota: 10 },
  { id: 'CUS-001835', name: 'Samuel Kariuki', phone: '+254 701 333 444', mpesaVerified: true, status: 'Active', plan: 'Standard Plan', price: 1500, used: 12.5, quota: 20 },
  { id: 'CUS-001834', name: 'Mary Chebet', phone: '+254 710 888 999', mpesaVerified: false, status: 'Flagged', plan: 'Premium Plan', price: 2500, used: 21.3, quota: 50 },
  { id: 'CUS-001833', name: 'Peter Kamau', phone: '+254 722 777 888', mpesaVerified: true, status: 'Active', plan: 'Basic Plan', price: 1000, used: 2.1, quota: 10 },
].map((customer, index) => ({
  ...customer,
  registeredOn: `2026-11-${String(10 + index).padStart(2, '0')}`,
  expiresOn: customer.status === 'Expired' ? '2026-11-18' : '2026-11-26',
  connection: ['Online', 'Offline', 'Offline', 'Online', 'Offline', 'Offline', 'Offline', 'Online', 'Offline', 'Online'][index],
})) : []

const statuses = ['All', 'Active', 'Expired', 'Flagged']

function initials(name) {
  return name.split(/\s+/).map((part) => part[0]).slice(0, 2).join('').toUpperCase()
}

function CustomerDialog({ customer, onClose, onRegister }) {
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [plan, setPlan] = useState('Basic Plan')

  const dialogRef = useRef(null)
  useEffect(() => {
    const dialog = dialogRef.current
    dialog.showModal()
    return () => dialog.close()
  }, [])

  function closeDialog(event) {
    event?.preventDefault()
    dialogRef.current.close()
    onClose()
  }

  if (customer) {
    return (
      <dialog ref={dialogRef} className="customer-modal" onCancel={closeDialog} aria-labelledby="customer-profile-title">
          <div className="customer-modal-heading">
            <div>
              <p className="eyebrow">CUSTOMER PROFILE</p>
              <h2 id="customer-profile-title">{customer.name}</h2>
            </div>
            <button type="button" className="customer-modal-close" aria-label="Close profile" onClick={closeDialog}>×</button>
          </div>
          <div className="customer-profile-grid">
            <div><span>Customer ID</span><strong>{customer.id}</strong></div>
            <div><span>Phone number</span><strong>{customer.phone}</strong></div>
            <div><span>Account status</span><strong>{customer.status}</strong></div>
            <div><span>M-PESA verification</span><strong>{customer.mpesaVerified ? 'Verified' : 'Not verified'}</strong></div>
            <div><span>Current package</span><strong>{customer.plan}</strong></div>
            <div><span>Package price</span><strong>KES {customer.price.toLocaleString('en-KE')}</strong></div>
            <div><span>Data usage</span><strong>{customer.used} / {customer.quota} GB</strong></div>
          </div>
          <p className="customer-modal-note">Demonstration profile. No live subscriber account is connected.</p>
          <button type="button" className="customer-primary-button modal-action" onClick={closeDialog}>Close profile</button>
        </dialog>
    )
  }

  function submit(event) {
    event.preventDefault()
    const packages = {
      'Basic Plan': { price: 1000, quota: 10 },
      'Standard Plan': { price: 1500, quota: 20 },
      'Premium Plan': { price: 2500, quota: 50 },
    }
    dialogRef.current.close()
    onRegister({
      id: `DEMO-${crypto.randomUUID().slice(0, 8)}`,
      name: name.trim(),
      phone: phone.trim(),
      mpesaVerified: false,
      status: 'Active',
      connection: 'Offline',
      registeredOn: new Date().toLocaleDateString('en-CA', { timeZone: 'Africa/Nairobi' }),
      expiresOn: null,
      plan,
      price: packages[plan].price,
      used: 0,
      quota: packages[plan].quota,
    })
  }

  return (
    <dialog ref={dialogRef} className="customer-modal" onCancel={closeDialog} aria-labelledby="customer-register-title">
        <div className="customer-modal-heading">
          <div>
            <p className="eyebrow">NEW SUBSCRIBER</p>
            <h2 id="customer-register-title">Register customer</h2>
          </div>
          <button type="button" className="customer-modal-close" aria-label="Close registration" onClick={closeDialog}>×</button>
        </div>
        <form className="customer-registration-form" onSubmit={submit}>
          <label>
            Customer name
            <input value={name} onChange={(event) => {
              event.target.setCustomValidity(event.target.value.trim() ? '' : 'Enter a customer name.')
              setName(event.target.value)
            }} placeholder="Enter full name" required />
          </label>
          <label>
            Phone number
            <input type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="+254 7XX XXX XXX" pattern={String.raw`\+?[0-9](?: ?[0-9]){8,14}`} required />
          </label>
          <label>
            Service package
            <select value={plan} onChange={(event) => setPlan(event.target.value)}>
              <option>Basic Plan</option>
              <option>Standard Plan</option>
              <option>Premium Plan</option>
            </select>
          </label>
          <p className="customer-modal-note">This creates a temporary demo record in this page only. It is not saved to the billing system.</p>
          <div className="customer-modal-actions">
            <button type="button" className="customer-secondary-button" onClick={closeDialog}>Cancel</button>
            <button type="submit" className="customer-primary-button">Add demo customer</button>
          </div>
        </form>
      </dialog>
  )
}

function dateLabel(date) {
  if (!date) return 'Unavailable'
  return new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeZone: 'UTC' })
    .format(new Date(date))
}

export default function CustomersPage() {
  const [customers, setCustomers] = useState(initialCustomers)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('All')
  const [packageName, setPackageName] = useState('')
  const [registeredOn, setRegisteredOn] = useState('')
  const [page, setPage] = useState(1)
  const [dialog, setDialog] = useState(null)

  const pageSize = 7
  const term = search.trim().toLowerCase()
  const phoneTerm = term.replace(/\D/g, '')
  const packages = [...new Set(customers.map((customer) => customer.plan))]
  const matchesControls = customers.filter((customer) =>
    (!packageName || customer.plan === packageName) &&
    (!registeredOn || customer.registeredOn === registeredOn) &&
    (!term || customer.name.toLowerCase().includes(term) ||
      customer.id.toLowerCase().includes(term) ||
      (/^\+?[\d\s]+$/.test(term) && customer.phone.replace(/\D/g, '').includes(phoneTerm)))
  )
  const filtered = matchesControls.filter((customer) => status === 'All' || customer.status === status)
  const pages = Math.max(1, Math.ceil(filtered.length / pageSize))
  const start = (page - 1) * pageSize
  const visible = filtered.slice(start, start + pageSize)
  const metrics = [
    { label: 'Total Registered', count: customers.length, description: 'Demo subscriber accounts', icon: 'groups' },
    { label: 'Active Online', count: customers.filter(({ connection }) => connection === 'Online').length, description: 'Demo connections online', icon: 'wifi' },
    { label: 'Suspended / Inactive', count: customers.filter(({ status }) => status === 'Expired').length, description: 'Demo accounts with expired access', icon: 'wifi_off' },
  ]

  function resetFilters() {
    setSearch('')
    setStatus('All')
    setPackageName('')
    setRegisteredOn('')
    setPage(1)
  }

  function dismissDialog() {
    dialog.trigger.focus()
    setDialog(null)
  }

  function registerCustomer(customer) {
    setCustomers((current) => [customer, ...current])
    resetFilters()
    dismissDialog()
  }

  return (
    <section className="customers-page" aria-labelledby="customers-title">
      <div className="page-heading customers-heading">
        <div>
          <p className="eyebrow">Subscriber management / Directory</p>
          <h1 id="customers-title">Customers</h1>
          <p className="page-description">View and manage registered customers, subscription status, and access records.</p>
        </div>
        <button type="button" className="customer-primary-button" onClick={(event) => setDialog({ trigger: event.currentTarget })}>
          <span className="material-symbols-outlined" aria-hidden="true">add</span>
          Register customer
        </button>
      </div>

      <section className="customer-summary-grid" aria-label="Subscriber summary">
        {metrics.map(({ label, count, description, icon }) => (
          <article className="customer-summary-card" key={label}>
            <div className="customer-summary-heading">
              <span>{label}</span>
              <span className="material-symbols-outlined" aria-hidden="true">{icon}</span>
            </div>
            <strong>{count}</strong>
            <p>{description}</p>
          </article>
        ))}
      </section>

      <section className="customer-directory-controls" aria-label="Directory filters">
        <div className="customer-filter-fields">
          <input type="search" aria-label="Search customers" placeholder="Search name, phone or customer ID"
            value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} />
          <select aria-label="Filter by package" value={packageName}
            onChange={(event) => { setPackageName(event.target.value); setPage(1) }}>
            <option value="">All packages</option>
            {packages.map((plan) => <option key={plan}>{plan}</option>)}
          </select>
          <label className="customer-date-filter">
            Registration date
            <input type="date" value={registeredOn}
              onChange={(event) => { setRegisteredOn(event.target.value); setPage(1) }} />
          </label>
        </div>
        <div className="customer-filter-list" role="group" aria-label="Filter customers by status">
          {statuses.map((filter) => (
            <button key={filter} type="button" aria-pressed={status === filter}
              onClick={() => { setStatus(filter); setPage(1) }}>
              {filter} ({matchesControls.filter((customer) => filter === 'All' || customer.status === filter).length})
            </button>
          ))}
          {(term || status !== 'All' || packageName || registeredOn) &&
            <button type="button" onClick={resetFilters}>Clear filters</button>}
        </div>
      </section>

      <section className="customer-directory-panel" aria-label="Customer directory">
        <div className="customer-table-scroll" role="region" aria-label="Customer directory table" tabIndex={0}>
          <table className="customer-table" aria-label="Customers">
            <thead>
              <tr>
                {['Customer name', 'Phone number', 'Registration date', 'Current package', 'Connection status', 'Expiry', 'Actions'].map((label) => (
                  <th key={label} scope="col">{label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visible.map((customer) => (
                <tr key={customer.id}>
                  <th scope="row">
                    <div className="customer-identity">
                      <span className="customer-avatar" aria-hidden="true">{initials(customer.name)}</span>
                      <span>{customer.name}<small>{customer.id}</small></span>
                    </div>
                  </th>
                  <td>{customer.phone}</td>
                  <td><time dateTime={customer.registeredOn}>{dateLabel(customer.registeredOn)}</time></td>
                  <td><span className="customer-package">{customer.plan}</span></td>
                  <td><span className="customer-connection" data-online={customer.connection === 'Online'}>{customer.connection}</span></td>
                  <td>{customer.expiresOn ? <time dateTime={customer.expiresOn}>{dateLabel(customer.expiresOn)}</time> : 'Unavailable'}</td>
                  <td><button type="button" className="customer-secondary-button"
                    aria-label={`View profile for ${customer.name}`} onClick={(event) => setDialog({ customer, trigger: event.currentTarget })}>View profile</button></td>
                </tr>
              ))}
              {!visible.length && <tr><td colSpan={7}>No customers found. Try another search or clear the filters.</td></tr>}
            </tbody>
          </table>
        </div>
        <div className="customer-pagination">
          <span role="status">Showing {visible.length ? start + 1 : 0}–{start + visible.length} of {filtered.length} sample records</span>
          <nav aria-label="Customer pages">
            <button type="button" aria-label="Previous page" disabled={page <= 1} onClick={() => setPage(page - 1)}>‹</button>
            <span>{page} / {pages}</span>
            <button type="button" aria-label="Next page" disabled={page >= pages} onClick={() => setPage(page + 1)}>›</button>
          </nav>
        </div>
      </section>

      <p className="customer-data-footnote">Illustrative demo data. Registration lasts for this page visit.</p>
      {dialog && <CustomerDialog customer={dialog.customer} onClose={dismissDialog} onRegister={registerCustomer} />}
    </section>
  )
}
