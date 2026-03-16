import state from '../state.js';
import { escapeHtml, formatTime, isMobile } from '../utils.js';
import { getConversations, getConversation } from '../api.js';
import { appendMessage } from './messages.js';
import { showDrafts } from './drafts.js';
import { loadScheduledSends } from './schedule.js';
import { renderContextPanel, classifyConversation } from './context-panel.js';

export function closeSidebar() {
  document.getElementById("sidebar").classList.remove("open");
  document.getElementById("sidebar-backdrop").classList.remove("open");
}

export function toggleSidebar() {
  if (isMobile() && document.body.classList.contains("mobile-chat-active")) {
    document.body.classList.remove("mobile-chat-active");
  } else {
    document.getElementById("sidebar").classList.toggle("open");
    document.getElementById("sidebar-backdrop").classList.toggle("open");
  }
}

export async function loadConversations() {
  const res = await getConversations();
  const conversations = await res.json();
  renderConversationList(conversations);
}

export function renderConversationList(conversations) {
  const list = document.getElementById("conversation-list");
  list.innerHTML = "";

  for (const conv of conversations) {
    state.conversationNames.set(conv.id, conv.contact_name || conv.phone_number);
    const div = document.createElement("div");
    div.className = "conv-item" +
      (conv.id === state.currentConversationId ? " active" : "") +
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
    const clock = conv.has_scheduled ? '<span class="conv-clock" title="Envio agendado">&#x1F551;</span>' : "";

    div.innerHTML = `
      <span class="conv-time">${time}</span>
      <div class="conv-name">${dot}${escapeHtml(name)}${clock}</div>
      <div class="conv-preview">${escapeHtml(preview)}</div>
      ${responder}
    `;
    list.appendChild(div);
  }
}

export function filterConversations(query) {
  const items = document.querySelectorAll('#conversation-list .conv-item');
  const q = query.toLowerCase();
  items.forEach(item => {
    const name = item.querySelector('.conv-name')?.textContent.toLowerCase() || '';
    item.style.display = name.includes(q) ? '' : 'none';
  });
}

export async function openConversation(id) {
  state.currentConversationId = id;
  state.currentDraftId = null;
  state.currentDraftGroupId = null;
  state.currentDrafts = [];
  state.selectedDraftIndex = null;
  state.regenerationCount = 0;
  state.attachedFile = null;

  const res = await getConversation(id);
  const data = await res.json();

  document.getElementById("main-empty").style.display = "none";
  document.getElementById("chat-wrapper").style.display = "flex";

  if (isMobile()) document.body.classList.add("mobile-chat-active");

  const conv = data.conversation;
  document.getElementById("chat-header-name").textContent =
    conv.contact_name || conv.phone_number;

  const messagesEl = document.getElementById("messages");
  messagesEl.innerHTML = "";
  state.lastMessageDate = null;
  for (const msg of data.messages) {
    appendMessage(msg);
  }
  messagesEl.scrollTop = messagesEl.scrollHeight;

  // Track last message ID for regeneration fallback
  const msgs = data.messages;
  const lastInbound = [...msgs].reverse().find(m => m.direction === "inbound");
  state.lastTriggerMessageId = lastInbound ? lastInbound.id : (msgs.length > 0 ? msgs[msgs.length - 1].id : null);

  // Reset compose
  document.getElementById("draft-input").value = "";
  document.getElementById("clear-draft-btn").style.display = "none";
  document.getElementById("justification").style.display = "none";
  document.getElementById("justification").textContent = "";
  document.getElementById("draft-cards-container").style.display = "none";
  document.getElementById("attachment-bar").style.display = "none";

  if (data.pending_drafts && data.pending_drafts.length > 0) {
    showDrafts(data.pending_drafts, data.pending_drafts[0].draft_group_id);
  }

  // Load scheduled sends
  loadScheduledSends(id);

  // Render context panel
  renderContextPanel(conv, data.situation_summary);

  // Auto-classify if no funnel data exists yet
  if (!conv.funnel_product && !conv.funnel_stage) {
    classifyConversation();
  }

  loadConversations();
}
