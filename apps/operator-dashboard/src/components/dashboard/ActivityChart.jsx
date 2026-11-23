import { useState } from 'react'

// All chart figures are illustrative demonstration data.
// Replace these datasets with API responses during backend integration.
const chartData = {
  '7 days': {
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    revenue: {
      values: [104000, 118000, 129000, 136000, 152000, 168000, 142850],
      peak: 'KES 168,000',
      average: 'KES 135,693',
    },
    sessions: {
      values: [820, 940, 1080, 1020, 1190, 1410, 1248],
      peak: '1,410 clients',
      average: '1,101 clients',
    },
  },
  today: {
    labels: ['08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00'],
    revenue: {
      values: [8200, 12400, 18700, 23100, 19800, 28400, 32250],
      peak: 'KES 32,250',
      average: 'KES 20,407',
    },
    sessions: {
      values: [420, 610, 890, 1040, 980, 1180, 1248],
      peak: '1,248 clients',
      average: '910 clients',
    },
  },
  month: {
    labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
    revenue: {
      values: [684000, 742000, 816000, 789000],
      peak: 'KES 816,000',
      average: 'KES 757,750',
    },
    sessions: {
      values: [980, 1120, 1360, 1248],
      peak: '1,360 clients',
      average: '1,177 clients',
    },
  },
}

const ranges = [
  { value: '7 days', label: 'Last 7 Days' },
  { value: 'today', label: 'Today' },
  { value: 'month', label: 'This Month' },
]

function formatValue(value, metric) {
  if (metric === 'revenue') {
    return `KES ${value.toLocaleString('en-KE')}`
  }

  return `${value.toLocaleString('en-KE')} clients`
}

export default function ActivityChart() {
  const [metric, setMetric] = useState('revenue')
  const [range, setRange] = useState('7 days')

  const selectedData = chartData[range]
  const data = selectedData[metric]
  const maxValue = Math.max(...data.values)

  return (
    <section className="activity-section">
      <div className="activity-heading">
        <div>
          <p className="section-eyebrow">PERFORMANCE</p>
          <h2>Revenue & Session Activity</h2>
          <p className="section-description">
            Demonstration of billing performance and network usage
          </p>
        </div>

        <span className="demo-data-label">DEMO DATA</span>
      </div>

      <div className="activity-toolbar">
        <div className="metric-toggle" role="group" aria-label="Chart metric">
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
          <span className="material-symbols-outlined" aria-hidden="true">
            calendar_month
          </span>
          <select
            value={range}
            aria-label="Chart date range"
            onChange={(event) => setRange(event.target.value)}
          >
            {ranges.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="chart-summary">
        <div>
          <p>{metric === 'revenue' ? 'Period peak revenue' : 'Peak concurrency'}</p>
          <strong>{data.peak}</strong>
        </div>
        <div>
          <p>
            {metric === 'revenue'
              ? range === 'today'
                ? 'Average per interval'
                : range === 'month'
                  ? 'Weekly average'
                  : 'Daily average'
              : 'Average sessions'}
          </p>
          <strong>{data.average}</strong>
        </div>
      </div>

      <div
        className="activity-chart activity-bar-chart"
        role="img"
        aria-label={`${metric === 'revenue' ? 'Revenue' : 'Active sessions'} demonstration bar chart for ${ranges.find((item) => item.value === range).label}`}
      >
        {data.values.map((value, index) => {
          const height = Math.max((value / maxValue) * 100, 4)

          return (
            <div className="chart-bar-column" key={selectedData.labels[index]}>
              <span className="chart-bar-value">
                {metric === 'revenue'
                  ? `${Math.round(value / 1000)}k`
                  : value.toLocaleString('en-KE')}
              </span>

              <div className="chart-bar-track">
                <div
                  className={`chart-bar ${value === maxValue ? 'chart-bar-peak' : ''}`}
                  style={{ height: `${height}%` }}
                  title={`${selectedData.labels[index]}: ${formatValue(value, metric)}`}
                />
              </div>

              <span className="chart-bar-label">
                {selectedData.labels[index]}
              </span>
            </div>
          )
        })}
      </div>

      <p className="chart-footnote">
        Illustrative figures only. Date-range changes display sample datasets;
        no live or historical backend data is connected.
      </p>
    </section>
  )
}
