


import { NavLink } from 'react-router-dom'
import {
  Clock3,
  Smartphone,
  SlidersHorizontal,
  ArrowUpRight
} from 'lucide-react'

export default function Welcome() {
  return (
    <div className="welcome-page">
      <p className="hero-eyebrow">WELCOME TO WEZA</p>

      <h1 className="welcome-page-title">
        A little Wi-Fi. A lot of possibility.
      </h1>

      <p className="welcome-page-description">
        Pick your pace. Every package comes with a simple M-Pesa checkout.
      </p>

      <section className="welcome-main-hero">
        <div className="welcome-hero-content">
          <p className="hero-eyebrow">YOUR EVERYDAY CONNECTION</p>
          <h2>Your Internet. Your Way.</h2>

          <p>
            Big ideas. Favourite shows. People who matter.
            Enjoy flexible WEZA Wi-Fi packages made for the way you live.
          </p>

          <div className="welcome-hero-actions">
            <NavLink to="/login" className="welcome-login-button">
              Login
            </NavLink>

            <NavLink to="/register" className="welcome-register-button">
              Create account
            </NavLink>
          </div>
        </div>
      </section>

      <section className="welcome-feature-grid">
        <article className="welcome-feature-card">
          <Clock3 size={22} />
          <h3>Made for your day</h3>
          <p>An hour or a month. Pick the package that fits.</p>
        </article>

        <article className="welcome-feature-card">
          <Smartphone size={22} />
          <h3>Pay in a moment</h3>
          <p>An easy, familiar M-Pesa experience.</p>
        </article>

        <article className="welcome-feature-card">
          <SlidersHorizontal size={22} />
          <h3>You're in control</h3>
          <p>Your data, your payments and your connections all in one place.</p>
        </article>
      </section>

      <NavLink to="/Dashboard" className="welcome-dashboard-link">
        Explore the dashboard <ArrowUpRight size={16} />
      </NavLink>
    </div>
  )
}
