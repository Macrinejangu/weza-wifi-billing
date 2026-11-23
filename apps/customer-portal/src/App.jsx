import { useEffect, useState } from 'react'
import { Link, Navigate, Route, Routes } from 'react-router-dom'
import { demoDataEnabled } from '../../shared/demoMode.js'
import PaymentStatus from './components/payments/PaymentStatus'
import ConnectionStatus from './pages/ConnectionStatus'
import CustomerLayout from './components/layout/CustomerLayout'

import ConfirmPackage from './pages/ConfirmPackage'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import HotspotEntry from './pages/HotspotEntry'
import Packages from './pages/Packages'
import Payments from './pages/Payments'
import Profile from './pages/Profile'
import Register from './pages/Register'
import Support from './pages/Support'
import Usage from './pages/Usage'
import Welcome from './pages/Welcome'
import PackageExpired from './pages/PackageExpired'
import { getCustomerProfile, loginCustomer } from './services/api.js'

const sandboxCheckoutEnabled =
  import.meta.env.DEV && import.meta.env.VITE_ENABLE_SANDBOX_CHECKOUT === 'true'

function UnavailablePage({ title, message }) {
  return (
    <section className="page-heading">
      <h1>{title}</h1>
      <p role="status">{message}</p>
    </section>
  )
}

function getTokenExpiry(accessToken) {
  try {
    const payload = accessToken.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const { exp } = JSON.parse(atob(payload))
    return Number.isFinite(exp) ? exp * 1000 : 0
  } catch {
    return 0
  }
}

export default function App() {
  const [customerSession, setCustomerSession] = useState(null)
  const expiresAt = customerSession?.expiresAt

  useEffect(() => {
    if (!expiresAt) return undefined
    const timeout = window.setTimeout(() => setCustomerSession(null), Math.max(0, expiresAt - Date.now()))
    return () => window.clearTimeout(timeout)
  }, [expiresAt])

  async function handleSignIn(email, password) {
    const { access_token: accessToken } = await loginCustomer({ email, password })
    const expiry = getTokenExpiry(accessToken)
    if (expiry <= Date.now()) throw new Error('Customer session is unavailable.')

    const profile = await getCustomerProfile(accessToken)
    if (!Number.isInteger(profile.id) || typeof profile.full_name !== 'string' || typeof profile.email !== 'string') {
      throw new Error('Customer profile is unavailable.')
    }
    if (expiry <= Date.now()) throw new Error('Customer session is unavailable.')

    setCustomerSession({ accessToken, profile, expiresAt: expiry })
  }

  return (
    <Routes>
      <Route path="/" element={<Welcome />} />
      <Route path="/login" element={customerSession ? <Navigate to="/profile" replace /> : <Login onSignIn={handleSignIn} />} />
      <Route path="/register" element={<Register />} />
      <Route path="/support" element={<Support />} />
      <Route
        path="/package-expired"
        element={
          demoDataEnabled ? <PackageExpired /> : (
            <UnavailablePage
              title="Subscription status"
              message="Your subscription status could not be verified."
            />
          )
        }
      />
      <Route path="/hotspot-entry" element={<HotspotEntry />} />

      <Route
        path="/payment-status"
        element={
          demoDataEnabled ? <PaymentStatus /> : (
            <UnavailablePage
              title="Payment status"
              message="Live payment status is currently unavailable."
            />
          )
        }
      />
      <Route
        path="/connection-status"
        element={
          demoDataEnabled ? <ConnectionStatus /> : (
            <UnavailablePage
              title="Connection status"
              message="Live connection status is currently unavailable."
            />
          )
        }
      />

      <Route element={<CustomerLayout />}>
        <Route
          path="/dashboard"
          element={
            demoDataEnabled ? <Dashboard /> : (
              <UnavailablePage
                title="Dashboard"
                message="Connection and subscription details are currently unavailable."
              />
            )
          }
        />
        <Route path="/packages" element={<Packages />} />
        <Route
          path="/confirm-package"
          element={
            demoDataEnabled || sandboxCheckoutEnabled ? <ConfirmPackage /> : (
              <UnavailablePage
                title="Checkout"
                message="Live checkout is currently unavailable."
              />
            )
          }
        />
        <Route
          path="/payments"
          element={
            demoDataEnabled ? <Payments /> : (
              <UnavailablePage
                title="Payments"
                message="Payment history is currently unavailable."
              />
            )
          }
        />
        <Route
          path="/usage"
          element={
            demoDataEnabled ? <Usage /> : (
              <UnavailablePage
                title="Usage"
                message="Usage history and sessions are currently unavailable."
              />
            )
          }
        />
        <Route
          path="/profile"
          element={
            customerSession ? (
              <Profile customer={customerSession.profile} onSignOut={() => setCustomerSession(null)} />
            ) : demoDataEnabled ? <Profile /> : (
              <section className="page-heading">
                <h1>My profile</h1>
                <p role="status">Account details are currently unavailable.</p>
                <Link className="package-button" to="/login">Sign in to view your profile</Link>
              </section>
            )
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
