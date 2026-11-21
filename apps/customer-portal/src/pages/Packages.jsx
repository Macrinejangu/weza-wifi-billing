
import { useEffect, useState } from 'react'
import { ArrowRight, Wifi } from 'lucide-react'
import { Link } from 'react-router-dom'

const API_URL = import.meta.env.VITE_API_BASE_URL

function formatDuration(minutes) {
  if (minutes % 1440 === 0) {
    const days = minutes / 1440
    return `${days} ${days === 1 ? 'day' : 'days'}`
  }

  if (minutes % 60 === 0) {
    const hours = minutes / 60
    return `${hours} ${hours === 1 ? 'hour' : 'hours'}`
  }

  return `${minutes} minutes`
}

export default function Packages() {
  const [packages, setPackages] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function fetchPackages() {
      try {
        const response = await fetch(`${API_URL}/api/packages/`)

        if (!response.ok) {
          throw new Error('Unable to retrieve packages.')
        }

        const data = await response.json()
        setPackages(data.filter((item) => item.is_active))
      } catch (error) {
        console.error('Error fetching packages:', error)
        setError('Failed to fetch packages. Please try again.')
      } finally {
        setLoading(false)
      }
    }

    fetchPackages()
  }, [])

  return (
    <div className="page-content">
      <header className="page-heading">
        <p className="hero-eyebrow">Internet packages</p>
        <h1>A little Wi-Fi. A lot of possibility.</h1>
        <p>Compare packages by price, speed, and duration.</p>
      </header>

      {loading && (
        <p className="py-8 text-center text-sm text-[#655f75]">
          Loading available packages...
        </p>
      )}

      {error && (
        <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
          {error}
        </p>
      )}

      {!loading && !error && packages.length === 0 && (
        <p className="rounded-xl bg-white p-6 text-center text-sm text-[#655f75]">
          No packages are currently available.
        </p>
      )}

      {!loading && !error && packages.length > 0 && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {packages.map((item) => (
            <article
              className="flex min-w-0 flex-col rounded-2xl border border-[#edece8] bg-white p-5"
              key={item.id}
            >
              <div className="mb-4 flex items-center justify-between gap-3">
                <span className="text-xs font-semibold">
                  {item.service_type}
                </span>

                <Wifi
                  size={20}
                  className="text-[#726b91]"
                  aria-hidden="true"
                />
              </div>

              <h2 className="text-lg font-bold">{item.name}</h2>

              <p className="mb-4 mt-1 flex items-baseline gap-1">
                <span className="text-sm font-semibold">KES</span>
                <strong className="text-3xl">
                  {item.price.toLocaleString('en-KE')}
                </strong>
              </p>

              <dl className="grid gap-2 rounded-lg bg-[#f4f3f0] p-3 text-sm">
                <div className="flex justify-between gap-4">
                  <dt>Duration</dt>
                  <dd className="font-semibold">
                    {formatDuration(item.duration_minutes)}
                  </dd>
                </div>

                <div className="flex justify-between gap-4">
                  <dt>Download speed</dt>
                  <dd className="font-semibold">
                    {item.download_speed_mbps} Mbps
                  </dd>
                </div>

                <div className="flex justify-between gap-4">
                  <dt>Upload speed</dt>
                  <dd className="font-semibold">
                    {item.upload_speed_mbps} Mbps
                  </dd>
                </div>
              </dl>

              <p className="mb-4 mt-3 flex-1 text-sm text-[#655f75]">
                {item.description || 'Stay connected with WEZA Wi-Fi.'}
              </p>

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
      )}
    </div>
  )
}
