

import { useState } from 'react'
import { ChartNoAxesColumnIncreasing, CalendarDays, Wifi } from 'lucide-react'

const usageData = [
  { day: 'Mon', value: 42 },
  { day: 'Tue', value: 60 },
  { day: 'Wed', value: 48 },
  { day: 'Thu', value: 78 },
  { day: 'Fri', value: 55 },
  { day: 'Sat', value: 88 },
  { day: 'Sun', value: 68 },
]

export default function Usage() {
  const [period, setPeriod] = useState('week')

  return (
    <div className="page-content">
      <div className="page-heading">
        <p className="hero-eyebrow">YOUR CONNECTION</p>
        <h1>Data Usage</h1>
        <p>Keep track of how much internet you have been using.</p>
      </div>

      <section className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon lavender-icon">
            <ChartNoAxesColumnIncreasing size={20} />
          </div>
          <p>Data used</p>
          <h3>12.5 GB</h3>
          <span>This month</span>
        </div>

        <div className="stat-card">
          <div className="stat-icon lime-icon">
            <Wifi size={20} />
          </div>
          <p>Data remaining</p>
          <h3>7.5 GB</h3>
          <span>Of 20 GB</span>
        </div>
      </section>

      <section className="usage-chart usage-page-chart">
        <div className="chart-heading">
          <div>
            <h3>Usage history</h3>
            <p>Your internet consumption</p>
          </div>

          <div className="usage-period">
            <CalendarDays size={16} />
            <select
              value={period}
              onChange={(event) => setPeriod(event.target.value)}
              aria-label="Select usage period"
            >
              <option value="week">This week</option>
              <option value="month">This month</option>
            </select>
          </div>
        </div>

        <div className="chart-bars">
          {usageData.map((item) => (
            <div className="chart-column" key={item.day}>
              <div className="bar-area">
                <div
                  className={
                    item.day === 'Fri'
                      ? 'chart-bar lime-bar'
                      : 'chart-bar'
                  }
                  style={{ height: `${item.value}%` }}
                />
              </div>
              <span>{item.day}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="usage-note">
        <h2>Understanding your usage</h2>
        <p>
          Your usage information helps you monitor your internet
          consumption and plan when to renew your package.
        </p>
      </section>
    </div>
  )
}
