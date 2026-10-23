const activeKey = "qwen-harness-active-conversation";
const state = { conversationId: null, busy: false };

const list = document.getElementById("conversation-list");
const messages = document.getElementById("messages");
const title = document.getElementById("chat-title");
const idLabel = document.getElementById("conversation-id");
const input = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const errorBox = document.getElementById("error");

async function getJSON(path, options = {}) {
  const response = await fetch(path, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || `Request failed: ${response.status}`);
  return body;
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = !message;
}

function setBusy(busy) {
  state.busy = busy;
  sendButton.disabled = busy;
  sendButton.textContent = busy ? "Waiting for vLLM…" : "Send ↗";
}

function setStatus(id, label, value) {
  const element = document.getElementById(id);
  element.classList.toggle("ready", value === "ready");
  element.classList.toggle("unavailable", value !== "ready");
  element.replaceChildren(document.createTextNode(`${label} `));
  const bold = document.createElement("b");
  bold.textContent = value === "ready" ? "Ready" : "Unavailable";
  element.append(bold);
}

async function refreshHealth() {
  try {
    const health = await getJSON("/health");
    setStatus("api-status", "API", health.api);
    setStatus("database-status", "SQLite", health.database);
    setStatus("model-status", "vLLM", health.model);
  } catch {
    setStatus("api-status", "API", "unavailable");
    setStatus("database-status", "SQLite", "unavailable");
    setStatus("model-status", "vLLM", "unavailable");
  }
}

function renderMessages(rows) {
  messages.replaceChildren();
  if (rows.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.innerHTML = '<div class="empty-icon" aria-hidden="true">✦</div><h3>Start a local conversation</h3><p>Your message goes through FastAPI to vLLM. After a reply, both sides are saved in SQLite and appear here on refresh.</p>';
    messages.append(empty);
    return;
  }
  for (const row of rows) {
    const article = document.createElement("article");
    article.className = `message ${row.role}`;
    const label = document.createElement("div");
    label.className = "message-label";
    const speaker = document.createElement("span");
    speaker.textContent = row.role === "user" ? "You" : "Qwen";
    const rowId = document.createElement("span");
    rowId.textContent = `SQLite row ${row.id}`;
    label.append(speaker, rowId);
    const body = document.createElement("div");
    body.className = "message-body";
    body.textContent = row.content;
    article.append(label, body);
    messages.append(article);
  }
  messages.scrollTop = messages.scrollHeight;
}

function renderConversations(items) {
  list.replaceChildren();
  for (const item of items) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "conversation-button";
    button.classList.toggle("active", item.conversation_id === state.conversationId);
    const name = document.createElement("strong");
    name.textContent = item.title;
    const detail = document.createElement("small");
    detail.textContent = `Last saved row ${item.last_message_id}`;
    button.append(name, detail);
    button.addEventListener("click", () => openConversation(item.conversation_id));
    list.append(button);
  }
}

async function refreshConversations() {
  const items = await getJSON("/conversations");
  renderConversations(items);
  return items;
}

async function openConversation(conversationId) {
  try {
    const rows = await getJSON(`/conversations/${encodeURIComponent(conversationId)}/messages`);
    state.conversationId = conversationId;
    localStorage.setItem(activeKey, conversationId);
    idLabel.textContent = `ID ${conversationId}`;
    title.textContent = rows.find((row) => row.role === "user")?.content || "Conversation";
    renderMessages(rows);
    await refreshConversations();
    showError("");
  } catch (error) {
    showError(error.message);
  }
}

function newChat() {
  state.conversationId = null;
  localStorage.removeItem(activeKey);
  title.textContent = "New chat";
  idLabel.textContent = "ID assigned after first reply";
  document.getElementById("last-turn").textContent = "Send a message to see its saved row IDs.";
  renderMessages([]);
  showError("");
  refreshConversations().catch((error) => showError(error.message));
  input.focus();
}

document.getElementById("new-chat").addEventListener("click", newChat);
document.getElementById("chat-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message || state.busy) return;
  showError("");
  setBusy(true);
  const request = { message };
  if (state.conversationId) request.conversation_id = state.conversationId;
  try {
    const result = await getJSON("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    input.value = "";
    document.getElementById("last-turn").textContent =
      `Conversation ${result.conversation_id}. User row ${result.user_message_id}; assistant row ${result.assistant_message_id}.`;
    await openConversation(result.conversation_id);
    await refreshHealth();
  } catch (error) {
    showError(`${error.message}. Your message was not cleared; you can retry.`);
    await refreshHealth();
  } finally {
    setBusy(false);
    input.focus();
  }
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    document.getElementById("chat-form").requestSubmit();
  }
});

async function start() {
  renderMessages([]);
  await refreshHealth();
  try {
    const items = await refreshConversations();
    const remembered = localStorage.getItem(activeKey);
    if (remembered && items.some((item) => item.conversation_id === remembered)) {
      await openConversation(remembered);
    }
  } catch (error) {
    showError(error.message);
  }
}

start();
