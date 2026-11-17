

import { Wifi, WifiOff, LoaderCircle } from 'lucide-react'

export default function ConnectionStatus({ status = 'checking' }) {
  const states = {
    connected: {
      label: 'Connected to Weza Wi-Fi',
      color: 'bg-[#D9E52E]',
      text: 'text-[#17152D]',
      icon: Wifi
    },
    disconnected: {
      label: 'Disconnected',
      color: 'bg-red-500',
      text: 'text-red-600',
      icon: WifiOff
    },
    checking: {
      label: 'Checking connection...',
      color: 'bg-gray-400',
      text: 'text-gray-600',
      icon: LoaderCircle
    }
  }

  const current = states[status] || states.checking
  const Icon = current.icon

  return (
    <div className="flex items-center gap-3 rounded-full bg-white px-5 py-3 shrink-0">
      <span className={`w-3 h-3 rounded-full ${current.color}`} />

      <span className={`text-sm ${current.text}`}>
        {current.label}
      </span>
    </div>
  )
}
