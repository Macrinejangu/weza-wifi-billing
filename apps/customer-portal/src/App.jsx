import { useEffect, useState } from 'react'
import { Link, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { demoDataEnabled } from '../../shared/demoMode.js'
import PaymentStatus, { CustomerPaymentStatus } from './components/payments/PaymentStatus'
import ConnectionStatus, { CustomerConnectionStatus } from './pages/ConnectionStatus'
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

import { checkoutMode } from './checkoutSettings.js'

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
  const { state } = useLocation()
  const returnPaymentId = state?.returnPaymentId
  const returnPackageId = state?.returnPackageId
  const returnConnection = state?.returnConnection === true
  let signInDestination = returnConnection ? '/connection-status' : '/profile'
  if (typeof returnPaymentId === 'string' && /^[1-9]\d{0,9}$/.test(returnPaymentId)) {
    signInDestination = `${returnConnection ? '/connection-status' : '/payment-status'}?payment=${returnPaymentId}`
  } else if (Number.isSafeInteger(returnPackageId) && returnPackageId > 0) {
    signInDestination = `/packages?package=${returnPackageId}`
  }
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

  const connection = <CustomerConnectionStatus
    accessToken={customerSession?.accessToken}
    onSessionExpired={() => setCustomerSession(null)}
  />

  return (
    <Routes>
      <Route path="/" element={<Welcome />} />
      <Route path="/login" element={customerSession ? <Navigate to={signInDestination} replace /> : <Login onSignIn={handleSignIn} />} />
      <Route path="/register" element={<Register />} />
      <Route path="/support" element={<Support />} />
      <Route
        path="/package-expired"
        element={
          demoDataEnabled ? <PackageExpired /> : connection
        }
      />
      <Route path="/hotspot-entry" element={<HotspotEntry />} />

      <Route
        path="/payment-status"
        element={
          demoDataEnabled ? <PaymentStatus /> : (
            <CustomerPaymentStatus
              accessToken={customerSession?.accessToken}
              onSessionExpired={() => setCustomerSession(null)}
            />
          )
        }
      />
      <Route
        path="/connection-status"
        element={
          demoDataEnabled ? <ConnectionStatus /> : connection
        }
      />

      <Route element={<CustomerLayout />}>
        <Route
          path="/dashboard"
          element={
            demoDataEnabled ? <Dashboard /> : connection
          }
        />
        <Route path="/packages" element={<Packages />} />
        <Route
          path="/confirm-package"
          element={
            demoDataEnabled || checkoutMode ? <ConfirmPackage accessToken={customerSession?.accessToken} /> : (
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
