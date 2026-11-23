import { ArrowRight, CalendarDays, CircleHelp, Clock3, Hourglass, Radio, UserRound } from 'lucide-react'
import { Link } from 'react-router-dom'

const samplePackage = {
  name: 'Daily Connect',
  price: 50,
  data: '2 GB',
  duration: '24 hours',
}

const sampleUsage = {
  used: '2.0 GB',
  allowance: '2.0 GB',
  percent: 100,
  expiredAt: '2:15 PM EAT',
}

const focusRing =
  'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#585172]'

export default function PackageExpired() {
  return (
    <div className="flex min-h-screen flex-col bg-[#f8f7f4] text-[#17152d]">
      <header className="border-b border-[#e8e6e0]">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-3 sm:px-8">
          <Link to="/" className={`flex items-center gap-2 rounded-lg ${focusRing}`}>
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#585172] text-white">
              <Radio aria-hidden="true" size={19} />
            </span>
            <span>
              <span className="block text-sm font-semibold">Weza Wi-Fi</span>
              <span className="block text-xs text-[#57545f]">Customer Portal</span>
            </span>
          </Link>

          <nav
            aria-label="Customer navigation"
            className="flex flex-wrap items-center gap-1 sm:gap-3"
          >
            <Link to="/" className={`rounded-full px-3 py-3 text-sm hover:bg-[#eeede9] ${focusRing}`}>
              Home
            </Link>
            <Link
              to="/support"
              className={`rounded-full px-3 py-3 text-sm hover:bg-[#eeede9] ${focusRing}`}
            >
              Support
            </Link>
            <Link
              to="/profile"
              aria-label="My Profile"
              className={`grid h-11 w-11 place-items-center rounded-full bg-[#585172] text-white ${focusRing}`}
            >
              <UserRound aria-hidden="true" size={18} />
            </Link>
          </nav>
        </div>
      </header>

      <main className="grid flex-1 place-items-center px-4 py-10 sm:py-14">
        <div className="w-full max-w-md">
          <div className="text-center">
            <p className="inline-flex rounded-full bg-white px-4 py-2 text-xs font-semibold text-[#585172]">
              Development preview · Sample subscription
            </p>
            <div className="mx-auto mt-4 grid h-14 w-14 place-items-center rounded-full border border-red-200 bg-red-50 text-red-700">
              <Hourglass aria-hidden="true" size={24} />
            </div>
            <h1 className="mt-4 text-2xl font-bold sm:text-3xl">Your package has expired</h1>
            <p className="mt-2 text-sm leading-relaxed text-[#57545f]">
              Renew your previous package or choose another one to reconnect.
            </p>
          </div>

          <section
            aria-labelledby="previous-plan"
            className="mt-6 rounded-xl border border-[#ebe9e5] bg-white p-5 shadow-sm"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="text-xs font-semibold text-[#585172]">Previous plan</p>
                <h2 id="previous-plan" className="mt-1 text-base font-semibold">
                  {samplePackage.name} ({samplePackage.data})
                </h2>
              </div>
              <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-800">
                Expired
              </span>
            </div>

            <div className="mt-4 rounded-lg bg-[#f2f1ee] p-3">
              <p className="flex flex-wrap justify-between gap-2 text-sm">
                <span id="usage-label">Data used</span>
                <span id="usage-value" className="font-medium">
                  {sampleUsage.used} of {sampleUsage.allowance} ({sampleUsage.percent}%)
                </span>
              </p>
              <meter
                aria-labelledby="usage-label"
                aria-describedby="usage-value"
                className="mt-2 block h-2 w-full accent-[#585172]"
                min={0}
                max={100}
                value={sampleUsage.percent}
              />
            </div>

            <ul className="mt-4 flex flex-wrap justify-between gap-2 text-sm text-[#57545f]">
              <li className="flex items-center gap-2">
                <Clock3 aria-hidden="true" size={15} /> Expired at {sampleUsage.expiredAt}
              </li>
              <li className="flex items-center gap-2">
                <CalendarDays aria-hidden="true" size={15} /> Valid for {samplePackage.duration}
              </li>
            </ul>
          </section>

          <div className="mt-5 space-y-2">
            <Link
              to="/confirm-package"
              state={{ selectedPackage: samplePackage }}
              className={`inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-full bg-[#d5ec26] px-5 py-3 text-sm font-semibold text-[#202300] hover:bg-[#c4db1c] ${focusRing}`}
            >
              Renew Package (KES {samplePackage.price})
              <ArrowRight aria-hidden="true" size={17} />
            </Link>
            <Link
              to="/packages"
              className={`inline-flex min-h-11 w-full items-center justify-center rounded-full bg-[#eeede9] px-5 py-3 text-sm font-semibold hover:bg-[#e3e1dc] ${focusRing}`}
            >
              Browse Packages
            </Link>
          </div>

          <div className="mt-3 text-center">
            <Link
              to="/support"
              className={`inline-flex min-h-11 items-center gap-2 rounded px-2 text-sm text-[#47415e] underline underline-offset-4 ${focusRing}`}
            >
              <CircleHelp aria-hidden="true" size={16} /> Get support
            </Link>
          </div>
        </div>
      </main>

      <footer className="border-t border-[#e8e6e0] bg-[#f2f1ee]">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-x-4 px-4 py-2 text-sm text-[#57545f] sm:px-8">
          <span>Weza Wi-Fi</span>
          <Link
            to="/support"
            className={`inline-flex min-h-11 items-center rounded text-[#47415e] underline underline-offset-4 ${focusRing}`}
          >
            M-Pesa help and FAQs
          </Link>
        </div>
      </footer>
    </div>
  )
}