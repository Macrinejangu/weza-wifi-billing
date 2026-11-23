import { ArrowRight, CircleHelp, Radio, UserRound, Wifi } from 'lucide-react'
import { Link } from 'react-router-dom'
import { demoDataEnabled } from '../../../shared/demoMode.js'

const focusRing =
  'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#585172]'

export default function HotspotEntry() {
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

          <nav aria-label="Customer navigation" className="flex flex-wrap items-center gap-1 sm:gap-3">
            <Link to="/" className={`rounded-full px-3 py-3 text-sm hover:bg-[#eeede9] ${focusRing}`}>
              Home
            </Link>
            <Link to="/support" className={`rounded-full px-3 py-3 text-sm hover:bg-[#eeede9] ${focusRing}`}>
              Support
            </Link>
            <Link
              to="/login"
              aria-label="Sign in"
              className={`grid h-11 w-11 place-items-center rounded-full bg-[#585172] text-white ${focusRing}`}
            >
              <UserRound aria-hidden="true" size={18} />
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex flex-1 flex-col items-center justify-center px-4 py-10 sm:py-16">
        <p className="mb-5 inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-xs font-medium text-[#47415e]">
          <Wifi aria-hidden="true" size={15} />
          {demoDataEnabled ? 'Development preview' : 'Network status unverified'}
        </p>

        <section
          aria-labelledby="hotspot-title"
          className="w-full max-w-md overflow-hidden rounded-xl border border-[#ebe9e5] bg-white shadow-sm"
        >
          <div className="h-1 bg-gradient-to-r from-[#585172] to-[#d5ec26]" />

          <div className="p-5 text-center sm:p-7">
            <div className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-[#f0eef6] text-[#585172]">
              <Wifi aria-hidden="true" size={30} />
            </div>

            <h1 id="hotspot-title" className="mt-4 text-2xl font-bold">
              Welcome to Weza Wi-Fi
            </h1>

            <p className="mt-2 text-sm leading-relaxed text-[#57545f]">
              {demoDataEnabled
                ? 'Browse sample internet packages.'
                : 'Browse available internet packages for your device.'}
            </p>

            <div className="mt-5 flex items-start gap-3 rounded-xl bg-[#f2f1ee] p-4 text-left">
              <Radio aria-hidden="true" size={19} className="mt-0.5 shrink-0 text-[#585172]" />
              <div>
                <h2 className="text-sm font-semibold">Gateway status</h2>
                <p className="mt-1 text-sm leading-relaxed text-[#57545f]">
                  {demoDataEnabled
                    ? 'This preview uses sample data. Your connection status is unavailable.'
                    : 'We could not verify your connection status.'}
                </p>
              </div>
            </div>

            <Link
              to="/packages"
              className={`mt-5 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-full bg-[#d5ec26] px-5 py-3 text-sm font-semibold text-[#202300] hover:bg-[#c4db1c] ${focusRing}`}
            >
              Browse Packages <ArrowRight aria-hidden="true" size={17} />
            </Link>

            <p className="mt-2 text-sm text-[#57545f]">
              Already have an account?{' '}
              <Link
                to="/login"
                className={`inline-flex min-h-11 items-center rounded px-1 font-semibold text-[#47415e] underline underline-offset-4 ${focusRing}`}
              >
                Sign in
              </Link>
            </p>
          </div>
        </section>

        <Link
          to="/support"
          className={`mt-3 inline-flex min-h-11 items-center gap-2 rounded px-2 text-sm text-[#47415e] underline underline-offset-4 ${focusRing}`}
        >
          <CircleHelp aria-hidden="true" size={16} /> Get support
        </Link>
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