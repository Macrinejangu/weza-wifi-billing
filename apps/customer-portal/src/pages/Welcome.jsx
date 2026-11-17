import { Link } from 'react-router-dom'
import { demoDataEnabled } from '../../../shared/demoMode.js'
import {
  ArrowRight,
  Clock3,
  SlidersHorizontal,
  Smartphone,
  Wifi,
} from 'lucide-react'

export default function Welcome() {
  return (
    <div className="public-welcome">
      <header className="public-header">
        <div className="public-header-inner">
          <Link to="/" className="public-brand">
            <span className="public-brand-icon">
              <Wifi size={20} aria-hidden="true" />
            </span>
            <span>
              <strong>Weza Wi-Fi</strong>
              <small>Public network</small>
            </span>
          </Link>

          <nav className="public-nav" aria-label="Public navigation">
            <Link to="/packages">Packages</Link>
            <Link to="/login">Sign in</Link>
            <Link to="/packages" className="public-button">
              Get connected
            </Link>
          </nav>
        </div>
      </header>

      <main className="public-content">
        <section className="public-hero">
          <h1>Your Internet. Your Way.</h1>
          <p>
            Find a Wi-Fi package for a quick connection or a few days online.
            Compare prices, data allowances, and durations before choosing.
          </p>

          <div className="public-actions">
            <Link to="/packages" className="public-button">
              Choose package <ArrowRight size={17} aria-hidden="true" />
            </Link>
            <Link to="/login" className="public-button public-button-secondary">
              Sign in
            </Link>
          </div>
        </section>

        <section className="welcome-feature-grid" aria-label="How Weza works">
          <article className="welcome-feature-card">
            <Clock3 size={22} aria-hidden="true" />
            <h2>Made for your day</h2>
            <p>
              Compare plans by price, data, and duration. Pick a short pass for
              today or a longer plan for regular use.
            </p>
          </article>

          <article className="welcome-feature-card">
            <Smartphone size={22} aria-hidden="true" />
            <h2>Pay in a moment</h2>
            <p>
              Browse packages before signing in.{' '}
              {demoDataEnabled
                ? 'Preview M-Pesa checkout to see how payment works.'
                : 'M-Pesa checkout is currently unavailable.'}
            </p>
          </article>

          <article className="welcome-feature-card">
            <SlidersHorizontal size={22} aria-hidden="true" />
            <h2>You’re in control</h2>
            <p>
              See how much data you have left and when your plan expires.
              Find past payments in your account.
            </p>
          </article>
        </section>
      </main>

      <footer className="public-footer">
        <span>Weza Wi-Fi</span>
        <Link to="/support">Help &amp; Support</Link>
      </footer>
    </div>
  )
}