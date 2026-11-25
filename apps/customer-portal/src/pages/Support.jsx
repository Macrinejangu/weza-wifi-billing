import { ArrowLeft, CircleHelp, Wifi } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listSupportFaqs } from '../services/api.js'

export default function Support() {
  const [faqs, setFaqs] = useState(null)
  const [attempt, setAttempt] = useState(0)
  const [error, setError] = useState(false)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    const controller = new AbortController()
    listSupportFaqs(controller.signal).then((items) => {
      if (controller.signal.aborted) return
      if (!Array.isArray(items) || items.length === 0) throw new Error('No help topics')
      setFaqs(items)
    }).catch(() => {
      if (!controller.signal.aborted) setError(true)
    })
    return () => controller.abort()
  }, [attempt])

  return (
    <>
      <header className="public-header">
        <div className="public-header-inner">
          <Link to="/" className="public-brand">
            <span className="public-brand-icon"><Wifi size={20} aria-hidden="true" /></span>
            <strong>Weza Wi-Fi</strong>
          </Link>
          <span aria-current="page" className="public-button">Support</span>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6 sm:py-12">
        <header className="mb-8 text-center">
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Help &amp; Support</h1>
        </header>

        <section aria-labelledby="support-chat" className="rounded-2xl border border-[#edece8] bg-white p-4 sm:p-6">
          <h2 id="support-chat" className="mb-4 text-lg font-bold">Weza support chat</h2>
          <p className="rounded-xl bg-[#f4f3f0] p-3">How can we help? Choose a topic below.</p>
          <div role="log" aria-label="Support conversation" aria-live="polite">
            {selected && (
              <div className="my-4 space-y-3">
                <p className="ml-auto w-fit rounded-xl bg-[#ece7fa] px-4 py-3">{selected.question}</p>
                <ol className="list-decimal space-y-2 rounded-xl bg-[#f4f3f0] py-3 pl-8 pr-4">
                  {selected.steps.map((step, index) => <li key={index}>{step}</li>)}
                </ol>
              </div>
            )}
          </div>

          {error ? (
            <div className="mt-4">
              <p role="alert">Help topics could not load.</p>
              <button type="button" className="underline" onClick={() => { setError(false); setAttempt(attempt + 1) }}>Try again</button>
            </div>
          ) : !faqs ? <p role="status" className="mt-4">Loading help topics…</p> : (
            <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label="Help topics">
              {faqs.map((faq) => (
                <button
                  key={faq.id}
                  type="button"
                  aria-pressed={selected?.id === faq.id}
                  className="min-h-11 rounded-xl border border-[#726b91] px-3 text-left text-sm font-semibold aria-pressed:bg-[#ece7fa]"
                  onClick={() => setSelected(faq)}
                >
                  {faq.question}
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="mt-6 flex items-start gap-3 rounded-xl border border-[#edece8] bg-white p-4">
          <span className="rounded-lg bg-[#d9e52e] p-2"><CircleHelp size={19} aria-hidden="true" /></span>
          <div>
            <h2 className="font-bold">Still need help?</h2>
            <p className="mt-1 text-sm text-[#655f75]">Support contact details are awaiting confirmation.</p>
          </div>
        </section>

        <div className="mt-6 text-center">
          <Link to="/" className="public-button"><ArrowLeft size={18} aria-hidden="true" /> Back to portal home</Link>
        </div>
      </main>
    </>
  )
}
