import { ArrowRight, Wifi } from 'lucide-react'
import { Link } from 'react-router-dom'

const packages = [
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
]

export default function Packages() {
  return (
    <div className="page-content">
      <header className="page-heading">
        <p className="hero-eyebrow">Internet packages</p>
        <h1>A little Wi-Fi. A lot of possibility.</h1>
        <p>Compare packages by price, data, speed, and duration.</p>
      </header>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {packages.map((item) => (
          <article
            className={`flex min-w-0 flex-col rounded-2xl border border-[#edece8] bg-white p-5 ${item.popular ? 'border-t-4 border-t-[#726b91]' : ''}`}
            key={item.name}
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
              <div className="flex flex-wrap justify-between gap-x-4">
                <dt>Data</dt>
                <dd className="font-semibold">{item.data}</dd>
              </div>
              <div className="flex flex-wrap justify-between gap-x-4">
                <dt>Duration</dt>
                <dd className="font-semibold">{item.duration}</dd>
              </div>
              <div className="flex flex-wrap justify-between gap-x-4">
                <dt>Speed</dt>
                <dd className="font-semibold">{item.speed ?? 'To be confirmed'}</dd>
              </div>
            </dl>

            <p className="mb-4 mt-3 flex-1 text-sm text-[#655f75]">{item.description}</p>

            <Link
              to="/confirm-package"
              state={{ selectedPackage: item }}
              className="package-button text-center"
            >
              Choose {item.name}
              <ArrowRight size={17} className="shrink-0" aria-hidden="true" />
            </Link>
          </article>
        ))}
      </div>

      <p className="mt-5 text-sm text-[#655f75]">
        Sample packages. Prices and specifications are pending confirmation.
      </p>
    </div>
  )
}
