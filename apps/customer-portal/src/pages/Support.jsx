



import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Wifi, UserCircle, CreditCard, Smartphone,
  PackageX, UserRound, ChevronDown,
  Headset, CircleHelp, ArrowLeft, Info
} from 'lucide-react'

const faqs = [
  {
    question: 'Payment received but no internet?',
    icon: CreditCard,
    answer: 'Your payment may have been received while your connection is being activated. Wait a little, then check your connection status. Contact support if the problem continues.'
  },
  {
    question: "Didn't receive M-Pesa STK prompt?",
    icon: Smartphone,
    answer: 'Check your phone number, network connection and M-Pesa availability. You can then retry your payment.'
  },
  {
    question: 'Package expired?',
    icon: PackageX,
    answer: 'Your package may have reached its expiry date. Visit the Packages page to choose and purchase another package.'
  },
  {
    question: 'Account access problems?',
    icon: UserRound,
    answer: 'Check your login details. If you still cannot access your account, contact the support team for assistance.'
  }
]

export default function Support() {
  const [active, setActive] = useState(null)

  return (
    <div className="min-h-screen bg-[#F7F6F2] text-[#17152D]">

      {/* Navigation */}
      <nav className="border-b border-[#EEEAF3] bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">

          <div className="flex items-center gap-5">
            <Link to="/" className="flex items-center gap-2">
              <div className="rounded-lg bg-[#77709D] p-2 text-white">
                <Wifi size={19} />
              </div>
              <div>
                <p className="text-sm font-bold">Weza Wi-Fi</p>
                <p className="text-[9px] tracking-wider">CUSTOMER PORTAL</p>
              </div>
            </Link>

            <div className="hidden items-center gap-2 rounded-full bg-[#F7F6F2] px-3 py-2 text-xs sm:flex">
              <span className="h-2 w-2 rounded-full bg-[#D9E52E]" />
              Connected to Weza Wi-Fi
            </div>
          </div>

          <div className="flex items-center gap-5 text-xs">
            <Link to="/" className="hover:text-[#77709D]">Home</Link>
            <span className="rounded-full bg-[#D9E52E] px-4 py-2 font-semibold">
              Support
            </span>
            <UserCircle size={22} className="text-[#77709D]" />
          </div>

        </div>
      </nav>

      {/* Main content */}
      <main className="mx-auto max-w-2xl px-5 py-8">

        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 rounded-full bg-[#EEECE8] px-4 py-2 text-xs">
            <ArrowLeft size={14} />
            Back to Portal Home
          </Link>

          <span className="flex items-center gap-2 rounded-full bg-white px-3 py-2 text-[10px] text-[#77709D]">
            <Info size={12} />
            Free Support Portal
          </span>
        </div>

        {/* Heading */}
        <header className="my-8 text-center">
          <span className="inline-block rounded-full bg-[#E9E3FF] px-3 py-1 text-[10px] font-semibold text-[#77709D]">
            ASSISTANCE CENTER
          </span>
          <h1 className="mt-3 text-3xl font-bold tracking-tight">
            Help &amp; Support
          </h1>
          <p className="mt-2 text-xs text-[#88849A]">
            Find quick answers to common connection and payment questions.
          </p>
        </header>

        {/* FAQs */}
        <div className="mb-3 flex justify-between text-[10px]">
          <span className="font-semibold tracking-wider text-[#77709D]">
            FREQUENTLY ASKED QUESTIONS
          </span>
          <span className="text-[#88849A]">4 topics</span>
        </div>

        <section className="space-y-3">
          {faqs.map((faq, index) => {
            const Icon = faq.icon
            const isOpen = active === index

            return (
              <div key={faq.question} className="overflow-hidden rounded-xl border border-[#EEEAF3] bg-white">
                <button
                  onClick={() => setActive(isOpen ? null : index)}
                  aria-expanded={isOpen}
                  className="flex w-full items-center justify-between gap-3 px-4 py-4 text-left"
                >
                  <span className="flex items-center gap-3">
                    <span className="rounded-lg bg-[#E9E3FF] p-2 text-[#77709D]">
                      <Icon size={17} />
                    </span>
                    <span className="text-sm font-semibold">{faq.question}</span>
                  </span>

                  <span className="rounded-full bg-[#F0EEF6] p-1.5 text-[#77709D]">
                    <ChevronDown size={14} className={isOpen ? 'rotate-180' : ''} />
                  </span>
                </button>

                {isOpen && (
                  <p className="border-t border-[#F0EEF6] px-5 py-4 pl-14 text-xs leading-6 text-[#88849A]">
                    {faq.answer}
                  </p>
                )}
              </div>
            )
          })}
        </section>

        {/* Contact message */}
        <section className="mt-5 flex items-center gap-4 rounded-xl border border-[#EEEAF3] bg-white p-4">
          <div className="rounded-lg bg-[#D9E52E] p-2.5">
            <CircleHelp size={19} />
          </div>
          <div>
            <h2 className="text-sm font-semibold">
              Still need a little help?
            </h2>
            <p className="mt-1 text-xs leading-5 text-[#88849A]">
              Our support team is here to help you stay connected.
              Official support channels and contact details will be published here.
            </p>
          </div>
        </section>

        {/* Back button */}
        <div className="mt-5 text-center">
          <Link to="/" className="inline-flex items-center gap-2 rounded-full bg-[#D9E52E] px-8 py-3 text-xs font-semibold hover:brightness-95">
            <ArrowLeft size={14} />
            Back to Portal Home
          </Link>
          <p className="mt-3 text-[10px] text-[#88849A]">
            Free portal navigation. You will not be charged data browsing this section.
          </p>
        </div>

      </main>

      {/* Footer */}
      <footer className="mt-5 border-t border-[#EEEAF3] bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5 text-[10px] text-[#88849A]">
          <span>© 2024 Weza Wi-Fi. Empowering Community Connectivity.</span>
          <span>WEZA Wi-Fi</span>
        </div>
      </footer>

    </div>
  )
}
