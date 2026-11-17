
import { Routes, Route, Navigate } from 'react-router-dom'
import CustomerLayout from './components/layout/CustomerLayout'

import Login from './pages/Login'
import Register from './pages/Register'
import Welcome from './pages/Welcome'
import Packages from './pages/Packages'
import ConfirmPackage from './pages/ConfirmPackage'
import Payments from './pages/Payments'
import Usage from './pages/Usage'
import Profile from './pages/Profile'
import Support from './pages/Support'

export default function App() {
  return (
    <Routes>
  <Route path="/login" element={<Login />} />
  <Route path="/register" element={<Register />} />
  <Route path="/support" element={<Support />} />

  <Route element={<CustomerLayout />}>
    <Route path="/" element={<Welcome />} />
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
