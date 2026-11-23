import { Headset, ShieldCheck, UserRound } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'

const profileDetails = [
  ['Full name', 'Customer Name'],
  ['Email address', 'customer@example.com'],
  ['Phone number', '07XXXXXXXX'],
  ['Account status', 'Active'],
]

const card = 'min-w-0 rounded-2xl border border-[#edece8] bg-white p-4 sm:p-6'

export default function Profile({ customer, onSignOut } = {}) {
  const navigate = useNavigate()
  const fields = customer ? [
    ['Full name', customer.full_name],
    ['Email address', customer.email],
    ['Phone number', customer.phone || 'Unavailable'],
    ['Account status', 'Active'],
  ] : profileDetails
  return (
    <div className="page-content">
      <header className="page-heading">
        <h1>My profile</h1>
        <p>{customer ? 'View your customer account details.' : 'View your account details. This preview shows a sample profile.'}</p>
      </header>

      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <section className={card}>
          <h2 className="flex items-center gap-2 text-lg font-bold">
            <UserRound size={20} className="shrink-0 text-[#585172]" aria-hidden="true" /> Personal details
          </h2>
          <dl className="mt-4 grid gap-3">
            {fields.map(([label, value]) => (
              <div key={label} className="rounded-lg bg-[#f4f3f0] p-3">
                <dt className="text-sm text-[#655f75]">{label}</dt>
                <dd className="mt-1 break-words text-sm font-semibold">{value}</dd>
              </div>
            ))}
          </dl>
        </section>

        <div className="grid gap-4">
          <section className={card}>
            <h2 className="flex items-center gap-2 text-lg font-bold">
              <ShieldCheck size={20} className="shrink-0 text-[#585172]" aria-hidden="true" /> Account security
            </h2>
            <p className="mt-2 text-sm leading-6 text-[#655f75]">{customer ? 'Password changes are currently unavailable.' : 'Password changes are unavailable in this preview.'}</p>
            {customer && (
              <button className="package-button" type="button" onClick={() => {
                onSignOut()
                navigate('/login', { replace: true })
              }}>
                Sign out
              </button>
            )}
          </section>

          <section className={card}>
            <h2 className="flex items-center gap-2 text-lg font-bold">
              <Headset size={20} className="shrink-0 text-[#585172]" aria-hidden="true" /> Help with your account
            </h2>
            <Link to="/support" className="package-button">Get support</Link>
          </section>
        </div>
      </div>
    </div>
  )
}
