
import { useState } from 'react'
import { useLocation, useNavigate, Link } from 'react-router-dom'
import { Wifi, Smartphone, ArrowLeft, ArrowRight, ShieldCheck } from 'lucide-react'

export default function ConfirmPackage() {
  const location = useLocation()
  const navigate = useNavigate()

  const selectedPackage = location.state?.selectedPackage

  const [phone, setPhone] = useState('')
  const [message, setMessage] = useState('')

  if (!selectedPackage) {
    return (
      <div className="page-content">
        <h1>No package selected</h1>
        <p>Please choose an internet package first.</p>
        <Link to="/packages" className="package-button">
          Browse packages
        </Link>
      </div>
    )
  }

  function handlePayment(event) {
    event.preventDefault()

    if (!/^(\+254|254|0)7\d{8}$/.test(phone.trim())) {
      setMessage('Please enter a valid Kenyan mobile number.')
      return
    }

    // Payment integration will be connected to the backend.
    setMessage('Your package is ready. M-Pesa integration is the next step.')
  }

  return (
    <div className="page-content">

      <div className="page-heading">
        <p className="hero-eyebrow">PACKAGE CHECKOUT</p>
        <h1>Confirm your package</h1>
        <p>Review your selection before proceeding with payment.</p>
      </div>

      <div className="payment-layout">

        {/* Package summary */}
        <section className="payment-card">
          <div className="payment-title">
            <div className="payment-icon">
              <Wifi size={23} />
            </div>
            <div>
              <h2>{selectedPackage.name} Package</h2>
              <p>{selectedPackage.description}</p>
            </div>
          </div>

          <div className="package-detail">
            <span>Data allowance</span>
            <strong>{selectedPackage.data}</strong>
          </div>

          <div className="package-detail">
            <span>Validity</span>
            <strong>{selectedPackage.duration}</strong>
          </div>

          <div className="package-detail">
            <span>Payment method</span>
            <strong>M-Pesa</strong>
          </div>

          <div className="package-price">
            <h3>KSh {selectedPackage.price.toLocaleString()}</h3>
            <span>Total amount</span>
          </div>
        </section>

        {/* Payment details */}
        <section className="payment-card">
          <div className="payment-title">
            <div className="payment-icon">
              <Smartphone size={23} />
            </div>
            <div>
              <h2>M-Pesa payment</h2>
              <p>Enter the number to receive your payment prompt.</p>
            </div>
          </div>

          <form onSubmit={handlePayment}>
            <label htmlFor="phone">M-Pesa phone number</label>
            <input
              id="phone"
              type="tel"
              placeholder="07XXXXXXXX"
              value={phone}
              onChange={(event) => {
                setPhone(event.target.value)
                setMessage('')
              }}
              required
            />

            <button type="submit" className="package-button">
              Confirm and Pay <ArrowRight size={17} />
            </button>
          </form>

          {message && (
            <p className="payment-message" role="status">
              {message}
            </p>
          )}

          <div className="payment-note">
            <ShieldCheck size={18} />
            <span>Secure M-Pesa payment</span>
          </div>
        </section>

      </div>

      <button
        onClick={() => navigate('/packages')}
        className="mt-5 flex items-center gap-2 text-sm font-semibold text-[#77709D]"
      >
        <ArrowLeft size={16} />
        Back to packages
      </button>

    </div>
  )
}
