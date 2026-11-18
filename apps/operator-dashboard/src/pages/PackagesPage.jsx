import { useMemo, useState } from 'react'
import '../styles/packages.css'

const initialPackages = [
  {
    id: 'PKG-001',
    name: '1-Hour Quick Connect',
    speed: '5 Mbps',
    quota: 'Unlimited',
    price: 20,
    duration: '1 hour',
    category: 'passes',
    status: 'Active',
    badge: '',
  },
  {
    id: 'PKG-002',
    name: '24-Hour Day Pass',
    speed: '8 Mbps',
    quota: 'Unlimited',
    price: 50,
    duration: '24 hours',
    category: 'passes',
    status: 'Active',
    badge: 'Popular',
  },
  {
    id: 'PKG-003',
    name: 'Weekly Plus 10GB',
    speed: '10 Mbps',
    quota: '10 GB Fair-Use',
    price: 250,
    duration: '7 days',
    category: 'term',
    status: 'Active',
    badge: 'Top Revenue',
  },
  {
    id: 'PKG-004',
    name: 'Monthly FastTrack 50GB',
    speed: '15 Mbps',
    quota: '50 GB Fair-Use',
    price: 900,
    duration: '30 days',
    category: 'term',
    status: 'Active',
    badge: '',
  },
  {
    id: 'PKG-005',
    name: 'Night Owl Unlimited',
    speed: '12 Mbps',
    quota: 'Unlimited (22:00 - 06:00)',
    price: 35,
    duration: '8 hours',
    category: 'passes',
    status: 'Active',
    badge: 'Off-Peak',
  },
]

const filterOptions = [
  { label: 'All Tiers', value: 'all' },
  { label: 'Hourly / Passes', value: 'passes' },
  { label: 'Weekly / Monthly', value: 'term' },
]

function PackageDialog({ packageItem, onClose, onSave }) {
  const [name, setName] = useState(packageItem?.name ?? '')
  const [speed, setSpeed] = useState(packageItem?.speed ?? '5 Mbps')
  const [quota, setQuota] = useState(packageItem?.quota ?? 'Unlimited')
  const [price, setPrice] = useState(String(packageItem?.price ?? ''))
  const [duration, setDuration] = useState(packageItem?.duration ?? '1 hour')
  const [category, setCategory] = useState(packageItem?.category ?? 'passes')

  function submit(event) {
    event.preventDefault()
    onSave({
      id: packageItem?.id ?? `DEMO-${Date.now().toString().slice(-6)}`,
      name: name.trim(),
      speed: speed.trim(),
      quota: quota.trim(),
      price: Number(price),
      duration: duration.trim(),
      category,
      status: packageItem?.status ?? 'Active',
      badge: packageItem?.badge ?? '',
    })
  }

  return (
    <div className="package-modal-backdrop" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose()
    }}>
      <section className="package-modal" role="dialog" aria-modal="true" aria-labelledby="package-dialog-title">
        <div className="package-modal-heading">
          <div>
            <p className="eyebrow">PACKAGE CONFIGURATION</p>
            <h2 id="package-dialog-title">{packageItem ? 'Edit package' : 'Create package'}</h2>
          </div>
          <button type="button" className="package-modal-close" aria-label="Close dialog" onClick={onClose}>×</button>
        </div>

        <form className="package-form" onSubmit={submit}>
          <label>
            Package name
            <input value={name} onChange={(event) => setName(event.target.value)} required maxLength={60} />
          </label>
          <div className="package-form-grid">
            <label>
              Speed
              <input value={speed} onChange={(event) => setSpeed(event.target.value)} required />
            </label>
            <label>
              Data allowance
              <input value={quota} onChange={(event) => setQuota(event.target.value)} required />
            </label>
            <label>
              Price (KES)
              <input type="number" min="1" step="1" value={price} onChange={(event) => setPrice(event.target.value)} required />
            </label>
            <label>
              Duration
              <input value={duration} onChange={(event) => setDuration(event.target.value)} required />
            </label>
          </div>
          <label>
            Package category
            <select value={category} onChange={(event) => setCategory(event.target.value)}>
              <option value="passes">Hourly / Passes</option>
              <option value="term">Weekly / Monthly</option>
            </select>
          </label>
          <div className="package-form-actions">
            <button type="button" className="package-secondary-button" onClick={onClose}>Cancel</button>
            <button type="submit" className="package-primary-button">{packageItem ? 'Save changes' : 'Create package'}</button>
          </div>
        </form>
        <p className="package-modal-note">Demo configuration only. Changes are held in this page and are not saved to a server.</p>
      </section>
    </div>
  )
}

function PackageCard({ packageItem, onEdit }) {
  return (
    <article className="package-card">
      <div className="package-card-heading">
        <div>
          <span className="package-card-category">{packageItem.category === 'passes' ? 'QUICK ACCESS' : 'SUBSCRIPTION TIER'}</span>
          <h3>{packageItem.name}</h3>
        </div>
        <span className={`package-status ${packageItem.status.toLowerCase()}`}>
          <span />
          {packageItem.status}
        </span>
      </div>

      <div className="package-price-row">
        <div className="package-price">
          <span>KES</span>
          <strong>{packageItem.price.toLocaleString('en-KE')}</strong>
        </div>
        {packageItem.badge && <span className="package-highlight">{packageItem.badge}</span>}
      </div>

      <div className="package-specifications">
        <div>
          <span className="material-symbols-outlined">speed</span>
          <span><small>Speed</small><strong>{packageItem.speed} Burst</strong></span>
        </div>
        <div>
          <span className="material-symbols-outlined">data_usage</span>
          <span><small>Data allowance</small><strong>{packageItem.quota}</strong></span>
        </div>
        <div>
          <span className="material-symbols-outlined">schedule</span>
          <span><small>Validity</small><strong>{packageItem.duration}</strong></span>
        </div>
      </div>

      <div className="package-card-footer">
        <span className="package-demo-label">Demo package</span>
        <button type="button" className="package-edit-button" onClick={() => onEdit(packageItem)}>
          Edit package
          <span className="material-symbols-outlined">arrow_forward</span>
        </button>
      </div>
    </article>
  )
}

export default function PackagesPage() {
  const [packages, setPackages] = useState(initialPackages)
  const [activeFilter, setActiveFilter] = useState('all')
  const [editingPackage, setEditingPackage] = useState(null)
  const [showCreateDialog, setShowCreateDialog] = useState(false)

  const visiblePackages = useMemo(
    () => activeFilter === 'all'
      ? packages
      : packages.filter((item) => item.category === activeFilter),
    [packages, activeFilter]
  )

  function savePackage(packageItem) {
    setPackages((current) => {
      const exists = current.some((item) => item.id === packageItem.id)
      return exists
        ? current.map((item) => item.id === packageItem.id ? packageItem : item)
        : [...current, packageItem]
    })
    setEditingPackage(null)
    setShowCreateDialog(false)
  }

  return (
    <main className="packages-page">
      <div className="page-heading packages-heading">
        <div>
          <p className="eyebrow">TARIFF ARCHITECTURE</p>
          <h1>Internet Packages</h1>
          <p className="page-description">Manage the plans available to subscribers on your network.</p>
        </div>
        <button type="button" className="package-primary-button package-create-button" onClick={() => setShowCreateDialog(true)}>
          <span className="material-symbols-outlined">add</span>
          New Package
        </button>
      </div>

      <div className="package-overview">
        <div className="package-overview-card">
          <span className="package-overview-icon material-symbols-outlined">inventory_2</span>
          <div><strong>{packages.length}</strong><span>Configured packages</span></div>
        </div>
        <div className="package-overview-card">
          <span className="package-overview-icon material-symbols-outlined">check_circle</span>
          <div><strong>{packages.filter((item) => item.status === 'Active').length}</strong><span>Active packages</span></div>
        </div>
        <div className="package-overview-card">
          <span className="package-overview-icon material-symbols-outlined">payments</span>
          <div><strong>KES {Math.max(...packages.map((item) => item.price)).toLocaleString('en-KE')}</strong><span>Highest package price</span></div>
        </div>
      </div>

      <section className="package-catalogue" aria-label="Internet package catalogue">
        <div className="package-catalogue-heading">
          <div>
            <h2>Package catalogue</h2>
            <p>Select a package to review or update its configuration.</p>
          </div>
          <span className="package-catalogue-count">{visiblePackages.length} packages</span>
        </div>

        <div className="package-filters" role="group" aria-label="Filter packages">
          {filterOptions.map((filter) => {
            const count = filter.value === 'all'
              ? packages.length
              : packages.filter((item) => item.category === filter.value).length

            return (
              <button
                key={filter.value}
                type="button"
                className={`package-filter ${activeFilter === filter.value ? 'active' : ''}`}
                aria-pressed={activeFilter === filter.value}
                onClick={() => setActiveFilter(filter.value)}
              >
                {filter.label}
                <span>{count}</span>
              </button>
            )
          })}
        </div>

        <div className="package-grid">
          {visiblePackages.map((item) => (
            <PackageCard key={item.id} packageItem={item} onEdit={setEditingPackage} />
          ))}
        </div>

        <p className="package-data-notice">Illustrative package data for frontend review. No live billing or network configuration is connected.</p>
      </section>

      {(showCreateDialog || editingPackage) && (
        <PackageDialog
          packageItem={editingPackage}
          onClose={() => {
            setShowCreateDialog(false)
            setEditingPackage(null)
          }}
          onSave={savePackage}
        />
      )}
    </main>
  )
}
