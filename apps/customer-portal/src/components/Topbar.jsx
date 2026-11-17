

import { Wifi } from 'lucide-react'

export default function Topbar() {
  return (
    <header className="w-full min-h-[88px] px-6 md:px-10 flex items-center justify-between gap-4 bg-[#F7F6F2]">

      {/* WEZA Branding */}
      <div className="flex items-center gap-3 shrink-0">

        <div className="w-[52px] h-[52px] rounded-xl bg-[#77709D] flex items-center justify-center">
          <Wifi size={29} color="#FFFFFF" strokeWidth={2.2} />
        </div>

        <div className="flex flex-col gap-0.5">
          <h2 className="text-xl font-bold text-[#17152D]">
            Weza Wi-Fi
          </h2>

          <span className="text-xs tracking-wide text-[#17152D]">
            CUSTOMER PORTAL
          </span>
        </div>

      </div>

      {/* Preview status */}
      <div className="flex items-center gap-3 rounded-full bg-white px-5 py-3 shrink-0">

        <span className="w-3 h-3 rounded-full bg-[#D9E52E]"></span>

        <span className="text-sm text-[#17152D]">
          Portal preview
        </span>

      </div>

    </header>
  )
}
