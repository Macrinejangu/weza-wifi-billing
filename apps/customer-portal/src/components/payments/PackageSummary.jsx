
import { Wifi, Clock, Download, Upload } from 'lucide-react'
import { useCheckout } from '../../context/CheckoutContext'

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

export default function PackageSummary() {
  const { selectedPackage } = useCheckout()

  if (!selectedPackage) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-600">
        No package has been selected. Please go back and choose a package.
      </div>
    )
  }

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-[#F0EEF6] p-3 text-[#77709D]">
            <Wifi size={22} />
          </div>

          <div>
            <p className="text-xs text-gray-500">Selected package</p>
            <h3 className="font-semibold text-[#17152D]">
              {selectedPackage.name}
            </h3>
          </div>
        </div>

        <div className="text-right">
          <p className="text-xs text-gray-500">Amount</p>
          <p className="text-xl font-bold text-[#17152D]">
            KSh {Number(selectedPackage.price).toLocaleString('en-KE')}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 border-t border-gray-100 pt-4">
        <div className="flex items-center gap-2">
          <Clock size={17} className="text-[#77709D]" />
          <div>
            <p className="text-xs text-gray-500">Duration</p>
            <p className="text-sm font-medium text-[#17152D]">
              {formatDuration(selectedPackage.duration_minutes)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Wifi size={17} className="text-[#77709D]" />
          <div>
            <p className="text-xs text-gray-500">Service</p>
            <p className="text-sm font-medium text-[#17152D]">
              {selectedPackage.service_type}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Download size={17} className="text-[#77709D]" />
          <div>
            <p className="text-xs text-gray-500">Download</p>
            <p className="text-sm font-medium text-[#17152D]">
              {selectedPackage.download_speed_mbps} Mbps
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Upload size={17} className="text-[#77709D]" />
          <div>
            <p className="text-xs text-gray-500">Upload</p>
            <p className="text-sm font-medium text-[#17152D]">
              {selectedPackage.upload_speed_mbps} Mbps
            </p>
          </div>
        </div>
      </div>

      {selectedPackage.description && (
        <p className="mt-4 border-t border-gray-100 pt-3 text-sm text-gray-500">
          {selectedPackage.description}
        </p>
      )}
    </div>
  )
}
