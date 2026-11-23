import { useEffect, useState } from 'react'
import { getStaffOverview, listStaffConnectionIssues, listStaffPayments, StaffSessionError } from '../api.js'
import KpiGrid from '../components/dashboard/KpiGrid.jsx'
import ActivityChart from '../components/dashboard/ActivityChart.jsx'
import AttentionList from '../components/dashboard/AttentionList.jsx'
import RecentPayments from '../components/dashboard/RecentPayments.jsx'

export default function DashboardPage({ operator, accessToken, onSignOut, onOpenIssues }) {
  const live = Boolean(accessToken)
  const [totals, setTotals] = useState({ loading: true })
  const [payments, setPayments] = useState({ loading: true })
  const [issues, setIssues] = useState({ loading: true })
  const [reload, setReload] = useState(0)

  useEffect(() => {
    if (!accessToken) return undefined
    const controller = new AbortController()
    const { signal } = controller

    function failure(error, update) {
      if (signal.aborted) return
      if (error instanceof StaffSessionError) onSignOut()
      else update({ error: true })
    }

    getStaffOverview(accessToken, { signal }).then((data) => {
      if (!signal.aborted) setTotals({ data })
    }).catch((error) => failure(error, setTotals))
    listStaffPayments(accessToken, { limit: 5, signal }).then((data) => {
      if (!Array.isArray(data)) throw new Error('Invalid payment list')
      if (!signal.aborted) setPayments({ data })
    }).catch((error) => failure(error, setPayments))
    listStaffConnectionIssues(accessToken, { limit: 3, signal }).then((data) => {
      if (!Array.isArray(data)) throw new Error('Invalid connection issues list')
      if (!signal.aborted) setIssues({ data })
    }).catch((error) => failure(error, setIssues))

    return () => controller.abort()
  }, [accessToken, onSignOut, reload])

  function refresh() {
    setTotals({ loading: true })
    setPayments({ loading: true })
    setIssues({ loading: true })
    setReload((attempt) => attempt + 1)
  }

  return (
    <section className="dashboard-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">{live ? 'STAFF WORKSPACE' : 'DEMONSTRATION DASHBOARD'}</p>
          <h1>Overview</h1>
          <p className="page-description">
            {live ? 'Review billing and session records.' : `Good morning, ${operator.displayName}. Sample network and billing information.`}
          </p>
        </div>

        {live ? (
          <button type="button" className="payment-secondary-button" disabled={totals.loading && payments.loading && issues.loading} onClick={refresh}>
            Refresh
          </button>
        ) : (
          <div className="cluster-verification">
            <span className="material-symbols-outlined">info</span>
            Cluster KE-NBO-01: Demo environment
          </div>
        )}
      </div>

      <KpiGrid report={live ? totals : undefined} />

      <div className="dashboard-operations-grid">
        {live ? (
          <>
            <section className="activity-section">
              <div className="activity-heading"><h2>Revenue &amp; Session Activity</h2></div>
              <p className="section-description" role="status">Historical activity is unavailable.</p>
            </section>
            <AttentionList report={issues} onOpenIssues={onOpenIssues} />
          </>
        ) : (
          <>
            <ActivityChart />
            <AttentionList />
          </>
        )}
      </div>

      <RecentPayments report={live ? payments : undefined} />
    </section>
  )
}
