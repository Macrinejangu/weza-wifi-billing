


import { Routes, Route, Navigate } from 'react-router-dom'
import CustomerLayout from './components/CustomerLayout'

import Welcome from './Pages/Welcome'
import Dashboard from './Pages/Dashboard'
import Packages from './Pages/Packages'
import Payments from './Pages/Payments'
import Usage from './Pages/Usage'
import Profile from './Pages/Profile'



export default function App() {
  return (
    <Routes>
      <Route element={<CustomerLayout />}>
        <Route path="/" element={<Welcome />} />
        <Route path= "/dashboard" element={<Dashboard />}/>
        <Route path="/packages" element={<Packages />} />
        <Route path="/payments" element={<Payments />} />
        <Route path="/usage" element={<Usage />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
