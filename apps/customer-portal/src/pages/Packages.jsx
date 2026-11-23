import { ArrowLeft, ArrowRight, Wifi } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { demoDataEnabled } from '../../../shared/demoMode.js'
import { fetchActivePackages } from '../services/api.js'

const sandboxCheckoutEnabled =
  import.meta.env.DEV && import.meta.env.VITE_ENABLE_SANDBOX_CHECKOUT === 'true'

const sandboxPackageId = Number(import.meta.env.VITE_SANDBOX_PACKAGE_ID)

const demoPackages = demoDataEnabled ? [
  {
    name: 'Quick Connect',
    price: 10,
    duration: '1 hour',
    data: '500 MB',
    description: 'For quick messaging and browsing.',
  },
  {
    name: 'Daily Connect',
    price: 50,
    duration: '24 hours',
    data: '2 GB',
    speed: 'Up to 15 Mbps',
    description: 'Stream, study, and stay connected.',
  },
  {
    name: 'Weekly Plus',
    price: 250,
    duration: '7 days',
    data: '10 GB',
    speed: 'Up to 20 Mbps',
    description: 'For work and streaming throughout the week.',
    popular: true,
  },
  {
    name: 'Monthly Max',
    price: 900,
    duration: '30 days',
    data: '40 GB',
    speed: 'Up to 25 Mbps',
    description: 'More data for sharing across devices.',
  },
] : []

function PackageCard({ item, children }) {
  return (
    <article
      className={`flex min-w-0 flex-col rounded-2xl border border-[#edece8] bg-white p-5 ${item.popular ? 'border-t-4 border-t-[#726b91]' : ''}`}
    >
      <div className="mb-4 flex items-center justify-between gap-3">
        <span className="text-xs font-semibold">
          {item.popular ? 'Popular choice' : 'Weza Wi-Fi'}
        </span>
        <Wifi size={20} className="text-[#726b91]" aria-hidden="true" />
      </div>

      <h2 className="text-lg font-bold">{item.name}</h2>
      <p className="mb-4 mt-1 flex items-baseline gap-1">
        <span className="text-sm font-semibold">KES</span>
        <strong className="text-3xl">{item.price.toLocaleString('en-KE')}</strong>
      </p>

      <dl className="grid gap-2 rounded-lg bg-[#f4f3f0] p-3 text-sm">
        {item.data && (
          <div className="flex flex-wrap justify-between gap-x-4">
            <dt>Data</dt>
            <dd className="font-semibold">{item.data}</dd>
          </div>
        )}
        <div className="flex flex-wrap justify-between gap-x-4">
          <dt>Duration</dt>
          <dd className="font-semibold">{item.duration}</dd>
        </div>
        <div className="flex flex-wrap justify-between gap-x-4">
          <dt>Speed</dt>
          <dd className="font-semibold">{item.speed ?? 'To be confirmed'}</dd>
        </div>
      </dl>

      {item.description && (
        <p className="mb-4 mt-3 flex-1 text-sm text-[#655f75]">{item.description}</p>
      )}

      {children}
    </article>
  )
}

export default function Packages() {
  const [searchParams] = useSearchParams()
  const packageId = demoDataEnabled ? null : searchParams.get('package')
  const [packages, setPackages] = useState(demoPackages)
  const [status, setStatus] = useState(demoDataEnabled ? 'ready' : 'loading')

  useEffect(() => {
    if (demoDataEnabled) return

    const controller = new AbortController()

    fetchActivePackages(controller.signal)
      .then((items) => {
        if (controller.signal.aborted) return
        setPackages(items)
        setStatus('ready')
      })
      .catch(() => {
        if (!controller.signal.aborted) setStatus('error')
      })

    return () => controller.abort()
  }, [])

  const isReviewing = packageId !== null
  const selectedPackage = isReviewing
    ? packages.find((item) => String(item.id) === packageId)
    : undefined

  const showSandboxCheckout =
    sandboxCheckoutEnabled &&
    selectedPackage?.id === sandboxPackageId

  return (
    <div className="page-content">
      {isReviewing && (
        <Link
          to="/packages"
          className="mb-4 inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-[#585172] underline underline-offset-4"
        >
          <ArrowLeft size={16} aria-hidden="true" /> Back to packages
        </Link>
      )}

      <header className="page-heading">
        <p className="hero-eyebrow">Internet packages</p>
        <h1>{isReviewing ? 'Review your package' : 'A little Wi-Fi. A lot of possibility.'}</h1>
        {!isReviewing && <p>Compare packages by price, speed, and duration.</p>}
      </header>

      {status === 'loading' && <p role="status">Loading internet packages…</p>}
      {status === 'error' && (
        <p role="alert">Internet packages could not load. Try again later.</p>
      )}

      {status === 'ready' && isReviewing && (
        selectedPackage ? (
          <div className="max-w-lg">
            <PackageCard item={selectedPackage} />
            {showSandboxCheckout ? (
              <Link
                to="/confirm-package"
                state={{ selectedPackage }}
                className="package-button mt-5 text-center"
              >
                Continue to M-Pesa checkout
                <ArrowRight size={17} aria-hidden="true" />
              </Link>
            ) : (
              <p className="mt-5 text-sm text-[#655f75]">
                Live checkout is currently unavailable.
              </p>
            )}
          </div>
        ) : (
          <p role="status">This package is no longer available. Choose another package.</p>
        )
      )}

      {status === 'ready' && !isReviewing && (
        packages.length === 0 ? (
          <p role="status">No internet packages are currently available.</p>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {packages.map((item) => (
                <PackageCard item={item} key={item.id ?? item.name}>
                  <Link
                    to={demoDataEnabled ? '/confirm-package' : `/packages?package=${item.id}`}
                    state={demoDataEnabled ? { selectedPackage: item } : undefined}
                    className="package-button text-center"
                  >
                    Choose {item.name}
                    <ArrowRight size={17} aria-hidden="true" />
                  </Link>
                </PackageCard>
              ))}
            </div>

            {demoDataEnabled && (
              <p className="mt-5 text-sm text-[#655f75]">
                Sample packages. Prices and specifications are pending confirmation.
              </p>
            )}
          </>
        )
      )}
    </div>
  )
}