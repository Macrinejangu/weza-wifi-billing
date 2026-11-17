import { ArrowUpRight, ChartNoAxesColumnIncreasing, CreditCard, Package, Wifi } from 'lucide-react'
import { Link } from 'react-router-dom'

const quickActions = [
  { label: 'Browse packages', to: '/packages', icon: Package },
  { label: 'View payment history', to: '/payments', icon: CreditCard },
  { label: 'View data usage', to: '/usage', icon: ChartNoAxesColumnIncreasing },
]

const recentPayments = [
  { name: 'Weekly Plus', date: '10 Nov 2026', amount: 250, status: 'Paid' },
  { name: 'Daily Connect', date: '05 Nov 2026', amount: 50, status: 'Paid' },
  { name: 'Quick Connect', date: '04 Nov 2026', amount: 10, status: 'Failed' },
]

const card = 'min-w-0 rounded-2xl border border-[#edece8] bg-white p-4 sm:p-6'

export default function Dashboard() {
  return (
    <div className="page-content space-y-4">
      <header className="page-heading">
        <h1>Karibu, Enoch.</h1>
        <p>Here’s your connection overview. This preview uses sample data.</p>
      </header>

      <section className={card} aria-labelledby="connection-overview">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-full bg-[#d9e52e]">
              <Wifi size={20} aria-hidden="true" />
            </span>
            <div>
              <h2 id="connection-overview" className="text-lg font-bold">Connection</h2>
              <p className="text-sm text-[#655f75]">Sample status: internet active</p>
            </div>
          </div>
          <Link to="/packages" className="public-button">Browse packages</Link>
        </div>

        <dl className="mt-5 grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl bg-[#f4f3f0] p-3">
            <dt className="text-sm text-[#655f75]">Active package</dt>
            <dd className="mt-1 font-bold">Weekly Plus</dd>
          </div>
          <div className="rounded-xl bg-[#f4f3f0] p-3">
            <dt className="text-sm text-[#655f75]">Remaining data</dt>
            <dd className="mt-1 font-bold">6.4 GB of 10 GB</dd>
            <progress
              className="mt-2 block w-full accent-[#726b91]"
              value={6.4}
              max={10}
              aria-label="6.4 GB remaining out of 10 GB"
            />
          </div>
          <div className="rounded-xl bg-[#f4f3f0] p-3">
            <dt className="text-sm text-[#655f75]">Valid until</dt>
            <dd className="mt-1 font-bold">18 Nov, 11:42 AM EAT</dd>
          </div>
        </dl>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className={card}>
          <h2 className="text-lg font-bold">Your data, at a glance</h2>
          <p className="mt-3 text-sm text-[#655f75]">
            <strong className="text-2xl text-[#17152d]">3.6 GB</strong> used in the last 7 days
          </p>
          <Link to="/usage" className="mt-3 inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-[#585172]">
            View usage details <ArrowUpRight size={16} aria-hidden="true" />
          </Link>
        </section>

        <section className={card}>
          <h2 className="text-lg font-bold">Quick actions</h2>
          <ul className="mt-2 divide-y divide-[#edece8]">
            {quickActions.map(({ label, to, icon: Icon }) => (
              <li key={to}>
                <Link to={to} className="flex min-h-11 items-center gap-3 py-2 text-sm font-semibold">
                  <Icon size={18} className="shrink-0 text-[#585172]" aria-hidden="true" />
                  <span className="flex-1">{label}</span>
                  <ArrowUpRight size={15} className="shrink-0" aria-hidden="true" />
                </Link>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className={card}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-bold">Recent payments</h2>
          <Link to="/payments" className="inline-flex min-h-11 items-center text-sm font-semibold text-[#585172]">
            View all payments
          </Link>
        </div>

        <ul className="divide-y divide-[#edece8]">
          {recentPayments.map(({ name, date, amount, status }) => (
            <li key={name} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
              <div>
                <p className="font-semibold">{name}</p>
                <p className="text-xs text-[#655f75]">{date} · M-Pesa</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <strong>KES {amount.toLocaleString('en-KE')}</strong>
                <span className={`rounded-full px-2 py-1 text-xs font-semibold ${status === 'Paid' ? 'bg-lime-100 text-lime-900' : 'bg-red-100 text-red-900'}`}>
                  {status}
                </span>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
