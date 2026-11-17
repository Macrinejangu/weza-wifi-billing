import { Navigate, Route, Routes } from 'react-router-dom'
import CustomerLayout from './components/layout/CustomerLayout'

import ConfirmPackage from './pages/ConfirmPackage'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Packages from './pages/Packages'
import Payments from './pages/Payments'
import Profile from './pages/Profile'
import Register from './pages/Register'
import Support from './pages/Support'
import Usage from './pages/Usage'
import Welcome from './pages/Welcome'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Welcome />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/support" element={<Support />} />

      <Route element={<CustomerLayout />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/packages" element={<Packages />} />
        <Route path="/confirm-package" element={<ConfirmPackage />} />
        <Route path="/payments" element={<Payments />} />
        <Route path="/usage" element={<Usage />} />
        <Route path="/profile" element={<Profile />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}