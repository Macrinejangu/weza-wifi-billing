import { ArrowLeft, ChevronDown, CircleHelp, CreditCard, PackageX, Smartphone, UserRound, Wifi } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

const faqs = [
  {
    question: 'Payment received but no internet?',
    icon: CreditCard,
    steps: [
      'Check for the official M-Pesa confirmation message.',
      'Reconnect to the Weza Wi-Fi network and check your connection status.',
      'If you already paid, keep your receipt reference and avoid paying again.',
    ],
  },
  {
    question: 'Didn’t receive the M-Pesa prompt?',
    icon: Smartphone,
    steps: [
      'Check the phone number you entered at checkout.',
      'Check for an open M-Pesa prompt on the phone.',
      'Check the status of the first payment before trying again.',
    ],
  },
  {
    question: 'Package expired?',
    icon: PackageX,
    steps: [
      'Check the package balance or expiry shown in the portal.',
      'Return to Packages to choose another plan.',
    ],
  },
  {
    question: 'Account access problems?',
    icon: UserRound,
    steps: [
      'Check the email address and password you entered.',
      'If you lose access while on the hotspot, reconnect to Weza Wi-Fi and reopen the portal.',
    ],
  },
]

export default function Support() {
  const [active, setActive] = useState(null)

  return (
    <>
      <header className="public-header">
        <div className="public-header-inner">
          <Link to="/" className="public-brand">
            <span className="public-brand-icon"><Wifi size={20} aria-hidden="true" /></span>
            <strong>Weza Wi-Fi</strong>
          </Link>
          <span aria-current="page" className="public-button">Support</span>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6 sm:py-12">
        <header className="mb-8 text-center">
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Help &amp; Support</h1>
          <p className="mt-2 text-sm leading-6 text-[#655f75] sm:text-base">
            Find answers to common connection and payment questions.
          </p>
        </header>

        <section aria-labelledby="support-faqs">
          <h2 id="support-faqs" className="mb-3 text-sm font-semibold">Frequently asked questions</h2>
          <div className="space-y-3">
            {faqs.map(({ question, icon: Icon, steps }, index) => {
              const isOpen = active === index

              return (
                <article className="rounded-xl border border-[#edece8] bg-white" key={question}>
                  <h3>
                    <button
                      type="button"
                      className="flex min-h-14 w-full items-center gap-3 rounded-xl p-3 text-left font-semibold sm:p-4"
                      aria-expanded={isOpen}
                      aria-controls={`faq-answer-${index}`}
                      onClick={() => setActive(isOpen ? null : index)}
                    >
                      <span className="rounded-lg bg-[#ece7fa] p-2 text-[#585172]"><Icon size={18} aria-hidden="true" /></span>
                      <span className="flex-1">{question}</span>
                      <ChevronDown size={18} className={isOpen ? 'shrink-0 rotate-180' : 'shrink-0'} aria-hidden="true" />
                    </button>
                  </h3>
                  <div id={`faq-answer-${index}`} hidden={!isOpen} className="px-3 pb-3 sm:px-4 sm:pb-4">
                    <ul className="list-disc space-y-1 rounded-lg bg-[#f4f3f0] py-3 pl-8 pr-3 text-sm leading-6 text-[#454052]">
                      {steps.map((step) => <li key={step}>{step}</li>)}
                    </ul>
                  </div>
                </article>
              )
            })}
          </div>
        </section>

        <section className="mt-6 flex items-start gap-3 rounded-xl border border-[#edece8] bg-white p-4">
          <span className="rounded-lg bg-[#d9e52e] p-2"><CircleHelp size={19} aria-hidden="true" /></span>
          <div>
            <h2 className="font-bold">Contact support</h2>
            <p className="mt-1 text-sm text-[#655f75]">Support contact details are awaiting confirmation.</p>
          </div>
        </section>

        <div className="mt-6 text-center">
          <Link to="/" className="public-button"><ArrowLeft size={16} aria-hidden="true" /> Back to portal home</Link>
        </div>
      </main>
    </>
  )
}
