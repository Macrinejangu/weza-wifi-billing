


import {
  CheckCircle2,
  Clock,
  Wifi,
  WifiOff,
  XCircle,
  LoaderCircle,
  ArrowRight,
  RefreshCw,
  Headset
} from 'lucide-react'

import { Link } from 'react-router-dom'
import { useCheckout } from '../../context/CheckoutContext'

export default function PaymentStatus() {
  const {
    selectedPackage,
    transaction,
    paymentStatus,
    activationStatus
  } = useCheckout()

  const transactionReference =
    transaction?.reference || transaction?.checkout_request_id

  // 1. Waiting for M-Pesa confirmation
  if (paymentStatus === 'pending') {
    return (
      <StatusLayout>
        <LoaderCircle className="mx-auto animate-spin text-[#77709D]" size={55} />

        <h1 className="mt-5 text-2xl font-bold text-[#17152D]">
          Waiting for payment
        </h1>

        <p className="mt-3 text-sm text-gray-500">
          Check your phone and enter your M-Pesa PIN to complete payment.
        </p>

        <StatusNote>
          Do not close this page while we confirm your payment.
        </StatusNote>
      </StatusLayout>
    )
  }

  // 2. Payment confirmed, Wi-Fi activating
  if (
    paymentStatus === 'successful' &&
    activationStatus === 'activating'
  ) {
    return (
      <StatusLayout>
        <CheckCircle2 className="mx-auto text-green-600" size={55} />

        <h1 className="mt-5 text-2xl font-bold text-[#17152D]">
          Payment confirmed!
        </h1>

        <p className="mt-3 text-sm text-gray-500">
          Your payment has been received. We are now activating your Wi-Fi.
        </p>

        <LoaderCircle className="mx-auto mt-6 animate-spin text-[#77709D]" size={30} />

        <StatusNote>
          Please wait. You do not need to make another payment.
        </StatusNote>
      </StatusLayout>
    )
  }

  // 3. Payment received, but Wi-Fi activation failed
  if (
    paymentStatus === 'successful' &&
    activationStatus === 'failed'
  ) {
    return (
      <StatusLayout>
        <WifiOff className="mx-auto text-orange-500" size={55} />

        <h1 className="mt-5 text-2xl font-bold text-[#17152D]">
          Payment received, internet not active
        </h1>

        <p className="mt-3 text-sm text-gray-500">
          Your payment was successful, but we could not activate your internet yet.
        </p>

        <StatusNote>
          You have already paid. Please do not pay again.
          Contact support if the problem continues.
        </StatusNote>

        <Link to="/connection-status" className="status-button">
          Check connection status <ArrowRight size={17} />
        </Link>

        <Link to="/support" className="mt-3 text-sm font-semibold text-[#77709D]">
          Contact support
        </Link>
      </StatusLayout>
    )
  }

  // 4. Payment and Wi-Fi activation successful
  if (
    paymentStatus === 'successful' &&
    activationStatus === 'active'
  ) {
    return (
      <StatusLayout>
        <CheckCircle2 className="mx-auto text-green-600" size={60} />

        <h1 className="mt-5 text-2xl font-bold text-[#17152D]">
          You're connected!
        </h1>

        <p className="mt-3 text-sm text-gray-500">
          Your payment was received and your Wi-Fi is now active.
        </p>

        <div className="mt-5 flex items-center justify-center gap-2 rounded-xl bg-green-50 p-4 text-green-700">
          <Wifi size={20} />
          <span className="font-semibold">Internet activated</span>
        </div>

        <Link to="/connection-status" className="status-button">
          View connection <ArrowRight size={17} />
        </Link>

        <Link to="/dashboard" className="mt-3 text-sm font-semibold text-[#77709D]">
          Go to dashboard
        </Link>
      </StatusLayout>
    )
  }

  // 5. Payment unsuccessful
  if (paymentStatus === 'failed') {
    return (
      <StatusLayout>
        <XCircle className="mx-auto text-red-500" size={55} />

        <h1 className="mt-5 text-2xl font-bold text-[#17152D]">
          Payment not completed
        </h1>

        <p className="mt-3 text-sm text-gray-500">
          Your M-Pesa payment was unsuccessful, cancelled or declined.
        </p>

        <StatusNote>
          No successful payment has been recorded for this request.
        </StatusNote>

        <Link
          to="/confirm-package"
          state={{ selectedPackage }}
          className="status-button"
        >
          <RefreshCw size={17} /> Try again
        </Link>
      </StatusLayout>
    )
  }

  // Default state
  return (
    <StatusLayout>
      <Clock className="mx-auto text-[#77709D]" size={55} />

      <h1 className="mt-5 text-2xl font-bold text-[#17152D]">
        No payment request found
      </h1>

      <p className="mt-3 text-sm text-gray-500">
        Choose a package to begin your checkout.
      </p>

      <Link to="/packages" className="status-button">
        Browse packages <ArrowRight size={17} />
      </Link>
    </StatusLayout>
  )

  function StatusLayout({ children }) {
    return (
      <div className="mx-auto flex min-h-[70vh] w-full max-w-lg items-center justify-center px-4 py-10">
        <div className="w-full rounded-2xl border border-gray-200 bg-white p-7 text-center shadow-sm">
          {children}

          {transactionReference && (
            <p className="mt-6 border-t border-gray-100 pt-4 text-xs text-gray-500">
              Transaction reference: {transactionReference}
            </p>
          )}

          {selectedPackage && (
            <p className="mt-2 text-xs text-gray-500">
              Package: {selectedPackage.name}
            </p>
          )}
        </div>
      </div>
    )
  }

  function StatusNote({ children }) {
    return (
      <div className="mt-5 rounded-xl bg-[#F0EEF6] p-4 text-sm text-[#585172]">
        {children}
      </div>
    )
  }
}
