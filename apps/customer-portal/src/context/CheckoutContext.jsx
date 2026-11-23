

import { createContext, useContext, useState } from 'react'

const CheckoutContext = createContext()

export function CheckoutProvider({ children }) {
  const [selectedPackage, setSelectedPackage] = useState(null)
  const [phoneNumber, setPhoneNumber] = useState('')
  const [transaction, setTransaction] = useState(null)

  const [paymentStatus, setPaymentStatus] = useState('not_started')
  const [activationStatus, setActivationStatus] = useState('not_started')

  function startCheckout(packageData) {
    setSelectedPackage(packageData)
    setPhoneNumber('')
    setTransaction(null)
    setPaymentStatus('not_started')
    setActivationStatus('not_started')
  }

  function setPaymentPending(transactionData) {
    setTransaction(transactionData)
    setPaymentStatus('pending')
    setActivationStatus('not_started')
  }

  function confirmPayment(transactionData) {
    setTransaction(transactionData)
    setPaymentStatus('successful')
    setActivationStatus('activating')
  }

  function failPayment(transactionData) {
    setTransaction(transactionData)
    setPaymentStatus('failed')
    setActivationStatus('not_started')
  }

  function updateActivationStatus(status) {
    setActivationStatus(status)
  }

  function clearCheckout() {
    setSelectedPackage(null)
    setPhoneNumber('')
    setTransaction(null)
    setPaymentStatus('not_started')
    setActivationStatus('not_started')
  }

  const value = {
    selectedPackage,
    setSelectedPackage,
    phoneNumber,
    setPhoneNumber,
    transaction,
    paymentStatus,
    activationStatus,
    startCheckout,
    setPaymentPending,
    confirmPayment,
    failPayment,
    updateActivationStatus,
    clearCheckout
  }

  return (
    <CheckoutContext.Provider value={value}>
      {children}
    </CheckoutContext.Provider>
  )
}

export function useCheckout() {
  const context = useContext(CheckoutContext)

  if (!context) {
    throw new Error('useCheckout must be used inside CheckoutProvider')
  }

  return context
}
