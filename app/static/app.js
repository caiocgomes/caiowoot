let currentConversationId = null;
let currentDraftId = null;
let currentDraftGroupId = null;
let currentDrafts = [];
let selectedDraftIndex = null;
let regenerationCount = 0;
let attachedFile = null;
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
  console.log("WS event:", data.type, "conv:", data.conversation_id, "current:", currentConversationId);
  if (data.type === "new_message") {
    loadConversations();
    if (data.conversation_id === currentConversationId) {
      appendMessage(data.message);
    }
  } else if (data.type === "drafts_ready") {
    console.log("drafts_ready received, drafts count:", data.drafts?.length, "match:", data.conversation_id === currentConversationId);
    if (data.conversation_id === currentConversationId) {
      showDrafts(data.drafts, data.draft_group_id);
    }
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
    div.onclick = () => { openConversation(conv.id); closeSidebar(); };

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
  currentDraftGroupId = null;
  currentDrafts = [];
  selectedDraftIndex = null;
  regenerationCount = 0;
  attachedFile = null;

  const res = await fetch(`/conversations/${id}`);
  const data = await res.json();

  document.getElementById("main-empty").style.display = "none";
  document.getElementById("chat-header").style.display = "block";
  document.getElementById("messages").style.display = "flex";
  document.getElementById("messages").style.flexDirection = "column";
  document.getElementById("compose").style.display = "block";

  if (isMobile()) document.body.classList.add("mobile-chat-active");

  const conv = data.conversation;
  document.getElementById("chat-header-name").textContent =
    conv.contact_name || conv.phone_number;

  const messagesEl = document.getElementById("messages");
  messagesEl.innerHTML = "";
  for (const msg of data.messages) {
    appendMessage(msg);
  }
  messagesEl.scrollTop = messagesEl.scrollHeight;

  // Reset compose
  document.getElementById("draft-input").value = "";
  document.getElementById("justification").style.display = "none";
  document.getElementById("justification").textContent = "";
  document.getElementById("draft-cards-container").style.display = "none";
  document.getElementById("instruction-bar").style.display = "none";
  document.getElementById("attachment-bar").style.display = "none";

  if (data.pending_drafts && data.pending_drafts.length > 0) {
    showDrafts(data.pending_drafts, data.pending_drafts[0].draft_group_id);
  }

  loadConversations();
}

function appendMessage(msg) {
  const messagesEl = document.getElementById("messages");
  const div = document.createElement("div");
  div.className = `msg ${msg.direction}`;
  div.textContent = msg.content;
  if (msg.media_type) {
    const badge = document.createElement("div");
    badge.style.cssText = "font-size:11px;color:#888;margin-top:4px;";
    badge.textContent = `[${msg.media_type === "image" ? "Imagem" : "Documento"} anexado]`;
    div.appendChild(badge);
  }
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// --- Draft Variations ---
function showDrafts(drafts, groupId) {
  currentDrafts = drafts;
  currentDraftGroupId = groupId;
  selectedDraftIndex = null;
  currentDraftId = null;

  const container = document.getElementById("draft-cards-container");
  const cardsEl = document.getElementById("draft-cards");
  cardsEl.innerHTML = "";

  const labels = ["Direta", "Consultiva", "Casual"];

  for (let i = 0; i < drafts.length; i++) {
    const draft = drafts[i];
    const card = document.createElement("div");
    card.className = "draft-card";
    card.dataset.index = i;

    const header = document.createElement("div");
    header.className = "draft-card-header";

    const label = document.createElement("span");
    label.className = "draft-card-label";
    label.textContent = draft.approach || labels[i] || `Opção ${i + 1}`;

    const actions = document.createElement("div");
    actions.className = "draft-card-actions";

    const selectBtn = document.createElement("button");
    selectBtn.title = "Usar esta resposta";
    selectBtn.textContent = "\u2713";
    selectBtn.onclick = (e) => { e.stopPropagation(); selectDraft(i); };

    const regenBtn = document.createElement("button");
    regenBtn.title = "Regenerar esta";
    regenBtn.textContent = "\uD83D\uDD04";
    regenBtn.onclick = (e) => { e.stopPropagation(); regenerateDraft(i); };

    actions.appendChild(selectBtn);
    actions.appendChild(regenBtn);
    header.appendChild(label);
    header.appendChild(actions);

    const text = document.createElement("div");
    text.className = "draft-card-text";
    text.textContent = draft.draft_text;

    card.appendChild(header);
    card.appendChild(text);
    card.onclick = () => selectDraft(i);
    cardsEl.appendChild(card);
  }

  container.style.display = "block";
  document.getElementById("instruction-bar").style.display = "block";

  // Auto-select first draft (on mobile, pills don't show text so this is essential)
  if (drafts.length > 0) {
    selectDraft(0);
  }
}

function selectDraft(index) {
  const draft = currentDrafts[index];
  if (!draft) return;

  selectedDraftIndex = index;
  currentDraftId = draft.id;

  document.getElementById("draft-input").value = draft.draft_text;

  // Update justification
  if (draft.justification) {
    const justEl = document.getElementById("justification");
    justEl.textContent = `IA: ${draft.justification}`;
    justEl.style.display = "block";
  }

  // Highlight selected card
  document.querySelectorAll(".draft-card").forEach((card, i) => {
    card.classList.toggle("selected", i === index);
  });
}

async function pollForUpdatedDrafts(convId) {
  // Poll until drafts change (max 15s)
  const oldTexts = currentDrafts.map(d => d.draft_text).join("|");
  for (let i = 0; i < 15; i++) {
    await new Promise(r => setTimeout(r, 1000));
    if (convId !== currentConversationId) return;
    const res = await fetch(`/conversations/${convId}`);
    const data = await res.json();
    if (data.pending_drafts && data.pending_drafts.length > 0) {
      const newTexts = data.pending_drafts.map(d => d.draft_text).join("|");
      if (newTexts !== oldTexts) {
        console.log("Poll: drafts updated after", i + 1, "seconds");
        showDrafts(data.pending_drafts, data.pending_drafts[0].draft_group_id);
        return;
      }
    }
  }
}

async function regenerateDraft(index) {
  if (!currentConversationId || currentDrafts.length === 0) return;
  regenerationCount++;

  const triggerId = currentDrafts[0].trigger_message_id;
  const instruction = document.getElementById("instruction-input").value.trim() || null;
  const convId = currentConversationId;

  await fetch(`/conversations/${currentConversationId}/regenerate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      draft_index: index,
      operator_instruction: instruction,
      trigger_message_id: triggerId,
    }),
  });

  pollForUpdatedDrafts(convId);
}

async function regenerateAll() {
  if (!currentConversationId || currentDrafts.length === 0) return;
  regenerationCount++;

  const triggerId = currentDrafts[0].trigger_message_id;
  const instruction = document.getElementById("instruction-input").value.trim() || null;
  const convId = currentConversationId;

  await fetch(`/conversations/${currentConversationId}/regenerate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      draft_index: null,
      operator_instruction: instruction,
      trigger_message_id: triggerId,
    }),
  });

  pollForUpdatedDrafts(convId);
}

// --- Attachments ---
function handleFileSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  attachedFile = file;
  document.getElementById("attachment-name").textContent = `\uD83D\uDCCE ${file.name}`;
  document.getElementById("attachment-bar").style.display = "block";
}

function removeAttachment() {
  attachedFile = null;
  document.getElementById("attach-file").value = "";
  document.getElementById("attachment-bar").style.display = "none";
}

// --- Send ---
async function sendMessage() {
  const input = document.getElementById("draft-input");
  const text = input.value.trim();
  if (!text || !currentConversationId) return;

  const btn = document.getElementById("send-btn");
  btn.disabled = true;

  try {
    const formData = new FormData();
    formData.append("text", text);

    if (currentDraftId) {
      formData.append("draft_id", currentDraftId);
    }
    if (currentDraftGroupId) {
      formData.append("draft_group_id", currentDraftGroupId);
    }
    if (selectedDraftIndex !== null) {
      formData.append("selected_draft_index", selectedDraftIndex);
    }
    const instruction = document.getElementById("instruction-input").value.trim();
    if (instruction) {
      formData.append("operator_instruction", instruction);
    }
    formData.append("regeneration_count", regenerationCount);

    if (attachedFile) {
      formData.append("file", attachedFile);
    }

    const res = await fetch(`/conversations/${currentConversationId}/send`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json();
      alert(`Erro ao enviar: ${err.detail || "erro desconhecido"}`);
      return;
    }

    input.value = "";
    currentDraftId = null;
    currentDraftGroupId = null;
    currentDrafts = [];
    selectedDraftIndex = null;
    regenerationCount = 0;
    removeAttachment();
    document.getElementById("justification").style.display = "none";
    document.getElementById("draft-cards-container").style.display = "none";
    document.getElementById("instruction-bar").style.display = "none";
    document.getElementById("instruction-input").value = "";
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

// --- Sidebar toggle (mobile) ---
function isMobile() {
  return window.innerWidth < 768;
}

function toggleSidebar() {
  if (isMobile() && document.body.classList.contains("mobile-chat-active")) {
    // In chat view: go back to conversation list
    document.body.classList.remove("mobile-chat-active");
  } else {
    document.getElementById("sidebar").classList.toggle("open");
    document.getElementById("sidebar-backdrop").classList.toggle("open");
  }
}

function closeSidebar() {
  document.getElementById("sidebar").classList.remove("open");
  document.getElementById("sidebar-backdrop").classList.remove("open");
}

// --- Auto-resize textarea ---
function autoResize(el) {
  var maxH = isMobile() ? window.innerHeight * 0.4 : 500;
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, maxH) + "px";
}

// --- Knowledge Base ---
let currentTab = "conversations";
let currentDocName = null;

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll(".sidebar-tab").forEach(t => {
    t.classList.toggle("active", t.dataset.tab === tab);
  });

  const convList = document.getElementById("conversation-list");
  const kbList = document.getElementById("knowledge-list");

  if (tab === "conversations") {
    convList.style.display = "block";
    kbList.style.display = "none";
    hideKnowledgePanels();
    // Restore chat view if a conversation was open
    if (currentConversationId) {
      document.getElementById("chat-header").style.display = "block";
      document.getElementById("messages").style.display = "flex";
      document.getElementById("compose").style.display = "block";
      document.getElementById("main-empty").style.display = "none";
    } else {
      document.getElementById("main-empty").style.display = "flex";
    }
  } else {
    convList.style.display = "none";
    kbList.style.display = "block";
    // Hide chat panels but preserve state
    document.getElementById("chat-header").style.display = "none";
    document.getElementById("messages").style.display = "none";
    document.getElementById("compose").style.display = "none";
    document.getElementById("main-empty").style.display = "none";
    hideKnowledgePanels();
    loadKnowledgeDocs();
  }
}

function hideKnowledgePanels() {
  document.getElementById("kb-editor").style.display = "none";
  document.getElementById("kb-new-form").style.display = "none";
}

async function loadKnowledgeDocs() {
  const res = await fetch("/knowledge");
  const docs = await res.json();
  const container = document.getElementById("kb-docs");
  container.innerHTML = "";

  for (const doc of docs) {
    const div = document.createElement("div");
    div.className = "kb-item" + (doc.name === currentDocName ? " active" : "");
    div.onclick = () => openDoc(doc.name);

    const time = formatTime(doc.modified_at);
    div.innerHTML = `
      <span class="kb-item-time">${time}</span>
      <div class="kb-item-name">${escapeHtml(doc.name)}</div>
    `;
    container.appendChild(div);
  }
}

async function openDoc(name) {
  const res = await fetch(`/knowledge/${encodeURIComponent(name)}`);
  if (!res.ok) return;
  const data = await res.json();
  currentDocName = name;

  hideKnowledgePanels();
  document.getElementById("kb-editor").style.display = "flex";
  document.getElementById("kb-editor-name").textContent = name;
  document.getElementById("kb-editor-textarea").value = data.content;
  document.getElementById("main-empty").style.display = "none";

  // Update active state in list
  document.querySelectorAll(".kb-item").forEach(item => {
    item.classList.toggle("active", item.querySelector(".kb-item-name").textContent === name);
  });
}

async function saveDoc() {
  if (!currentDocName) return;
  const content = document.getElementById("kb-editor-textarea").value;
  const res = await fetch(`/knowledge/${encodeURIComponent(currentDocName)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (res.ok) {
    loadKnowledgeDocs();
  } else {
    const err = await res.json();
    alert(`Erro ao salvar: ${err.detail || "erro desconhecido"}`);
  }
}

async function deleteDoc() {
  if (!currentDocName) return;
  if (!confirm(`Deletar "${currentDocName}"?`)) return;

  const res = await fetch(`/knowledge/${encodeURIComponent(currentDocName)}`, {
    method: "DELETE",
  });
  if (res.ok) {
    currentDocName = null;
    hideKnowledgePanels();
    document.getElementById("main-empty").style.display = "flex";
    loadKnowledgeDocs();
  } else {
    const err = await res.json();
    alert(`Erro ao deletar: ${err.detail || "erro desconhecido"}`);
  }
}

function showNewDocForm() {
  hideKnowledgePanels();
  document.getElementById("kb-new-form").style.display = "flex";
  document.getElementById("kb-new-name-input").value = "";
  document.getElementById("kb-new-textarea").value = "";
  document.getElementById("main-empty").style.display = "none";
  document.getElementById("kb-new-name-input").focus();
}

function cancelNewDoc() {
  hideKnowledgePanels();
  if (!currentDocName && !currentConversationId) {
    document.getElementById("main-empty").style.display = "flex";
  }
}

async function createDoc() {
  const name = document.getElementById("kb-new-name-input").value.trim();
  const content = document.getElementById("kb-new-textarea").value;

  if (!name) {
    alert("Nome do documento é obrigatório");
    return;
  }
  if (!/^[a-z0-9][a-z0-9-]*$/.test(name)) {
    alert("Nome inválido. Use apenas letras minúsculas, números e hífens.");
    return;
  }

  const res = await fetch("/knowledge", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, content }),
  });

  if (res.ok) {
    await loadKnowledgeDocs();
    openDoc(name);
  } else {
    const err = await res.json();
    alert(`Erro ao criar: ${err.detail || "erro desconhecido"}`);
  }
}

// --- Init ---
document.getElementById("send-btn").onclick = sendMessage;
document.getElementById("draft-input").onkeydown = (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
};
document.getElementById("draft-input").oninput = function () {
  autoResize(this);
};
document.getElementById("regen-all-btn").onclick = regenerateAll;
document.getElementById("regen-instruction-btn").onclick = regenerateAll;
document.getElementById("instruction-input").onkeydown = (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    regenerateAll();
  }
};
document.getElementById("attach-btn").onclick = () => document.getElementById("attach-file").click();
document.getElementById("attach-file").onchange = handleFileSelect;
document.getElementById("attachment-remove").onclick = removeAttachment;

loadConversations();
connectWS();
