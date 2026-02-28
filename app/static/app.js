let currentConversationId = null;
let currentDraftId = null;
let ws = null;

// --- WebSocket ---
function connectWS() {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(`${protocol}//${location.host}/ws`);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleWSEvent(data);
  };

  ws.onclose = () => {
    setTimeout(connectWS, 2000);
  };
}

function handleWSEvent(data) {
  if (data.type === "new_message") {
    // Update conversation list
    loadConversations();
    // If we're viewing this conversation, add the message
    if (data.conversation_id === currentConversationId) {
      appendMessage(data.message);
    }
  } else if (data.type === "draft_ready") {
    if (data.conversation_id === currentConversationId) {
      showDraft(data.draft);
    }
    // Update conversation list to show draft indicator
    loadConversations();
  } else if (data.type === "message_sent") {
    if (data.conversation_id === currentConversationId) {
      appendMessage(data.message);
    }
    loadConversations();
  }
}

// --- Conversations ---
async function loadConversations() {
  const res = await fetch("/conversations");
  const conversations = await res.json();
  renderConversationList(conversations);
}

function renderConversationList(conversations) {
  const list = document.getElementById("conversation-list");
  list.innerHTML = "";

  for (const conv of conversations) {
    const div = document.createElement("div");
    div.className = "conv-item" +
      (conv.id === currentConversationId ? " active" : "") +
      (conv.has_unread ? " unread" : "");
    div.onclick = () => openConversation(conv.id);

    const name = conv.contact_name || conv.phone_number;
    const preview = conv.last_message
      ? conv.last_message.substring(0, 50)
      : "";
    const time = conv.last_message_at
      ? formatTime(conv.last_message_at)
      : "";

    div.innerHTML = `
      <span class="conv-time">${time}</span>
      <div class="conv-name">${escapeHtml(name)}</div>
      <div class="conv-preview">${escapeHtml(preview)}</div>
    `;
    list.appendChild(div);
  }
}

// --- Chat ---
async function openConversation(id) {
  currentConversationId = id;
  currentDraftId = null;

  const res = await fetch(`/conversations/${id}`);
  const data = await res.json();

  // Show chat elements
  document.getElementById("main-empty").style.display = "none";
  document.getElementById("chat-header").style.display = "block";
  document.getElementById("messages").style.display = "flex";
  document.getElementById("messages").style.flexDirection = "column";
  document.getElementById("compose").style.display = "block";

  // Header
  const conv = data.conversation;
  document.getElementById("chat-header").textContent =
    conv.contact_name || conv.phone_number;

  // Messages
  const messagesEl = document.getElementById("messages");
  messagesEl.innerHTML = "";
  for (const msg of data.messages) {
    appendMessage(msg);
  }
  messagesEl.scrollTop = messagesEl.scrollHeight;

  // Draft
  const draftInput = document.getElementById("draft-input");
  const justEl = document.getElementById("justification");
  draftInput.value = "";
  justEl.style.display = "none";
  justEl.textContent = "";

  if (data.pending_draft) {
    showDraft(data.pending_draft);
  }

  // Update active state in list
  loadConversations();
}

function appendMessage(msg) {
  const messagesEl = document.getElementById("messages");
  const div = document.createElement("div");
  div.className = `msg ${msg.direction}`;
  div.textContent = msg.content;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function showDraft(draft) {
  const draftInput = document.getElementById("draft-input");
  const justEl = document.getElementById("justification");

  // Only populate if textarea is empty (don't overwrite user typing)
  if (!draftInput.value.trim()) {
    draftInput.value = draft.draft_text;
    currentDraftId = draft.id;
  }

  if (draft.justification) {
    justEl.textContent = `IA: ${draft.justification}`;
    justEl.style.display = "block";
  }
}

// --- Send ---
async function sendMessage() {
  const input = document.getElementById("draft-input");
  const text = input.value.trim();
  if (!text || !currentConversationId) return;

  const btn = document.getElementById("send-btn");
  btn.disabled = true;

  try {
    const body = { text };
    if (currentDraftId) {
      body.draft_id = currentDraftId;
    }

    const res = await fetch(`/conversations/${currentConversationId}/send`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const err = await res.json();
      alert(`Erro ao enviar: ${err.detail || "erro desconhecido"}`);
      return;
    }

    input.value = "";
    currentDraftId = null;
    document.getElementById("justification").style.display = "none";
  } finally {
    btn.disabled = false;
  }
}

// --- Utils ---
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function formatTime(dateStr) {
  const date = new Date(dateStr);
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();

  if (isToday) {
    return date.toLocaleTimeString("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
    });
  }
  return date.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
  });
}

// --- Init ---
document.getElementById("send-btn").onclick = sendMessage;
document.getElementById("draft-input").onkeydown = (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
};

loadConversations();
connectWS();
