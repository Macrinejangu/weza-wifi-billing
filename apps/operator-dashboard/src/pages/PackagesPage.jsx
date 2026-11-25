import { useEffect, useRef, useState } from 'react'
import { demoDataEnabled } from '../../../shared/demoMode.js'
import { listActivePackages, listStaffPackages, StaffSessionError } from '../api.js'
import StaffPackageDialog from './StaffPackageDialog.jsx'
import '../styles/packages.css'

function toCatalogueRow(record) {
  const category = record.service_type === 'hotspot'
    ? 'Hotspot Captive'
    : record.service_type.split(/[_ -]+/).filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(' ')

  return {
    id: String(record.id),
    record,
    name: record.name,
    category,
    price: record.price,
    duration: `${record.duration_minutes} min`,
    speed: `${record.download_speed_mbps} Mbps / ${record.upload_speed_mbps} Mbps`,
    quota: 'Unavailable',
    status: record.is_active ? 'Active' : 'Inactive',
    description: record.description,
    icon: record.service_type === 'hotspot' ? 'wifi' : 'lan',
  }
}

const demoPackages = [
  {
    id: 'PKG-001',
    name: 'Quick Connect',
    speed: '5 Mbps / 2 Mbps',
    quota: '500 MB limit',
    price: 10,
    duration: '1 Hour',
    category: 'Hotspot Captive',
    status: 'Active',
    icon: 'bolt',
  },
  {
    id: 'PKG-002',
    name: 'Daily Connect',
    speed: '5 Mbps / 2 Mbps',
    quota: '2 GB limit',
    price: 50,
    duration: '24 Hours',
    category: 'Hotspot Captive',
    status: 'Active',
    icon: 'calendar_today',
  },
  {
    id: 'PKG-003',
    name: 'Weekly Plus',
    speed: '10 Mbps / 5 Mbps',
    quota: '10 GB limit',
    price: 250,
    duration: '7 Days',
    category: 'Hotspot Captive',
    status: 'Active',
    icon: 'star',
    badge: 'Popular',
  },
  {
    id: 'PKG-004',
    name: 'Unlimited 24h',
    speed: '5 Mbps uncapped',
    quota: 'Unlimited',
    price: 100,
    duration: '24 Hours',
    category: 'Hotspot Captive',
    status: 'Active',
    icon: 'all_inclusive',
  },
  {
    id: 'PKG-005',
    name: 'Monthly Max',
    speed: '10 Mbps / 5 Mbps',
    quota: '40 GB limit',
    price: 900,
    duration: '30 Days',
    category: 'Home Fiber',
    status: 'Active',
    icon: 'calendar_month',
  },
  {
    id: 'PKG-006',
    name: 'Night Owl 12h',
    speed: '8 Mbps / 4 Mbps',
    quota: 'Unlimited',
    price: 30,
    duration: '12 Hours (Off-peak)',
    category: 'Hotspot Captive',
    status: 'Inactive',
    icon: 'dark_mode',
  },
]

const packageTypes = ['Hotspot Captive', 'Home Fiber']
const statuses = ['Active', 'Inactive']

function PackageDialog({ packageItem, onClose, onSave }) {
  const [name, setName] = useState(packageItem?.name ?? '')
  const [speed, setSpeed] = useState(packageItem?.speed ?? '5 Mbps')
  const [quota, setQuota] = useState(packageItem?.quota ?? 'Unlimited')
  const [price, setPrice] = useState(String(packageItem?.price ?? ''))
  const [duration, setDuration] = useState(packageItem?.duration ?? '1 hour')
  const [category, setCategory] = useState(packageItem?.category ?? packageTypes[0])

  const dialogRef = useRef(null)
  const nameRef = useRef(null)

  useEffect(() => {
    const dialog = dialogRef.current
    dialog.showModal()
    nameRef.current.focus()
    return () => dialog.close()
  }, [])

  function submit(event) {
    event.preventDefault()
    const form = event.currentTarget
    for (const field of form.querySelectorAll('input[required]')) {
      if (!field.value.trim() && field.type === 'text') {
        field.setCustomValidity('Enter a value other than spaces.')
      }
      if (field.name === 'price' && !Number.isSafeInteger(field.valueAsNumber)) {
        field.setCustomValidity('Enter a positive whole amount in KES.')
      }
    }
    if (!form.reportValidity()) return

    onSave({
      id: packageItem?.id ?? `DEMO-${crypto.randomUUID()}`,
      name: name.trim(),
      speed: speed.trim(),
      quota: quota.trim(),
      price: Number(price),
      duration: duration.trim(),
      category,
      status: packageItem?.status ?? 'Active',
      badge: packageItem?.badge,
      icon: packageItem?.icon ?? 'wifi',
    })
  }

  function dismissBackdrop(event) {
    if (event.target !== event.currentTarget) return
    const { left, right, top, bottom } = event.currentTarget.getBoundingClientRect()
    if (event.clientX < left || event.clientX > right || event.clientY < top || event.clientY > bottom) {
      onClose()
    }
  }

  return (
    <dialog
      ref={dialogRef}
      className="package-modal"
      aria-labelledby="package-dialog-title"
      aria-describedby="package-dialog-note"
      onClick={dismissBackdrop}
      onCancel={(event) => {
        event.preventDefault()
        onClose()
      }}
    >
      <div className="package-modal-heading">
        <div>
          <p className="eyebrow">PACKAGE CONFIGURATION</p>
          <h2 id="package-dialog-title">{packageItem ? 'Edit package' : 'Create package'}</h2>
        </div>
        <button type="button" className="package-modal-close" aria-label="Close dialog" onClick={onClose}>×</button>
      </div>

      <form className="package-form" onSubmit={submit} onInput={(event) => {
        if (event.target instanceof HTMLInputElement) event.target.setCustomValidity('')
      }}>
        <label>
          Package name
          <input ref={nameRef} type="text" value={name} onChange={(event) => setName(event.target.value)} required maxLength={60} />
        </label>
        <div className="package-form-grid">
          <label>
            Download / upload speed
            <input type="text" value={speed} onChange={(event) => setSpeed(event.target.value)} required maxLength={60} />
          </label>
          <label>
            Data allowance
            <input type="text" value={quota} onChange={(event) => setQuota(event.target.value)} required maxLength={60} />
          </label>
          <label>
            Price (KES)
            <input type="number" name="price" min="1" step="1" value={price} onChange={(event) => setPrice(event.target.value)} required />
          </label>
          <label>
            Duration
            <input type="text" value={duration} onChange={(event) => setDuration(event.target.value)} required maxLength={60} />
          </label>
        </div>
        <label>
          Package type
          <select value={category} onChange={(event) => setCategory(event.target.value)}>
            {packageTypes.map((type) => <option key={type}>{type}</option>)}
          </select>
        </label>
        <div className="package-form-actions">
          <button type="button" className="package-secondary-button" onClick={onClose}>Cancel</button>
          <button type="submit" className="package-primary-button">{packageItem ? 'Save changes' : 'Create package'}</button>
        </div>
      </form>
      <p className="package-modal-note" id="package-dialog-note">Demo configuration only. Changes are held in this page and are not saved to a server.</p>
    </dialog>
  )
}

function PackageRow({ item, onEdit, editable }) {
  const inactive = item.status === 'Inactive'
  return (
    <tr className={inactive ? 'package-row-inactive' : undefined}>
      <th scope="row">
        <div className="package-name">
          <span className={`package-icon material-symbols-outlined${item.badge ? ' featured' : ''}`} aria-hidden="true">{item.icon}</span>
          <div>
            <strong>{item.name}</strong>
            <span className="package-type">{item.category}</span>
            {!editable && item.description && <span className="package-type">{item.description}</span>}
          </div>
          {item.badge && <span className="package-badge">{item.badge}</span>}
        </div>
      </th>
      <td className="package-price">KES<br />{item.price.toLocaleString('en-KE')}</td>
      <td><div className="package-speed"><span className="material-symbols-outlined" aria-hidden="true">speed</span>{item.speed}</div></td>
      <td>{item.duration}</td>
      <td><span className={`package-quota${item.quota === 'Unlimited' && !inactive ? ' unlimited' : ''}`}>{item.quota}</span></td>
      <td><span className={`package-status${inactive ? ' inactive' : ''}`}>{item.status}</span></td>
      <td className="package-actions">
        <button type="button" className="package-edit-button" aria-label={`Edit package: ${item.name}`} disabled={!editable} onClick={(event) => onEdit(item, event.currentTarget)}>Edit</button>
      </td>
    </tr>
  )
}

function PackageFilters({ label, options, selected, onSelect }) {
  return (
    <div className="package-filters" role="group" aria-label={label}>
      {options.map(({ value, text }) => (
        <button key={value} type="button" aria-pressed={selected === value} onClick={() => onSelect(value)}>
          {text}
        </button>
      ))}
    </div>
  )
}

export default function PackagesPage({ live = false, accessToken, canManage = false, onSignOut }) {
  const showDemo = !live && demoDataEnabled
  const editable = showDemo || (live && canManage && Boolean(accessToken))
  const [packages, setPackages] = useState(() => showDemo ? demoPackages : [])
  const [request, setRequest] = useState({ loading: live })
  const [reload, setReload] = useState(0)

  useEffect(() => {
    if (!live) return undefined
    const controller = new AbortController()
    const { signal } = controller
    const catalogue = accessToken ? listStaffPackages(accessToken, { signal }) : listActivePackages({ signal })
    catalogue.then((records) => {
      if (signal.aborted) return
      setPackages(records.map(toCatalogueRow))
      setRequest({ loading: false })
    }).catch((error) => {
      if (signal.aborted) return
      if (error instanceof StaffSessionError) onSignOut?.()
      setRequest({ loading: false, error: 'Could not load packages. Please try again.' })
    })
    return () => controller.abort()
  }, [accessToken, live, onSignOut, reload])

  function refreshCatalogue() {
    setRequest({ loading: true })
    setPackages([])
    setStatus('all')
    setType('all')
    setReload((attempt) => attempt + 1)
  }
  const [status, setStatus] = useState('all')
  const [type, setType] = useState('all')
  const [query, setQuery] = useState('')
  const [dialog, setDialog] = useState(null)
  const searchRef = useRef(null)
  const triggerRef = useRef(null)

  const search = query.trim().toLowerCase()
  const activeCount = packages.filter((item) => item.status === 'Active').length
  const statusOptions = [
    { value: 'all', text: `All (${packages.length})` },
    ...(live && !accessToken ? ['Active'] : statuses).map((value) => ({
      value,
      text: `${value} (${value === 'Active' ? activeCount : packages.length - activeCount})`,
    })),
  ]
  const categories = live ? [...new Set(packages.map((item) => item.category))] : packageTypes
  const typeOptions = [{ value: 'all', text: 'All Types' }, ...categories.map((value) => ({ value, text: value }))]
  const visiblePackages = packages.filter((item) =>
    (status === 'all' || item.status === status)
    && (type === 'all' || item.category === type)
    && [item.name, item.id, item.speed, item.description, `KES ${item.price}`].some((value) => String(value ?? '').toLowerCase().includes(search))
  )

  function openDialog(packageItem, trigger) {
    if (!editable) return
    triggerRef.current = trigger
    setDialog({ packageItem })
  }

  function closeDialog() {
    setDialog(null)
  }

  useEffect(() => {
    if (dialog || !triggerRef.current) return
    const target = triggerRef.current.isConnected ? triggerRef.current : searchRef.current
    target.focus()
    triggerRef.current = null
  }, [dialog])

  function savePackage(packageItem) {
    setPackages((current) => {
      const exists = current.some((item) => item.id === packageItem.id)
      return exists
        ? current.map((item) => item.id === packageItem.id ? packageItem : item)
        : [...current, packageItem]
    })
    closeDialog()
  }

  return (
    <div className="packages-page">
      <header className="page-heading packages-heading">
        <div>
          <div className="package-title"><h1>Packages</h1><span>Tariff Engine</span></div>
          <p className="page-description">{live ? 'Review the packages offered in the customer portal.' : 'Create and manage available internet packages, captive tiers, and rate limit quotas.'}</p>
        </div>
        <button type="button" className="package-primary-button package-create-button" disabled={!editable || request.loading || Boolean(request.error)} onClick={(event) => openDialog(null, event.currentTarget)}>
          <span className="material-symbols-outlined" aria-hidden="true">add</span>
          Add Package
        </button>
      </header>

      <div className="package-toolbar">
        <div className="package-filter-stack">
          <div className="package-filter-line">
            <span className="package-active-count">
              {request.loading || request.error ? 'Active packages' : `${activeCount} Active ${activeCount === 1 ? 'Package' : 'Packages'}`}
            </span>
            {!request.loading && !request.error && <PackageFilters label="Filter packages by status" options={statusOptions} selected={status} onSelect={setStatus} />}
          </div>
          <PackageFilters label="Filter packages by type" options={typeOptions} selected={type} onSelect={setType} />
        </div>
        <label className="package-search">
          <span className="material-symbols-outlined" aria-hidden="true">search</span>
          <input
            ref={searchRef}
            type="search"
            aria-label="Search packages"
            placeholder="Search packages by name, speed, or price"
            value={query}
            onChange={(event) => setQuery(event.currentTarget.value)}
          />
        </label>
      </div>

      <section className="package-catalogue" aria-label="Internet package catalogue">
        <div className="package-table-scroll" role="region" aria-label="Scrollable packages table" tabIndex={0}>
          <table className="package-table" aria-label="Internet packages">
            <thead>
              <tr>
                <th scope="col">Package name</th>
                <th scope="col">Price (KES)</th>
                <th scope="col">Download / upload speed</th>
                <th scope="col">Duration</th>
                <th scope="col">Data allowance</th>
                <th scope="col">Status</th>
                <th scope="col" className="package-actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {visiblePackages.map((item) => <PackageRow key={item.id} item={item} onEdit={openDialog} editable={editable} />)}
              {visiblePackages.length === 0 && (
                <tr>
                  <td colSpan={7} className="package-empty">
                    {request.loading ? <span role="status">Loading packages…</span> : request.error ? (
                      <>
                        <p role="alert">{request.error}</p>
                        <button type="button" className="package-primary-button" onClick={refreshCatalogue}>Retry</button>
                      </>
                    ) : live && packages.length === 0 ? 'No packages are available.'
                      : !live && !showDemo ? 'Package records unavailable.'
                      : 'No matching packages. Try another search or filter.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <footer className="package-table-footer">
          <span role="status">{!request.loading && !request.error && `Showing ${visiblePackages.length} of ${packages.length} packages`}</span>
          {live && !editable && <span>Only administrators manage packages.</span>}
          {showDemo && <span>Demo data · Changes are temporary</span>}
        </footer>
      </section>

      {live && editable && dialog && (
        <StaffPackageDialog packageRecord={dialog.packageItem?.record} accessToken={accessToken}
          onClose={closeDialog} onSaved={(record) => savePackage(toCatalogueRow(record))} onSignOut={onSignOut} />
      )}
      {showDemo && dialog && (
        <PackageDialog packageItem={dialog.packageItem} onClose={closeDialog} onSave={savePackage} />
      )}
    </div>
  )
}
