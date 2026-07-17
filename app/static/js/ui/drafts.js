import state from '../state.js';
import { getConversation, regenerateDraftApi } from '../api.js';
import { loadSuggestedAttachment } from './compose.js';
import { showToast } from './toast.js';

export function showDraftLoading() {
  const container = document.getElementById("draft-cards-container");
  const cardsEl = document.getElementById("draft-cards");
  cardsEl.innerHTML = '<div class="draft-loading">Gerando sugestões...</div>';
  container.style.display = "block";
}

// Timer único de segurança: se o WS não entregar drafts_ready/drafts_error,
// um GET ressincroniza a conversa aberta.
let draftsFallbackTimer = null;

function setRegenButtonsDisabled(disabled) {
  const regenAllBtn = document.getElementById("regen-all-btn");
  if (regenAllBtn) regenAllBtn.disabled = disabled;
  const regenInstructionBtn = document.getElementById("regen-instruction-btn");
  if (regenInstructionBtn) regenInstructionBtn.disabled = disabled;
  document.querySelectorAll(".draft-card-actions button").forEach(btn => {
    btn.disabled = disabled;
  });
}

export function setDraftsGenerating(draftIndex = null) {
  state.draftsGenerating = true;
  if (draftIndex === null || draftIndex === undefined) {
    showDraftLoading();
  } else {
    const card = document.querySelector(`.draft-card[data-index="${draftIndex}"]`);
    if (card) card.classList.add("loading");
    else showDraftLoading();
  }
  setRegenButtonsDisabled(true);
  clearTimeout(draftsFallbackTimer);
  draftsFallbackTimer = setTimeout(() => {
    draftsFallbackTimer = null;
    if (state.draftsGenerating) refreshCurrentConversationDrafts();
  }, 30000);
}

export function clearDraftsGenerating() {
  state.draftsGenerating = false;
  clearTimeout(draftsFallbackTimer);
  draftsFallbackTimer = null;
  document.querySelectorAll(".draft-card.loading").forEach(card => card.classList.remove("loading"));
  setRegenButtonsDisabled(false);
}

// Ressincronização pontual (1 GET) da conversa aberta — usada pelo fallback
// de 30s e pela reconexão do WS.
export async function refreshCurrentConversationDrafts() {
  const convId = state.currentConversationId;
  if (!convId) return;
  const res = await getConversation(convId);
  if (!res.ok) return;
  if (convId !== state.currentConversationId) return;
  const data = await res.json();
  if (data.pending_drafts && data.pending_drafts.length > 0) {
    showDrafts(data.pending_drafts, data.pending_drafts[0].draft_group_id);
  } else {
    clearDraftsGenerating();
  }
}

export function restoreDraftsAfterError(message) {
  clearDraftsGenerating();
  if (state.currentDrafts.length > 0) {
    showDrafts(state.currentDrafts, state.currentDraftGroupId);
  } else {
    document.getElementById("draft-cards").innerHTML = "";
    document.getElementById("draft-cards-container").style.display = "none";
  }
  showToast(message, "error");
}

export function showDrafts(drafts, groupId) {
  clearDraftsGenerating();
  state.currentDrafts = drafts;
  state.currentDraftGroupId = groupId;
  state.selectedDraftIndex = null;
  state.currentDraftId = null;

  const container = document.getElementById("draft-cards-container");
  const cardsEl = document.getElementById("draft-cards");
  cardsEl.innerHTML = "";

  const approachLabels = { direct: "Direta", consultive: "Consultiva", casual: "Casual" };
  const fallbackLabels = ["Direta", "Consultiva", "Casual"];

  for (let i = 0; i < drafts.length; i++) {
    const draft = drafts[i];
    const card = document.createElement("div");
    card.className = "draft-card";
    card.dataset.index = i;

    const header = document.createElement("div");
    header.className = "draft-card-header";

    const label = document.createElement("span");
    label.className = "draft-card-label";
    label.textContent = approachLabels[draft.approach] || fallbackLabels[i] || `Opção ${i + 1}`;

    const actions = document.createElement("div");
    actions.className = "draft-card-actions";

    const selectBtn = document.createElement("button");
    selectBtn.title = "Selecionar";
    selectBtn.innerHTML = '<span class="material-symbols-outlined" style="font-size:16px;">check</span>';
    selectBtn.onclick = (e) => { e.stopPropagation(); selectDraft(i); };

    const regenBtn = document.createElement("button");
    regenBtn.title = "Regenerar";
    regenBtn.innerHTML = '<span class="material-symbols-outlined" style="font-size:16px;">refresh</span>';
    regenBtn.onclick = (e) => { e.stopPropagation(); regenerateDraft(i); };

    actions.appendChild(selectBtn);
    actions.appendChild(regenBtn);
    header.appendChild(label);
    header.appendChild(actions);

    const text = document.createElement("p");
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

  // Auto-select removed: let operator choose explicitly
}

export function selectDraft(index) {
  const draft = state.currentDrafts[index];
  if (!draft) return;

  state.selectedDraftIndex = index;
  state.currentDraftId = draft.id;

  document.getElementById("draft-input").value = draft.draft_text;
  document.getElementById("clear-draft-btn").style.display = draft.draft_text.trim() ? "flex" : "none";

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

export async function regenerateDraft(index) {
  if (!state.currentConversationId) return;
  if (state.draftsGenerating) return;
  const triggerId = state.currentDrafts[0]?.trigger_message_id || state.lastTriggerMessageId;
  if (!triggerId) return;
  state.regenerationCount++;
  const instruction = document.getElementById("instruction-input").value.trim() || null;

  // Feedback otimista: loading antes do await; o resultado chega via WS
  setDraftsGenerating(index);
  try {
    const res = await regenerateDraftApi(state.currentConversationId, {
      draft_index: index,
      operator_instruction: instruction,
      trigger_message_id: triggerId,
    });
    if (!res.ok) restoreDraftsAfterError("Erro ao regenerar sugestões");
  } catch (e) {
    restoreDraftsAfterError("Erro ao regenerar sugestões");
  }
}

export async function regenerateAll() {
  if (!state.currentConversationId) return;
  if (state.draftsGenerating) return;
  const triggerId = state.currentDrafts[0]?.trigger_message_id || state.lastTriggerMessageId;
  if (!triggerId) return;
  state.regenerationCount++;
  const instruction = document.getElementById("instruction-input").value.trim() || null;

  // Feedback otimista: loading antes do await; o resultado chega via WS
  setDraftsGenerating(null);
  try {
    const res = await regenerateDraftApi(state.currentConversationId, {
      draft_index: null,
      operator_instruction: instruction,
      trigger_message_id: triggerId,
    });
    if (!res.ok) restoreDraftsAfterError("Erro ao regenerar sugestões");
  } catch (e) {
    restoreDraftsAfterError("Erro ao regenerar sugestões");
  }
}
