import { ArrowRight } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AccountField, AccountForm } from '../components/AccountForm'

export default function Login() {
  const [message, setMessage] = useState('')
  
  function handleLogin(event) {
    event.preventDefault()
    setMessage('Sign-in is currently unavailable.')
  }

  return (
    <AccountForm
      title="Sign in"
      description="Use your email address to sign in to the Weza customer portal."
      footer={<>New to Weza Wi-Fi? <Link to="/register" className="font-semibold underline">Create an account</Link></>}
    >
      <form onSubmit={handleLogin} className="space-y-4">
        <AccountField
          label="Email address"
          name="email"
          type="email"
          autoComplete="username"
          placeholder="name@example.com"
        />
        <AccountField
          label="Password"
          name="password"
          type="password"
          autoComplete="current-password"
          placeholder="Enter your password"
        />
        <button type="submit" className="package-button">
          Sign in <ArrowRight size={18} aria-hidden="true" />
        </button>
        {message && <p role="status" className="text-sm text-[#585172]">{message}</p>}
      </form>
    </AccountForm>
  )
}
