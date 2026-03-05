let currentConversationId = null;
let currentDraftId = null;
let currentDraftGroupId = null;
let currentDrafts = [];
let selectedDraftIndex = null;
let regenerationCount = 0;
let attachedFile = null;
let lastTriggerMessageId = null;
let ws = null;

// --- Auth: intercept 401 responses ---
const _origFetch = window.fetch;
window.fetch = async (...args) => {
  const res = await _origFetch(...args);
  if (res.status === 401) {
    window.location.href = "/login.html";
  }
  return res;
};

// --- WebSocket ---
var wsPingInterval = null;

function connectWS() {
  if (ws && ws.readyState === WebSocket.OPEN) return;
  if (ws) { try { ws.close(); } catch(e) {} }

  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(`${protocol}//${location.host}/ws`);

  ws.onopen = () => {
    clearInterval(wsPingInterval);
    wsPingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send("ping");
      }
    }, 30000);
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleWSEvent(data);
  };

  ws.onerror = () => {
    ws.close();
  };

  ws.onclose = () => {
    clearInterval(wsPingInterval);
    setTimeout(connectWS, 2000);
  };
}

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      connectWS();
    }
    loadConversations();
  }
});

function handleWSEvent(data) {
  console.log("WS event:", data.type, "conv:", data.conversation_id, "current:", currentConversationId);
  if (data.type === "new_message") {
    loadConversations();
    if (data.conversation_id === currentConversationId) {
      appendMessage(data.message);
      if (data.message.direction === "inbound") {
        lastTriggerMessageId = data.message.id;
      }
    }
  } else if (data.type === "drafts_ready") {
    console.log("drafts_ready received, drafts count:", data.drafts?.length, "match:", data.conversation_id === currentConversationId);
    if (data.conversation_id === currentConversationId) {
      showDrafts(data.drafts, data.draft_group_id);
      // Update context panel with AI classification
      if (data.funnel_product != null || data.funnel_stage != null || data.situation_summary != null) {
        renderContextPanel(
          { funnel_product: data.funnel_product, funnel_stage: data.funnel_stage },
          data.situation_summary,
        );
      }
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
      (conv.is_new ? " is-new" : conv.needs_reply ? " needs-reply" : "");
    div.onclick = () => { openConversation(conv.id); closeSidebar(); };

    const name = conv.contact_name || conv.phone_number;
    const preview = conv.last_message
      ? conv.last_message.substring(0, 50)
      : "";
    const time = conv.last_message_at
      ? formatTime(conv.last_message_at)
      : "";

    const responder = conv.last_responder
      ? `<div class="conv-responder">${escapeHtml(conv.last_responder)}</div>`
      : "";

    const dot = conv.is_new ? '<span class="conv-new-dot"></span>' : "";

    div.innerHTML = `
      <span class="conv-time">${time}</span>
      <div class="conv-name">${dot}${escapeHtml(name)}</div>
      <div class="conv-preview">${escapeHtml(preview)}</div>
      ${responder}
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
  document.getElementById("chat-wrapper").style.display = "flex";

  if (isMobile()) document.body.classList.add("mobile-chat-active");

  const conv = data.conversation;
  document.getElementById("chat-header-name").textContent =
    conv.contact_name || conv.phone_number;

  const messagesEl = document.getElementById("messages");
  messagesEl.innerHTML = "";
  lastMessageDate = null;
  for (const msg of data.messages) {
    appendMessage(msg);
  }
  messagesEl.scrollTop = messagesEl.scrollHeight;

  // Track last message ID for regeneration fallback
  const msgs = data.messages;
  const lastInbound = [...msgs].reverse().find(m => m.direction === "inbound");
  lastTriggerMessageId = lastInbound ? lastInbound.id : (msgs.length > 0 ? msgs[msgs.length - 1].id : null);

  // Reset compose
  document.getElementById("draft-input").value = "";
  document.getElementById("justification").style.display = "none";
  document.getElementById("justification").textContent = "";
  document.getElementById("draft-cards-container").style.display = "none";
  document.getElementById("attachment-bar").style.display = "none";

  if (data.pending_drafts && data.pending_drafts.length > 0) {
    showDrafts(data.pending_drafts, data.pending_drafts[0].draft_group_id);
  }

  // Render context panel
  renderContextPanel(conv, data.situation_summary);

  // Auto-classify if no funnel data exists yet
  if (!conv.funnel_product && !conv.funnel_stage) {
    classifyConversation();
  }

  loadConversations();
}

function appendMessage(msg) {
  const messagesEl = document.getElementById("messages");

  // Date separator
  if (msg.created_at) {
    const msgDate = new Date(normalizeTimestamp(msg.created_at)).toLocaleDateString("pt-BR", { timeZone: "America/Sao_Paulo" });
    if (msgDate !== lastMessageDate) {
      const sep = document.createElement("div");
      sep.className = "date-separator";
      sep.innerHTML = `<span>${formatDateSeparator(msg.created_at)}</span>`;
      messagesEl.appendChild(sep);
      lastMessageDate = msgDate;
    }
  }

  const div = document.createElement("div");
  div.className = `msg ${msg.direction}`;
  div.textContent = msg.content;
  if (msg.media_type) {
    const badge = document.createElement("div");
    badge.style.cssText = "font-size:11px;color:#888;margin-top:4px;";
    badge.textContent = `[${msg.media_type === "image" ? "Imagem" : "Documento"} anexado]`;
    div.appendChild(badge);
  }
  if (msg.created_at) {
    const timeEl = document.createElement("span");
    timeEl.className = "msg-time";
    timeEl.textContent = formatTimeShort(msg.created_at);
    div.appendChild(timeEl);
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

    // Show attachment suggestion if present
    if (draft.suggested_attachment) {
      const attachSuggestion = document.createElement("div");
      attachSuggestion.className = "draft-attachment-suggestion";

      const attachLabel = document.createElement("span");
      attachLabel.textContent = `\uD83D\uDCCE ${draft.suggested_attachment}`;

      const attachBtn = document.createElement("button");
      attachBtn.textContent = "Anexar";
      attachBtn.className = "draft-attach-btn";
      attachBtn.onclick = (e) => {
        e.stopPropagation();
        loadSuggestedAttachment(draft.suggested_attachment);
      };

      attachSuggestion.appendChild(attachLabel);
      attachSuggestion.appendChild(attachBtn);
      card.appendChild(attachSuggestion);
    }

    card.onclick = () => selectDraft(i);
    cardsEl.appendChild(card);
  }

  container.style.display = "block";

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
  if (!currentConversationId) return;
  const triggerId = currentDrafts[0]?.trigger_message_id || lastTriggerMessageId;
  if (!triggerId) return;
  regenerationCount++;
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
  if (!currentConversationId) return;
  const triggerId = currentDrafts[0]?.trigger_message_id || lastTriggerMessageId;
  if (!triggerId) return;
  regenerationCount++;
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

async function loadSuggestedAttachment(filename) {
  try {
    const res = await fetch(`/api/attachments/${encodeURIComponent(filename)}`);
    if (!res.ok) return;
    const blob = await res.blob();
    attachedFile = new File([blob], filename, { type: blob.type });
    document.getElementById("attachment-name").textContent = `\uD83D\uDCCE ${filename}`;
    document.getElementById("attachment-bar").style.display = "block";
  } catch (e) {
    console.error("Failed to load suggested attachment:", e);
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
    document.getElementById("instruction-input").value = "";
  } finally {
    btn.disabled = false;
  }
}

// --- Rewrite ---
async function rewriteText() {
  const input = document.getElementById("draft-input");
  const text = input.value.trim();
  if (!text || !currentConversationId) return;

  const btn = document.getElementById("rewrite-btn");
  const originalLabel = btn.textContent;
  btn.disabled = true;
  btn.textContent = "Reescrevendo...";

  try {
    const res = await fetch(`/conversations/${currentConversationId}/rewrite`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    if (!res.ok) {
      const err = await res.json();
      alert(`Erro ao reescrever: ${err.detail || "erro desconhecido"}`);
      return;
    }

    const data = await res.json();
    input.value = data.text;
    autoResize(input);
  } catch (e) {
    alert("Erro ao reescrever: falha na conexão");
  } finally {
    btn.textContent = originalLabel;
    btn.disabled = !input.value.trim();
  }
}

// --- Utils ---
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function formatTime(dateStr) {
  const date = new Date(normalizeTimestamp(dateStr));
  const tz = "America/Sao_Paulo";

  const todayStr = new Date().toLocaleDateString("pt-BR", { timeZone: tz });
  const dateStr2 = date.toLocaleDateString("pt-BR", { timeZone: tz });
  const isToday = todayStr === dateStr2;

  if (isToday) {
    return date.toLocaleTimeString("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
      timeZone: tz,
    });
  }
  return date.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    timeZone: tz,
  });
}

function normalizeTimestamp(dateStr) {
  return dateStr.includes("+") || dateStr.includes("Z")
    ? dateStr
    : dateStr.replace(" ", "T") + "Z";
}

function formatTimeShort(dateStr) {
  const date = new Date(normalizeTimestamp(dateStr));
  return date.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "America/Sao_Paulo",
  });
}

function formatDateSeparator(dateStr) {
  const date = new Date(normalizeTimestamp(dateStr));
  const tz = "America/Sao_Paulo";
  const todayStr = new Date().toLocaleDateString("pt-BR", { timeZone: tz });
  const dateStr2 = date.toLocaleDateString("pt-BR", { timeZone: tz });
  if (todayStr === dateStr2) return "Hoje";
  return date.toLocaleDateString("pt-BR", {
    day: "numeric",
    month: "long",
    timeZone: tz,
  });
}

var lastMessageDate = null;

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

// --- Review / Learning ---
let currentReviewItems = [];
let currentReviewItemId = null;

async function loadReviewItems() {
  const res = await fetch("/review");
  const data = await res.json();
  currentReviewItems = data.annotations || [];
  renderReviewStats(data.stats, data.history_stats);
  renderReviewList(data.annotations);
}

function renderReviewStats(stats, historyStats) {
  const el = document.getElementById("review-stats");
  let html = "";

  if (stats && stats.total_pending > 0) {
    html += `<div class="review-stats-row">
      <div class="review-stat"><span class="review-stat-count">${stats.total_pending}</span> pendentes</div>
      <div class="review-stat"><span class="review-stat-count">${stats.total_edited}</span> editadas</div>
      <div class="review-stat"><span class="review-stat-count">${stats.total_accepted}</span> aceitas</div>
    </div>`;
  }

  if (historyStats && (historyStats.total_validated > 0 || historyStats.total_rejected > 0 || historyStats.total_promoted > 0)) {
    html += `<div class="review-stats-row history">
      <div class="review-stat"><span class="review-stat-count">${historyStats.total_validated}</span> validadas</div>
      <div class="review-stat"><span class="review-stat-count">${historyStats.total_rejected}</span> rejeitadas</div>
      <div class="review-stat"><span class="review-stat-count">${historyStats.total_promoted}</span> regras</div>
    </div>`;
  }

  el.innerHTML = html;
}

function renderReviewList(annotations) {
  const container = document.getElementById("review-items");
  const emptyEl = document.getElementById("review-empty");
  container.innerHTML = "";

  if (!annotations || annotations.length === 0) {
    emptyEl.style.display = "block";
    return;
  }
  emptyEl.style.display = "none";

  for (const ann of annotations) {
    const div = document.createElement("div");
    div.className = "review-item" + (ann.id === currentReviewItemId ? " active" : "");
    div.onclick = () => openReviewItem(ann.id);

    const badgeClass = ann.was_edited ? "edited" : "confirmed";
    const badgeText = ann.was_edited ? "Editada" : "Confirmada";

    div.innerHTML = `
      <span class="review-item-badge ${badgeClass}">${badgeText}</span>
      <div class="review-item-situation">${escapeHtml(ann.situation_summary || "Sem resumo")}</div>
      <div class="review-item-msg">${escapeHtml(ann.customer_message || "")}</div>
    `;
    container.appendChild(div);
  }
}

function openReviewItem(id) {
  const ann = currentReviewItems.find(a => a.id === id);
  if (!ann) return;
  currentReviewItemId = id;

  hideKnowledgePanels();
  hideReviewDetail();
  document.getElementById("review-detail").style.display = "flex";
  document.getElementById("main-empty").style.display = "none";
  if (isMobile()) document.body.classList.add("mobile-chat-active");

  document.getElementById("review-detail-situation").textContent =
    ann.situation_summary || "Sem resumo de situação";
  document.getElementById("review-detail-time").textContent =
    ann.created_at ? formatTime(ann.created_at) : "";
  document.getElementById("review-detail-customer").textContent =
    ann.customer_message || "";
  document.getElementById("review-detail-draft").textContent =
    ann.original_draft || "";
  document.getElementById("review-detail-final").textContent =
    ann.final_message || "";
  document.getElementById("review-detail-annotation").textContent =
    ann.strategic_annotation || "";

  // Update active state
  document.querySelectorAll(".review-item").forEach(item => {
    item.classList.toggle("active", currentReviewItems[Array.from(item.parentNode.children).indexOf(item)]?.id === id);
  });
}

function hideReviewDetail() {
  document.getElementById("review-detail").style.display = "none";
}

function reviewGoBack() {
  currentReviewItemId = null;
  hideReviewDetail();
  document.body.classList.remove("mobile-chat-active");
  document.getElementById("main-empty").style.display = "flex";
  document.getElementById("main-empty").textContent = "Selecione uma anotação ou regra";
}

async function validateAnnotation() {
  if (!currentReviewItemId) return;
  const res = await fetch(`/review/${currentReviewItemId}/validate`, { method: "POST" });
  if (res.ok) {
    afterReviewAction();
  }
}

async function rejectAnnotation() {
  if (!currentReviewItemId) return;
  const res = await fetch(`/review/${currentReviewItemId}/reject`, { method: "POST" });
  if (res.ok) {
    afterReviewAction();
  }
}

function showPromoteModal() {
  if (!currentReviewItemId) return;
  const ann = currentReviewItems.find(a => a.id === currentReviewItemId);
  if (!ann) return;
  document.getElementById("promote-rule-input").value = ann.strategic_annotation || "";
  document.getElementById("promote-modal").classList.add("open");
}

function closePromoteModal() {
  document.getElementById("promote-modal").classList.remove("open");
}

async function confirmPromote() {
  if (!currentReviewItemId) return;
  const ruleText = document.getElementById("promote-rule-input").value.trim();
  if (!ruleText) return;

  const body = { rule_text: ruleText };
  const res = await fetch(`/review/${currentReviewItemId}/promote`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.ok) {
    closePromoteModal();
    afterReviewAction();
  }
}

function afterReviewAction() {
  currentReviewItemId = null;
  hideReviewDetail();
  if (isMobile()) document.body.classList.remove("mobile-chat-active");
  document.getElementById("main-empty").style.display = "flex";
  document.getElementById("main-empty").textContent = "Anotação processada";
  loadReviewItems();
  loadRules();
}

// --- Rules ---
let currentRules = [];
let currentRuleId = null;

async function loadRules() {
  const res = await fetch("/rules");
  const data = await res.json();
  currentRules = data.rules || [];
  renderRulesList(currentRules);
}

function renderRulesList(rules) {
  const container = document.getElementById("rules-items");
  const emptyEl = document.getElementById("rules-empty");
  container.innerHTML = "";

  if (!rules || rules.length === 0) {
    emptyEl.style.display = "block";
    return;
  }
  emptyEl.style.display = "none";

  for (const rule of rules) {
    const div = document.createElement("div");
    div.className = "rule-item" + (rule.id === currentRuleId ? " active" : "") + (rule.is_active ? "" : " inactive");
    div.onclick = () => openRuleDetail(rule.id);

    const toggle = document.createElement("button");
    toggle.className = "rule-toggle" + (rule.is_active ? " on" : "");
    toggle.onclick = (e) => { e.stopPropagation(); toggleRule(rule.id); };

    const text = document.createElement("span");
    text.className = "rule-text-preview";
    text.textContent = rule.rule_text;

    div.appendChild(toggle);
    div.appendChild(text);
    container.appendChild(div);
  }
}

function openRuleDetail(id) {
  const rule = currentRules.find(r => r.id === id);
  if (!rule) return;
  currentRuleId = id;

  hideKnowledgePanels();
  hideReviewDetail();
  hideRuleDetail();
  document.getElementById("rule-detail").style.display = "flex";
  document.getElementById("main-empty").style.display = "none";
  document.getElementById("rule-edit-textarea").value = rule.rule_text;

  renderRulesList(currentRules);
}

function hideRuleDetail() {
  document.getElementById("rule-detail").style.display = "none";
}

async function toggleRule(id) {
  await fetch(`/rules/${id}/toggle`, { method: "PATCH" });
  await loadRules();
}

async function saveRule() {
  if (!currentRuleId) return;
  const text = document.getElementById("rule-edit-textarea").value.trim();
  if (!text) return;

  await fetch(`/rules/${currentRuleId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rule_text: text }),
  });

  currentRuleId = null;
  hideRuleDetail();
  document.getElementById("main-empty").style.display = "flex";
  document.getElementById("main-empty").textContent = "Regra salva";
  await loadRules();
}

function cancelRuleEdit() {
  currentRuleId = null;
  hideRuleDetail();
  document.getElementById("main-empty").style.display = "flex";
  document.getElementById("main-empty").textContent = "Selecione uma anotação ou regra";
  renderRulesList(currentRules);
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
  const reviewList = document.getElementById("review-list");

  // Hide all sidebar panels
  convList.style.display = "none";
  kbList.style.display = "none";
  reviewList.style.display = "none";

  // Hide all main panels
  document.getElementById("chat-wrapper").style.display = "none";
  document.getElementById("main-empty").style.display = "none";
  hideKnowledgePanels();
  hideReviewDetail();
  hideRuleDetail();

  if (tab === "conversations") {
    convList.style.display = "block";
    if (currentConversationId) {
      document.getElementById("chat-wrapper").style.display = "flex";
    } else {
      document.getElementById("main-empty").style.display = "flex";
      document.getElementById("main-empty").textContent = "Selecione uma conversa";
    }
  } else if (tab === "knowledge") {
    kbList.style.display = "block";
    loadKnowledgeDocs();
  } else if (tab === "review") {
    reviewList.style.display = "block";
    document.getElementById("main-empty").style.display = "flex";
    document.getElementById("main-empty").textContent = "Selecione uma anotação ou regra";
    loadReviewItems();
    loadRules();
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

// --- Settings ---
let settingsIsAdmin = false;
let settingsCurrentTab = "profile";
let settingsPrompts = {};
let settingsProfile = {};

const PROMPT_LABELS = {
  postura: "Postura",
  tom: "Tom",
  regras: "Regras",
  approach_direta: "Abordagem Direta",
  approach_consultiva: "Abordagem Consultiva",
  approach_casual: "Abordagem Casual",
  summary_prompt: "Prompt de Resumo de Situacao",
  annotation_prompt: "Prompt de Anotacao Estrategica",
};

async function openSettings() {
  document.getElementById("settings-status").textContent = "";
  settingsCurrentTab = "profile";

  // Check admin status
  try {
    const res = await fetch("/api/settings/is-admin");
    const data = await res.json();
    settingsIsAdmin = data.is_admin;
  } catch (e) {
    settingsIsAdmin = false;
  }

  // Show/hide prompts tab
  const promptsTab = document.getElementById("settings-prompts-tab");
  promptsTab.style.display = settingsIsAdmin ? "" : "none";

  // Load data
  await loadSettingsProfile();
  if (settingsIsAdmin) {
    await loadSettingsPrompts();
  }

  // Reset tab state
  document.querySelectorAll(".settings-tab").forEach(t => {
    t.classList.toggle("active", t.dataset.stab === "profile");
  });

  renderSettingsTab("profile");
  document.getElementById("settings-modal").classList.add("open");
}

function closeSettings() {
  document.getElementById("settings-modal").classList.remove("open");
}

function switchSettingsTab(tab) {
  settingsCurrentTab = tab;
  document.querySelectorAll(".settings-tab").forEach(t => {
    t.classList.toggle("active", t.dataset.stab === tab);
  });
  document.getElementById("settings-status").textContent = "";
  renderSettingsTab(tab);
}

async function loadSettingsPrompts() {
  try {
    const res = await fetch("/api/settings/prompts");
    settingsPrompts = await res.json();
  } catch (e) {
    settingsPrompts = {};
  }
}

async function loadSettingsProfile() {
  try {
    const res = await fetch("/api/settings/profile");
    settingsProfile = await res.json();
  } catch (e) {
    settingsProfile = {};
  }
}

function renderSettingsTab(tab) {
  const body = document.getElementById("settings-body");

  if (tab === "profile") {
    body.innerHTML = `
      <div class="settings-field">
        <label>Nome de exibicao</label>
        <input type="text" id="settings-display-name" value="${escapeHtml(settingsProfile.display_name || "")}" placeholder="Como a IA deve se apresentar (ex: Joao Silva)">
      </div>
      <div class="settings-field">
        <label>Contexto sobre voce</label>
        <textarea id="settings-context" rows="6" placeholder="Informacoes que a IA deve saber sobre voce. Ex: Trabalho na equipe do Caio. Sou responsavel pelo suporte tecnico. Nao sou o dono dos cursos.">${escapeHtml(settingsProfile.context || "")}</textarea>
      </div>
    `;
  } else if (tab === "prompts") {
    let html = "";
    for (const [key, label] of Object.entries(PROMPT_LABELS)) {
      const value = settingsPrompts[key] || "";
      html += `
        <div class="settings-field">
          <div class="settings-field-header">
            <label>${label}</label>
            <button class="reset-btn" onclick="resetPrompt('${key}')">Resetar</button>
          </div>
          <textarea id="settings-prompt-${key}" rows="4">${escapeHtml(value)}</textarea>
        </div>
      `;
    }
    body.innerHTML = html;
  }
}

async function saveSettings() {
  const statusEl = document.getElementById("settings-status");
  statusEl.textContent = "Salvando...";

  try {
    if (settingsCurrentTab === "profile") {
      const displayName = document.getElementById("settings-display-name").value.trim();
      const context = document.getElementById("settings-context").value.trim();

      const res = await fetch("/api/settings/profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ display_name: displayName, context: context }),
      });

      if (res.ok) {
        settingsProfile = { display_name: displayName, context: context };
        statusEl.textContent = "Perfil salvo!";
      } else {
        statusEl.textContent = "Erro ao salvar perfil";
      }
    } else if (settingsCurrentTab === "prompts") {
      const updates = {};
      for (const key of Object.keys(PROMPT_LABELS)) {
        const el = document.getElementById(`settings-prompt-${key}`);
        if (el) updates[key] = el.value;
      }

      const res = await fetch("/api/settings/prompts", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });

      if (res.ok) {
        settingsPrompts = updates;
        statusEl.textContent = "Prompts salvos!";
      } else {
        const err = await res.json();
        statusEl.textContent = err.detail || "Erro ao salvar prompts";
      }
    }
  } catch (e) {
    statusEl.textContent = "Erro de conexao";
  }

  setTimeout(() => { statusEl.textContent = ""; }, 3000);
}

async function resetPrompt(key) {
  const statusEl = document.getElementById("settings-status");

  const res = await fetch("/api/settings/prompts", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ [key]: null }),
  });

  if (res.ok) {
    await loadSettingsPrompts();
    renderSettingsTab("prompts");
    statusEl.textContent = `"${PROMPT_LABELS[key]}" resetado`;
    setTimeout(() => { statusEl.textContent = ""; }, 3000);
  }
}

// --- Context Panel ---
const FUNNEL_STAGES = ["qualifying", "decided", "handbook_sent", "link_sent", "purchased"];

function renderContextPanel(conv, situationSummary) {
  // Product
  const select = document.getElementById("ctx-product-select");
  select.value = conv.funnel_product || "";

  // Stage
  const currentStage = conv.funnel_stage;
  const stageIdx = FUNNEL_STAGES.indexOf(currentStage);
  document.querySelectorAll(".ctx-stage-item").forEach((item, i) => {
    item.classList.remove("active", "done");
    if (item.dataset.stage === currentStage) {
      item.classList.add("active");
    } else if (stageIdx >= 0 && i < stageIdx) {
      item.classList.add("done");
    }
  });

  // Summary
  document.getElementById("ctx-summary-text").textContent =
    situationSummary || "Sem resumo ainda";
}

async function updateFunnelProduct(value) {
  if (!currentConversationId) return;
  await fetch(`/conversations/${currentConversationId}/funnel`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ funnel_product: value || null }),
  });
}

async function classifyConversation() {
  if (!currentConversationId) return;
  const btn = document.getElementById("ctx-classify-btn");
  btn.disabled = true;
  btn.textContent = "Analisando...";
  try {
    const res = await fetch(`/conversations/${currentConversationId}/classify`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      renderContextPanel(
        { funnel_product: data.product, funnel_stage: data.stage },
        data.summary,
      );
    } else {
      console.error("Classify failed:", res.status);
      btn.textContent = "Erro - tentar de novo";
      return;
    }
  } catch (e) {
    console.error("Classify error:", e);
    btn.textContent = "Erro - tentar de novo";
    return;
  }
  btn.disabled = false;
  btn.textContent = "Atualizar";
}

async function updateFunnelStage(stage) {
  if (!currentConversationId) return;
  await fetch(`/conversations/${currentConversationId}/funnel`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ funnel_stage: stage }),
  });
  // Re-render stage UI
  const stageIdx = FUNNEL_STAGES.indexOf(stage);
  document.querySelectorAll(".ctx-stage-item").forEach((item, i) => {
    item.classList.remove("active", "done");
    if (item.dataset.stage === stage) {
      item.classList.add("active");
    } else if (i < stageIdx) {
      item.classList.add("done");
    }
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
document.getElementById("draft-input").oninput = function () {
  autoResize(this);
  document.getElementById("rewrite-btn").disabled = !this.value.trim();
};
document.getElementById("regen-all-btn").onclick = regenerateAll;
document.getElementById("regen-instruction-btn").onclick = regenerateAll;
document.getElementById("instruction-input").onkeydown = (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    regenerateAll();
  }
};
document.getElementById("rewrite-btn").onclick = rewriteText;
document.getElementById("attach-btn").onclick = () => document.getElementById("attach-file").click();
document.getElementById("attach-file").onchange = handleFileSelect;
document.getElementById("attachment-remove").onclick = removeAttachment;

loadConversations();
connectWS();
