import KpiGrid from '../components/dashboard/KpiGrid.jsx'
import ActivityChart from '../components/dashboard/ActivityChart.jsx'
import AttentionList from '../components/dashboard/AttentionList.jsx'
import RecentPayments from '../components/dashboard/RecentPayments.jsx'

export default function DashboardPage({ operator }) {
  return (
    <section className="dashboard-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">DEMONSTRATION DASHBOARD</p>
          <h1>Overview</h1>
          <p className="page-description">
            Good morning, {operator.displayName}. Sample network and billing information.
          </p>
        </div>

        <div className="cluster-verification">
          <span className="material-symbols-outlined">verified</span>
          Cluster KE-NBO-01: Demo environment
        </div>
      </div>

      <KpiGrid />
      <ActivityChart />
      <AttentionList />
      <RecentPayments />
    </section>
  )
}
