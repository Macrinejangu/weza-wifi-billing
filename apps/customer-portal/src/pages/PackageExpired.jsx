import {
  ArrowRight,
  CalendarDays,
  CircleHelp,
  Clock3,
  Hourglass,
  Radio,
  RefreshCw,
  UserRound,
  Wifi,
} from 'lucide-react'
import { Link } from 'react-router-dom'

const samplePackage = {
  name: 'Daily Connect',
  price: 50,
  data: '2 GB',
  duration: '24 hours',
}

const sampleUsage = {
  dataUsed: '2.0 GB',
  totalData: '2.0 GB',
  percent: 100,
  expiry: '2:15 PM EAT',
}

export default function PackageExpired() {
  return (
    <div className="min-h-screen bg-[#F7F6F2] flex flex-col">
      <header className="bg-white border-b border-[#F0EEF6]">
        <div className="max-w-7xl mx-auto px-5 md:px-8 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-[#77709D] flex items-center justify-center text-white">
              <Radio size={22} />
            </div>

            <div>
              <h2 className="font-bold text-sm text-[#17152D]">
                Weza Wi-Fi
              </h2>
              <p className="text-[10px] tracking-wide text-[#88849A]">
                CUSTOMER PORTAL
              </p>
            </div>

            <div className="hidden sm:flex items-center gap-2 ml-4 bg-[#F7F6F2] rounded-full px-3 py-2">
              <span className="w-2 h-2 rounded-full bg-[#88849A]" />
              <Wifi size={13} className="text-[#77709D]" />
              <span className="text-xs text-[#17152D]">
                Portal preview
              </span>
            </div>
          </div>

          <nav className="flex items-center gap-3 md:gap-5">
            <Link
              to="/"
              className="text-xs text-[#655F75] hover:text-[#77709D]"
            >
              Home
            </Link>

            <Link
              to="/support"
              className="text-xs text-[#77709D] border border-dashed border-[#77709D] rounded-full px-4 py-2"
            >
              Support
            </Link>

            <Link
              to="/profile"
              aria-label="Profile"
              className="w-8 h-8 rounded-full bg-[#77709D] text-white flex items-center justify-center"
            >
              <UserRound size={16} />
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1 flex justify-center px-4 py-10 md:py-14">
        <div className="w-full max-w-md">
          <div className="flex justify-center mb-7">
            <div className="flex items-center gap-2 rounded-full bg-white px-4 py-2 shadow-sm">
              <span className="w-2 h-2 rounded-full bg-[#88849A]" />
              <Wifi size={13} className="text-[#77709D]" />

              <span className="text-[10px] text-[#17152D]">
                Network status unverified
              </span>
            </div>
          </div>

          <div className="flex justify-center mb-5">
            <div className="relative">
              <div className="w-16 h-16 rounded-full border-2 border-red-400 bg-red-50 flex items-center justify-center text-red-500 shadow-sm">
                <Hourglass size={27} />
              </div>

              <div className="absolute -bottom-1 -right-2 w-6 h-6 rounded-full bg-white shadow flex items-center justify-center">
                <RefreshCw size={12} className="text-[#77709D]" />
              </div>
            </div>
          </div>

          <div className="text-center mb-7">
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-[#17152D]">
              Your package has
              <br />
              expired
            </h1>

            <p className="text-xs text-[#77709D] mt-3">
              Preview renewal or browse other packages.
            </p>
          </div>

          <section className="bg-white rounded-xl p-4 shadow-sm border border-[#F0EEF6]">
            <p className="mb-3 text-xs font-semibold text-[#655F75]">
              Demo subscription details
            </p>

            <div className="flex justify-between items-start mb-4">
              <div>
                <div className="flex items-center gap-1 text-[10px] text-[#88849A] uppercase tracking-wide mb-1">
                  Previous plan
                  <CircleHelp size={11} />
                </div>

                <h2 className="font-bold text-sm text-[#17152D]">
                  {samplePackage.name} ({samplePackage.data})
                </h2>
              </div>

              <span className="bg-red-100 text-red-600 text-[10px] font-semibold rounded-full px-3 py-1">
                • Expired
              </span>
            </div>

            <div className="bg-[#F7F6F2] rounded-lg p-3">
              <div className="flex justify-between items-center mb-2">
                <span className="text-[10px] text-[#77709D]">
                  <span className="inline-block w-2 h-2 rounded-full border border-[#77709D] mr-1" />
                  Data used
                </span>

                <span className="text-[10px] font-semibold text-[#17152D]">
                  {sampleUsage.dataUsed} of {sampleUsage.totalData} ({sampleUsage.percent}%)
                </span>
              </div>

              <div className="w-full h-1.5 rounded-full bg-[#E5E2ED] overflow-hidden">
                <div
                  className="h-full rounded-full bg-[#77709D]"
                  style={{ width: `${sampleUsage.percent}%` }}
                />
              </div>
            </div>

            <div className="flex justify-between items-center mt-4 text-[10px] text-[#77709D]">
              <div className="flex items-center gap-1">
                <Clock3 size={12} />
                Sample expiry at {sampleUsage.expiry}
              </div>

              <div className="flex items-center gap-1">
                <CalendarDays size={12} />
                Valid for {samplePackage.duration}
              </div>
            </div>
          </section>

          <div className="mt-5 space-y-3">
            <Link
              to="/confirm-package"
              state={{ selectedPackage: samplePackage }}
              className="w-full flex items-center justify-center gap-2 rounded-full bg-[#D9E52E] hover:bg-[#cbd622] text-[#17152D] text-xs font-semibold py-3.5 transition-colors"
            >
              Renew Package (KES {samplePackage.price})
              <ArrowRight size={15} aria-hidden="true" />
            </Link>

            <Link
              to="/packages"
              className="w-full flex items-center justify-center gap-2 rounded-full border border-dashed border-[#77709D] bg-white hover:bg-[#F0EEF6] text-[#17152D] text-xs font-semibold py-3.5 transition-colors"
            >
              Browse Packages
            </Link>
          </div>

          <div className="flex justify-center mt-8">
            <Link
              to="/support"
              className="flex items-center gap-1.5 text-xs text-[#77709D] hover:underline"
            >
              <CircleHelp size={13} />
              Need help? Get Support
            </Link>
          </div>
        </div>
      </main>

      <footer className="bg-white border-t border-[#F0EEF6]">
        <div className="max-w-7xl mx-auto px-5 md:px-8 py-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-[10px] text-[#77709D]">
            <div className="w-5 h-5 rounded-md bg-[#77709D] text-white flex items-center justify-center">
              <Radio size={12} />
            </div>

            © Weza Wi-Fi. Empowering Community Connectivity.
          </div>

          <Link
            to="/support"
            className="text-[10px] text-[#77709D] hover:underline"
          >
            M-Pesa Help & FAQs
          </Link>
        </div>
      </footer>
    </div>
  )
}