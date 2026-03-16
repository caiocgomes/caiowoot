import state from '../state.js';
import { escapeHtml } from '../utils.js';
import {
  getCampaigns, getCampaign, createCampaignApi,
  generateVariationsApi, editVariationApi,
  startCampaignApi, pauseCampaignApi, resumeCampaignApi, retryCampaignApi
} from '../api.js';
import { showToast, showConfirm } from './toast.js';

// Task 4.5: Module-level constants for campaign status display
const STATUS_COLORS = { draft: "#888", running: "#25D366", paused: "#f57f17", blocked: "#c62828", completed: "#1565c0" };
const STATUS_LABELS = { draft: "Rascunho", running: "Enviando", paused: "Pausada", blocked: "Bloqueada", completed: "Concluída" };

export function hideCampaignPanels() {
  document.getElementById("campaign-form").style.display = "none";
  document.getElementById("campaign-detail").style.display = "none";
}

export function showCampaignForm() {
  hideCampaignPanels();
  document.getElementById("main-empty").style.display = "none";
  document.getElementById("campaign-form").style.display = "flex";
  document.getElementById("campaign-name-input").value = "";
  document.getElementById("campaign-msg-input").value = "";
  document.getElementById("campaign-csv-input").value = "";
  document.getElementById("campaign-img-input").value = "";
  document.getElementById("campaign-min-interval").value = "60";
  document.getElementById("campaign-max-interval").value = "180";
}

export function cancelCampaignForm() {
  hideCampaignPanels();
  document.getElementById("main-empty").style.display = "flex";
  document.getElementById("main-empty").textContent = "Selecione ou crie uma campanha";
}

export async function createCampaign() {
  const name = document.getElementById("campaign-name-input").value.trim();
  const baseMessage = document.getElementById("campaign-msg-input").value.trim();
  const csvInput = document.getElementById("campaign-csv-input");
  const imgInput = document.getElementById("campaign-img-input");
  const minInterval = document.getElementById("campaign-min-interval").value;
  const maxInterval = document.getElementById("campaign-max-interval").value;

  if (!name || !baseMessage || !csvInput.files.length) {
    showToast("Preencha nome, mensagem e selecione o CSV.", 'error');
    return;
  }

  const formData = new FormData();
  formData.append("name", name);
  formData.append("base_message", baseMessage);
  formData.append("csv_file", csvInput.files[0]);
  formData.append("min_interval", minInterval);
  formData.append("max_interval", maxInterval);
  if (imgInput.files.length) {
    formData.append("image", imgInput.files[0]);
  }

  const res = await createCampaignApi(formData);
  if (!res.ok) {
    const err = await res.json();
    showToast(err.detail || "Erro ao criar campanha", 'error');
    return;
  }
  const data = await res.json();
  await loadCampaigns();
  openCampaignDetail(data.campaign.id);
}

export async function loadCampaigns() {
  const res = await getCampaigns();
  const campaigns = await res.json();
  const container = document.getElementById("campaign-items");
  container.innerHTML = "";

  for (const c of campaigns) {
    const div = document.createElement("div");
    div.className = "conv-item" + (c.id === state.currentCampaignId ? " active" : "");
    div.onclick = () => openCampaignDetail(c.id);

    const color = STATUS_COLORS[c.status] || "#888";
    const label = STATUS_LABELS[c.status] || c.status;

    div.innerHTML = `
      <span class="conv-time campaign-sidebar-status" style="color:${color};">${label}</span>
      <div class="conv-name">${escapeHtml(c.name)}</div>
      <div class="conv-preview">${c.sent || 0}/${c.total || 0} enviados</div>
    `;
    container.appendChild(div);
  }
}

export async function openCampaignDetail(id) {
  state.currentCampaignId = id;
  hideCampaignPanels();
  document.getElementById("main-empty").style.display = "none";
  document.getElementById("campaign-detail").style.display = "flex";

  const res = await getCampaign(id);
  if (!res.ok) return;
  const data = await res.json();

  document.getElementById("campaign-detail-name").textContent = data.name;

  const statusEl = document.getElementById("campaign-detail-status");
  statusEl.textContent = STATUS_LABELS[data.status] || data.status;
  statusEl.style.background = (STATUS_COLORS[data.status] || "#888") + "20";
  statusEl.style.color = STATUS_COLORS[data.status] || "#888";

  // Counts
  document.getElementById("campaign-sent-count").textContent = `\u2713 ${data.sent} enviados`;
  document.getElementById("campaign-failed-count").textContent = `\u2717 ${data.failed} falharam`;
  document.getElementById("campaign-pending-count").textContent = `\u2026 ${data.pending} pendentes`;

  const total = data.total || 1;
  const pct = Math.round((data.sent / total) * 100);
  document.getElementById("campaign-progress-bar").style.width = pct + "%";

  // Actions (Task 4.4: use CSS classes instead of inline styles)
  const actionsEl = document.getElementById("campaign-detail-actions");
  actionsEl.innerHTML = "";

  if (data.status === "draft") {
    if (data.variations.length === 0) {
      actionsEl.innerHTML += `<button data-campaign-id="${id}" class="campaign-action-btn generate campaign-generate-btn">Gerar variações</button>`;
    } else {
      actionsEl.innerHTML += `<button onclick="startCampaign(${id})" class="campaign-action-btn primary">Iniciar</button>`;
    }
  } else if (data.status === "running") {
    actionsEl.innerHTML += `<button onclick="pauseCampaign(${id})" class="campaign-action-btn pause">Pausar</button>`;
  } else if (data.status === "paused" || data.status === "blocked") {
    actionsEl.innerHTML += `<button onclick="resumeCampaign(${id})" class="campaign-action-btn primary">Retomar</button>`;
  }
  if (data.failed > 0) {
    actionsEl.innerHTML += `<button onclick="retryCampaign(${id})" class="campaign-action-btn retry">Reenviar falhos</button>`;
  }

  // Task 4.6: Attach event listener for generate button instead of relying on event.target
  const genBtn = actionsEl.querySelector('.campaign-generate-btn');
  if (genBtn) {
    genBtn.addEventListener('click', () => generateVariations(id, genBtn));
  }

  // Variations (Task 4.4: use CSS classes)
  const varList = document.getElementById("campaign-variations-list");
  varList.innerHTML = "";
  for (const v of data.variations) {
    const vDiv = document.createElement("div");
    vDiv.className = "campaign-variation";
    vDiv.innerHTML = `
      <span class="campaign-variation-label">v${v.variation_index + 1}</span>
      <span class="campaign-variation-usage">(${v.usage_count}x usado)</span>
      ${data.status === "draft" ? `<button onclick="editVariation(${id}, ${v.variation_index}, this)" class="campaign-variation-edit-inline">\u270E</button>` : ""}
      <div class="campaign-variation-body">${escapeHtml(v.variation_text)}</div>
    `;
    varList.appendChild(vDiv);
  }

  const varActions = document.getElementById("campaign-variations-actions");
  varActions.innerHTML = "";
  if (data.status === "draft") {
    if (data.variations.length > 0) {
      varActions.innerHTML = `<button data-campaign-id="${id}" class="campaign-action-btn secondary campaign-generate-btn">Regenerar variações</button>`;
      const regenBtn = varActions.querySelector('.campaign-generate-btn');
      if (regenBtn) {
        regenBtn.addEventListener('click', () => generateVariations(id, regenBtn));
      }
    }
  }

  // Contacts (Task 4.4: use CSS classes)
  const contactsList = document.getElementById("campaign-contacts-list");
  contactsList.innerHTML = "";
  for (const c of data.contacts) {
    const cDiv = document.createElement("div");
    cDiv.className = "campaign-contact";
    const statusIcon = c.status === "sent" ? "\u2713" : c.status === "failed" ? "\u2717" : "\u2026";
    const statusColor = c.status === "sent" ? "#2e7d32" : c.status === "failed" ? "#c62828" : "#888";
    const timeStr = c.sent_at ? new Date(c.sent_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) : "";
    const errorStr = c.error_message ? ` — ${c.error_message}` : "";
    cDiv.innerHTML = `
      <span class="campaign-contact-icon" style="color:${statusColor};">${statusIcon}</span>
      <span class="campaign-contact-name">${escapeHtml(c.name || c.phone_number)}</span>
      <span class="campaign-contact-phone">${c.phone_number}</span>
      <span class="campaign-contact-status" style="color:${statusColor};">${timeStr}${errorStr}</span>
    `;
    contactsList.appendChild(cDiv);
  }

  loadCampaigns(); // refresh sidebar list
}

// Task 4.6: Accept button element directly instead of relying on implicit event.target
export async function generateVariations(campaignId, btn) {
  btn.disabled = true;
  btn.textContent = "Gerando...";
  try {
    const res = await generateVariationsApi(campaignId);
    if (!res.ok) {
      const err = await res.json();
      showToast(err.detail || "Erro ao gerar variações", 'error');
      return;
    }
    await openCampaignDetail(campaignId);
  } finally {
    btn.disabled = false;
  }
}

export async function editVariation(campaignId, variationIdx, btnEl) {
  const container = btnEl.closest("div");
  const textDiv = container.querySelector("div");
  const currentText = textDiv.textContent;

  const textarea = document.createElement("textarea");
  textarea.value = currentText;
  textarea.className = "campaign-variation-textarea";

  const saveBtn = document.createElement("button");
  saveBtn.textContent = "Salvar";
  saveBtn.className = "campaign-variation-save-btn";

  const cancelBtn = document.createElement("button");
  cancelBtn.textContent = "Cancelar";
  cancelBtn.className = "campaign-variation-cancel-btn";

  textDiv.replaceWith(textarea);
  btnEl.style.display = "none";
  container.appendChild(saveBtn);
  container.appendChild(cancelBtn);

  saveBtn.onclick = async () => {
    const res = await editVariationApi(campaignId, variationIdx, textarea.value);
    if (res.ok) await openCampaignDetail(campaignId);
  };
  cancelBtn.onclick = () => openCampaignDetail(campaignId);
}

export async function startCampaign(id) {
  showConfirm("Iniciar o envio da campanha?", async () => {
    await startCampaignApi(id);
    await openCampaignDetail(id);
  });
}

export async function pauseCampaign(id) {
  await pauseCampaignApi(id);
  await openCampaignDetail(id);
}

export async function resumeCampaign(id) {
  await resumeCampaignApi(id);
  await openCampaignDetail(id);
}

export async function retryCampaign(id) {
  showConfirm("Reenviar para todos os contatos que falharam?", async () => {
    await retryCampaignApi(id);
    await openCampaignDetail(id);
  });
}
