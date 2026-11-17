

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Wifi, Eye, EyeOff, ArrowRight } from 'lucide-react'

export default function Login() {
  const [showPassword, setShowPassword] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')

  function handleLogin(event) {
    event.preventDefault()
    setMessage('Login authentication will be connected to the backend.')
  }

  return (
    <main className="min-h-screen bg-[#F7F6F2] flex items-center justify-center px-5 py-12">

      <div className="w-full max-w-[430px]">

        {/* Logo */}
        <Link to="/" className="flex items-center justify-center gap-3 mb-9">
          <div className="bg-[#77709D] text-white p-3 rounded-2xl shadow-md">
            <Wifi size={26} />
          </div>

          <span className="text-3xl font-bold tracking-tight text-[#17152D]">
            WEZA
          </span>
        </Link>

        {/* Login Card */}
        <section className="bg-white rounded-[28px] border border-[#EAE7F0] shadow-[0_12px_45px_rgba(23,21,45,0.07)] p-7 sm:p-10">

          <div className="text-center mb-9">
            <div className="w-12 h-1.5 bg-[#D9E52E] rounded-full mx-auto mb-6" />

            <p className="text-xs font-bold tracking-[0.22em] text-[#77709D] mb-3">
              CUSTOMER PORTAL
            </p>

            <h1 className="text-3xl font-bold text-[#17152D] tracking-tight">
              Welcome back
            </h1>

            <p className="text-sm text-[#88849A] mt-3 leading-6">
              Sign in to manage your internet connection and packages.
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-6">

            {/* Email */}
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-semibold text-[#17152D] mb-2"
              >
                Email address
              </label>

              <input
                id="email"
                type="email"
                placeholder="name@example.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                className="w-full rounded-xl border border-[#E5E2EA] bg-[#FAF9FC] px-4 py-3.5 text-sm text-[#17152D] outline-none transition focus:border-[#77709D] focus:ring-4 focus:ring-[#F0EEF6]"
              />
            </div>

            {/* Password */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <label
                  htmlFor="password"
                  className="text-sm font-semibold text-[#17152D]"
                >
                  Password
                </label>
              </div>

              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  className="w-full rounded-xl border border-[#E5E2EA] bg-[#FAF9FC] px-4 py-3.5 pr-12 text-sm text-[#17152D] outline-none transition focus:border-[#77709D] focus:ring-4 focus:ring-[#F0EEF6]"
                />

                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-[#88849A] hover:text-[#77709D]"
                >
                  {showPassword ? <EyeOff size={19} /> : <Eye size={19} />}
                </button>
              </div>
            </div>

            {/* Forgot Password */}
            <div className="flex justify-end -mt-2">
              <Link
                to="/forgot-password"
                className="text-sm font-semibold text-[#77709D] hover:text-[#17152D] transition"
              >
                Forgot password?
              </Link>
            </div>

            {/* Sign In */}
            <button
              type="submit"
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-[#D9E52E] px-5 py-4 font-bold text-[#17152D] shadow-sm transition hover:brightness-95 hover:shadow-md active:scale-[0.99]"
            >
              Sign in
              <ArrowRight size={18} />
            </button>

          </form>

          {/* Message */}
          {message && (
            <p
              role="status"
              className="mt-5 rounded-xl bg-[#F0EEF6] p-4 text-center text-sm text-[#77709D]"
            >
              {message}
            </p>
          )}

          {/* Support */}
          <div className="border-t border-[#F0EEF6] mt-8 pt-6 text-center">
            <p className="text-sm text-[#88849A] leading-6">
              Need help accessing your account?
            </p>

            <Link
              to="/support"
              className="inline-flex items-center gap-1 mt-2 text-sm font-bold text-[#77709D] hover:underline"
            >
              Contact support
              <ArrowRight size={15} />
            </Link>
          </div>

        </section>

        {/* Footer */}
        <p className="text-center text-xs text-[#88849A] mt-8">
          WEZA Wi-Fi · Stay connected, your way.
        </p>

      </div>
    </main>
  )
}
