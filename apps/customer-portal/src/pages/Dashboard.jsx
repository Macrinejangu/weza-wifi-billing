
import { NavLink } from 'react-router-dom'
import {
  Wifi,
  Database,
  CalendarDays,
  Package,
  CreditCard,
  ChartNoAxesColumnIncreasing,
  ArrowUpRight,
  CheckCircle2
} from 'lucide-react'

const weeklyUsage = [
  { day: 'Mon', amount: 35 },
  { day: 'Tue', amount: 55 },
  { day: 'Wed', amount: 45 },
  { day: 'Thu', amount: 75 },
  { day: 'Fri', amount: 50 },
  { day: 'Sat', amount: 90, highlight: true },
  { day: 'Sun', amount: 30 }
]

function UsageChart() {
  return (
    <section className="usage-chart">
      <div className="chart-heading">
        <div>
          <h3>Weekly data usage</h3>
          <p>Your internet consumption this week</p>
        </div>
        <NavLink to="/usage">View details <ArrowUpRight size={14} /></NavLink>
      </div>

      <div className="chart-bars">
        {weeklyUsage.map((item) => (
          <div className="chart-column" key={item.day}>
            <div className="bar-area">
              <div
                className={`chart-bar ${item.highlight ? 'lime-bar' : ''}`}
                style={{ height: `${item.amount}%` }}
              />
            </div>
            <span>{item.day}</span>
          </div>
        ))}
      </div>
    </section>
  )
}

export default function Dashboard() {
  return (
    <div className="page-content">

      <div className="dashboard-heading">
        <p className="hero-eyebrow">CUSTOMER OVERVIEW</p>
        <h1>Karibu, Enoch.</h1>
        <p>Here's what's happening with your WEZA connection.</p>
      </div>

      <section className="welcome-hero dashboard-hero">
        <div className="hero-content">
          <p className="hero-eyebrow">YOUR CONNECTION</p>
          <h1>Your Internet. Your Way.</h1>
          <p className="hero-description">
            Stay connected to the things that matter.
            Manage your package and track your usage here.
          </p>
          <NavLink to="/packages" className="hero-button">
            Explore packages <ArrowUpRight size={15} />
          </NavLink>
        </div>
        <Wifi className="hero-decoration" size={100} />
      </section>

      <section className="dashboard-stats">

        <article className="stat-card">
          <div className="dashboard-stat-top">
            Active package
            <Package size={19} />
          </div>
          <h3>Weekly Plus</h3>
          <p>10 GB package</p>
        </article>

        <article className="stat-card">
          <div className="dashboard-stat-top">
            Data remaining
            <Database size={19} />
          </div>
          <h3>6.4 GB</h3>
          <p>Out of 10 GB</p>
        </article>

        <article className="stat-card">
          <div className="dashboard-stat-top">
            Valid until
            <CalendarDays size={19} />
          </div>
          <h3>18 Nov</h3>
          <p>Package expiry date</p>
        </article>

      </section>

      <div className="dashboard-content-grid">
        <UsageChart />

        <section className="dashboard-actions">
          <h3>Quick actions</h3>

          <NavLink to="/packages" className="dashboard-action">
            <Package size={19} />
            <span>
              <strong>Buy a package</strong>
              <small>Explore available packages</small>
            </span>
            <ArrowUpRight size={15} />
          </NavLink>

          <NavLink to="/payments" className="dashboard-action">
            <CreditCard size={19} />
            <span>
              <strong>Make a payment</strong>
              <small>Pay using M-Pesa</small>
            </span>
            <ArrowUpRight size={15} />
          </NavLink>

          <NavLink to="/usage" className="dashboard-action">
            <ChartNoAxesColumnIncreasing size={19} />
            <span>
              <strong>View usage</strong>
              <small>Check your data consumption</small>
            </span>
            <ArrowUpRight size={15} />
          </NavLink>
        </section>
      </div>

      <section className="dashboard-payments">
        <div className="section-heading">
          <div>
            <h3>Recent payments</h3>
            <p>Your latest transactions</p>
          </div>
          <NavLink to="/payments">View all</NavLink>
        </div>

        <div className="dashboard-payment-row">
          <div className="dashboard-payment-icon">
            <CheckCircle2 size={18} />
          </div>
          <div>
            <strong>Weekly Plus</strong>
            <p>M-Pesa · 11 Nov 2026</p>
          </div>
          <div className="dashboard-payment-amount">
            <strong>KSh 250</strong>
            <small>Successful</small>
          </div>
        </div>

        <div className="dashboard-payment-row">
          <div className="dashboard-payment-icon">
            <CheckCircle2 size={18} />
          </div>
          <div>
            <strong>Daily Package</strong>
            <p>M-Pesa · 8 Nov 2026</p>
          </div>
          <div className="dashboard-payment-amount">
            <strong>KSh 50</strong>
            <small>Successful</small>
          </div>
        </div>
      </section>

    </div>
  )
}
