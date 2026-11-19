
import {
  Wifi,
  Radio,
  ArrowRight,
  UserRound,
  CircleHelp,
  ShieldCheck,
  Zap
} from 'lucide-react'

import { Link } from 'react-router-dom'

export default function HotspotEntry() {
  return (
    <div className="min-h-screen flex flex-col bg-[#F7F6F2]">

      {/* Header */}
      <header className="bg-white border-b border-[#F0EEF6]">
        <div className="max-w-7xl mx-auto px-5 md:px-8 py-4 flex items-center justify-between">

          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#77709D] flex items-center justify-center text-white">
              <Radio size={21} />
            </div>

            <div>
              <h2 className="text-sm font-bold text-[#17152D]">
                Weza Wi-Fi
              </h2>
              <p className="text-[9px] tracking-wide text-[#88849A]">
                CUSTOMER PORTAL
              </p>
            </div>

            <div className="hidden sm:flex items-center gap-2 ml-4 rounded-full bg-[#F7F6F2] px-3 py-2">
              <span className="w-2 h-2 rounded-full bg-[#D9E52E]" />
              <Wifi size={13} className="text-[#77709D]" />
              <span className="text-[10px] text-[#17152D]">
                Connected to Weza Wi-Fi
              </span>
            </div>
          </div>

          <nav className="flex items-center gap-3">
            <Link
              to="/"
              className="rounded-full bg-[#D9E52E] px-4 py-2 text-xs font-semibold text-[#17152D]"
            >
              Home
            </Link>

            <Link
              to="/support"
              className="rounded-full border border-dashed border-[#77709D] px-4 py-2 text-xs text-[#655F75] hover:bg-[#F0EEF6]"
            >
              Support
            </Link>

            <Link
              to="/login"
              aria-label="Sign in"
              className="w-8 h-8 rounded-full bg-[#77709D] text-white flex items-center justify-center"
            >
              <UserRound size={15} />
            </Link>
          </nav>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-10">

        {/* Connection indicator */}
        <div className="flex items-center gap-2 rounded-full bg-white px-4 py-2 shadow-sm mb-5">
          <span className="w-2 h-2 rounded-full bg-[#D9E52E]" />

          <Wifi size={13} className="text-[#77709D]" />

          <span className="text-[10px] text-[#17152D]">
            Connected to Weza Wi-Fi
          </span>

          <span className="text-[#88849A]">•</span>

          <span className="text-[10px] text-[#77709D]">
            Internet Inactive
          </span>
        </div>

        {/* Welcome card */}
        <section className="w-full max-w-[345px] bg-white rounded-xl shadow-md border border-[#EDECE8] overflow-hidden">

          {/* Decorative top border */}
          <div className="h-1 bg-gradient-to-r from-[#77709D] to-[#D9E52E]" />

          <div className="p-6 text-center">

            {/* Gateway label */}
            <div className="inline-flex items-center gap-2 rounded-full bg-[#F0EEF6] px-3 py-1.5 mb-5">
              <Radio size={12} className="text-[#77709D]" />
              <span className="text-[9px] font-semibold tracking-wide text-[#655F75]">
                PUBLIC HOTSPOT GATEWAY
              </span>
            </div>

            {/* Wi-Fi icon */}
            <div className="w-16 h-16 rounded-full bg-[#F0EEF6] flex items-center justify-center mx-auto mb-4 relative">
              <Wifi size={30} className="text-[#77709D]" />

              <span className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-white shadow-sm flex items-center justify-center">
                <Zap size={13} className="text-[#77709D]" />
              </span>
            </div>

            {/* Heading */}
            <h1 className="text-xl font-bold text-[#17152D]">
              Welcome to Weza Wi-Fi
            </h1>

            <p className="text-xs leading-5 text-[#655F75] mt-2">
              You are connected to the Weza Wi-Fi hotspot.
              Select a package to activate high-speed internet
              on your device.
            </p>

            {/* Gateway status */}
            <div className="mt-6 rounded-lg bg-[#F7F6F2] p-3 flex items-center justify-between gap-2">

              <div className="flex items-center gap-2 text-left">
                <div className="w-8 h-8 rounded-full bg-[#F0EEF6] flex items-center justify-center">
                  <Radio size={15} className="text-[#77709D]" />
                </div>

                <div>
                  <p className="text-[10px] font-semibold text-[#17152D]">
                    Gateway Status
                  </p>
                  <p className="text-[9px] text-[#88849A]">
                    Connected to Weza Wi-Fi · Internet inactive
                  </p>
                </div>
              </div>

              <span className="shrink-0 rounded-full bg-[#EAE8E3] px-2 py-1 text-[8px] font-semibold text-[#655F75]">
                AWAITING PASS
              </span>

            </div>

            {/* Actions */}
            <div className="mt-5 space-y-2">

              <Link
                to="/packages"
                className="w-full min-h-11 flex items-center justify-center gap-2 rounded-full bg-[#D9E52E] hover:bg-[#CBD622] text-[#17152D] text-xs font-semibold transition-colors"
              >
                Browse Packages
                <ArrowRight size={15} />
              </Link>

              <div className="min-h-10 border border-dashed border-[#77709D] flex items-center justify-center rounded-sm text-[10px] text-[#655F75]">
                Already have an account?

                <Link
                  to="/login"
                  className="ml-1 font-semibold text-[#17152D] underline"
                >
                  Sign In
                </Link>
              </div>

            </div>

          </div>
        </section>

        {/* Help links */}
        <div className="flex flex-wrap items-center justify-center gap-4 mt-5 text-[10px] text-[#77709D]">

          <Link to="/support" className="flex items-center gap-1 hover:underline">
            <CircleHelp size={12} />
            Need help? Get Support
          </Link>

          <span>•</span>

          <Link to="/support" className="flex items-center gap-1 hover:underline">
            <ShieldCheck size={12} />
            Instant M-Pesa Setup
          </Link>

        </div>

      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-[#F0EEF6]">
        <div className="max-w-7xl mx-auto px-5 md:px-8 py-4 flex flex-col sm:flex-row items-center justify-between gap-3">

          <div className="flex items-center gap-2 text-[9px] text-[#77709D]">
            <div className="w-5 h-5 rounded-md bg-[#77709D] flex items-center justify-center text-white">
              <Radio size={11} />
            </div>

            © 2024 Weza Wi-Fi. Empowering Community Connectivity.
          </div>

          <div className="flex items-center gap-4 text-[9px] text-[#77709D]">
            <Link to="/support" className="hover:underline">
              M-Pesa Help & FAQs
            </Link>

            <span>•</span>

            <span className="flex items-center gap-1">
              <ShieldCheck size={11} />
              Secure Safaricom Gateway
            </span>
          </div>

        </div>
      </footer>

    </div>
  )
}
