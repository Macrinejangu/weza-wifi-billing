import { Eye, EyeOff, Wifi } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

export function AccountForm({ title, description, children, footer }) {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-md flex-col justify-center gap-4 px-4 py-8 sm:py-12">
      <Link to="/" className="self-start text-sm font-semibold">Weza Wi-Fi</Link>
      <section className="rounded-2xl border border-[#edece8] bg-white p-5 sm:p-8">
        <span className="mb-4 inline-grid size-10 place-items-center rounded-lg bg-[#ece7fa] text-[#585172]">
          <Wifi size={21} aria-hidden="true" />
        </span>
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        <p className="mb-6 mt-2 text-sm leading-6 text-[#655f75]">{description}</p>
        {children}
        <div className="mt-4 rounded-lg bg-[#f4f3f0] p-3 text-center text-sm">{footer}</div>
      </section>
      <Link
        to="/support"
        className="flex min-h-11 items-center justify-center rounded-lg bg-[#f4f3f0] px-4 text-sm font-semibold text-[#585172]"
      >
        Get support
      </Link>
    </main>
  )
}

export function AccountField({ label, name, type = 'text', autoComplete, placeholder, minLength }) {
  const [visible, setVisible] = useState(false)
  const isPassword = type === 'password'
  const inputType = isPassword && visible ? 'text' : type

  return (
    <div>
      <label htmlFor={name} className="mb-1.5 block text-sm font-semibold">{label}</label>
      <div className="relative">
        <input
          id={name}
          name={name}
          type={inputType}
          autoComplete={autoComplete}
          placeholder={placeholder}
          minLength={minLength}
          required
          className={`min-h-11 w-full rounded-lg border border-[#edece8] bg-[#f4f3f0] px-3 py-2 focus-visible:outline-2 focus-visible:outline-[#726b91] ${isPassword ? 'pr-12' : ''}`}
        />
        {isPassword && (
          <button
            type="button"
            aria-label={visible ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
            onClick={() => setVisible((current) => !current)}
            className="absolute inset-y-0 right-0 grid w-11 place-items-center rounded-r-lg text-[#585172] focus-visible:outline-2 focus-visible:outline-[#726b91]"
          >
            {visible ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
          </button>
        )}
      </div>
    </div>
  )
}
