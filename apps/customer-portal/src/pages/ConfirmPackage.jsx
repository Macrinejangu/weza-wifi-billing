
import { useEffect } from 'react'
import { ArrowLeft } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'

import { useCheckout } from '../context/CheckoutContext'
import PackageSummary from '../components/payments/PackageSummary'
import MpesaForm from '../components/payments/Mpesaform'

export default function ConfirmPackage() {
  const { state } = useLocation()
  const selectedPackage = state?.selectedPackage

  const { setSelectedPackage } = useCheckout()

  // Save the selected package in the shared checkout context
  useEffect(() => {
    if (selectedPackage) {
      setSelectedPackage(selectedPackage)
    }
  }, [selectedPackage, setSelectedPackage])

  async function handlePaymentRequest(phone) {
    // Backend integration will go here.
    // Do not mark payment as successful before M-Pesa confirms it.
    throw new Error(
      'M-Pesa payment is not connected to the backend yet.'
    )
  }

  return (
    <div className="mx-auto w-full max-w-lg">

      <Link
        to="/packages"
        className="mb-4 inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-[#585172]"
      >
        <ArrowLeft size={16} />
        Back to packages
      </Link>

      <header className="page-heading">
        <h1>
          {selectedPackage
            ? 'Confirm your package'
            : 'No package selected'}
        </h1>

        <p>
          {selectedPackage
            ? 'Review your package and enter your M-Pesa number.'
            : 'Choose a package before opening checkout.'}
        </p>
      </header>

      {selectedPackage ? (
        <div className="space-y-5">

          <PackageSummary />

          <MpesaForm
            onPaymentRequest={handlePaymentRequest}
          />

        </div>
      ) : (
        <div className="rounded-2xl border border-[#edece8] bg-white p-6 text-center">
          <p className="mb-4 text-sm text-[#655f75]">
            You haven't selected a package yet.
          </p>

          <Link
            to="/packages"
            className="inline-flex items-center gap-2 rounded-full bg-[#D9E52E] px-6 py-3 font-semibold text-[#17152D]"
          >
            Browse packages
          </Link>
        </div>
      )}

    </div>
  )
}
