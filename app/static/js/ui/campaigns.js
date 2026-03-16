import state from '../state.js';
import { escapeHtml } from '../utils.js';
import {
  getCampaigns, getCampaign, createCampaignApi,
  generateVariationsApi, editVariationApi,
  startCampaignApi, pauseCampaignApi, resumeCampaignApi, retryCampaignApi
} from '../api.js';

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
    alert("Preencha nome, mensagem e selecione o CSV.");
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
    alert(err.detail || "Erro ao criar campanha");
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

    const statusColors = { draft: "#888", running: "#25D366", paused: "#f57f17", blocked: "#c62828", completed: "#1565c0" };
    const statusLabels = { draft: "Rascunho", running: "Enviando", paused: "Pausada", blocked: "Bloqueada", completed: "Concluída" };
    const color = statusColors[c.status] || "#888";
    const label = statusLabels[c.status] || c.status;

    div.innerHTML = `
      <span class="conv-time" style="color:${color};font-weight:600;">${label}</span>
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
  const statusLabels = { draft: "Rascunho", running: "Enviando", paused: "Pausada", blocked: "Bloqueada", completed: "Concluída" };
  const statusColors = { draft: "#888", running: "#25D366", paused: "#f57f17", blocked: "#c62828", completed: "#1565c0" };
  statusEl.textContent = statusLabels[data.status] || data.status;
  statusEl.style.background = (statusColors[data.status] || "#888") + "20";
  statusEl.style.color = statusColors[data.status] || "#888";

  // Counts
  document.getElementById("campaign-sent-count").textContent = `\u2713 ${data.sent} enviados`;
  document.getElementById("campaign-failed-count").textContent = `\u2717 ${data.failed} falharam`;
  document.getElementById("campaign-pending-count").textContent = `\u2026 ${data.pending} pendentes`;

  const total = data.total || 1;
  const pct = Math.round((data.sent / total) * 100);
  document.getElementById("campaign-progress-bar").style.width = pct + "%";

  // Actions
  const actionsEl = document.getElementById("campaign-detail-actions");
  actionsEl.innerHTML = "";
  const btnStyle = "padding:8px 16px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;border:1px solid #ddd;";

  if (data.status === "draft") {
    if (data.variations.length === 0) {
      actionsEl.innerHTML += `<button onclick="generateVariations(${id})" style="${btnStyle}background:#e3f2fd;color:#1565c0;border-color:#bbdefb;">Gerar variações</button>`;
    } else {
      actionsEl.innerHTML += `<button onclick="startCampaign(${id})" style="${btnStyle}background:#25D366;color:#fff;border-color:#25D366;">Iniciar</button>`;
    }
  } else if (data.status === "running") {
    actionsEl.innerHTML += `<button onclick="pauseCampaign(${id})" style="${btnStyle}background:#fff3e0;color:#e65100;border-color:#ffcc80;">Pausar</button>`;
  } else if (data.status === "paused" || data.status === "blocked") {
    actionsEl.innerHTML += `<button onclick="resumeCampaign(${id})" style="${btnStyle}background:#25D366;color:#fff;border-color:#25D366;">Retomar</button>`;
  }
  if (data.failed > 0) {
    actionsEl.innerHTML += `<button onclick="retryCampaign(${id})" style="${btnStyle}background:#ffebee;color:#c62828;border-color:#ffcdd2;">Reenviar falhos</button>`;
  }

  // Variations
  const varList = document.getElementById("campaign-variations-list");
  varList.innerHTML = "";
  for (const v of data.variations) {
    const vDiv = document.createElement("div");
    vDiv.style.cssText = "padding:8px 12px;background:#f9f9f9;border-radius:8px;margin-bottom:6px;font-size:13px;line-height:1.4;white-space:pre-wrap;border:1px solid #eee;position:relative;";
    vDiv.innerHTML = `
      <span style="font-size:11px;font-weight:600;color:#888;">v${v.variation_index + 1}</span>
      <span style="font-size:11px;color:#bbb;margin-left:8px;">(${v.usage_count}x usado)</span>
      ${data.status === "draft" ? `<button onclick="editVariation(${id}, ${v.variation_index}, this)" style="position:absolute;top:6px;right:6px;background:none;border:none;cursor:pointer;font-size:12px;color:#888;">\u270E</button>` : ""}
      <div style="margin-top:4px;">${escapeHtml(v.variation_text)}</div>
    `;
    varList.appendChild(vDiv);
  }

  const varActions = document.getElementById("campaign-variations-actions");
  varActions.innerHTML = "";
  if (data.status === "draft") {
    if (data.variations.length > 0) {
      varActions.innerHTML = `<button onclick="generateVariations(${id})" style="padding:6px 12px;border:1px solid #ddd;border-radius:6px;background:#fff;cursor:pointer;font-size:12px;color:#555;">Regenerar variações</button>`;
    }
  }

  // Contacts
  const contactsList = document.getElementById("campaign-contacts-list");
  contactsList.innerHTML = "";
  for (const c of data.contacts) {
    const cDiv = document.createElement("div");
    const statusIcon = c.status === "sent" ? "\u2713" : c.status === "failed" ? "\u2717" : "\u2026";
    const statusColor = c.status === "sent" ? "#2e7d32" : c.status === "failed" ? "#c62828" : "#888";
    const timeStr = c.sent_at ? new Date(c.sent_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) : "";
    const errorStr = c.error_message ? ` — ${c.error_message}` : "";
    cDiv.style.cssText = "padding:6px 0;border-bottom:1px solid #f0f0f0;font-size:13px;display:flex;align-items:center;gap:8px;";
    cDiv.innerHTML = `
      <span style="color:${statusColor};font-weight:600;width:16px;text-align:center;">${statusIcon}</span>
      <span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(c.name || c.phone_number)}</span>
      <span style="font-size:11px;color:#999;flex-shrink:0;">${c.phone_number}</span>
      <span style="font-size:11px;color:${statusColor};flex-shrink:0;">${timeStr}${errorStr}</span>
    `;
    contactsList.appendChild(cDiv);
  }

  loadCampaigns(); // refresh sidebar list
}

export async function generateVariations(campaignId) {
  const btn = event.target;
  btn.disabled = true;
  btn.textContent = "Gerando...";
  try {
    const res = await generateVariationsApi(campaignId);
    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Erro ao gerar variações");
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
  textarea.style.cssText = "width:100%;min-height:80px;border:1px solid #1565c0;border-radius:6px;padding:8px;font-family:inherit;font-size:13px;resize:vertical;margin-top:4px;";

  const saveBtn = document.createElement("button");
  saveBtn.textContent = "Salvar";
  saveBtn.style.cssText = "padding:4px 12px;background:#25D366;color:#fff;border:none;border-radius:4px;font-size:12px;cursor:pointer;margin-top:4px;margin-right:4px;";

  const cancelBtn = document.createElement("button");
  cancelBtn.textContent = "Cancelar";
  cancelBtn.style.cssText = "padding:4px 12px;background:#fff;border:1px solid #ddd;border-radius:4px;font-size:12px;cursor:pointer;margin-top:4px;";

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
  if (!confirm("Iniciar o envio da campanha?")) return;
  await startCampaignApi(id);
  await openCampaignDetail(id);
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
  if (!confirm("Reenviar para todos os contatos que falharam?")) return;
  await retryCampaignApi(id);
  await openCampaignDetail(id);
}
