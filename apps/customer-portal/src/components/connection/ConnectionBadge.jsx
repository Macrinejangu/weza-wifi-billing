

import { Wifi, WifiOff, LoaderCircle } from 'lucide-react'

export default function ConnectionBadge({ status = 'checking' }) {
  const states = {
    connected: {
      label: 'Connected',
      description: 'Your internet is active',
      icon: Wifi,
      styles: 'bg-[#D9E52E]/20 text-[#687000]',
      dot: 'bg-[#A6B900]'
    },
    disconnected: {
      label: 'Disconnected',
      description: 'You are not connected',
      icon: WifiOff,
      styles: 'bg-red-100 text-red-700',
      dot: 'bg-red-500'
    },
    checking: {
      label: 'Checking connection',
      description: 'Please wait...',
      icon: LoaderCircle,
      styles: 'bg-gray-100 text-gray-600',
      dot: 'bg-gray-400'
    }
  }

  const current = states[status] || states.checking
  const Icon = current.icon

  return (
    <div className={`inline-flex items-center gap-3 rounded-xl px-4 py-3 ${current.styles}`}>
      <Icon
        size={22}
        className={status === 'checking' ? 'animate-spin' : ''}
      />

      <div>
        <p className="text-sm font-semibold">
          {current.label}
        </p>
        <p className="text-xs opacity-80">
          {current.description}
        </p>
      </div>

      <span className={`ml-2 h-2.5 w-2.5 rounded-full ${current.dot}`} />
    </div>
  )
}
