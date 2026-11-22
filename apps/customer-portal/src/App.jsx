import { Navigate, Route, Routes } from 'react-router-dom'
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

function UnavailablePage({ title, message }) {
  return (
    <section className="page-heading">
      <h1>{title}</h1>
      <p role="status">{message}</p>
    </section>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Welcome />} />
      <Route path="/login" element={<Login />} />
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
        element={demoDataEnabled ? <PaymentStatus /> : (
          <UnavailablePage title="Payment status" message="Live payment status is currently unavailable." />
        )}
      />
      <Route
        path="/connection-status"
        element={demoDataEnabled ? <ConnectionStatus /> : (
          <UnavailablePage title="Connection status" message="Live connection status is currently unavailable." />
        )}
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
            demoDataEnabled ? <ConfirmPackage /> : (
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
            demoDataEnabled ? <Profile /> : (
              <UnavailablePage
                title="My profile"
                message="Account details are currently unavailable."
              />
            )
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
