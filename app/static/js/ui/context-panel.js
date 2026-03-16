import state from '../state.js';
import { classifyConversationApi, updateFunnelApi } from '../api.js';

export const FUNNEL_STAGES = ["qualifying", "decided", "handbook_sent", "link_sent", "purchased"];

export function renderContextPanel(conv, situationSummary) {
  // Product
  const select = document.getElementById("ctx-product-select");
  select.value = conv.funnel_product || "";

  // Stage
  const currentStage = conv.funnel_stage;
  const stageIdx = FUNNEL_STAGES.indexOf(currentStage);
  document.querySelectorAll(".ctx-stage-item").forEach((item, i) => {
    item.classList.remove("active", "done");
    if (item.dataset.stage === currentStage) {
      item.classList.add("active");
    } else if (stageIdx >= 0 && i < stageIdx) {
      item.classList.add("done");
    }
  });

  // Summary
  document.getElementById("ctx-summary-text").textContent =
    situationSummary || "Sem resumo ainda";
}

export async function updateFunnelProduct(value) {
  if (!state.currentConversationId) return;
  await updateFunnelApi(state.currentConversationId, { funnel_product: value || null });
}

export async function classifyConversation() {
  if (!state.currentConversationId) return;
  const btn = document.getElementById("ctx-classify-btn");
  btn.disabled = true;
  btn.textContent = "Analisando...";
  try {
    const res = await classifyConversationApi(state.currentConversationId);
    if (res.ok) {
      const data = await res.json();
      renderContextPanel(
        { funnel_product: data.product, funnel_stage: data.stage },
        data.summary,
      );
    } else {
      console.error("Classify failed:", res.status);
      btn.textContent = "Erro - tentar de novo";
      return;
    }
  } catch (e) {
    console.error("Classify error:", e);
    btn.textContent = "Erro - tentar de novo";
    return;
  }
  btn.disabled = false;
  btn.textContent = "Atualizar";
}

export async function updateFunnelStage(stage) {
  if (!state.currentConversationId) return;
  await updateFunnelApi(state.currentConversationId, { funnel_stage: stage });
  // Re-render stage UI
  const stageIdx = FUNNEL_STAGES.indexOf(stage);
  document.querySelectorAll(".ctx-stage-item").forEach((item, i) => {
    item.classList.remove("active", "done");
    if (item.dataset.stage === stage) {
      item.classList.add("active");
    } else if (i < stageIdx) {
      item.classList.add("done");
    }
  });
}
