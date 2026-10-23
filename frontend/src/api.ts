// These types describe the JSON our FastAPI routes return; they do not validate it at runtime.
export type Conversation = { conversation_id: string; title: string; last_message_id: number }
export type Message = { id: number; role: string; content: string }
export type ChatReply = {
  conversation_id: string
  assistant: string
  user_message_id: number
  assistant_message_id: number
}

async function readJson<T>(response: Response): Promise<T> {
  // fetch resolves even for HTTP errors, so check the status after parsing the body.
  const body = await response.json()
  if (!response.ok) throw new Error(body.detail ?? `HTTP ${response.status}`)
  return body as T
}

export async function listConversations(): Promise<Conversation[]> {
  return readJson<Conversation[]>(await fetch('/conversations'))
}

export async function loadMessages(conversationId: string): Promise<Message[]> {
  // encodeURIComponent keeps a returned ID inside this single URL path segment.
  const path = `/conversations/${encodeURIComponent(conversationId)}/messages`
  return readJson<Message[]>(await fetch(path))
}

export async function sendChat(message: string, conversationId: string | null): Promise<ChatReply> {
  // JSON.stringify turns this browser object into the HTTP request body FastAPI receives.
  const body = { message, ...(conversationId ? { conversation_id: conversationId } : {}) }
  return readJson<ChatReply>(await fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }))
}
