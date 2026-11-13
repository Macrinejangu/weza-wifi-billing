const kpiItems = [
  {
    title: 'Revenue Today',
    value: 'KES 142,850',
    detail: '814 confirmed transactions',
    icon: 'payments',
    trend: '+12.8%',
    trendLabel: 'vs yesterday',
    accent: 'revenue',
  },
  {
    title: 'Active Sessions',
    value: '1,248',
    detail: 'Hotspot & GPON Fiber online',
    icon: 'wifi',
    trend: 'Live',
    trendLabel: 'connected clients',
    accent: 'sessions',
  },
  {
    title: 'Pending Payments',
    value: '3',
    detail: 'Awaiting M-Pesa callback',
    icon: 'pending_actions',
    trend: 'Action needed',
    trendLabel: 'Daraja sync',
    accent: 'pending',
  },
  {
    title: 'Failed Activations',
    value: '2',
    detail: 'Paid subscribers awaiting access',
    icon: 'error',
    trend: 'Attention',
    trendLabel: 'activation queue',
    accent: 'failed',
  },
]

function KpiCard({ item }) {
  return (
    <article className={`kpi-card kpi-card-${item.accent}`}>
      <div className="kpi-card-top">
        <span className="kpi-title">{item.title}</span>
        <span className="kpi-icon material-symbols-outlined">
          {item.icon}
        </span>
      </div>

      <p className="kpi-value">{item.value}</p>
      <p className="kpi-detail">{item.detail}</p>

      <div className="kpi-card-footer">
        <span className="kpi-trend">{item.trend}</span>
        <span className="kpi-trend-label">{item.trendLabel}</span>
      </div>
    </article>
  )
}

export default function KpiGrid() {
  return (
    <section className="kpi-section" aria-label="Key performance indicators">
      <div className="kpi-section-heading">
        <div>
          <h2>Network & Billing Overview</h2>
          <p>Key operational metrics for today</p>
        </div>
        <span className="demo-data-label">DEMO DATA</span>
      </div>

      <div className="kpi-grid">
        {kpiItems.map((item) => (
          <KpiCard key={item.title} item={item} />
        ))}
      </div>
    </section>
  )
}
