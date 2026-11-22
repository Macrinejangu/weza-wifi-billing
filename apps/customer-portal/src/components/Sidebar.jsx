


import { Headset, ArrowUpRight, Router } from 'lucide-react'
import { Link } from 'react-router-dom'
import { NavigationLinks } from './layout/Navigation'

export default function Sidebar() {
  return (
    <aside className="customer-sidebar w-[245px] min-h-screen bg-white px-[22px] pt-[30px] pb-[22px] flex flex-col shrink-0">

      
      <div className="flex items-center min-h-[48px] mb-[45px]">
        <Router
          size={38}
          color="#77709D"
          strokeWidth={2.2}
        />
      </div>

      {/* Navigation */}
      <NavigationLinks />

      {/* Support card */}
      <div className="mt-auto mb-6 rounded-xl bg-[#F0EEF6] p-4">

        <div className="w-10 h-10 rounded-lg bg-white flex items-center justify-center text-[#77709D] mb-3">
          <Headset size={21} />
        </div>

        <h3 className="text-base font-bold text-[#17152D] mb-2">
          A little help?
        </h3>

        <p className="text-sm leading-5 text-[#88849A] mb-4">
          We're here to keep you connected.
          Reach out whenever you need us.
        </p>

        <Link
          to="/support"
          className="flex items-center justify-center gap-2 w-full rounded-lg bg-[#77709D] text-white py-2.5 px-3 text-sm font-semibold hover:bg-[#625B88] transition-colors"
        >
          Get support
          <ArrowUpRight size={15} />
        </Link>

      </div>

      {/* Customer information */}
      <div className="border-t border-[#F0EEF6] pt-5 flex items-center gap-3">

        <div className="w-10 h-10 rounded-full bg-[#F0EEF6] text-[#77709D] flex items-center justify-center font-bold text-sm">
          EM
        </div>

        <div>
          <h4 className="text-sm font-bold text-[#17152D]">
            Customer
          </h4>
          <p className="text-xs text-[#88849A]">
            WEZA member
          </p>
        </div>

      </div>

    </aside>
  )
}
