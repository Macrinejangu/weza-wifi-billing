import { useEffect, useRef, useState } from 'react'
import { listManualStkPurchases, sendManualStk, StaffSessionError } from '../api.js'

export default function ManualStkDialog({ accessToken, onClose, onSent, onSignOut }) {
  const ref = useRef(null)
  const [options, setOptions] = useState(null)
  const [selected, setSelected] = useState('')
  const [sending, setSending] = useState(false)
  const [blocked, setBlocked] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const modal = ref.current
    modal.showModal()
    const controller = new AbortController()
    listManualStkPurchases(accessToken, { signal: controller.signal }).then((data) => {
      if (!controller.signal.aborted) setOptions(data)
    }).catch((failure) => {
      if (controller.signal.aborted) return
      if (failure instanceof StaffSessionError) onSignOut?.()
      else setError(failure.message)
    })
    return () => { controller.abort(); modal.close() }
  }, [accessToken, onSignOut])

  const purchase = options?.purchases.find(({ id }) => String(id) === selected)

  async function send(event) {
    event.preventDefault()
    if (!purchase || sending || blocked) return
    setSending(true)
    setError('')
    try {
      onSent(await sendManualStk(accessToken, purchase))
    } catch (failure) {
      if (failure instanceof StaffSessionError) onSignOut?.()
      else setError(failure.message)
      // The server could have sent a prompt despite a lost connection.
      setBlocked(true)
    } finally {
      setSending(false)
    }
  }

  return (
    <dialog ref={ref} className="package-modal" aria-labelledby="manual-stk-title" onCancel={(event) => {
      event.preventDefault()
      if (!sending) onClose()
    }}>
      <div className="package-modal-heading"><h2 id="manual-stk-title">Manual STK</h2></div>
      <form className="package-form" onSubmit={send}>
        {options?.mode === 'unavailable' ? <p>Enable the local simulation or configure Daraja with an approved test handset.</p>
          : options?.purchases.length ? (
            <label>Unpaid purchase
              <select required value={selected} disabled={sending || blocked} onChange={(event) => setSelected(event.target.value)}>
                <option value="">Choose a purchase</option>
                {options.purchases.map((item) => <option key={item.id} value={item.id}>#{item.id} · {item.customer} · {item.package}</option>)}
              </select>
            </label>
          ) : options ? <p>No eligible unpaid purchases. A saved purchase without a pending or confirmed payment is required.</p>
            : !error && <p role="status">Loading eligible purchases…</p>}
        {purchase && (
          <div>
            <p>Send one prompt for KES {purchase.amount} to {purchase.phone}.</p>
            <p>{options.mode === 'simulated' ? 'Simulation. No message will reach the phone.' : 'Daraja test prompt. The payment stays pending until verified.'}</p>
          </div>
        )}
        {error && <p role="alert">{error}</p>}
        <div className="package-form-actions">
          <button type="button" className="package-secondary-button" disabled={sending} onClick={onClose}>Close</button>
          <button type="submit" className="package-primary-button" disabled={!purchase || sending || blocked}>
            {sending ? 'Sending…' : options?.mode === 'simulated' ? 'Simulate prompt' : 'Send test prompt'}
          </button>
        </div>
      </form>
    </dialog>
  )
}
