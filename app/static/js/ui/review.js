import state from '../state.js';
import { escapeHtml, formatTime, isMobile } from '../utils.js';
import { getReviewItems, validateAnnotationApi, rejectAnnotationApi, promoteAnnotationApi, getRules, toggleRuleApi, saveRuleApi } from '../api.js';

function hideKnowledgePanels() {
  document.getElementById("kb-editor").style.display = "none";
  document.getElementById("kb-new-form").style.display = "none";
}

export async function loadReviewItems() {
  const res = await getReviewItems();
  const data = await res.json();
  state.currentReviewItems = data.annotations || [];
  renderReviewStats(data.stats, data.history_stats);
  renderReviewList(data.annotations);
}

export function renderReviewStats(stats, historyStats) {
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

export function renderReviewList(annotations) {
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
    div.className = "review-item" + (ann.id === state.currentReviewItemId ? " active" : "");
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

export function openReviewItem(id) {
  const ann = state.currentReviewItems.find(a => a.id === id);
  if (!ann) return;
  state.currentReviewItemId = id;

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
    item.classList.toggle("active", state.currentReviewItems[Array.from(item.parentNode.children).indexOf(item)]?.id === id);
  });
}

export function hideReviewDetail() {
  document.getElementById("review-detail").style.display = "none";
}

export function reviewGoBack() {
  state.currentReviewItemId = null;
  hideReviewDetail();
  document.body.classList.remove("mobile-chat-active");
  document.getElementById("main-empty").style.display = "flex";
  document.getElementById("main-empty").textContent = "Selecione uma anotação ou regra";
}

export async function validateAnnotation() {
  if (!state.currentReviewItemId) return;
  const res = await validateAnnotationApi(state.currentReviewItemId);
  if (res.ok) {
    afterReviewAction();
  }
}

export async function rejectAnnotation() {
  if (!state.currentReviewItemId) return;
  const res = await rejectAnnotationApi(state.currentReviewItemId);
  if (res.ok) {
    afterReviewAction();
  }
}

export function showPromoteModal() {
  if (!state.currentReviewItemId) return;
  const ann = state.currentReviewItems.find(a => a.id === state.currentReviewItemId);
  if (!ann) return;
  document.getElementById("promote-rule-input").value = ann.strategic_annotation || "";
  document.getElementById("promote-modal").classList.add("open");
}

export function closePromoteModal() {
  document.getElementById("promote-modal").classList.remove("open");
}

export async function confirmPromote() {
  if (!state.currentReviewItemId) return;
  const ruleText = document.getElementById("promote-rule-input").value.trim();
  if (!ruleText) return;

  const res = await promoteAnnotationApi(state.currentReviewItemId, ruleText);
  if (res.ok) {
    closePromoteModal();
    afterReviewAction();
  }
}

export function afterReviewAction() {
  state.currentReviewItemId = null;
  hideReviewDetail();
  if (isMobile()) document.body.classList.remove("mobile-chat-active");
  document.getElementById("main-empty").style.display = "flex";
  document.getElementById("main-empty").textContent = "Anotação processada";
  loadReviewItems();
  loadRules();
}

// --- Rules ---

export async function loadRules() {
  const res = await getRules();
  const data = await res.json();
  state.currentRules = data.rules || [];
  renderRulesList(state.currentRules);
}

export function renderRulesList(rules) {
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
    div.className = "rule-item" + (rule.id === state.currentRuleId ? " active" : "") + (rule.is_active ? "" : " inactive");
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

export function openRuleDetail(id) {
  const rule = state.currentRules.find(r => r.id === id);
  if (!rule) return;
  state.currentRuleId = id;

  hideKnowledgePanels();
  hideReviewDetail();
  hideRuleDetail();
  document.getElementById("rule-detail").style.display = "flex";
  document.getElementById("main-empty").style.display = "none";
  document.getElementById("rule-edit-textarea").value = rule.rule_text;

  renderRulesList(state.currentRules);
}

export function hideRuleDetail() {
  document.getElementById("rule-detail").style.display = "none";
}

export async function toggleRule(id) {
  await toggleRuleApi(id);
  await loadRules();
}

export async function saveRule() {
  if (!state.currentRuleId) return;
  const text = document.getElementById("rule-edit-textarea").value.trim();
  if (!text) return;

  await saveRuleApi(state.currentRuleId, text);

  state.currentRuleId = null;
  hideRuleDetail();
  document.getElementById("main-empty").style.display = "flex";
  document.getElementById("main-empty").textContent = "Regra salva";
  await loadRules();
}

export function cancelRuleEdit() {
  state.currentRuleId = null;
  hideRuleDetail();
  document.getElementById("main-empty").style.display = "flex";
  document.getElementById("main-empty").textContent = "Selecione uma anotação ou regra";
  renderRulesList(state.currentRules);
}
