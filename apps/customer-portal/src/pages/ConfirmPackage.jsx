import { ArrowLeft, ArrowRight, Smartphone, Wifi } from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

export default function ConfirmPackage() {
  const { state } = useLocation()
  const selectedPackage = state?.selectedPackage
  const [feedback, setFeedback] = useState(null)

  function handlePayment(event) {
    event.preventDefault()
    const phone = new FormData(event.currentTarget).get('phone').replace(/\s/g, '')

    if (!/^(?:\+254|254|0)[17]\d{8}$/.test(phone)) {
      setFeedback({ text: 'Enter a Kenyan mobile number, for example 0712 345 678.', error: true })
      return
    }

    setFeedback({ text: 'This is a preview. No M-Pesa prompt was sent.', error: false })
  }

  return (
    <div className="mx-auto w-full max-w-lg">
      <Link to="/packages" className="mb-4 inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-[#585172]">
        <ArrowLeft size={16} aria-hidden="true" /> Back to packages
      </Link>

      <header className="page-heading">
        <h1>{selectedPackage ? 'Confirm your package' : 'No package selected'}</h1>
        <p>{selectedPackage ? 'Review your package and enter your M-Pesa number.' : 'Choose a package before opening checkout.'}</p>
      </header>

      {selectedPackage && (
        <section className="rounded-2xl border border-[#edece8] bg-white p-4 sm:p-6">
          <div className="rounded-xl bg-[#f4f3f0] p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-3">
                <Wifi size={21} className="shrink-0 text-[#585172]" aria-hidden="true" />
                <h2 className="text-base font-bold">{selectedPackage.name}</h2>
              </div>
              <strong className="text-lg">KES {selectedPackage.price.toLocaleString('en-KE')}</strong>
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-[#655f75]">Data allowance</dt>
                <dd className="font-semibold">{selectedPackage.data}</dd>
              </div>
              <div>
                <dt className="text-[#655f75]">Validity</dt>
                <dd className="font-semibold">{selectedPackage.duration}</dd>
              </div>
            </dl>
          </div>

          <form onSubmit={handlePayment} className="mt-6">
            <label htmlFor="checkout-phone" className="mb-2 flex items-center gap-2 text-sm font-semibold">
              <Smartphone size={17} aria-hidden="true" /> M-Pesa phone number
            </label>
            <input
              id="checkout-phone"
              name="phone"
              type="tel"
              autoComplete="tel"
              placeholder="0712 345 678"
              aria-describedby="checkout-help"
              aria-invalid={feedback?.error || undefined}
              onChange={() => setFeedback(null)}
              required
              className="min-h-11 w-full rounded-lg border border-[#edece8] bg-[#f4f3f0] px-3 py-2 focus-visible:outline-2 focus-visible:outline-[#726b91]"
            />
            <p id="checkout-help" className="mt-2 text-sm text-[#655f75]">Use a sample number for this preview.</p>

            <button type="submit" className="package-button">
              Preview M-Pesa payment <ArrowRight size={17} aria-hidden="true" />
            </button>
            {feedback && (
              <p role={feedback.error ? 'alert' : 'status'} className={feedback.error ? 'mt-3 text-sm text-red-700' : 'mt-3 text-sm text-[#585172]'}>
                {feedback.text}
              </p>
            )}
          </form>
        </section>
      )}
    </div>
  )
}
