import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Wifi,
  User,
  Mail,
  Phone,
  Lock,
  Eye,
  EyeOff,
  ArrowRight
} from 'lucide-react'

export default function Register() {
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [message, setMessage] = useState('')

  function handleRegister(event) {
    event.preventDefault()

    const form = new FormData(event.currentTarget)
    const password = form.get('password')
    const confirmPassword = form.get('confirmPassword')

    if (password !== confirmPassword) {
      setMessage('Your passwords do not match.')
      return
    }

    setMessage('Registration is ready. Account creation will be connected to the backend.')
  }

  return (
    <div className="min-h-screen bg-[#F7F6F2] flex items-center justify-center px-4 py-10">

      <div className="w-full max-w-[440px]">

        {/* Branding */}
        <div className="flex flex-col items-center mb-7">
          <div className="w-14 h-14 rounded-2xl bg-[#77709D] flex items-center justify-center mb-3">
            <Wifi size={30} color="white" />
          </div>

          <h1 className="text-2xl font-bold text-[#17152D]">
            Weza Wi-Fi
          </h1>

          <p className="text-xs tracking-widest text-[#88849A] mt-1">
            CUSTOMER PORTAL
          </p>
        </div>

        {/* Registration Card */}
        <div className="bg-white rounded-2xl p-7 sm:p-9 shadow-sm">

          <div className="mb-6">
            <h2 className="text-2xl font-bold text-[#17152D]">
              Create your account
            </h2>

            <p className="text-sm text-[#88849A] mt-2">
              Join Weza Wi-Fi and stay connected.
            </p>
          </div>

          <form onSubmit={handleRegister} className="space-y-4">

            {/* Full name */}
            <div>
              <label className="block text-sm font-semibold text-[#17152D] mb-2">
                Full name
              </label>

              <div className="flex items-center gap-3 border border-[#E9E7EE] rounded-lg px-3">
                <User size={18} className="text-[#88849A]" />

                <input
                  type="text"
                  name="fullName"
                  placeholder="Enter your full name"
                  required
                  className="w-full py-3 outline-none text-sm bg-transparent"
                />
              </div>
            </div>

            {/* Phone */}
            <div>
              <label className="block text-sm font-semibold text-[#17152D] mb-2">
                Phone number
              </label>

              <div className="flex items-center gap-3 border border-[#E9E7EE] rounded-lg px-3">
                <Phone size={18} className="text-[#88849A]" />

                <input
                  type="tel"
                  name="phone"
                  placeholder="07XXXXXXXX"
                  required
                  className="w-full py-3 outline-none text-sm bg-transparent"
                />
              </div>
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-semibold text-[#17152D] mb-2">
                Email address
              </label>

              <div className="flex items-center gap-3 border border-[#E9E7EE] rounded-lg px-3">
                <Mail size={18} className="text-[#88849A]" />

                <input
                  type="email"
                  name="email"
                  placeholder="you@example.com"
                  required
                  className="w-full py-3 outline-none text-sm bg-transparent"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-semibold text-[#17152D] mb-2">
                Password
              </label>

              <div className="flex items-center gap-3 border border-[#E9E7EE] rounded-lg px-3">
                <Lock size={18} className="text-[#88849A]" />

                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  placeholder="Create a password"
                  minLength="8"
                  required
                  className="w-full py-3 outline-none text-sm bg-transparent"
                />

                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="text-[#88849A]"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {/* Confirm password */}
            <div>
              <label className="block text-sm font-semibold text-[#17152D] mb-2">
                Confirm password
              </label>

              <div className="flex items-center gap-3 border border-[#E9E7EE] rounded-lg px-3">
                <Lock size={18} className="text-[#88849A]" />

                <input
                  type={showConfirmPassword ? 'text' : 'password'}
                  name="confirmPassword"
                  placeholder="Confirm your password"
                  minLength="8"
                  required
                  className="w-full py-3 outline-none text-sm bg-transparent"
                />

                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="text-[#88849A]"
                >
                  {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {message && (
              <p role="status" className="text-sm text-[#77709D]">
                {message}
              </p>
            )}
               {/* Register button */}
            <button
              type="submit"
              className="w-full bg-[#D9E52E] text-[#17152D] py-3 rounded-lg font-bold text-sm flex items-center justify-center gap-2 hover:brightness-95 transition"
            >
              Create account
              <ArrowRight size={17} />
            </button>

          </form>

          <div className="mt-6 text-center text-sm text-[#88849A]">
            Already have an account?{' '}
            <Link
              to="/login"
              className="text-[#77709D] font-bold hover:underline"
            >
              Sign in
            </Link>
          </div>

        </div>

        <p className="text-center text-xs text-[#88849A] mt-6">
          © 2026 Weza Wi-Fi. All rights reserved.
        </p>

      </div>
    </div>
  )
}
