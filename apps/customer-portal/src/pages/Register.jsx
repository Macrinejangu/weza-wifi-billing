import { ArrowRight } from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { AccountField, AccountForm } from '../components/AccountForm'
import { registerCustomer } from '../services/api.js'

export default function Register() {
  const { state } = useLocation()
  const navigate = useNavigate()
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleRegister(event) {
    event.preventDefault()
    if (submitting) return
    const form = new FormData(event.currentTarget)
    const password = form.get('password')
    if (password !== form.get('confirmPassword')) {
      setMessage('Your passwords do not match.')
      return
    }

    setMessage('')
    setSubmitting(true)
    try {
      await registerCustomer({
        fullName: form.get('fullName').trim(),
        phone: form.get('phone').trim(),
        email: form.get('email').trim(),
        password,
      })
      navigate('/login', { replace: true, state: { ...state, registered: true } })
    } catch (error) {
      setMessage(error.status === 409 ? 'An account already uses these details. Sign in or contact support.'
        : error.status === 422 ? 'Check your name, email, phone number and password, then try again.'
          : 'Could not create the account. Please try again.')
      setSubmitting(false)
    }
  }

  return (
    <AccountForm
      title="Create an account"
      description="Set up your Weza Wi-Fi account to buy and manage packages."
      footer={<>Already have an account? <Link to="/login" state={state} className="font-semibold underline">Sign in</Link></>}
    >
      <form onSubmit={handleRegister} className="space-y-4">
        <AccountField label="Full name" name="fullName" autoComplete="name" placeholder="Enter your full name" maxLength={100} />
        <AccountField label="Phone number" name="phone" type="tel" autoComplete="tel" placeholder="07XXXXXXXX" maxLength={32} />
        <AccountField label="Email address" name="email" type="email" autoComplete="email" placeholder="name@example.com" maxLength={150} />
        <AccountField label="Password" name="password" type="password" autoComplete="new-password" minLength={8} maxLength={128} placeholder="At least 8 characters" />
        <AccountField label="Confirm password" name="confirmPassword" type="password" autoComplete="new-password" minLength={8} maxLength={128} placeholder="Re-enter your password" />
        <button type="submit" className="package-button" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create account'} <ArrowRight size={18} aria-hidden="true" />
        </button>
        {message && <p role="alert" className="text-sm text-red-700">{message}</p>}
      </form>
    </AccountForm>
  )
}
