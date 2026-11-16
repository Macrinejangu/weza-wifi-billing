

import { useState } from 'react'
import { Wifi, ArrowRight, Check } from 'lucide-react'

const packages = [
  {
    name: 'Daily',
    price: 50,
    duration: '24 hours',
    data: '5 GB',
    description: 'For everyday browsing'
  },
  {
    name: 'Weekly',
    price: 250,
    duration: '7 days',
    data: '20 GB',
    description: 'Stay connected all week'
  },
  {
    name: 'Monthly',
    price: 800,
    duration: '30 days',
    data: '80 GB',
    description: 'For regular internet users',
    popular: true
  },
  {
    name: 'Unlimited',
    price: 1500,
    duration: '30 days',
    data: 'Unlimited',
    description: 'Enjoy uninterrupted browsing'
  }
]

export default function Packages() {
  const [selectedPackage, setSelectedPackage] = useState(null)

  return (
    <div className="page-content">
      <div className="page-heading">
        <p className="hero-eyebrow">INTERNET PACKAGES</p>
        <h1>Find your perfect connection.</h1>
        <p>Choose an internet package that works for you.</p>
      </div>

      <div className="packages-grid">
        {packages.map((item) => (
          <div className="package-card" key={item.name}>
            {item.popular && (
              <span className="package-badge">POPULAR</span>
            )}

            <div className="package-icon">
              <Wifi size={22} />
            </div>

            <h2>{item.name}</h2>
            <p>{item.description}</p>

            <div className="package-price">
              <h3>KSh {item.price.toLocaleString()}</h3>
              <span>/ {item.duration}</span>
            </div>

            <div className="package-detail">
              <span>Data allowance</span>
              <strong>{item.data}</strong>
            </div>

            <div className="package-detail">
              <span>Validity</span>
              <strong>{item.duration}</strong>
            </div>

            <button
              className="package-button"
              onClick={() => setSelectedPackage(item)}
            >
              {selectedPackage?.name === item.name
                ? 'Selected'
                : 'Choose package'}

              {selectedPackage?.name === item.name
                ? <Check size={17} />
                : <ArrowRight size={17} />}
            </button>
          </div>
        ))}
      </div>

      {selectedPackage && (
        <div className="selection-message">
          <p>
            You selected the <strong>{selectedPackage.name}</strong> package
            for <strong>KSh {selectedPackage.price.toLocaleString()}</strong>.
          </p>
          <p>
            Package purchasing will be connected to the payment system
            during backend integration.
          </p>
        </div>
      )}
    </div>
  )
}
