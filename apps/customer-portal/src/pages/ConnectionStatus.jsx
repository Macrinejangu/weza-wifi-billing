import {
  Wifi,
  WifiOff,
  Clock,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Headset
} from 'lucide-react'

import { Link } from 'react-router-dom'
import { useCheckout } from '../context/CheckoutContext'

export default function ConnectionStatus() {
  const {
    selectedPackage,
    paymentStatus,
    activationStatus
  } = useCheckout()

  const isActive = activationStatus === 'active'
  const isActivating = activationStatus === 'activating'
  const hasFailed = activationStatus === 'failed'

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-8">

      <div className="mb-6">
        <p className="text-sm font-medium text-[#77709D]">
          WEZA Wi-Fi
        </p>

        <h1 className="mt-2 text-2xl font-bold text-[#17152D]">
          Connection Status
        </h1>

        <p className="mt-1 text-sm text-gray-500">
          Check the status of your internet connection.
        </p>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">

        <div className="text-center">

          {isActive && (
            <>
              <CheckCircle2
                size={60}
                className="mx-auto text-green-600"
              />

              <h2 className="mt-4 text-xl font-bold text-[#17152D]">
                You're connected!
              </h2>

              <p className="mt-2 text-sm text-gray-500">
                Your WEZA Wi-Fi connection is active.
              </p>
            </>
          )}

          {isActivating && (
            <>
              <Clock
                size={60}
                className="mx-auto text-[#77709D]"
              />

              <h2 className="mt-4 text-xl font-bold text-[#17152D]">
                Activating your internet
              </h2>

              <p className="mt-2 text-sm text-gray-500">
                Your payment is confirmed. We are configuring your connection.
              </p>
            </>
          )}

          {hasFailed && (
            <>
              <WifiOff
                size={60}
                className="mx-auto text-orange-500"
              />

              <h2 className="mt-4 text-xl font-bold text-[#17152D]">
                Internet not activated
              </h2>

              <p className="mt-2 text-sm text-gray-500">
                Your payment was received, but your internet connection could not be activated.
              </p>
            </>
          )}

          {!isActive && !isActivating && !hasFailed && (
            <>
              <AlertCircle
                size={60}
                className="mx-auto text-gray-400"
              />

              <h2 className="mt-4 text-xl font-bold text-[#17152D]">
                No active connection
              </h2>

              <p className="mt-2 text-sm text-gray-500">
                Your internet connection is not currently active.
              </p>
            </>
          )}

        </div>

        <div className="mt-7 space-y-4 border-t border-gray-100 pt-5">

          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-500">Payment status</span>

            <span className="font-semibold text-[#17152D]">
              {paymentStatus === 'successful'
                ? 'Payment received'
                : paymentStatus === 'pending'
                  ? 'Pending'
                  : paymentStatus === 'failed'
                    ? 'Failed'
                    : 'Not paid'}
            </span>
          </div>

          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-500">Internet status</span>

            <span className="font-semibold text-[#17152D]">
              {isActive
                ? 'Active'
                : isActivating
                  ? 'Activating'
                  : hasFailed
                    ? 'Activation failed'
                    : 'Not active'}
            </span>
          </div>

          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-500">Selected package</span>

            <span className="font-semibold text-[#17152D]">
              {selectedPackage?.name || 'No package selected'}
            </span>
          </div>

        </div>

        {paymentStatus === 'successful' && !isActive && (
          <div className="mt-5 rounded-xl bg-[#F0EEF6] p-4 text-sm text-[#585172]">
            Your payment has already been received. Please do not make another payment while we resolve your connection.
          </div>
        )}

        {isActive && (
          <Link
            to="/dashboard"
            className="mt-6 flex w-full items-center justify-center gap-2 rounded-full bg-[#D9E52E] px-5 py-3 font-semibold text-[#17152D]"
          >
            Start browsing <Wifi size={18} />
          </Link>
        )}

        {!isActive && (
          <Link
            to="/payment-status"
            className="mt-6 flex w-full items-center justify-center gap-2 rounded-full bg-[#D9E52E] px-5 py-3 font-semibold text-[#17152D]"
          >
            View payment status <RefreshCw size={17} />
          </Link>
        )}

        <Link
          to="/support"
          className="mt-4 flex items-center justify-center gap-2 text-sm font-semibold text-[#77709D]"
        >
          <Headset size={17} /> Contact support
        </Link>

      </div>
    </div>
  )
}
