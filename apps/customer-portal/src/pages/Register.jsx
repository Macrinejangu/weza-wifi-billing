import { ArrowRight } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AccountField, AccountForm } from '../components/AccountForm'

export default function Register() {
  const [feedback, setFeedback] = useState(null)

  function handleRegister(event) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)

    if (form.get('password') !== form.get('confirmPassword')) {
      setFeedback({ text: 'Your passwords do not match.', error: true })
      return
    }

    setFeedback({ text: 'Account creation is currently unavailable.', error: false })
  }

  return (
    <AccountForm
      title="Create an account"
      description="Set up your Weza Wi-Fi account to manage your packages and data."
      footer={<>Already have an account? <Link to="/login" className="font-semibold underline">Sign in</Link></>}
    >
      <form onSubmit={handleRegister} className="space-y-4">
        <AccountField label="Full name" name="fullName" autoComplete="name" placeholder="Enter your full name" />
        <AccountField label="Phone number" name="phone" type="tel" autoComplete="tel" placeholder="07XXXXXXXX" />
        <AccountField label="Email address" name="email" type="email" autoComplete="email" placeholder="name@example.com" />
        <AccountField label="Password" name="password" type="password" autoComplete="new-password" minLength={8} placeholder="At least 8 characters" />
        <AccountField label="Confirm password" name="confirmPassword" type="password" autoComplete="new-password" minLength={8} placeholder="Re-enter your password" />
        <button type="submit" className="package-button">
          Create account <ArrowRight size={18} aria-hidden="true" />
        </button>
        {feedback && (
          <p role={feedback.error ? 'alert' : 'status'} className={feedback.error ? 'text-sm text-red-700' : 'text-sm text-[#585172]'}>
            {feedback.text}
          </p>
        )}
      </form>
    </AccountForm>
  )
}
