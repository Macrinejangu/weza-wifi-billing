import { ArrowLeft, ArrowRight, Smartphone, Wifi } from 'lucide-react'
import { useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { demoDataEnabled } from '../../../shared/demoMode.js'
import { createCustomerPurchase, startMpesaPayment } from '../services/api.js'

const sandboxEnabled =
  import.meta.env.DEV && import.meta.env.VITE_ENABLE_SANDBOX_CHECKOUT === 'true'

const sandboxPackageId = Number(import.meta.env.VITE_SANDBOX_PACKAGE_ID)
const kenyanMobile = /^(?:\+?254|0)([17][0-9]{8})$/

const retryableErrors = {
  provider_rejected: 'M-Pesa declined the request. Check the number before trying again.',
  provider_not_reached: 'We could not reach M-Pesa. Please try again later.',
  payments_not_configured: 'M-Pesa checkout is currently unavailable.',
}

function paymentErrorFeedback(error) {
  if (error.code === 'payment_already_pending') {
    return {
      kind: 'blocked',
      text: 'A payment is already pending. Check your phone before trying again.',
      paymentId: error.paymentId,
    }
  }

  if (error.status === 422) {
    return {
      kind: 'phone-error',
      text: 'Enter a valid Kenyan mobile number, for example 0712 345 678.',
    }
  }

  const retryMessage = Object.hasOwn(retryableErrors, error.code)
    ? retryableErrors[error.code]
    : null

  if (retryMessage) return { kind: 'error', text: retryMessage }

  if (error.status === 404 || error.code === 'purchase_not_payable') {
    return {
      kind: 'blocked',
      text: 'Checkout is unavailable for this purchase. Go back to packages or get support.',
    }
  }

  return {
    kind: 'blocked',
    text: 'We could not confirm whether the M-Pesa prompt was sent. Check your phone and get support before trying again.',
    paymentId: error.paymentId,
  }
}

export default function ConfirmPackage({ accessToken }) {
  const { state, key: checkoutKey } = useLocation()
  const selectedPackage = state?.selectedPackage
  const [feedback, setFeedback] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const requestInProgress = useRef(false)
  const purchaseRequest = useRef(null)

  const isSandboxCheckout =
    sandboxEnabled &&
    selectedPackage?.id === sandboxPackageId

  const showForm = Boolean(selectedPackage && (demoDataEnabled || (isSandboxCheckout && accessToken)))
  const isSandboxSubmission = isSandboxCheckout && !demoDataEnabled
  const paymentLocked = feedback?.kind === 'pending' || feedback?.kind === 'blocked'
  const isPhoneError = feedback?.kind === 'phone-error'
  const isAlert = feedback && feedback.kind !== 'pending' && feedback.kind !== 'preview'

  async function handlePayment(event) {
    event.preventDefault()
    if (!showForm || requestInProgress.current || paymentLocked) return

    const phone = String(new FormData(event.currentTarget).get('phone') ?? '')
      .replace(/\s/g, '')
    const match = phone.match(kenyanMobile)

    if (!match) {
      setFeedback({
        kind: 'phone-error',
        text: 'Enter a Kenyan mobile number, for example 0712 345 678.',
      })
      return
    }

    if (!isSandboxSubmission) {
      setFeedback({
        kind: 'preview',
        text: 'This is a preview. No M-Pesa prompt was sent.',
      })
      return
    }

    requestInProgress.current = true
    setIsSubmitting(true)
    setFeedback(null)

    let purchase
    try {
      if (purchaseRequest.current?.checkoutKey !== checkoutKey ||
          purchaseRequest.current?.accessToken !== accessToken) {
        purchaseRequest.current = { checkoutKey, accessToken, key: crypto.randomUUID() }
      }

      purchase = await createCustomerPurchase({
        accessToken,
        packageId: selectedPackage.id,
        idempotencyKey: purchaseRequest.current.key,
      })
      if (!Number.isSafeInteger(purchase?.id) || purchase.id <= 0) {
        setFeedback({ kind: 'error', text: 'Could not confirm the purchase. Please try again.' })
        return
      }
      if (purchase.amount !== selectedPackage.price) {
        setFeedback({ kind: 'blocked', text: 'The package price changed. Go back to packages and review the current price.' })
        return
      }

      const payment = await startMpesaPayment({
        accessToken,
        purchaseId: purchase.id,
        phoneNumber: `254${match[1]}`,
      })

      if (payment?.status !== 'pending' || payment.purchase_id !== purchase.id) {
        setFeedback(paymentErrorFeedback({}))
        return
      }

      setFeedback({
        kind: 'pending',
        text: 'Check your phone for the M-Pesa prompt. Your payment is pending confirmation.',
        paymentId: payment.payment_id,
      })
    } catch (error) {
      if (error.status === 401) {
        setFeedback({ kind: 'blocked', text: 'Your session expired. Sign in again to continue.' })
      } else if (!purchase) {
        setFeedback({ kind: 'error', text: 'Could not confirm the purchase. Check the package or try again.' })
      } else {
        setFeedback(paymentErrorFeedback(error))
      }
    } finally {
      requestInProgress.current = false
      setIsSubmitting(false)
    }
  }

  return (
    <div className="mx-auto w-full max-w-lg">
      <Link
        to="/packages"
        className="mb-4 inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-[#585172]"
      >
        <ArrowLeft size={16} aria-hidden="true" /> Back to packages
      </Link>

      <header className="page-heading">
        <h1>{selectedPackage ? 'Confirm your package' : 'No package selected'}</h1>
        <p>
          {selectedPackage
            ? 'Review your package before continuing.'
            : 'Choose a package before opening checkout.'}
        </p>
      </header>

      {selectedPackage && (
        <section className="rounded-2xl border border-[#edece8] bg-white p-4 sm:p-6">
          <div className="rounded-xl bg-[#f4f3f0] p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-3">
                <Wifi size={21} className="shrink-0 text-[#585172]" aria-hidden="true" />
                <h2 className="text-base font-bold">{selectedPackage.name}</h2>
              </div>
              <strong className="text-lg">
                KES {selectedPackage.price.toLocaleString('en-KE')}
              </strong>
            </div>

            <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
              {selectedPackage.data && (
                <div>
                  <dt className="text-[#655f75]">Data allowance</dt>
                  <dd className="font-semibold">{selectedPackage.data}</dd>
                </div>
              )}
              <div>
                <dt className="text-[#655f75]">Validity</dt>
                <dd className="font-semibold">{selectedPackage.duration}</dd>
              </div>
              {selectedPackage.speed && (
                <div>
                  <dt className="text-[#655f75]">Speed</dt>
                  <dd className="font-semibold">{selectedPackage.speed}</dd>
                </div>
              )}
            </dl>
          </div>

          {!showForm && (
            <p role="status" className="mt-4 text-sm text-[#655f75]">
              {isSandboxCheckout && !accessToken ? (
                <>Sign in to continue. <Link to="/login" className="underline">Sign in</Link></>
              ) : 'Live checkout is currently unavailable.'}
            </p>
          )}

          {showForm && (
            <form onSubmit={handlePayment} className="mt-6">
              <label
                htmlFor="checkout-phone"
                className="mb-2 flex items-center gap-2 text-sm font-semibold"
              >
                <Smartphone size={17} aria-hidden="true" /> M-Pesa phone number
              </label>
              <input
                id="checkout-phone"
                name="phone"
                type="tel"
                autoComplete="tel"
                placeholder="0712 345 678"
                aria-describedby={isPhoneError ? 'checkout-help checkout-feedback' : 'checkout-help'}
                aria-invalid={isPhoneError || undefined}
                disabled={isSubmitting || paymentLocked}
                onChange={() => setFeedback(null)}
                required
                className="min-h-11 w-full rounded-lg border border-[#edece8] bg-[#f4f3f0] px-3 py-2 focus-visible:outline-2 focus-visible:outline-[#726b91]"
              />
              <p id="checkout-help" className="mt-2 text-sm text-[#655f75]">
                {isSandboxSubmission
                  ? 'Sandbox checkout. Use the agreed test number. Enter your PIN only on your phone.'
                  : 'Use a sample number for this preview.'}
              </p>

              <button
                type="submit"
                disabled={isSubmitting || paymentLocked}
                className="package-button disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSubmitting
                  ? 'Requesting M-Pesa prompt…'
                  : isSandboxSubmission
                    ? 'Request M-Pesa payment'
                    : 'Preview M-Pesa payment'}
                <ArrowRight size={17} aria-hidden="true" />
              </button>

              {feedback && (
                <p
                  id="checkout-feedback"
                  role={isAlert ? 'alert' : 'status'}
                  className={isAlert ? 'mt-3 text-sm text-red-700' : 'mt-3 text-sm text-[#585172]'}
                >
                  {feedback.text}
                  {Number.isSafeInteger(feedback.paymentId) && feedback.paymentId > 0 && (
                    <> Payment reference: {feedback.paymentId}.{' '}
                    <Link to={`/payment-status?payment=${feedback.paymentId}`} className="underline">
                      Check payment status
                    </Link></>
                  )}
                  {feedback.kind === 'blocked' && (
                    <> <Link to="/support" className="underline">Get support</Link></>
                  )}
                </p>
              )}
            </form>
          )}
        </section>
      )}
    </div>
  )
}