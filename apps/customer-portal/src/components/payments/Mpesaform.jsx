

import { useState } from 'react'
import { Smartphone, ShieldCheck, ArrowRight } from 'lucide-react'
import { useCheckout } from '../../context/CheckoutContext'

export default function MpesaForm({ onPaymentRequest }) {
  const {
    selectedPackage,
    phoneNumber,
    setPhoneNumber,
    paymentStatus
  } = useCheckout()

  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')

    if (!selectedPackage) {
      setError('Please select a package first.')
      return
    }

    const cleanedPhone = phoneNumber.replace(/\s/g, '')

    if (!/^(?:\+254|254|0)[17]\d{8}$/.test(cleanedPhone)) {
      setError('Enter a valid Kenyan mobile number.')
      return
    }

    if (paymentStatus === 'pending' || submitting) {
      setError('A payment request is already in progress.')
      return
    }

    if (!onPaymentRequest) {
      setError('Payment service is not connected yet.')
      return
    }

    try {
      setSubmitting(true)
      await onPaymentRequest(cleanedPhone)
    } catch (err) {
      setError(err.message || 'Unable to request payment. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm"
    >
      <div className="mb-5">
        <h2 className="text-xl font-bold text-[#17152D]">
          Pay with M-Pesa
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          Enter your Safaricom number to receive an STK payment prompt.
        </p>
      </div>

      <label
        htmlFor="mpesa-phone"
        className="mb-2 block text-sm font-medium text-[#17152D]"
      >
        M-Pesa Phone Number
      </label>

      <div className="flex items-center gap-3 rounded-xl border border-gray-200 px-4 py-3 focus-within:border-[#77709D]">
        <Smartphone size={19} className="text-[#77709D]" />

        <span className="text-sm text-gray-500">+254</span>

        <input
          id="mpesa-phone"
          type="tel"
          value={phoneNumber}
          onChange={(event) => setPhoneNumber(event.target.value)}
          placeholder="712 345 678"
          className="w-full bg-transparent text-sm text-[#17152D] outline-none"
          required
        />
      </div>

      {error && (
        <p className="mt-3 text-sm text-red-600">{error}</p>
      )}

      <div className="mt-4 flex gap-2 rounded-xl bg-[#F0EEF6] p-3">
        <ShieldCheck size={19} className="shrink-0 text-[#77709D]" />
        <p className="text-xs text-gray-600">
          Never share your M-Pesa PIN with anyone. Enter it only on the
          official Safaricom prompt on your phone.
        </p>
      </div>

      <button
        type="submit"
        disabled={submitting || paymentStatus === 'pending'}
        className="mt-5 flex w-full items-center justify-center gap-2 rounded-full bg-[#D9E52E] px-5 py-3 font-semibold text-[#17152D] transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {submitting ? 'Sending request...' : 'Request M-Pesa Payment'}
        {!submitting && <ArrowRight size={18} />}
      </button>
    </form>
  )
}
