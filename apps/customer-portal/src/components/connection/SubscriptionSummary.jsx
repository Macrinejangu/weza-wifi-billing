
import { CalendarDays, Clock3, Gauge, Wifi } from 'lucide-react'

export default function SubscriptionSummary({ subscription }) {
  if (!subscription) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-[#17152D]">
          My Subscription
        </h2>

        <p className="mt-3 text-sm text-gray-500">
          You do not have an active subscription yet.
        </p>
      </div>
    )
  }

  const expiryDate = subscription.expires_at
    ? new Date(subscription.expires_at).toLocaleDateString('en-KE', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
      })
    : 'Not available'

  const details = [
    {
      label: 'Package',
      value: subscription.package_name || 'Not available',
      icon: Wifi
    },
    {
      label: 'Subscription status',
      value: subscription.status || 'Unknown',
      icon: CalendarDays
    },
    {
      label: 'Expires on',
      value: expiryDate,
      icon: Clock3
    },
    {
      label: 'Internet speed',
      value: subscription.download_speed_mbps
        ? `${subscription.download_speed_mbps} Mbps download`
        : 'Not available',
      icon: Gauge
    }
  ]

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-[#17152D]">
            My Subscription
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            Your current internet package
          </p>
        </div>

        <div className="rounded-xl bg-[#D9E52E]/20 p-3 text-[#17152D]">
          <Wifi size={22} />
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2">
        {details.map((item) => {
          const Icon = item.icon

          return (
            <div key={item.label} className="flex items-start gap-3">
              <div className="rounded-lg bg-gray-100 p-2 text-gray-600">
                <Icon size={19} />
              </div>

              <div>
                <p className="text-xs text-gray-500">
                  {item.label}
                </p>
                <p className="mt-1 text-sm font-semibold text-[#17152D]">
                  {item.value}
                </p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

