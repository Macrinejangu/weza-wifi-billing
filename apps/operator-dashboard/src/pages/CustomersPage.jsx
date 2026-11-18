import { useMemo, useState } from 'react'
import '../styles/customers.css'

const initialCustomers = [
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
]

const filters = [
  { label: 'All', value: 'All' },
  { label: 'Active', value: 'Active' },
  { label: 'Expired', value: 'Expired' },
  { label: 'Flagged', value: 'Flagged' },
]

const summary = [
  { label: 'Total subscribers', value: '1,842', icon: 'groups', tone: 'purple' },
  { label: 'Active', value: '1,429', icon: 'check_circle', tone: 'green' },
  { label: 'Expired', value: '341', icon: 'schedule', tone: 'amber' },
  { label: 'Flagged', value: '72', icon: 'flag', tone: 'red' },
]

function initials(name) {
  return name.split(' ').map((part) => part[0]).slice(0, 2).join('').toUpperCase()
}

function CustomerCard({ customer, onView }) {
  const usage = Math.min((customer.used / customer.quota) * 100, 100)

  return (
    <article className="customer-card">
      <div className="customer-card-top">
        <div className="customer-identity">
          <div className="customer-avatar">{initials(customer.name)}</div>
          <div className="customer-name-block">
            <h3>{customer.name}</h3>
            <p>{customer.id}</p>
          </div>
        </div>
        <span className={`customer-status status-${customer.status.toLowerCase()}`}>
          <span />
          {customer.status}
        </span>
      </div>

      <div className="customer-contact">
        <span className="material-symbols-outlined">call</span>
        <span>{customer.phone}</span>
        <span className={`mpesa-indicator ${customer.mpesaVerified ? 'verified' : 'unverified'}`}>
          <span className="material-symbols-outlined">{customer.mpesaVerified ? 'verified' : 'error'}</span>
          {customer.mpesaVerified ? 'M-PESA verified' : 'Not verified'}
        </span>
      </div>

      <div className="customer-plan-row">
        <div>
          <span className="customer-field-label">CURRENT PACKAGE</span>
          <strong>{customer.plan}</strong>
        </div>
        <div className="customer-price">
          <span className="customer-field-label">PACKAGE PRICE</span>
          <strong>KES {customer.price.toLocaleString('en-KE')}</strong>
        </div>
      </div>

      <div className="customer-usage">
        <div className="customer-usage-heading">
          <span>Data usage</span>
          <strong>{customer.used} / {customer.quota} GB</strong>
        </div>
        <div className="customer-usage-track">
          <span style={{ width: `${usage}%` }} />
        </div>
      </div>

      <div className="customer-card-footer">
        <span className="customer-demo-tag">Demo record</span>
        <button type="button" className="customer-view-button" onClick={() => onView(customer)}>
          View profile
          <span className="material-symbols-outlined">arrow_forward</span>
        </button>
      </div>
    </article>
  )
}

function CustomerDialog({ customer, onClose, onRegister }) {
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [plan, setPlan] = useState('Basic Plan')

  if (customer) {
    return (
      <div className="customer-modal-backdrop" onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}>
        <section className="customer-modal" role="dialog" aria-modal="true" aria-labelledby="customer-profile-title">
          <div className="customer-modal-heading">
            <div>
              <p className="eyebrow">CUSTOMER PROFILE</p>
              <h2 id="customer-profile-title">{customer.name}</h2>
            </div>
            <button type="button" className="customer-modal-close" aria-label="Close profile" onClick={onClose}>×</button>
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
          <button type="button" className="customer-primary-button modal-action" onClick={onClose}>Close profile</button>
        </section>
      </div>
    )
  }

  function submit(event) {
    event.preventDefault()
    const packages = {
      'Basic Plan': { price: 1000, quota: 10 },
      'Standard Plan': { price: 1500, quota: 20 },
      'Premium Plan': { price: 2500, quota: 50 },
    }
    onRegister({
      id: `DEMO-${Date.now().toString().slice(-6)}`,
      name: name.trim(),
      phone: phone.trim(),
      mpesaVerified: false,
      status: 'Active',
      plan,
      price: packages[plan].price,
      used: 0,
      quota: packages[plan].quota,
    })
  }

  return (
    <div className="customer-modal-backdrop" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose()
    }}>
      <section className="customer-modal" role="dialog" aria-modal="true" aria-labelledby="customer-register-title">
        <div className="customer-modal-heading">
          <div>
            <p className="eyebrow">NEW SUBSCRIBER</p>
            <h2 id="customer-register-title">Register customer</h2>
          </div>
          <button type="button" className="customer-modal-close" aria-label="Close registration" onClick={onClose}>×</button>
        </div>
        <form className="customer-registration-form" onSubmit={submit}>
          <label>
            Customer name
            <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Enter full name" required />
          </label>
          <label>
            Phone number
            <input type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="+254 7XX XXX XXX" pattern="\\+?[0-9 ]{9,16}" required />
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
            <button type="button" className="customer-secondary-button" onClick={onClose}>Cancel</button>
            <button type="submit" className="customer-primary-button">Add demo customer</button>
          </div>
        </form>
      </section>
    </div>
  )
}

export default function CustomersPage() {
  const [customers, setCustomers] = useState(initialCustomers)
  const [search, setSearch] = useState('')
  const [activeFilter, setActiveFilter] = useState('All')
  const [page, setPage] = useState(1)
  const [dialog, setDialog] = useState(null)
  const pageSize = 5

  const filteredCustomers = useMemo(() => {
    const term = search.trim().toLowerCase()
    return customers.filter((customer) => {
      const matchesFilter = activeFilter === 'All' || customer.status === activeFilter
      const matchesSearch = !term || [customer.name, customer.phone, customer.id]
        .some((value) => value.toLowerCase().includes(term))
      return matchesFilter && matchesSearch
    })
  }, [customers, search, activeFilter])

  const pageCount = Math.max(1, Math.ceil(filteredCustomers.length / pageSize))
  const visibleCustomers = filteredCustomers.slice((page - 1) * pageSize, page * pageSize)

  function changeFilter(filter) {
    setActiveFilter(filter)
    setPage(1)
  }

  function registerCustomer(customer) {
    setCustomers((current) => [customer, ...current])
    setSearch('')
    setActiveFilter('All')
    setPage(1)
    setDialog(null)
  }

  return (
    <section className="customers-page">
      <div className="page-heading customers-heading">
        <div>
          <p className="eyebrow">SUBSCRIBER MANAGEMENT</p>
          <h1>Customers</h1>
          <p className="page-description">Manage subscriber accounts, service packages, and account status.</p>
        </div>
        <button type="button" className="customer-primary-button" onClick={() => setDialog({ type: 'register' })}>
          <span className="material-symbols-outlined">add</span>
          Add customer
        </button>
      </div>

      <div className="customer-demo-notice">
        <span className="material-symbols-outlined">info</span>
        <span>Illustrative demo data — figures and subscriber records are not live network data.</span>
      </div>

      <section className="customer-summary-grid" aria-label="Subscriber summary">
        {summary.map((item) => (
          <article className="customer-summary-card" key={item.label}>
            <div className={`customer-summary-icon tone-${item.tone}`}>
              <span className="material-symbols-outlined">{item.icon}</span>
            </div>
            <div>
              <p>{item.label}</p>
              <strong>{item.value}</strong>
            </div>
          </article>
        ))}
        <article className="customer-summary-card retention-card">
          <div className="customer-summary-icon tone-green">
            <span className="material-symbols-outlined">trending_up</span>
          </div>
          <div>
            <p>Retention rate</p>
            <strong>94.2%</strong>
          </div>
        </article>
      </section>

      <section className="customer-directory-panel">
        <div className="customer-directory-heading">
          <div>
            <h2>Subscriber directory</h2>
            <p>Search and review customer accounts</p>
          </div>
          <span className="customer-record-count">{filteredCustomers.length} demo records</span>
        </div>

        <div className="customer-directory-controls">
          <label className="customer-search">
            <span className="material-symbols-outlined">search</span>
            <input
              type="search"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value)
                setPage(1)
              }}
              placeholder="Search by name, phone number or customer ID..."
              aria-label="Search customers"
            />
            {search && <button type="button" onClick={() => { setSearch(''); setPage(1) }} aria-label="Clear search">×</button>}
          </label>

          <div className="customer-filter-list" aria-label="Filter customers by status">
            {filters.map((filter) => (
              <button
                key={filter.value}
                type="button"
                className={`customer-filter ${activeFilter === filter.value ? 'selected' : ''}`}
                aria-pressed={activeFilter === filter.value}
                onClick={() => changeFilter(filter.value)}
              >
                {filter.label}
                {filter.value === 'All' ? (
                  <span>{customers.length}</span>
                ) : (
                  <span>{customers.filter((customer) => customer.status === filter.value).length}</span>
                )}
              </button>
            ))}
          </div>
        </div>

        {visibleCustomers.length ? (
          <div className="customer-card-grid">
            {visibleCustomers.map((customer) => (
              <CustomerCard key={customer.id} customer={customer} onView={(item) => setDialog({ type: 'profile', customer: item })} />
            ))}
          </div>
        ) : (
          <div className="customer-empty-state">
            <span className="material-symbols-outlined">person_search</span>
            <h3>No customers found</h3>
            <p>Try another search term or status filter.</p>
            <button type="button" className="customer-secondary-button" onClick={() => {
              setSearch('')
              changeFilter('All')
            }}>Clear filters</button>
          </div>
        )}

        <div className="customer-pagination">
          <span>
            Showing {visibleCustomers.length ? (page - 1) * pageSize + 1 : 0}–{Math.min(page * pageSize, filteredCustomers.length)} of {filteredCustomers.length} sample records
          </span>
          <div>
            <button type="button" className="customer-page-button" aria-label="Previous page" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>
              <span className="material-symbols-outlined">chevron_left</span>
            </button>
            <span className="customer-page-number">{page} / {pageCount}</span>
            <button type="button" className="customer-page-button" aria-label="Next page" disabled={page >= pageCount} onClick={() => setPage((current) => current + 1)}>
              <span className="material-symbols-outlined">chevron_right</span>
            </button>
          </div>
        </div>
      </section>

      <p className="customer-data-footnote">The summary figures are illustrative reference values. Customer registration and changes remain in temporary page state and are not persisted.</p>

      {dialog && (
        <CustomerDialog
          customer={dialog.type === 'profile' ? dialog.customer : null}
          onClose={() => setDialog(null)}
          onRegister={registerCustomer}
        />
      )}
    </section>
  )
}
