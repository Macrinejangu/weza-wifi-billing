

import { useState } from 'react'
import {
  Smartphone,
  ArrowUpRight,
  Receipt,
  CheckCircle2
} from 'lucide-react'

const recentPayments = [
  {
    reference: 'WEZA001',
    date: '10 Nov 2026',
    method: 'M-Pesa',
    amount: 250,
    status: 'Successful'
  },
  {
    reference: 'WEZA002',
    date: '05 Nov 2026',
    method: 'M-Pesa',
    amount: 50,
    status: 'Successful'
  }
]

export default function Payments() {
  const [phone, setPhone] = useState('')
  const [amount, setAmount] = useState('')
  const [message, setMessage] = useState('')

  function handlePayment(event) {
    event.preventDefault()

    if (!phone || !amount) {
      setMessage('Please enter your phone number and amount.')
      return
    }

    setMessage(
      'Your details are ready. M-Pesa payment processing will be connected through the backend.'
    )
  }

  return (
    <div className="page-content">
      <div className="page-heading">
        <p className="hero-eyebrow">PAYMENTS.INSTANT HOTSPOT ACCESS</p>
        <h1>More connection is a tap away</h1>
        <p>Manage your payments and keep your connection active.</p>
      </div>

      <div className="payment-layout">

        <section className="payment-card">
          <div className="payment-title">
            <div className="payment-icon">
              <Smartphone size={23} />
            </div>

            <div>
              <h2>Pay with M-Pesa</h2>
              <p>Enter your details to make a payment.</p>
            </div>
          </div>

          <form onSubmit={handlePayment}>
            <label htmlFor="phone">M-Pesa phone number</label>

            <input
              id="phone"
              type="tel"
              placeholder="07XXXXXXXX"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              required
            />

            <label htmlFor="amount">Amount (KSh)</label>

            <input
              id="amount"
              type="number"
              placeholder="Enter amount"
              min="1"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              required
            />

            <button type="submit" className="package-button">
              Continue <ArrowUpRight size={17} />
            </button>
          </form>

          {message && (
            <p className="payment-message" role="status">
              {message}
            </p>
          )}
        </section>

        <section className="payment-info-card">
          <div className="payment-icon">
            <Receipt size={23} />
          </div>

          <h2>Payment information</h2>
          <p>
            Your payments will be processed securely through
            M-Pesa once the payment integration is connected.
          </p>

          <div className="payment-note">
            <CheckCircle2 size={18} />
            <span>M-Pesa payment option</span>
          </div>
        </section>

      </div>

      <section className="recent-payments">
        <div className="section-heading">
          <div>
            <h2>Recent payments</h2>
            <p>Review your previous transactions.</p>
          </div>
        </div>

        {recentPayments.map((payment) => (
          <div className="transaction-row" key={payment.reference}>
            <div className="transaction-icon">
              <Receipt size={19} />
            </div>

            <div className="transaction-details">
              <strong>{payment.reference}</strong>
              <p>{payment.date} · {payment.method}</p>
            </div>

            <div className="transaction-amount">
              <strong>
                KSh {payment.amount.toLocaleString()}
              </strong>
              <span>{payment.status}</span>
            </div>
          </div>
        ))}
      </section>
    </div>
  )
}
