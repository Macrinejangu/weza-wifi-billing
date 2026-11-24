import { ArrowRight, CheckCircle2, Clock, Headset, WifiOff } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getMyConnection } from '../services/api.js'
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
    note: 'Please do not pay again. Your package time started when your payment was confirmed.',
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
  expired: {
    icon: Clock,
    label: 'Package expired',
    title: 'Your package has ended',
    description: 'Choose another package to get back online.',
    tone: 'bg-[#f0eef6] text-[#47415e]',
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
  return <ConnectionView
    state={state}
    isPreview={isPreview}
    packageName={isPreview ? 'Daily Connect' : selectedPackage?.name}
    receipt={isPreview ? 'DEMO-RECEIPT-001' : transaction?.mpesa_receipt_number}
    reference={transaction?.reference ?? transaction?.checkout_request_id}
  />
}

export function CustomerConnectionStatus({ accessToken, onSessionExpired }) {
  const [searchParams] = useSearchParams()
  const paymentId = searchParams.get('payment')
  const [refresh, setRefresh] = useState(0)
  const [result, setResult] = useState(null)
  const [tick, setTick] = useState(0)
  const current = result?.paymentId === paymentId && result?.accessToken === accessToken
    ? result : null

  useEffect(() => {
    if (!accessToken) return undefined
    const controller = new AbortController()
    getMyConnection({ accessToken, paymentId, signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) {
          setResult({ accessToken, paymentId, data, receivedAt: performance.now() })
        }
      })
      .catch((error) => {
        if (!controller.signal.aborted) setResult({ accessToken, paymentId, error })
      })
    return () => controller.abort()
  }, [accessToken, paymentId, refresh])

  const data = current?.data
  useEffect(() => {
    if (!accessToken || !data?.expires_at) return undefined
    const interval = window.setInterval(() => setTick(performance.now()), 1000)
    return () => window.clearInterval(interval)
  }, [accessToken, data])

  useEffect(() => {
    if (!accessToken || data?.access_status !== 'activating') return undefined
    const timeout = window.setTimeout(() => setRefresh((value) => value + 1), 5000)
    return () => window.clearTimeout(timeout)
  }, [accessToken, data])

  if (!accessToken || current?.error?.status === 401) {
    return (
      <section className="page-heading">
        <h1>Connection status</h1>
        <p role="status">Sign in to check your connection.</p>
        <Link to="/login" state={{ returnConnection: true, returnPaymentId: paymentId }}
          onClick={onSessionExpired} className={primaryLink}>Sign in</Link>
      </section>
    )
  }

  if (!current || current.error || !data) {
    return (
      <section className="page-heading">
        <h1>Connection status</h1>
        <p role="status">{!current ? 'Checking your connection…' : current.error
          ? 'Connection status could not be checked.' : 'No paid package found yet.'}</p>
        {current?.error
          ? <button type="button" onClick={() => setRefresh((value) => value + 1)}>Check again</button>
          : current && <Link to="/packages" className={primaryLink}>Browse packages</Link>}
      </section>
    )
  }

  const expiry = Date.parse(data.expires_at)
  const serverNow = Date.parse(data.server_now) + Math.max(0, tick - current.receivedAt)
  const remaining = Number.isFinite(expiry) && Number.isFinite(serverNow)
    ? Math.max(0, Math.ceil((expiry - serverNow) / 1000)) : null
  const state = remaining === 0 ? 'expired' : data.access_status

  return <ConnectionView
    state={state}
    packageName={data.package_name}
    receipt={data.mpesa_receipt_number}
    remaining={remaining}
    paymentId={data.payment_id}
    simulated={data.simulated}
    onCheck={() => setRefresh((value) => value + 1)}
  />
}

function ConnectionView({ state, isPreview, packageName, receipt, reference, remaining, paymentId, simulated, onCheck }) {
  const view = simulated && state === 'active'
    ? { ...views.active, label: 'Simulated access active', title: 'Test access is active',
        description: 'The test package has started.' }
    : Object.hasOwn(views, state) ? views[state] : views.unknown
  const Icon = view.icon
  const showPaymentDetails = state !== 'unconfirmed'

  return (
    <main className="grid min-h-screen place-items-center bg-[#f8f7f4] px-4 py-8 sm:py-12">
      <section
        aria-labelledby="connection-status-title"
        className="w-full max-w-md rounded-2xl border border-[#ebe9e5] bg-white p-5 text-center text-[#17152d] shadow-sm sm:p-7"
      >
        {(isPreview || simulated) && (
          <p className="mb-4 text-xs font-semibold text-[#585172]">
            {simulated ? 'Simulated connection. No router was contacted.' : 'Development preview · Sample transaction'}
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
                <dt className="text-[#57545f]">{receipt ? (simulated ? 'Test receipt' : 'M-Pesa receipt') : 'Request reference'}</dt>
                <dd className="break-all text-right font-medium">{receipt ?? reference}</dd>
              </div>
            )}
          </dl>
        )}

        {remaining != null && (
          <p className="mt-4 font-semibold">
            Time left: {Math.floor(remaining / 60)} min {remaining % 60} sec
          </p>
        )}

        {view.note && (
          <p className={`mt-4 rounded-xl p-4 text-left text-sm leading-relaxed ${view.tone}`}>
            {view.note}
          </p>
        )}

        <div className="mt-6 space-y-3">
          {state === 'expired' && <Link to="/packages" className={primaryLink}>Browse packages</Link>}
          {onCheck && state !== 'expired' && (
            <button type="button" onClick={onCheck} className={secondaryLink}>Check connection status</button>
          )}
          {state === 'active' && !onCheck && (
            <Link to="/dashboard" className={primaryLink}>
              View overview <ArrowRight aria-hidden="true" size={17} />
            </Link>
          )}
          {state === 'unconfirmed' && (
            <Link to={paymentId ? `/payment-status?payment=${paymentId}` : '/payment-status'} className={primaryLink}>
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