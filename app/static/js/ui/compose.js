import state from '../state.js';
import { autoResize } from '../utils.js';
import { sendMessageApi, rewriteTextApi, getAttachmentBlob, getAttachments } from '../api.js';
import { regenerateAll } from './drafts.js';
import { showToast } from './toast.js';

export function handleFileSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  state.attachedFile = file;
  document.getElementById("attachment-name").textContent = `\uD83D\uDCCE ${file.name}`;
  document.getElementById("attachment-bar").style.display = "block";
}

export function removeAttachment() {
  state.attachedFile = null;
  document.getElementById("attach-file").value = "";
  document.getElementById("attachment-bar").style.display = "none";
}

export async function loadSuggestedAttachment(filename) {
  try {
    const res = await getAttachmentBlob(filename);
    if (!res.ok) return;
    const blob = await res.blob();
    state.attachedFile = new File([blob], filename, { type: blob.type });
    document.getElementById("attachment-name").textContent = `\uD83D\uDCCE ${filename}`;
    document.getElementById("attachment-bar").style.display = "block";
  } catch (e) {
    console.error("Failed to load suggested attachment:", e);
  }
}

export async function loadQuickAttachButtons() {
  try {
    const res = await getAttachments();
    if (!res.ok) return;
    const files = await res.json();
    if (!files.length) return;
    const container = document.getElementById("quick-attach");
    container.innerHTML = "";
    files.forEach(filename => {
      const btn = document.createElement("button");
      btn.className = "quick-attach-btn";
      btn.title = filename;
      const label = filename.replace(/\.[^.]+$/, "").replace(/[-_]/g, " ");
      btn.textContent = "\uD83D\uDCCE " + label;
      btn.onclick = () => loadSuggestedAttachment(filename);
      container.appendChild(btn);
    });
    container.classList.add("visible");
  } catch (e) {
    console.error("Failed to load quick-attach buttons:", e);
  }
}

export async function sendMessage() {
  const input = document.getElementById("draft-input");
  const text = input.value.trim();
  if (!text || !state.currentConversationId) return;

  const btn = document.getElementById("send-btn");
  btn.disabled = true;
  btn.textContent = "Enviando...";

  try {
    const formData = new FormData();
    formData.append("text", text);

    if (state.currentDraftId) {
      formData.append("draft_id", state.currentDraftId);
    }
    if (state.currentDraftGroupId) {
      formData.append("draft_group_id", state.currentDraftGroupId);
    }
    if (state.selectedDraftIndex !== null) {
      formData.append("selected_draft_index", state.selectedDraftIndex);
    }
    const instruction = document.getElementById("instruction-input").value.trim();
    if (instruction) {
      formData.append("operator_instruction", instruction);
    }
    formData.append("regeneration_count", state.regenerationCount);

    if (state.attachedFile) {
      formData.append("file", state.attachedFile);
    }

    const res = await sendMessageApi(state.currentConversationId, formData);

    if (!res.ok) {
      const err = await res.json();
      showToast(`Erro ao enviar: ${err.detail || "erro desconhecido"}`, 'error');
      return;
    }

    showToast("Mensagem enviada", "success");

    input.value = "";
    state.currentDraftId = null;
    state.currentDraftGroupId = null;
    state.currentDrafts = [];
    state.selectedDraftIndex = null;
    state.regenerationCount = 0;
    removeAttachment();
    document.getElementById("clear-draft-btn").style.display = "none";
    document.getElementById("justification").style.display = "none";
    document.getElementById("draft-cards-container").style.display = "none";
    document.getElementById("instruction-input").value = "";
  } finally {
    btn.textContent = "Enviar";
    btn.disabled = false;
  }
}

export async function rewriteText() {
  const input = document.getElementById("draft-input");
  const text = input.value.trim();
  if (!text || !state.currentConversationId) return;

  const btn = document.getElementById("rewrite-btn");
  const originalLabel = btn.textContent;
  btn.disabled = true;
  btn.textContent = "Reescrevendo...";

  try {
    const res = await rewriteTextApi(state.currentConversationId, text);

    if (!res.ok) {
      const err = await res.json();
      showToast(`Erro ao reescrever: ${err.detail || "erro desconhecido"}`, 'error');
      return;
    }

    const data = await res.json();
    input.value = data.text;
    autoResize(input);
  } catch (e) {
    showToast("Erro ao reescrever: falha na conexão", 'error');
  } finally {
    btn.textContent = originalLabel;
    btn.disabled = !input.value.trim();
  }
}

export async function formalizeText() {
  const textarea = document.getElementById('draft-input');
  const text = textarea.value.trim();
  if (!text) return;

  const btn = document.getElementById('formalize-btn');
  btn.disabled = true;

  try {
    const convId = state.currentConversationId;
    const res = await fetch(`/conversations/${convId}/rewrite`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text})
    });
    const data = await res.json();
    if (data.text) textarea.value = data.text;
  } catch(e) {
    console.error('Formalize failed:', e);
  } finally {
    btn.disabled = false;
  }
}

export async function translateText() {
  const textarea = document.getElementById('draft-input');
  const text = textarea.value.trim();
  if (!text) return;

  const btn = document.getElementById('translate-btn');
  btn.disabled = true;

  try {
    const convId = state.currentConversationId;
    const res = await fetch(`/conversations/${convId}/rewrite`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text, instruction: 'Traduza para inglês'})
    });
    const data = await res.json();
    if (data.text) textarea.value = data.text;
  } catch(e) {
    console.error('Translate failed:', e);
  } finally {
    btn.disabled = false;
  }
}

export function initCompose() {
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
    document.getElementById("clear-draft-btn").style.display = this.value.trim() ? "flex" : "none";
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
  document.getElementById("clear-draft-btn").onclick = function () {
    document.getElementById("draft-input").value = "";
    state.currentDraftId = null;
    state.currentDraftGroupId = null;
    state.selectedDraftIndex = null;
    state.currentDrafts = [];
    document.getElementById("justification").style.display = "none";
    document.getElementById("justification").textContent = "";
    document.getElementById("clear-draft-btn").style.display = "none";
    document.getElementById("rewrite-btn").disabled = true;
    // Deselect draft cards
    document.querySelectorAll(".draft-card").forEach(c => c.classList.remove("selected"));
  };
  document.getElementById("attach-btn").onclick = () => document.getElementById("attach-file").click();
  document.getElementById("attach-file").onchange = handleFileSelect;
  document.getElementById("attachment-remove").onclick = removeAttachment;
}
