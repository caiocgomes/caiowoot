import state from '../state.js';
import { escapeHtml, normalizeTimestamp } from '../utils.js';
import { getScheduledSends, createScheduledSend, deleteScheduledSend } from '../api.js';
import { removeAttachment } from './compose.js';
import { showToast } from './toast.js';

export async function loadScheduledSends(convId) {
  const container = document.getElementById("scheduled-pills");
  container.innerHTML = "";
  state.scheduledSends = [];
  try {
    const res = await getScheduledSends(convId);
    if (!res.ok) return;
    state.scheduledSends = await res.json();
    for (const s of state.scheduledSends) {
      addScheduledPill(s);
    }
  } catch (e) {
    console.error("Failed to load scheduled sends:", e);
  }
}

export function addScheduledPill(send) {
  const container = document.getElementById("scheduled-pills");
  // Remove existing pill for this id if any
  const existing = container.querySelector(`[data-scheduled-id="${send.id}"]`);
  if (existing) existing.remove();

  const pill = document.createElement("div");
  pill.className = "scheduled-pill";
  pill.dataset.scheduledId = send.id;

  const sendAt = new Date(normalizeTimestamp(send.send_at));
  const timeStr = sendAt.toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit",
    hour: "2-digit", minute: "2-digit",
    timeZone: "America/Sao_Paulo",
  });
  const preview = (send.content || "").substring(0, 60);

  pill.innerHTML = `
    <span class="scheduled-pill-icon">&#x1F551;</span>
    <div class="scheduled-pill-info">
      <div class="scheduled-pill-time">Agendado para ${timeStr}</div>
      <div class="scheduled-pill-preview">${escapeHtml(preview)}</div>
    </div>
    <button class="scheduled-pill-cancel" onclick="cancelScheduledSend(${send.id})">Cancelar</button>
  `;
  container.appendChild(pill);
}

export function removeScheduledPill(sendId) {
  const container = document.getElementById("scheduled-pills");
  const pill = container.querySelector(`[data-scheduled-id="${sendId}"]`);
  if (pill) pill.remove();
  state.scheduledSends = state.scheduledSends.filter(s => s.id !== sendId);
}

export async function cancelScheduledSend(sendId) {
  try {
    const res = await deleteScheduledSend(sendId);
    if (!res.ok) {
      const err = await res.json();
      showToast(`Erro ao cancelar: ${err.detail || "erro desconhecido"}`, 'error');
    }
  } catch (e) {
    showToast("Erro ao cancelar agendamento", 'error');
  }
}

export function computeSendAt(option) {
  const now = new Date();
  if (option.minutes) {
    return new Date(now.getTime() + option.minutes * 60 * 1000).toISOString();
  }
  if (option.preset === "tomorrow-9") {
    const d = new Date(now);
    d.setDate(d.getDate() + 1);
    d.setHours(9, 0, 0, 0);
    return d.toISOString();
  }
  if (option.preset === "tomorrow-14") {
    const d = new Date(now);
    d.setDate(d.getDate() + 1);
    d.setHours(14, 0, 0, 0);
    return d.toISOString();
  }
  return option.custom;
}

export async function scheduleMessage(sendAt) {
  const input = document.getElementById("draft-input");
  const text = input.value.trim();
  if (!text || !state.currentConversationId) return;

  const body = {
    content: text,
    send_at: sendAt,
  };
  if (state.currentDraftId) body.draft_id = state.currentDraftId;
  if (state.currentDraftGroupId) body.draft_group_id = state.currentDraftGroupId;
  if (state.selectedDraftIndex !== null) body.selected_draft_index = state.selectedDraftIndex;

  try {
    const res = await createScheduledSend(state.currentConversationId, body);

    if (!res.ok) {
      const err = await res.json();
      showToast(`Erro ao agendar: ${err.detail || "erro desconhecido"}`, 'error');
      return;
    }

    // Reset UI like after send
    input.value = "";
    state.currentDraftId = null;
    state.currentDraftGroupId = null;
    state.currentDrafts = [];
    state.selectedDraftIndex = null;
    state.regenerationCount = 0;
    removeAttachment();
    document.getElementById("justification").style.display = "none";
    document.getElementById("draft-cards-container").style.display = "none";
    document.getElementById("instruction-input").value = "";
    closeScheduleDropdown();
  } catch (e) {
    showToast("Erro ao agendar: falha na conexao", 'error');
  }
}

export function toggleScheduleDropdown() {
  const dropdown = document.getElementById("schedule-dropdown");
  dropdown.classList.toggle("open");
  document.getElementById("schedule-custom-row").style.display = "none";
}

export function closeScheduleDropdown() {
  document.getElementById("schedule-dropdown").classList.remove("open");
  document.getElementById("schedule-custom-row").style.display = "none";
}

export function initScheduleUI() {
  document.getElementById("schedule-btn").onclick = toggleScheduleDropdown;

  document.querySelectorAll(".schedule-option").forEach(opt => {
    opt.onclick = () => {
      if (opt.dataset.minutes) {
        const sendAt = computeSendAt({ minutes: parseInt(opt.dataset.minutes) });
        scheduleMessage(sendAt);
      } else if (opt.dataset.preset) {
        const sendAt = computeSendAt({ preset: opt.dataset.preset });
        scheduleMessage(sendAt);
      } else if (opt.dataset.custom) {
        const customRow = document.getElementById("schedule-custom-row");
        customRow.style.display = customRow.style.display === "none" ? "block" : "none";
      }
    };
  });

  document.getElementById("schedule-custom-confirm").onclick = () => {
    const dt = document.getElementById("schedule-custom-datetime").value;
    if (!dt) { showToast("Selecione data e hora", 'error'); return; }
    const sendAt = new Date(dt).toISOString();
    scheduleMessage(sendAt);
  };

  // Close dropdown when clicking outside
  document.addEventListener("click", (e) => {
    const wrapper = document.getElementById("schedule-wrapper");
    if (!wrapper.contains(e.target)) {
      closeScheduleDropdown();
    }
  });
}
