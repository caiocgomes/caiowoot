import state from '../state.js';
import { getConversation, regenerateDraftApi } from '../api.js';
import { loadSuggestedAttachment } from './compose.js';

export function showDraftLoading() {
  const container = document.getElementById("draft-cards-container");
  const cardsEl = document.getElementById("draft-cards");
  cardsEl.innerHTML = '<div class="draft-loading">Gerando sugestões...</div>';
  container.style.display = "block";
}

export function showDrafts(drafts, groupId) {
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

export async function pollForUpdatedDrafts(convId) {
  // Poll until drafts change (max 15s)
  const oldTexts = state.currentDrafts.map(d => d.draft_text).join("|");
  for (let i = 0; i < 15; i++) {
    await new Promise(r => setTimeout(r, 1000));
    if (convId !== state.currentConversationId) return;
    const res = await getConversation(convId);
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

export async function regenerateDraft(index) {
  if (!state.currentConversationId) return;
  const triggerId = state.currentDrafts[0]?.trigger_message_id || state.lastTriggerMessageId;
  if (!triggerId) return;
  state.regenerationCount++;
  const instruction = document.getElementById("instruction-input").value.trim() || null;
  const convId = state.currentConversationId;

  await regenerateDraftApi(state.currentConversationId, {
    draft_index: index,
    operator_instruction: instruction,
    trigger_message_id: triggerId,
  });

  pollForUpdatedDrafts(convId);
}

export async function regenerateAll() {
  if (!state.currentConversationId) return;
  const triggerId = state.currentDrafts[0]?.trigger_message_id || state.lastTriggerMessageId;
  if (!triggerId) return;
  state.regenerationCount++;
  const instruction = document.getElementById("instruction-input").value.trim() || null;
  const convId = state.currentConversationId;

  await regenerateDraftApi(state.currentConversationId, {
    draft_index: null,
    operator_instruction: instruction,
    trigger_message_id: triggerId,
  });

  pollForUpdatedDrafts(convId);
}
