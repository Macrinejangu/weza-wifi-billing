import { useEffect, useRef, useState } from 'react'
import { saveStaffCustomer, StaffSessionError } from '../api.js'

export default function StaffCustomerEditor({ customer, accessToken, onClose, onSaved, onSignOut }) {
  const dialogRef = useRef(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    const dialog = dialogRef.current
    dialog.showModal()
    return () => dialog.close()
  }, [])

  async function save(event) {
    event.preventDefault()
    if (saving) return
    const data = new FormData(event.currentTarget)
    const fullName = data.get('name').trim()
    if (!fullName) {
      setError('Enter a customer name.')
      return
    }
    setSaving(true)
    setError('')
    try {
      await saveStaffCustomer(accessToken, customer?.id, {
        full_name: fullName,
        phone: data.get('phone').trim() || null,
        ...(!customer && { email: data.get('email').trim(), password: data.get('password') }),
      })
      onSaved()
    } catch (failure) {
      if (failure instanceof StaffSessionError) onSignOut?.()
      else setError(failure.message)
      setSaving(false)
    }
  }

  return (
    <dialog ref={dialogRef} className="customer-modal" aria-labelledby="staff-customer-title" onCancel={(event) => {
      event.preventDefault()
      if (!saving) onClose()
    }}>
      <div className="customer-modal-heading">
        <h2 id="staff-customer-title">{customer ? 'Edit customer' : 'Register customer'}</h2>
        <button type="button" className="customer-modal-close" aria-label="Close editor" disabled={saving} onClick={onClose}>×</button>
      </div>
      <form className="customer-registration-form" onSubmit={save}>
        <label>Customer name
          <input name="name" required maxLength={100} defaultValue={customer?.name} disabled={saving} />
        </label>
        <label>Phone number
          <input name="phone" type="tel" required={!customer} maxLength={32} defaultValue={customer?.storedPhone ?? ''} disabled={saving} />
        </label>
        {!customer && <>
          <label>Email address<input name="email" type="email" required maxLength={150} disabled={saving} /></label>
          <label>Account password<input name="password" type="password" autoComplete="new-password" required minLength={8} maxLength={128} disabled={saving} /></label>
        </>}
        {error && <p role="alert">{error}</p>}
        <div className="customer-modal-actions">
          <button type="button" className="customer-secondary-button" onClick={onClose} disabled={saving}>Cancel</button>
          <button type="submit" className="customer-primary-button" disabled={saving}>{saving ? 'Saving…' : customer ? 'Save customer' : 'Register customer'}</button>
        </div>
      </form>
    </dialog>
  )
}
