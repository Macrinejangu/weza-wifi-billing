import { useState } from 'react'
import { Link } from 'react-router-dom'

const usageHistory = {
  week: [
    ['Mon', 0.3], ['Tue', 0.5], ['Wed', 0.4], ['Thu', 0.7],
    ['Fri', 0.4], ['Sat', 0.8], ['Sun', 0.5],
  ],
  month: [['Week 1', 3], ['Week 2', 4], ['Week 3', 4.2], ['Week 4', 3.6]],
}

const sessions = [
  { device: 'Desktop', status: 'Active', data: '420 MB', time: 'Today, 11:42 AM' },
  { device: 'Laptop', status: 'Completed', data: '860 MB', time: 'Yesterday, 7:15 PM' },
  { device: 'Phone', status: 'Completed', data: '310 MB', time: '10 Nov, 9:03 AM' },
]

const card = 'min-w-0 rounded-2xl border border-[#edece8] bg-white p-4 sm:p-6'

export default function Usage() {
  const [period, setPeriod] = useState('week')
  const readings = usageHistory[period]
  const peak = Math.max(...readings.map(([, data]) => data))
  const total = readings.reduce((sum, [, data]) => sum + data, 0)

  return (
    <div className="page-content">
      <header className="page-heading">
        <h1>Know your connection.</h1>
        <p>Compare your usage history with your current package balance. All figures are samples.</p>
      </header>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <section className={card}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-bold">Usage history</h2>
            <select
              aria-label="Usage period"
              className="min-h-11 rounded-lg bg-[#f4f3f0] px-3 text-sm"
              value={period}
              onChange={(event) => setPeriod(event.target.value)}
            >
              <option value="week">Last 7 days</option>
              <option value="month">Last 30 days</option>
            </select>
          </div>
          <p className="mt-3 text-sm text-[#655f75]">
            <strong className="text-2xl text-[#17152d]">{total.toFixed(1)} GB</strong> used
          </p>
          <ul className="mt-4 grid grid-flow-col auto-cols-fr gap-1 text-center text-xs sm:gap-2">
            {readings.map(([label, data]) => (
              <li key={label} className="min-w-0">
                <div className="flex h-24 items-end justify-center" aria-hidden="true">
                  <div
                    className={`w-4 rounded-t sm:w-6 ${data === peak ? 'bg-[#d9e52e]' : 'bg-[#726b91]'}`}
                    style={{ height: `${(data / peak) * 100}%` }}
                  />
                </div>
                <span className="mt-2 block">{label}</span>
                <span className="block text-[#655f75]">{data.toFixed(1)} GB</span>
              </li>
            ))}
          </ul>
        </section>

        <section className={card}>
          <h2 className="text-lg font-bold">Active package balance</h2>
          <p className="mt-2 text-sm text-[#655f75]">Weekly Plus</p>
          <p className="mt-4"><strong className="text-2xl">6.4 GB</strong> of 10 GB remaining</p>
          <progress
            className="mt-3 block w-full accent-[#726b91]"
            value={6.4}
            max={10}
            aria-label="Remaining data, 6.4 GB of 10 GB"
          />
          <Link to="/packages" className="package-button">Browse packages</Link>
        </section>
      </div>

      <section className={`mt-4 ${card}`}>
        <h2 className="text-lg font-bold">Recent sessions</h2>
        <ul className="mt-3 divide-y divide-[#edece8]">
          {sessions.map((session) => (
            <li key={session.device} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
              <div>
                <p className="font-semibold">{session.device} · {session.status}</p>
                <p className="text-[#655f75]">{session.time}</p>
              </div>
              <strong>{session.data}</strong>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
