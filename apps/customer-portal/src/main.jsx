

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import './App.css'
import { CheckoutProvider } from './context/CheckoutContext.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <CheckoutProvider>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </CheckoutProvider>
  </StrictMode>,
)
