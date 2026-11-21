import { ArrowRight, Receipt } from 'lucide-react'
import { Link } from 'react-router-dom'

const recentPayments = [
  { reference: 'WEZA001', packageName: 'Weekly Plus', date: '10 Nov 2026', amount: 250, status: 'Paid' },
  { reference: 'WEZA002', packageName: 'Daily Connect', date: '05 Nov 2026', amount: 50, status: 'Paid' },
  { reference: 'WEZA003', packageName: 'Quick Connect', date: '04 Nov 2026', amount: 10, status: 'Failed' },
  { reference: 'WEZA004', packageName: 'Daily Connect', date: '03 Nov 2026', amount: 50, status: 'Pending' },
]

const statusStyles = {
  Paid: 'bg-lime-100 text-lime-900',
  Failed: 'bg-red-100 text-red-900',
  Pending: 'bg-amber-100 text-amber-900',
}

export default function Payments() {
  return (
    <div className="page-content">
      <header className="page-heading">
        <h1>Payments</h1>
        <p>Review your M-Pesa payment history.</p>
      </header>

      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <section className="rounded-2xl border border-[#edece8] bg-white p-4 sm:p-6">
          <h2 className="text-lg font-bold">Recent payments</h2>
          <p className="mt-1 text-sm text-[#655f75]">Sample transactions</p>

          <ul className="mt-3 divide-y divide-[#edece8]">
            {recentPayments.map((payment) => (
              <li className="flex flex-wrap items-start justify-between gap-3 py-4" key={payment.reference}>
                <div className="flex min-w-0 items-start gap-2">
                  <Receipt size={18} className="mt-0.5 shrink-0 text-[#585172]" aria-hidden="true" />
                  <div>
                    <p className="text-sm font-semibold">{payment.packageName}</p>
                    <p className="mt-1 text-xs text-[#655f75]">{payment.date} · M-Pesa · {payment.reference}</p>
                  </div>
                </div>

                <div className="flex flex-col items-start gap-1 sm:items-end">
                  <strong className="text-sm">KES {payment.amount.toLocaleString('en-KE')}</strong>
                  <span className={`rounded-full px-2 py-1 text-xs font-semibold ${statusStyles[payment.status]}`}>
                    {payment.status}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-2xl border border-[#edece8] bg-white p-4 sm:p-6">
          <h2 className="text-lg font-bold">Buy a package</h2>
          <p className="mt-2 text-sm leading-6 text-[#655f75]">Choose a package to see its price and open M-Pesa checkout.</p>
          <Link to="/packages" className="package-button">
            Browse packages <ArrowRight size={17} aria-hidden="true" />
          </Link>
        </section>
      </div>
    </div>
  )
}
