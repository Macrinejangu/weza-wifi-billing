import { MessageCircle, Send, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { askWezaAssist } from '../services/api.js'

const contact = [
  { label: 'Email', href: 'mailto:support@wezawifi.co.ke' },
  { label: 'Call', href: 'tel:+254710268735' },
  { label: 'WhatsApp', href: 'https://wa.me/254710268735' },
]
const fallback = {
  answer: 'I don’t have a reliable answer for that. Please contact Weza Support for help.',
  sources: [],
  handoff: true,
}

export default function WezaAssist() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [waiting, setWaiting] = useState(false)
  const launcher = useRef(null)
  const composer = useRef(null)
  const bottom = useRef(null)

  useEffect(() => {
    if (open) composer.current?.focus({ preventScroll: true })
  }, [open])
  useEffect(() => {
    if (open) bottom.current?.scrollIntoView?.({ block: 'nearest' })
  }, [messages, open, waiting])

  function close() {
    setOpen(false)
    launcher.current?.focus({ preventScroll: true })
  }

  async function submit(event) {
    event.preventDefault()
    const text = draft.trim()
    if (!text || waiting) return
    const history = [...messages, { role: 'user', text }]
    setMessages(history)
    setDraft('')
    setWaiting(true)
    let result
    try {
      result = await askWezaAssist(history.slice(-7).map(({ role, text }) => ({ role, text })))
    } catch {
      result = fallback
    } finally {
      setWaiting(false)
    }
    setMessages([...history, { role: 'assistant', text: result.answer, sources: result.sources, handoff: result.handoff }])
  }

  return (
    <aside className="fixed right-4 bottom-[max(1rem,env(safe-area-inset-bottom))] z-50" aria-label="Weza Assist">
      {open && (
        <section
          id="weza-assist-panel"
          aria-labelledby="weza-assist-title"
          className="absolute right-0 bottom-16 flex max-h-[min(36rem,calc(100dvh-6rem))] w-[min(22.5rem,calc(100vw-2rem))] flex-col overflow-hidden rounded-2xl border border-[#edece8] bg-white shadow-xl"
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              event.stopPropagation()
              close()
            }
          }}
        >
          <header className="flex items-center justify-between bg-[#3b1d5a] px-4 py-3 text-white">
            <h2 id="weza-assist-title" className="font-bold">Weza Assist</h2>
            <button type="button" onClick={close} aria-label="Close Weza Assist" className="grid min-h-9 min-w-9 place-items-center rounded-full hover:bg-white/20">
              <X size={20} aria-hidden="true" />
            </button>
          </header>
          <div role="log" aria-label="Chat messages" className="min-h-20 flex-1 space-y-3 overflow-y-auto p-4 text-sm">
            <p className="rounded-xl bg-[#f4f3f0] p-3">Hi, I’m Weza Assist. Ask me about packages, payments or getting online. Keep passwords, PINs and payment codes private.</p>
            {messages.map((message, index) => (
              <div key={index} className={message.role === 'user' ? 'ml-8 rounded-xl bg-[#ece7fa] p-3' : 'mr-4 rounded-xl bg-[#f4f3f0] p-3'}>
                <p className="break-words whitespace-pre-wrap">{message.text}</p>
                {!!message.sources?.length && (
                  <ul className="mt-2 space-y-1 text-xs">
                    {message.sources.map(({ title, url }, sourceIndex) => (
                      <li key={sourceIndex}>
                        {url ? <a className="underline" href={url} target="_blank" rel="noreferrer">{title}</a> : title}
                      </li>
                    ))}
                  </ul>
                )}
                {message.handoff && (
                  <div className="mt-2 flex flex-wrap gap-x-3 gap-y-2">
                    {contact.map(({ href, label }) => <a className="font-semibold underline" key={href} href={href} target={label === 'WhatsApp' ? '_blank' : undefined} rel="noreferrer">{label} support</a>)}
                  </div>
                )}
              </div>
            ))}
            {waiting && <p role="status">Checking the help sources…</p>}
            <div ref={bottom} />
          </div>
          <form onSubmit={submit} className="flex gap-2 border-t border-[#edece8] p-3">
            <input
              value={draft} onChange={(event) => setDraft(event.target.value)} maxLength={700}
              ref={composer} aria-label="Ask Weza Assist" placeholder="Type your question"
              className="min-w-0 flex-1 rounded-xl border border-[#726b91] px-3 text-base"
            />
            <button type="submit" aria-label="Send message" disabled={waiting || !draft.trim()}
              className="grid min-h-11 min-w-11 place-items-center rounded-xl bg-[#3b1d5a] text-white disabled:opacity-45">
              <Send size={18} aria-hidden="true" />
            </button>
          </form>
        </section>
      )}
      <button
        type="button" ref={launcher} aria-expanded={open} aria-controls={open ? 'weza-assist-panel' : undefined}
        aria-label={open ? 'Close Weza Assist chat' : 'Open Weza Assist chat'} onClick={() => open ? close() : setOpen(true)}
        className="flex min-h-12 items-center gap-2 rounded-full bg-[#3b1d5a] px-4 py-3 font-semibold text-white shadow-lg focus-visible:outline-2 focus-visible:outline-offset-2"
      >
        {open ? <X size={20} aria-hidden="true" /> : <MessageCircle size={20} aria-hidden="true" />}
        <span>Weza Assist</span>
      </button>
    </aside>
  )
}
