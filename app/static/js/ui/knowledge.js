import state from '../state.js';
import { escapeHtml, formatTime } from '../utils.js';
import { getKnowledgeDocs, getKnowledgeDoc, saveKnowledgeDoc, deleteKnowledgeDoc, createKnowledgeDoc } from '../api.js';

function hideKnowledgePanels() {
  document.getElementById("kb-editor").style.display = "none";
  document.getElementById("kb-new-form").style.display = "none";
}

export async function loadKnowledgeDocs() {
  const res = await getKnowledgeDocs();
  const docs = await res.json();
  const container = document.getElementById("kb-docs");
  container.innerHTML = "";

  for (const doc of docs) {
    const div = document.createElement("div");
    div.className = "kb-item" + (doc.name === state.currentDocName ? " active" : "");
    div.onclick = () => openDoc(doc.name);

    const time = formatTime(doc.modified_at);
    div.innerHTML = `
      <span class="kb-item-time">${time}</span>
      <div class="kb-item-name">${escapeHtml(doc.name)}</div>
    `;
    container.appendChild(div);
  }
}

export async function openDoc(name) {
  const res = await getKnowledgeDoc(name);
  if (!res.ok) return;
  const data = await res.json();
  state.currentDocName = name;

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

export async function saveDoc() {
  if (!state.currentDocName) return;
  const content = document.getElementById("kb-editor-textarea").value;
  const res = await saveKnowledgeDoc(state.currentDocName, content);
  if (res.ok) {
    loadKnowledgeDocs();
  } else {
    const err = await res.json();
    alert(`Erro ao salvar: ${err.detail || "erro desconhecido"}`);
  }
}

export async function deleteDoc() {
  if (!state.currentDocName) return;
  if (!confirm(`Deletar "${state.currentDocName}"?`)) return;

  const res = await deleteKnowledgeDoc(state.currentDocName);
  if (res.ok) {
    state.currentDocName = null;
    hideKnowledgePanels();
    document.getElementById("main-empty").style.display = "flex";
    loadKnowledgeDocs();
  } else {
    const err = await res.json();
    alert(`Erro ao deletar: ${err.detail || "erro desconhecido"}`);
  }
}

export function showNewDocForm() {
  hideKnowledgePanels();
  document.getElementById("kb-new-form").style.display = "flex";
  document.getElementById("kb-new-name-input").value = "";
  document.getElementById("kb-new-textarea").value = "";
  document.getElementById("main-empty").style.display = "none";
  document.getElementById("kb-new-name-input").focus();
}

export function cancelNewDoc() {
  hideKnowledgePanels();
  if (!state.currentDocName && !state.currentConversationId) {
    document.getElementById("main-empty").style.display = "flex";
  }
}

export async function createDoc() {
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

  const res = await createKnowledgeDoc(name, content);

  if (res.ok) {
    await loadKnowledgeDocs();
    openDoc(name);
  } else {
    const err = await res.json();
    alert(`Erro ao criar: ${err.detail || "erro desconhecido"}`);
  }
}
