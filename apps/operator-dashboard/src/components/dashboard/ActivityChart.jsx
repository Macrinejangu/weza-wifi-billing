import { useState } from 'react'

// Static illustrative figures; replace with API data when the backend is integrated.
const chartData = {
  revenue: {
    label: 'Revenue',
    values: [104000, 118000, 129000, 136000, 152000, 168000, 142850],
    peak: 'KES 168,000',
    average: 'KES 135,693',
  },
  sessions: {
    label: 'Active Sessions',
    values: [820, 940, 1080, 1020, 1190, 1410, 1248],
    peak: '1,410 clients',
    average: '1,101 clients',
  },
}

const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

// Convert metric values into coordinates for the SVG line chart.
function createPoints(values) {
  const min = Math.min(...values) * 0.85
  const max = Math.max(...values) * 1.05
  const range = max - min || 1

  return values.map((value, index) => {
    const x = 40 + (index * 620) / (values.length - 1)
    const y = 170 - ((value - min) / range) * 135
    return `${x},${y}`
  })
}

export default function ActivityChart() {
  // Switch between the two illustrative metrics displayed by the chart.
  const [metric, setMetric] = useState('revenue')

  const data = chartData[metric]
  const points = createPoints(data.values)
  const pointString = points.join(' ')
  const areaString = `40,180 ${pointString} 660,180`

  return (
    <section className="activity-section">
      <div className="activity-heading">
        <div>
          <p className="section-eyebrow">PERFORMANCE</p>
          <h2>Revenue & Session Activity</h2>
          <p className="section-description">
            Monitor billing performance and network usage
          </p>
        </div>

        <span className="demo-data-label">DEMO DATA</span>
      </div>

      <div className="activity-toolbar">
        <div className="metric-toggle" aria-label="Chart metric">
          <button
            type="button"
            className={metric === 'revenue' ? 'selected' : ''}
            aria-pressed={metric === 'revenue'}
            onClick={() => setMetric('revenue')}
          >
            Revenue (KES)
          </button>

          <button
            type="button"
            className={metric === 'sessions' ? 'selected' : ''}
            aria-pressed={metric === 'sessions'}
            onClick={() => setMetric('sessions')}
          >
            Active Sessions
          </button>
        </div>

        <label className="date-range-control">
          <span className="material-symbols-outlined">calendar_month</span>
          <select
            value="7 days"
            aria-label="Chart date range"
            disabled
          >
            <option value="7 days">Last 7 Days</option>
          </select>
        </label>

      </div>

      <div className="chart-summary">
        <div>
          <p>{metric === 'revenue' ? 'Weekly revenue peak' : 'Peak concurrency'}</p>
          <strong>{data.peak}</strong>
        </div>
        <div>
          <p>{metric === 'revenue' ? 'Daily average' : 'Average sessions'}</p>
          <strong>{data.average}</strong>
        </div>
      </div>

      <div className="activity-chart" role="img" aria-label={`${data.label} demonstration chart for the last seven days`}>
        <div className="chart-y-labels" aria-hidden="true">
          <span>High</span>
          <span>Mid</span>
          <span>Low</span>
        </div>

        <svg viewBox="0 0 700 200" preserveAspectRatio="none" aria-hidden="true">
          <defs>
            <linearGradient id="activity-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#746d97" stopOpacity="0.24" />
              <stop offset="100%" stopColor="#746d97" stopOpacity="0.02" />
            </linearGradient>
          </defs>

          {[35, 102, 170].map((y) => (
            <line
              key={y}
              x1="40"
              y1={y}
              x2="660"
              y2={y}
              className="chart-grid-line"
            />
          ))}

          <polygon points={areaString} fill="url(#activity-fill)" />
          <polyline
            points={pointString}
            className="chart-line"
            fill="none"
          />

          {points.map((point, index) => {
            const [x, y] = point.split(',')
            return (
              <circle
                key={days[index]}
                cx={x}
                cy={y}
                r="5"
                className="chart-point"
              />
            )
          })}
        </svg>
      </div>

      <div className="chart-x-labels" aria-hidden="true">
        {days.map((day) => <span key={day}>{day}</span>)}
      </div>

      <p className="chart-footnote">
        Illustrative figures only. The selected date range does not yet load
        historical data from a backend.
      </p>
    </section>
  )
}
