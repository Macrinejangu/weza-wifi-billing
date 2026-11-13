const issues = [
  {
    id: 'ISS-4091',
    title: 'Router CoA Timeout',
    description: 'Router did not respond to a Change of Authorization request.',
    priority: 'High',
    time: '10m ago',
    icon: 'router',
  },
  {
    id: 'ISS-4088',
    title: 'Activation Pending',
    description: 'Subscriber payment received; activation is still pending.',
    priority: 'Medium',
    time: '24m ago',
    icon: 'pending_actions',
  },
  {
    id: 'ISS-4085',
    title: 'Telco Delay',
    description: 'Upstream provider response is taking longer than expected.',
    priority: 'Low',
    time: '45m ago',
    icon: 'network_check',
  },
]

export default function AttentionList() {
  return (
    <section className="attention-section">
      <div className="attention-heading">
        <div>
          <p className="section-eyebrow">OPERATIONS</p>
          <h2>Requires Attention</h2>
          <p className="section-description">
            Sample issues that may need operator review
          </p>
        </div>

        <span className="demo-data-label">DEMO DATA</span>
      </div>

      <div className="attention-list">
        {issues.map((issue) => (
          <article className="attention-item" key={issue.id}>
            <div className="attention-icon">
              <span className="material-symbols-outlined">
                {issue.icon}
              </span>
            </div>

            <div className="attention-details">
              <div className="attention-title-row">
                <h3>{issue.title}</h3>
                <span className={`priority-badge priority-${issue.priority.toLowerCase()}`}>
                  {issue.priority}
                </span>
              </div>

              <p>{issue.description}</p>

              <div className="attention-meta">
                <span>{issue.id}</span>
                <span>{issue.time}</span>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
