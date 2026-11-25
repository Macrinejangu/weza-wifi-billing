import { useEffect, useRef, useState } from 'react'
import { deactivateStaffPackage, saveStaffPackage, StaffSessionError } from '../api.js'

export default function StaffPackageDialog({ packageRecord, accessToken, onClose, onSaved, onSignOut }) {
  const modal = useRef(null)
  const [saving, setSaving] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const dialog = modal.current
    dialog.showModal()
    dialog.querySelector('input').focus()
    return () => dialog.close()
  }, [])

  async function changePackage(action) {
    if (saving) return
    setSaving(true)
    setError('')
    try {
      onSaved(await action())
    } catch (failure) {
      if (failure instanceof StaffSessionError) onSignOut?.()
      setError(failure.message)
      setSaving(false)
    }
  }

  function save(event) {
    event.preventDefault()
    const fields = new FormData(event.currentTarget)
    const name = fields.get('name').trim()
    if (!name) {
      setError('Enter a package name.')
      return
    }
    const data = {
      name,
      service_type: packageRecord?.service_type ?? 'hotspot',
      description: fields.get('description').trim() || null,
      price: Number(fields.get('price')),
      duration_minutes: Number(fields.get('duration_minutes')),
      download_speed_mbps: Number(fields.get('download_speed_mbps')),
      upload_speed_mbps: Number(fields.get('upload_speed_mbps')),
      ...(packageRecord && { is_active: packageRecord.is_active }),
    }
    changePackage(() => saveStaffPackage(accessToken, packageRecord?.id, data))
  }

  function deactivate() {
    changePackage(async () => {
      await deactivateStaffPackage(accessToken, packageRecord.id)
      return { ...packageRecord, is_active: false }
    })
  }

  return (
    <dialog ref={modal} className="package-modal" aria-labelledby="staff-package-title" onCancel={(event) => {
      event.preventDefault()
      if (!saving) onClose()
    }}>
      <div className="package-modal-heading">
        <h2 id="staff-package-title">{packageRecord ? 'Edit package' : 'Create package'}</h2>
        <button type="button" className="package-modal-close" aria-label="Close dialog" disabled={saving} onClick={onClose}>×</button>
      </div>
      <form className="package-form" onSubmit={save}>
        <label>
          Package name
          <input name="name" required maxLength={100} defaultValue={packageRecord?.name} disabled={saving} />
        </label>
        <div className="package-form-grid">
          {[
            ['price', 'Price (KES)'],
            ['duration_minutes', 'Duration (minutes)'],
            ['download_speed_mbps', 'Download speed (Mbps)'],
            ['upload_speed_mbps', 'Upload speed (Mbps)'],
          ].map(([name, label]) => (
            <label key={name}>
              {label}
              <input name={name} type="number" min="1" max="2147483647" step="1" required
                defaultValue={packageRecord?.[name]} disabled={saving} />
            </label>
          ))}
        </div>
        <label>
          Description (optional)
          <input name="description" maxLength={500} defaultValue={packageRecord?.description ?? ''} disabled={saving} />
        </label>
        {error && <p role="alert">{error}</p>}
        {confirming && <p role="status">Hide this package from new purchases? Existing purchases keep their terms.</p>}
        <div className="package-form-actions">
          <button type="button" className="package-secondary-button" disabled={saving}
            onClick={confirming ? () => setConfirming(false) : onClose}>Cancel</button>
          {confirming ? (
            <button type="button" className="package-primary-button" disabled={saving} onClick={deactivate}>Confirm deactivation</button>
          ) : (
            <>
              {packageRecord?.is_active && <button type="button" className="package-secondary-button" disabled={saving}
                onClick={() => setConfirming(true)}>Deactivate package</button>}
              <button type="submit" className="package-primary-button" disabled={saving}>
                {saving ? 'Saving…' : packageRecord ? 'Save changes' : 'Create package'}
              </button>
            </>
          )}
        </div>
      </form>
    </dialog>
  )
}
