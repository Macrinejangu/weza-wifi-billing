import { useEffect, useState } from 'react'
import { listSupportFaqs, StaffSessionError, updateSupportFaq } from '../api.js'

export default function SupportFaqSettings({ accessToken, onSignOut }) {
  const [faqs, setFaqs] = useState(null)
  const [attempt, setAttempt] = useState(0)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    listSupportFaqs(accessToken, { signal: controller.signal }).then((items) => {
      if (!controller.signal.aborted) setFaqs(items)
    }).catch((failure) => {
      if (controller.signal.aborted) return
      if (failure instanceof StaffSessionError) onSignOut()
      else setError(failure.message)
    })
    return () => controller.abort()
  }, [accessToken, attempt, onSignOut])

  return (
    <section className="system-settings-panel" aria-label="Customer support answers">
      <header><h2>Customer Support Answers</h2><p>Updates appear in the customer support chat.</p></header>
      {error ? (
        <div>
          <p role="alert">{error}</p>
          <button type="button" onClick={() => { setError(''); setAttempt(attempt + 1) }}>Try again</button>
        </div>
      ) : !faqs ? <p role="status">Loading support answers…</p> : (
        <div className="system-settings-grid">
          {faqs.map((faq) => <FaqForm key={faq.id} faq={faq} accessToken={accessToken} onSignOut={onSignOut} />)}
        </div>
      )}
    </section>
  )
}

function FaqForm({ faq, accessToken, onSignOut }) {
  const [question, setQuestion] = useState(faq.question)
  const [answer, setAnswer] = useState(faq.steps.join('\n'))
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  async function save(event) {
    event.preventDefault()
    if (saving) return
    setNotice('')
    setError('')
    const steps = answer.split('\n').map((step) => step.trim()).filter(Boolean)
    if (!question.trim() || !steps.length || steps.length > 8 || steps.some((step) => step.length > 300)) {
      setError('Enter a question and one to eight steps, up to 300 characters per line.')
      return
    }
    setSaving(true)
    try {
      const updated = await updateSupportFaq(accessToken, faq.id, { question: question.trim(), steps })
      setQuestion(updated.question)
      setAnswer(updated.steps.join('\n'))
      setNotice('Support answer saved.')
    } catch (failure) {
      if (failure instanceof StaffSessionError) onSignOut()
      else setError(failure.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="system-settings-tile support-faq-form" onSubmit={save}>
      <label>
        Question
        <input value={question} onChange={(event) => setQuestion(event.target.value)} required maxLength={160} disabled={saving} />
      </label>
      <label>
        Answer, one step per line
        <textarea value={answer} onChange={(event) => setAnswer(event.target.value)} rows={5} required disabled={saving} />
      </label>
      <button type="submit" className="system-settings-primary" disabled={saving}>{saving ? 'Saving…' : 'Save answer'}</button>
      {notice && <p role="status">{notice}</p>}
      {error && <p role="alert">{error}</p>}
    </form>
  )
}
