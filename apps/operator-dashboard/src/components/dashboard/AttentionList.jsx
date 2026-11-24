const issues = [
  {
    id: 'ISS-4091',
    title: 'Router CoA Timeout',
    description: 'Router did not respond to a Change of Authorization request.',
    priority: 'High',
    time: '10m ago',
    action: 'Resolve Issue',
    icon: 'router',
  },
  {
    id: 'ISS-4088',
    title: 'Activation Pending',
    description: 'Subscriber payment received; activation is still pending.',
    priority: 'Medium',
    time: '24m ago',
    action: 'Triage',
    icon: 'pending_actions',
  },
  {
    id: 'ISS-4085',
    title: 'Telco Delay',
    description: 'Upstream provider response is taking longer than expected.',
    priority: 'Low',
    time: '45m ago',
    action: 'Check Daraja',
    icon: 'network_check',
  },
]

const dateTime = new Intl.DateTimeFormat('en-KE', {
  dateStyle: 'medium', timeStyle: 'short', timeZone: 'Africa/Nairobi',
})

export default function AttentionList({ report, onOpenIssues }) {
  const entries = report ? (report.data ?? []).map((record) => ({
    id: `Payment #${record.payment_id}`,
    title: record.activation_status === 'failed' ? 'Activation failed' : 'Awaiting activation',
    description: record.failure_reason,
    payment: `Payment #${record.payment_id}`,
    time: `${dateTime.format(new Date(record.updated_at))} EAT`,
    icon: 'warning',
  })) : issues

  return (
    <section className="attention-section">
      <div className="attention-heading">
        <div>
          <p className="section-eyebrow">OPERATIONS</p>
          <h2>Requires Attention</h2>
          <p className="section-description">
            {report ? 'Paid customers awaiting access or with failed activation' : 'Sample issues that may need operator review'}
          </p>
        </div>

        {report ? (
          onOpenIssues && <button className="payment-secondary-button" type="button" onClick={onOpenIssues}>View Connection Issues</button>
        ) : <span className="demo-data-label">DEMO DATA</span>}
      </div>

      <div className="attention-list">
        {report && entries.length === 0 && (
          report.error
            ? <p role="alert">Could not load connection issues. Use Refresh to try again.</p>
            : <p role="status">{report.loading ? 'Loading connection issues…' : 'No paid customers are waiting for activation.'}</p>
        )}
        {entries.map((issue) => (
          <article className="attention-item" key={issue.id}>
            <div className="attention-icon">
              <span className="material-symbols-outlined">
                {issue.icon}
              </span>
            </div>

            <div className="attention-details">
              <div className="attention-title-row">
                <h3>{issue.title}</h3>
                {issue.priority && (
                  <span className={`priority-badge priority-${issue.priority.toLowerCase()}`}>{issue.priority}</span>
                )}
              </div>

              <p>{issue.description}</p>

              <div className="attention-meta">
                <span>{issue.id}</span>
                {issue.payment && <span>{issue.payment}</span>}
                <span>{issue.time}</span>
              </div>

              {issue.action && <span className="attention-action-label">{issue.action}</span>}
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
