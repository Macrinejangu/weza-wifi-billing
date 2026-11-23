const kpiItems = [
  {
    title: 'Revenue Today',
    value: 'KES 142,850',
    detail: '814 sample confirmed transactions',
    icon: 'payments',
    trend: '+12.8%',
    trendLabel: 'vs yesterday',
    accent: 'revenue',
  },
  {
    title: 'Active Sessions',
    value: '1,248',
    detail: 'Sample hotspot sessions',
    icon: 'wifi',
    trend: 'Sample',
    trendLabel: 'illustrative sessions',
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

      {item.trend && <div className="kpi-card-footer">
        <span className="kpi-trend">{item.trend}</span>
        <span className="kpi-trend-label">{item.trendLabel}</span>
      </div>}
    </article>
  )
}

const number = new Intl.NumberFormat('en-KE')

export default function KpiGrid({ report }) {
  const overview = report?.data
  const values = [
    ['Sandbox Settlements Today', overview ? `KES ${number.format(overview.sandbox_settled_today_kes)}` : null,
      overview ? `${number.format(overview.sandbox_settled_today_count)} sandbox payments today (EAT)` : 'Daraja sandbox only'],
    ['Active Sessions', overview?.active_session_records, 'Active, unexpired session records'],
    ['Pending Payments', overview?.pending_payments, 'Payment attempts awaiting settlement'],
    ['Failed Activations', overview?.failed_activations, 'Session records with failed activation'],
  ]
  const items = report ? kpiItems.map(({ accent, icon }, index) => {
    const [title, value, detail] = values[index]
    return { accent, icon, title, detail, value: typeof value === 'number' ? number.format(value) : value ?? (report.loading ? 'Loading…' : 'Unavailable') }
  }) : kpiItems

  return (
    <section className="kpi-section" aria-label="Key performance indicators">
      <div className="kpi-section-heading">
        <div>
          <h2>Network & Billing Overview</h2>
          <p>{report ? 'Totals across recorded payments and sessions' : 'Key operational metrics for today'}</p>
        </div>
        {!report && <span className="demo-data-label">DEMO DATA</span>}
      </div>

      {report?.error && <p role="alert">Could not load overview totals. Use Refresh to try again.</p>}
      <div className="kpi-grid">
        {items.map((item) => (
          <KpiCard key={item.title} item={item} />
        ))}
      </div>
    </section>
  )
}
