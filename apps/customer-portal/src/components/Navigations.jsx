
import { NavLink } from 'react-router-dom'

import {
  LayoutDashboard,
  Package,
  CreditCard,
  ChartNoAxesColumnIncreasing,
  UserRound
} from 'lucide-react'

const navigation = [
  {
    name: 'Overview',
    path: '/',
    icon: LayoutDashboard
  },
  {
    name: 'Packages',
    path: '/packages',
    icon: Package
  },
  {
    name: 'Payments',
    path: '/payments',
    icon: CreditCard
  },
  {
    name: 'Usage',
    path: '/usage',
    icon: ChartNoAxesColumnIncreasing
  },
  {
    name: 'My Profile',
    path: '/profile',
    icon: UserRound
  }
]

export function NavigationLinks({ mobile = false }) {
  return (
    <nav className={mobile ? 'mobile-navigation' : 'sidebar-navigation'}>
      {navigation.map((item) => {
        const Icon = item.icon

        return (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              isActive ? 'navigation-link active' : 'navigation-link'
            }
          >
            <Icon size={19} strokeWidth={1.8} />
            <span>{item.name}</span>
          </NavLink>
        )
      })}
    </nav>
  )
}
