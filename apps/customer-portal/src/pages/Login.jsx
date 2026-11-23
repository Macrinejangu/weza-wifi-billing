import { ArrowRight } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AccountField, AccountForm } from '../components/AccountForm'

export default function Login({ onSignIn }) {
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleLogin(event) {
    event.preventDefault()
    if (submitting) return

    const fields = new FormData(event.currentTarget)
    setMessage('')
    setSubmitting(true)
    try {
      await onSignIn(fields.get('email'), fields.get('password'))
    } catch (error) {
      setMessage(error.status === 401 ? 'Invalid email or password.' : 'Could not sign in. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AccountForm
      title="Sign in"
      description="Use your email address to sign in to the Weza customer portal."
      footer={<>Need a pilot account? <Link to="/support" className="font-semibold underline">Get support</Link></>}
    >
      <form onSubmit={handleLogin} className="space-y-4">
        <AccountField
          label="Email address"
          name="email"
          type="email"
          maxLength={150}
          autoComplete="username"
          placeholder="name@example.com"
        />
        <AccountField
          label="Password"
          name="password"
          type="password"
          maxLength={128}
          autoComplete="current-password"
          placeholder="Enter your password"
        />
        <button type="submit" className="package-button" disabled={submitting}>
          {submitting ? 'Signing in…' : 'Sign in'} <ArrowRight size={18} aria-hidden="true" />
        </button>
        {message && <p role="alert" className="text-sm text-red-700">{message}</p>}
      </form>
    </AccountForm>
  )
}
