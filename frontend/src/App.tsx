import { useEffect, useState, type FormEvent, type KeyboardEvent } from 'react'
import { listConversations, loadMessages, sendChat, type Conversation, type Message } from './api'

const activeKey = 'qwen-harness-active-conversation'

export default function App() {
  // React redraws the page when a setter changes one of these state values.
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    async function restore() {
      try {
        const saved = await listConversations()
        if (cancelled) return
        setConversations(saved)
        // localStorage remembers only the selected ID; SQLite holds the messages.
        const remembered = localStorage.getItem(activeKey)
        if (remembered && saved.some(item => item.conversation_id === remembered)) {
          const rows = await loadMessages(remembered)
          if (!cancelled) {
            setConversationId(remembered)
            setMessages(rows)
          }
        }
      } catch (cause) {
        if (!cancelled) setError(errorText(cause))
      }
    }
    void restore()
    // Ignore an old request if React reruns the effect or this page unmounts.
    return () => { cancelled = true }
  }, [])

  async function openConversation(id: string) {
    if (busy) return
    try {
      const rows = await loadMessages(id)
      setConversationId(id)
      setMessages(rows)
      localStorage.setItem(activeKey, id)
      setError('')
    } catch (cause) {
      setError(errorText(cause))
    }
  }

  function newChat() {
    if (busy) return
    setConversationId(null)
    setMessages([])
    localStorage.removeItem(activeKey)
    setError('')
  }

  async function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const text = draft.trim()
    if (!text || busy) return
    setBusy(true)
    setError('')
    let saved = false
    try {
      // The POST returns the new/reused conversation ID after SQLite commits both rows.
      const reply = await sendChat(text, conversationId)
      saved = true
      setConversationId(reply.conversation_id)
      localStorage.setItem(activeKey, reply.conversation_id)
      setDraft('')
      // Read the saved rows back so the screen shows what SQLite actually contains.
      const [rows, items] = await Promise.all([
        loadMessages(reply.conversation_id), listConversations(),
      ])
      setMessages(rows)
      setConversations(items)
    } catch (cause) {
      setError(saved ? `Reply saved, but reloading it failed: ${errorText(cause)}` : errorText(cause))
    } finally {
      setBusy(false)
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      event.currentTarget.form?.requestSubmit()
    }
  }

  const selected = conversations.find(item => item.conversation_id === conversationId)

  return (
    <div className="min-h-screen bg-[#0b1119] text-slate-100">
      <header className="flex items-center justify-between gap-4 border-b border-slate-800 px-5 py-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-emerald-300">DGX Spark · local chat</p>
          <h1 className="text-xl font-semibold">Qwen harness</h1>
        </div>
        <a href="/flow" target="_blank" rel="noreferrer" className="text-sm text-emerald-300 hover:underline">See request flow ↗</a>
      </header>

      <div className="grid min-h-[calc(100vh-77px)] md:grid-cols-[260px_minmax(0,1fr)]">
        <aside className="border-b border-slate-800 bg-slate-900/50 p-4 md:border-b-0 md:border-r">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="font-semibold">Conversations</h2>
            <button type="button" onClick={newChat} disabled={busy} className="rounded-lg bg-emerald-200 px-3 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50">+ New</button>
          </div>
          <nav aria-label="Saved conversations" className="flex gap-2 overflow-x-auto md:flex-col">
            {conversations.map(item => (
              <button key={item.conversation_id} type="button" disabled={busy} onClick={() => void openConversation(item.conversation_id)}
                className={`min-w-40 rounded-lg p-3 text-left text-sm hover:bg-slate-800 disabled:opacity-50 md:min-w-0 ${item.conversation_id === conversationId ? 'bg-slate-700' : 'bg-slate-800/50'}`}>
                <span className="block truncate">{item.title}</span>
                <span className="block text-xs text-slate-400">Last saved row {item.last_message_id}</span>
              </button>
            ))}
          </nav>
          <p className="mt-5 text-xs leading-relaxed text-slate-400">The browser remembers the selected ID. SQLite stores the chat.</p>
        </aside>

        <main className="flex min-h-[70vh] min-w-0 flex-col">
          <div className="border-b border-slate-800 px-5 py-4">
            <h2 className="truncate font-semibold">{selected?.title ?? 'New chat'}</h2>
            <p className="break-all font-mono text-xs text-slate-400">{conversationId ? `Conversation ID: ${conversationId}` : 'ID assigned after the first reply'}</p>
          </div>

          <div className="flex flex-1 flex-col gap-5 p-5" aria-live="polite">
            {messages.length === 0 && <p className="m-auto max-w-md text-center text-sm leading-relaxed text-slate-400">Send a message. FastAPI reads saved history, calls vLLM, then stores both sides of a successful turn in SQLite.</p>}
            {messages.map(row => (
              <article key={row.id} className={`max-w-[85%] ${row.role === 'user' ? 'self-end' : 'self-start'}`}>
                <p className="mb-1 text-xs text-slate-400">{row.role === 'user' ? 'You' : 'Qwen'} · SQLite row {row.id}</p>
                <div className={`whitespace-pre-wrap break-words rounded-xl border px-4 py-3 text-sm leading-relaxed ${row.role === 'user' ? 'border-emerald-700 bg-emerald-950' : 'border-slate-700 bg-slate-800'}`}>{row.content}</div>
              </article>
            ))}
          </div>

          <div className="border-t border-slate-800 p-5">
            {error && <p role="alert" className="mb-3 rounded-lg border border-red-800 bg-red-950 p-3 text-sm text-red-200">{error}</p>}
            <form onSubmit={event => void handleSend(event)} className="flex items-end gap-3 rounded-xl border border-slate-700 bg-slate-800 p-2">
              <label htmlFor="message" className="sr-only">Message</label>
              <textarea id="message" rows={2} value={draft} onChange={event => setDraft(event.target.value)} onKeyDown={handleKeyDown} placeholder="Ask the local model…" className="min-w-0 flex-1 resize-y bg-transparent p-2 text-sm outline-none placeholder:text-slate-400" />
              <button type="submit" disabled={busy || !draft.trim()} className="rounded-lg bg-emerald-200 px-4 py-3 text-sm font-semibold text-slate-950 disabled:opacity-50">{busy ? 'Waiting…' : 'Send'}</button>
            </form>
            <p className="mt-2 text-xs text-slate-400">Enter sends · Shift+Enter adds a line · Failed sends keep your draft</p>
          </div>
        </main>
      </div>
    </div>
  )
}

function errorText(cause: unknown): string {
  return cause instanceof Error ? cause.message : 'Request failed'
}
