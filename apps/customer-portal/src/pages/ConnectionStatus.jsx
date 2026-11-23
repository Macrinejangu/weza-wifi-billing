import { ArrowRight, CheckCircle2, Clock, Headset, WifiOff } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { demoDataEnabled } from '../../../shared/demoMode.js'
import { useCheckout } from '../context/CheckoutContext'

const views = {
  unconfirmed: {
    icon: Clock,
    label: 'Payment confirmation needed',
    title: 'Connection status unavailable',
    description: 'Internet access requires a confirmed payment.',
    tone: 'bg-[#f0eef6] text-[#47415e]',
  },
  activating: {
    icon: Clock,
    label: 'Activation in progress',
    title: 'Payment received',
    description: 'We’re setting up your internet connection.',
    note: 'Please do not pay again. Your package validity starts once activation succeeds.',
    tone: 'bg-[#eef3cc] text-[#414900]',
  },
  active: {
    icon: CheckCircle2,
    label: 'Internet active',
    title: 'You’re connected!',
    description: 'Your internet access is active and ready to use.',
    tone: 'bg-[#eef3cc] text-[#414900]',
  },
  failed: {
    icon: WifiOff,
    label: 'Activation unsuccessful',
    title: 'Payment received, internet not active',
    description: 'We received your payment but could not activate your internet.',
    note: 'Please do not pay again. Contact support and share your payment reference if available.',
    tone: 'bg-amber-100 text-amber-900',
  },
  unknown: {
    icon: Clock,
    label: 'Activation status unavailable',
    title: 'Payment received',
    description: 'We could not verify whether internet access is active.',
    note: 'Please do not pay again. Contact support if you need help.',
    tone: 'bg-[#f0eef6] text-[#47415e]',
  },
}

const previewStates = ['activating', 'active', 'failed']

const primaryLink =
  'inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-full bg-[#d5ec26] px-5 py-3 text-sm font-semibold text-[#202300] hover:bg-[#c4db1c] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#585172]'

const secondaryLink =
  'inline-flex min-h-11 items-center justify-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-[#47415e] underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#585172]'

function getConnectionState(paymentStatus, activationStatus) {
  if (paymentStatus !== 'successful') return 'unconfirmed'
  if (activationStatus === 'active' || activationStatus === 'succeeded') return 'active'
  if (activationStatus === 'failed') return 'failed'
  if (activationStatus === 'not_started' || activationStatus === 'activating') {
    return 'activating'
  }
  return 'unknown'
}

export default function ConnectionStatus() {
  const [searchParams] = useSearchParams()
  const { selectedPackage, transaction, paymentStatus, activationStatus } = useCheckout()
  const preview = searchParams.get('preview')
  const isPreview = demoDataEnabled && previewStates.includes(preview)
  const state = isPreview ? preview : getConnectionState(paymentStatus, activationStatus)
  const view = views[state]
  const Icon = view.icon
  const showPaymentDetails = state !== 'unconfirmed'
  const packageName = isPreview ? 'Daily Connect' : selectedPackage?.name
  const receipt = isPreview ? 'DEMO-RECEIPT-001' : transaction?.mpesa_receipt_number
  const reference = transaction?.reference ?? transaction?.checkout_request_id

  return (
    <main className="grid min-h-screen place-items-center bg-[#f8f7f4] px-4 py-8 sm:py-12">
      <section
        aria-labelledby="connection-status-title"
        className="w-full max-w-md rounded-2xl border border-[#ebe9e5] bg-white p-5 text-center text-[#17152d] shadow-sm sm:p-7"
      >
        {isPreview && (
          <p className="mb-4 text-xs font-semibold text-[#585172]">
            Development preview · Sample transaction
          </p>
        )}

        <div role="status">
          <div className={`mx-auto grid h-14 w-14 place-items-center rounded-full ${view.tone}`}>
            <Icon aria-hidden="true" size={26} />
          </div>
          <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-[#585172]">
            {view.label}
          </p>
          <h1 id="connection-status-title" className="mt-2 text-2xl font-bold sm:text-3xl">
            {view.title}
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-[#57545f]">{view.description}</p>
        </div>

        {showPaymentDetails && (packageName || receipt || reference) && (
          <dl className="mt-6 space-y-3 rounded-xl bg-[#f2f1ee] p-4 text-left text-sm">
            {packageName && (
              <div className="grid grid-cols-2 gap-3">
                <dt className="text-[#57545f]">Package</dt>
                <dd className="break-words text-right font-medium">{packageName}</dd>
              </div>
            )}
            {(receipt || reference) && (
              <div className="grid grid-cols-2 gap-3">
                <dt className="text-[#57545f]">{receipt ? 'M-Pesa receipt' : 'Request reference'}</dt>
                <dd className="break-all text-right font-medium">{receipt ?? reference}</dd>
              </div>
            )}
          </dl>
        )}

        {view.note && (
          <p className={`mt-4 rounded-xl p-4 text-left text-sm leading-relaxed ${view.tone}`}>
            {view.note}
          </p>
        )}

        <div className="mt-6 space-y-3">
          {state === 'active' && (
            <Link to="/dashboard" className={primaryLink}>
              View overview <ArrowRight aria-hidden="true" size={17} />
            </Link>
          )}
          {state === 'unconfirmed' && (
            <Link to="/payment-status" className={primaryLink}>
              View payment status <ArrowRight aria-hidden="true" size={17} />
            </Link>
          )}
          <Link
            to="/support"
            className={state === 'failed' || state === 'unknown' ? primaryLink : secondaryLink}
          >
            <Headset aria-hidden="true" size={16} /> Get support
          </Link>
        </div>
      </section>
    </main>
  )
}