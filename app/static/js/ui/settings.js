import state from '../state.js';
import { escapeHtml } from '../utils.js';
import { getIsAdmin, getSettingsProfile, getSettingsPrompts, saveSettingsProfile, saveSettingsPrompts, resetPromptApi } from '../api.js';

export const PROMPT_LABELS = {
  postura: "Postura",
  tom: "Tom",
  regras: "Regras",
  approach_direta: "Abordagem Direta",
  approach_consultiva: "Abordagem Consultiva",
  approach_casual: "Abordagem Casual",
  summary_prompt: "Prompt de Resumo de Situacao",
  annotation_prompt: "Prompt de Anotacao Estrategica",
};

export const FUNNEL_STAGES = ["qualifying", "decided", "handbook_sent", "link_sent", "purchased"];

export async function openSettings() {
  document.getElementById("settings-status").textContent = "";
  state.settingsCurrentTab = "profile";

  // Check admin status
  try {
    const res = await getIsAdmin();
    const data = await res.json();
    state.settingsIsAdmin = data.is_admin;
  } catch (e) {
    state.settingsIsAdmin = false;
  }

  // Show/hide prompts tab
  const promptsTab = document.getElementById("settings-prompts-tab");
  promptsTab.style.display = state.settingsIsAdmin ? "" : "none";

  // Load data
  await loadSettingsProfile();
  if (state.settingsIsAdmin) {
    await loadSettingsPrompts();
  }

  // Reset tab state
  document.querySelectorAll(".settings-tab").forEach(t => {
    t.classList.toggle("active", t.dataset.stab === "profile");
  });

  renderSettingsTab("profile");
  document.getElementById("settings-modal").classList.add("open");
}

export function closeSettings() {
  document.getElementById("settings-modal").classList.remove("open");
}

export function switchSettingsTab(tab) {
  state.settingsCurrentTab = tab;
  document.querySelectorAll(".settings-tab").forEach(t => {
    t.classList.toggle("active", t.dataset.stab === tab);
  });
  document.getElementById("settings-status").textContent = "";
  renderSettingsTab(tab);
}

export async function loadSettingsPrompts() {
  try {
    const res = await getSettingsPrompts();
    state.settingsPrompts = await res.json();
  } catch (e) {
    state.settingsPrompts = {};
  }
}

export async function loadSettingsProfile() {
  try {
    const res = await getSettingsProfile();
    state.settingsProfile = await res.json();
  } catch (e) {
    state.settingsProfile = {};
  }
}

export function renderSettingsTab(tab) {
  const body = document.getElementById("settings-body");

  if (tab === "profile") {
    body.innerHTML = `
      <div class="settings-field">
        <label>Nome de exibicao</label>
        <input type="text" id="settings-display-name" value="${escapeHtml(state.settingsProfile.display_name || "")}" placeholder="Como a IA deve se apresentar (ex: Joao Silva)">
      </div>
      <div class="settings-field">
        <label>Contexto sobre voce</label>
        <textarea id="settings-context" rows="6" placeholder="Informacoes que a IA deve saber sobre voce. Ex: Trabalho na equipe do Caio. Sou responsavel pelo suporte tecnico. Nao sou o dono dos cursos.">${escapeHtml(state.settingsProfile.context || "")}</textarea>
      </div>
    `;
  } else if (tab === "prompts") {
    let html = "";
    for (const [key, label] of Object.entries(PROMPT_LABELS)) {
      const value = state.settingsPrompts[key] || "";
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

export async function saveSettings() {
  const statusEl = document.getElementById("settings-status");
  statusEl.textContent = "Salvando...";

  try {
    if (state.settingsCurrentTab === "profile") {
      const displayName = document.getElementById("settings-display-name").value.trim();
      const context = document.getElementById("settings-context").value.trim();

      const res = await saveSettingsProfile(displayName, context);

      if (res.ok) {
        state.settingsProfile = { display_name: displayName, context: context };
        statusEl.textContent = "Perfil salvo!";
      } else {
        statusEl.textContent = "Erro ao salvar perfil";
      }
    } else if (state.settingsCurrentTab === "prompts") {
      const updates = {};
      for (const key of Object.keys(PROMPT_LABELS)) {
        const el = document.getElementById(`settings-prompt-${key}`);
        if (el) updates[key] = el.value;
      }

      const res = await saveSettingsPrompts(updates);

      if (res.ok) {
        state.settingsPrompts = updates;
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

export async function resetPrompt(key) {
  const statusEl = document.getElementById("settings-status");

  const res = await resetPromptApi(key);

  if (res.ok) {
    await loadSettingsPrompts();
    renderSettingsTab("prompts");
    statusEl.textContent = `"${PROMPT_LABELS[key]}" resetado`;
    setTimeout(() => { statusEl.textContent = ""; }, 3000);
  }
}
