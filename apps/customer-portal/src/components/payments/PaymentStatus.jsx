import {
  ArrowRight,
  CheckCircle2,
  Clock,
  Headset,
  RefreshCw,
  Smartphone,
  XCircle,
} from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { demoDataEnabled } from '../../../../shared/demoMode.js'
import { useCheckout } from '../../context/CheckoutContext'

const paymentViews = {
  pending: {
    icon: Smartphone,
    label: 'Waiting for M-Pesa confirmation',
    title: 'Check your phone',
    description: 'Enter your M-Pesa PIN on your phone to complete the payment.',
    note: 'If you already entered your PIN, wait for confirmation before starting another payment.',
    color: 'bg-[#eef3cc] text-[#414900]',
  },
  successful: {
    icon: CheckCircle2,
    label: 'Payment confirmed',
    title: 'Payment received',
    description: 'Your M-Pesa payment has been confirmed.',
    note: 'View your connection status to see whether internet access is ready. Please do not pay again for this purchase.',
    color: 'bg-[#eef3cc] text-[#414900]',
  },
  cancelled: {
    icon: XCircle,
    label: 'Transaction incomplete',
    title: 'Payment cancelled',
    description: 'The M-Pesa request was cancelled before payment was confirmed.',
    note: 'If you received a debit notification, contact support before starting another payment.',
    color: 'bg-red-100 text-red-800',
  },
  failed: {
    icon: XCircle,
    label: 'Transaction incomplete',
    title: 'Payment failed',
    description: 'We could not confirm payment for this request.',
    note: 'If you received a debit notification, contact support before starting another payment.',
    color: 'bg-red-100 text-red-800',
  },
  expired: {
    icon: Clock,
    label: 'Transaction incomplete',
    title: 'Payment request expired',
    description: 'The request timed out before we received confirmation.',
    note: 'If you received a debit notification, contact support before starting another payment.',
    color: 'bg-amber-100 text-amber-900',
  },
  not_started: {
    icon: Clock,
    label: 'Payment status',
    title: 'No payment request found',
    description: 'Choose a package to begin checkout.',
    color: 'bg-[#f0eef6] text-[#585172]',
  },
  unknown: {
    icon: Clock,
    label: 'Payment status',
    title: 'Payment status unavailable',
    description: 'We could not verify the status of this request. Contact support before starting another payment.',
    color: 'bg-[#f0eef6] text-[#585172]',
  },
}

const previewPackage = { name: 'Daily Connect', price: 50 }
const previewTransaction = { checkout_request_id: 'DEMO-001' }

const primaryAction =
  'inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-full bg-[#d5ec26] px-5 py-3 text-sm font-semibold text-[#202300] hover:bg-[#c4db1c] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#585172]'

const secondaryAction =
  'inline-flex min-h-11 items-center justify-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-[#47415e] underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#585172]'

function formatAmount(amount) {
  const value =
    typeof amount === 'string' && amount.trim() ? Number(amount) : amount

  if (!Number.isFinite(value)) return null

  return `KES ${new Intl.NumberFormat('en-KE', {
    maximumFractionDigits: 2,
  }).format(value)}`
}

function TransactionSummary({ selectedPackage, transaction, confirmed }) {
  const receipt =
    transaction?.mpesa_receipt_number ?? transaction?.receipt_number
  const reference = transaction?.reference ?? transaction?.checkout_request_id
  const amount = formatAmount(transaction?.amount ?? selectedPackage?.price)
  const packageName = selectedPackage?.name ?? transaction?.package_name

  if (!packageName && !amount && !receipt && !reference) return null

  return (
    <section className="mt-6 rounded-xl bg-[#f2f1ee] p-4 text-left">
      <h2 className="text-sm font-semibold text-[#17152d]">
        Transaction summary
      </h2>

      <dl className="mt-3 space-y-3 text-sm">
        {packageName && (
          <div className="grid grid-cols-2 gap-3">
            <dt className="text-[#57545f]">Selected package</dt>
            <dd className="break-words text-right font-medium">{packageName}</dd>
          </div>
        )}

        {amount && (
          <div className="grid grid-cols-2 gap-3">
            <dt className="text-[#57545f]">
              {confirmed ? 'Amount paid' : 'Amount payable'}
            </dt>
            <dd className="text-right font-medium">{amount}</dd>
          </div>
        )}

        {receipt && confirmed ? (
          <div className="grid grid-cols-2 gap-3">
            <dt className="text-[#57545f]">M-Pesa receipt</dt>
            <dd className="break-all text-right font-medium">{receipt}</dd>
          </div>
        ) : reference && (
          <div className="grid grid-cols-2 gap-3">
            <dt className="text-[#57545f]">Request reference</dt>
            <dd className="break-all text-right font-medium">{reference}</dd>
          </div>
        )}
      </dl>
    </section>
  )
}

export default function PaymentStatus() {
  const [searchParams] = useSearchParams()
  const checkout = useCheckout()
  const requestedPreview = searchParams.get('preview')
  const isPreview =
    demoDataEnabled && Object.hasOwn(paymentViews, requestedPreview)

  const paymentStatus = isPreview ? requestedPreview : checkout.paymentStatus
  const selectedPackage = isPreview ? previewPackage : checkout.selectedPackage
  const transaction = isPreview
    ? {
        ...previewTransaction,
        mpesa_receipt_number:
          paymentStatus === 'successful' ? 'DEMO-RECEIPT-001' : null,
      }
    : checkout.transaction

  const view = Object.hasOwn(paymentViews, paymentStatus)
    ? paymentViews[paymentStatus]
    : paymentViews.unknown

  const Icon = view.icon
  const isPending = paymentStatus === 'pending'
  const isSuccessful = paymentStatus === 'successful'
  const isIncomplete = ['cancelled', 'failed', 'expired'].includes(paymentStatus)
  const hasNoPayment = paymentStatus === 'not_started'

  return (
    <main className="grid min-h-screen place-items-center bg-[#f8f7f4] px-4 py-8 sm:py-12">
      <section
        aria-labelledby="payment-status-title"
        className="w-full max-w-md rounded-2xl border border-[#ebe9e5] bg-white p-5 text-center text-[#17152d] shadow-sm sm:p-7"
      >
        {isPreview && (
          <p className="mb-4 text-xs font-semibold text-[#585172]">
            Development preview · Sample transaction
          </p>
        )}

        <div role="status">
          <div className={`mx-auto grid h-14 w-14 place-items-center rounded-full ${view.color}`}>
            <Icon aria-hidden="true" size={26} />
          </div>

          <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-[#585172]">
            {view.label}
          </p>

          <h1 id="payment-status-title" className="mt-2 text-2xl font-bold sm:text-3xl">
            {view.title}
          </h1>

          <p className="mt-2 text-sm leading-relaxed text-[#57545f]">
            {view.description}
          </p>
        </div>

        {!hasNoPayment && (
          <TransactionSummary
            selectedPackage={selectedPackage}
            transaction={transaction}
            confirmed={isSuccessful}
          />
        )}

        {view.note && (
          <p className="mt-4 rounded-xl bg-[#f0eef6] p-4 text-left text-sm leading-relaxed text-[#47415e]">
            {view.note}
          </p>
        )}

        <div className="mt-6 space-y-3">
          {isPending && (
            <>
              <button
                type="button"
                disabled
                aria-describedby="payment-check-help"
                className={`${primaryAction} cursor-not-allowed bg-[#eeede9] text-[#57545f]`}
              >
                <RefreshCw aria-hidden="true" size={17} />
                Check payment status
              </button>
              <p id="payment-check-help" className="text-xs text-[#57545f]">
                Online payment status checks are unavailable.
              </p>
            </>
          )}

          {isSuccessful && !isPreview && (
            <Link to="/connection-status" className={primaryAction}>
              View connection status <ArrowRight aria-hidden="true" size={17} />
            </Link>
          )}

          {isIncomplete && selectedPackage && !isPreview && (
            <Link
              to="/confirm-package"
              state={{ selectedPackage }}
              className={primaryAction}
            >
              Return to checkout <ArrowRight aria-hidden="true" size={17} />
            </Link>
          )}

          {(hasNoPayment || isIncomplete) && (
            <Link
              to="/packages"
              className={hasNoPayment || !selectedPackage || isPreview
                ? primaryAction
                : secondaryAction}
            >
              Browse packages <ArrowRight aria-hidden="true" size={17} />
            </Link>
          )}

          {!hasNoPayment && (
            <Link to="/support" className={secondaryAction}>
              <Headset aria-hidden="true" size={16} /> Get support
            </Link>
          )}
        </div>
      </section>
    </main>
  )
}