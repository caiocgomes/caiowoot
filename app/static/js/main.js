import state from './state.js';
import { connectWS, on as wsOn } from './ws.js';
import { notifyInbound, updateTitleBadge, initNotificationButton, setOpenConversation } from './notifications.js';

import { loadConversations, openConversation, renderConversationList, closeSidebar, toggleSidebar, filterConversations } from './ui/conversations.js';
import { isMobile } from './utils.js';
import { showToast } from './ui/toast.js';
import { assumeConversationApi } from './api.js';
import { appendMessage } from './ui/messages.js';
import { showDrafts, showDraftLoading, selectDraft, pollForUpdatedDrafts, regenerateDraft, regenerateAll } from './ui/drafts.js';
import { initCompose, sendMessage, rewriteText, formalizeText, translateText, handleFileSelect, removeAttachment, loadSuggestedAttachment, loadQuickAttachButtons } from './ui/compose.js';
import { initScheduleUI, loadScheduledSends, addScheduledPill, removeScheduledPill, cancelScheduledSend, computeSendAt, scheduleMessage, toggleScheduleDropdown, closeScheduleDropdown } from './ui/schedule.js';
import { loadKnowledgeDocs, openDoc, saveDoc, deleteDoc, showNewDocForm, cancelNewDoc, createDoc } from './ui/knowledge.js';
import { loadReviewItems, renderReviewStats, renderReviewList, openReviewItem, hideReviewDetail, reviewGoBack, validateAnnotation, rejectAnnotation, showPromoteModal, closePromoteModal, confirmPromote, afterReviewAction, loadRules, renderRulesList, openRuleDetail, hideRuleDetail, toggleRule, saveRule, cancelRuleEdit } from './ui/review.js';
import { loadCampaigns, openCampaignDetail, showCampaignForm, cancelCampaignForm, createCampaign, generateFormVariations, editFormVariation, createAndStartCampaign, generateVariations, editVariation, startCampaign, pauseCampaign, resumeCampaign, retryCampaign, hideCampaignPanels } from './ui/campaigns.js';
import { openSettings, closeSettings, switchSettingsTab, loadSettingsPrompts, loadSettingsProfile, renderSettingsTab, saveSettings, resetPrompt } from './ui/settings.js';
import { renderContextPanel, updateFunnelProduct, classifyConversation, updateFunnelStage } from './ui/context-panel.js';

// Wire up notification's openConversation reference
setOpenConversation(openConversation);

// --- Tools menu ---
const TOOL_LABELS = {
  knowledge: '📚 Conhecimento',
  review: '🧠 Aprendizado',
  campaigns: '📢 Campanhas',
};

function toggleToolsMenu() {
  const menu = document.getElementById('tools-menu');
  menu.classList.toggle('open');
}

function closeToolsMenu() {
  document.getElementById('tools-menu').classList.remove('open');
}

function backToConversations() {
  switchTab('conversations');
  if (isMobile() && state.currentConversationId) {
    document.body.classList.add('mobile-chat-active');
  }
}

// Close tools menu when clicking outside
document.addEventListener('click', (e) => {
  const menu = document.getElementById('tools-menu');
  const btn = document.getElementById('tools-menu-btn');
  if (menu && btn && !menu.contains(e.target) && !btn.contains(e.target)) {
    closeToolsMenu();
  }
});

// --- switchTab ---
function switchTab(tab) {
  state.currentTab = tab;
  closeToolsMenu();

  const convList = document.getElementById("conversation-list");
  const convSearch = document.getElementById("conv-search-wrapper");
  const kbList = document.getElementById("knowledge-list");
  const reviewList = document.getElementById("review-list");
  const campaignList = document.getElementById("campaign-list");

  // Hide all sidebar panels
  convList.style.display = "none";
  if (convSearch) convSearch.style.display = "none";
  kbList.style.display = "none";
  reviewList.style.display = "none";
  campaignList.style.display = "none";

  // Hide all main panels
  document.getElementById("chat-wrapper").style.display = "none";
  document.getElementById("main-empty").style.display = "none";
  document.getElementById("kb-editor").style.display = "none";
  document.getElementById("kb-new-form").style.display = "none";
  hideReviewDetail();
  hideRuleDetail();
  hideCampaignPanels();

  // Update header
  const title = document.getElementById('sidebar-title');
  const menuBtn = document.getElementById('tools-menu-btn');
  const backBtn = document.getElementById('tools-back-btn');

  if (tab === "conversations") {
    // Default state: show conversations
    title.textContent = "CaioWoot";
    menuBtn.style.display = "";
    backBtn.style.display = "none";
    convList.style.display = "block";
    if (convSearch) convSearch.style.display = "block";
    if (state.currentConversationId) {
      document.getElementById("chat-wrapper").style.display = "flex";
    } else {
      document.getElementById("main-empty").style.display = "flex";
      document.getElementById("main-empty").textContent = "Selecione uma conversa";
    }
  } else {
    // Tool state: show tool name with back button
    title.textContent = TOOL_LABELS[tab] || tab;
    menuBtn.style.display = "none";
    backBtn.style.display = "inline-block";

    if (tab === "knowledge") {
      kbList.style.display = "block";
      loadKnowledgeDocs();
    } else if (tab === "review") {
      reviewList.style.display = "block";
      document.getElementById("main-empty").style.display = "flex";
      document.getElementById("main-empty").textContent = "Selecione uma anotação ou regra";
      loadReviewItems();
      loadRules();
    } else if (tab === "campaigns") {
      campaignList.style.display = "block";
      document.getElementById("main-empty").style.display = "flex";
      document.getElementById("main-empty").textContent = "Selecione ou crie uma campanha";
      loadCampaigns();
    }
  }
}

// --- WebSocket event handlers ---
wsOn("new_message", (data) => {
  if (data.message.direction === "inbound") {
    notifyInbound(data.conversation_id, data.message.content);
  }
  loadConversations();
  if (data.conversation_id === state.currentConversationId) {
    appendMessage(data.message);
    if (data.message.direction === "inbound") {
      state.lastTriggerMessageId = data.message.id;
      showDraftLoading();
    }
  }
});

wsOn("drafts_ready", (data) => {
  console.log("drafts_ready received, drafts count:", data.drafts?.length, "match:", data.conversation_id === state.currentConversationId);
  if (data.conversation_id === state.currentConversationId) {
    showDrafts(data.drafts, data.draft_group_id);
    // Update context panel with AI classification
    if (data.funnel_product != null || data.funnel_stage != null || data.situation_summary != null) {
      renderContextPanel(
        { funnel_product: data.funnel_product, funnel_stage: data.funnel_stage },
        data.situation_summary,
      );
    }
  }
  loadConversations();
});

wsOn("message_sent", (data) => {
  if (data.conversation_id === state.currentConversationId) {
    appendMessage(data.message);
  }
  loadConversations();
});

wsOn("scheduled_send_created", (data) => {
  if (data.conversation_id === state.currentConversationId) {
    addScheduledPill(data.scheduled_send);
  }
  loadConversations();
});

wsOn("scheduled_send_cancelled", (data) => {
  if (data.conversation_id === state.currentConversationId) {
    removeScheduledPill(data.scheduled_send_id);
  }
  loadConversations();
});

wsOn("scheduled_send_completed", (data) => {
  if (data.conversation_id === state.currentConversationId) {
    removeScheduledPill(data.scheduled_send_id);
  }
  loadConversations();
});

wsOn("campaign_progress", (data) => {
  if (state.currentTab === "campaigns" && state.currentCampaignId === data.campaign_id) {
    openCampaignDetail(data.campaign_id);
  }
  if (state.currentTab === "campaigns") {
    loadCampaigns();
  }
});

function setQualifyingUI(isQualifying) {
  document.getElementById("qualifying-banner").style.display = isQualifying ? "flex" : "none";
  document.getElementById("compose").style.display = isQualifying ? "none" : "";
}

wsOn("conversation_qualified", (data) => {
  loadConversations();
  if (data.conversation_id === state.currentConversationId) {
    setQualifyingUI(false);
    // Update context panel with summary from qualifying
    if (data.summary || data.funnel_product || data.funnel_stage) {
      renderContextPanel(
        { funnel_product: data.funnel_product, funnel_stage: data.funnel_stage },
        data.summary,
      );
    }
  }
});

wsOn("conversation_assumed", (data) => {
  loadConversations();
  if (data.conversation_id === state.currentConversationId) {
    setQualifyingUI(false);
  }
});

wsOn("campaign_status", (data) => {
  if (state.currentTab === "campaigns" && state.currentCampaignId === data.campaign_id) {
    openCampaignDetail(data.campaign_id);
  }
  if (state.currentTab === "campaigns") {
    loadCampaigns();
  }
});

// --- Visibility change ---
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") {
    if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
      connectWS();
    }
    state.unreadCount = 0;
    updateTitleBadge();
    loadConversations();
  }
});

// --- Init ---
initCompose();
initScheduleUI();
initNotificationButton();
loadConversations();
loadQuickAttachButtons();
connectWS();

// --- Expose functions to window for onclick handlers in HTML ---
window.switchTab = switchTab;
window.toggleToolsMenu = toggleToolsMenu;
window.backToConversations = backToConversations;
window.openConversation = openConversation;
window.closeSidebar = closeSidebar;
window.toggleSidebar = toggleSidebar;
window.openSettings = openSettings;
window.closeSettings = closeSettings;
window.switchSettingsTab = switchSettingsTab;
window.saveSettings = saveSettings;
window.resetPrompt = resetPrompt;
window.openDoc = openDoc;
window.saveDoc = saveDoc;
window.deleteDoc = deleteDoc;
window.showNewDocForm = showNewDocForm;
window.cancelNewDoc = cancelNewDoc;
window.createDoc = createDoc;
window.openReviewItem = openReviewItem;
window.reviewGoBack = reviewGoBack;
window.validateAnnotation = validateAnnotation;
window.rejectAnnotation = rejectAnnotation;
window.showPromoteModal = showPromoteModal;
window.closePromoteModal = closePromoteModal;
window.confirmPromote = confirmPromote;
window.toggleRule = toggleRule;
window.saveRule = saveRule;
window.cancelRuleEdit = cancelRuleEdit;
window.showCampaignForm = showCampaignForm;
window.cancelCampaignForm = cancelCampaignForm;
window.createCampaign = createCampaign;
window.generateFormVariations = generateFormVariations;
window.editFormVariation = editFormVariation;
window.createAndStartCampaign = createAndStartCampaign;
window.openCampaignDetail = openCampaignDetail;
window.generateVariations = generateVariations;
window.editVariation = editVariation;
window.startCampaign = startCampaign;
window.pauseCampaign = pauseCampaign;
window.resumeCampaign = resumeCampaign;
window.retryCampaign = retryCampaign;
window.cancelScheduledSend = cancelScheduledSend;
window.classifyConversation = classifyConversation;
window.updateFunnelProduct = updateFunnelProduct;
window.updateFunnelStage = updateFunnelStage;
window.loadSuggestedAttachment = loadSuggestedAttachment;
window.formalizeText = formalizeText;
window.translateText = translateText;
window.filterConversations = filterConversations;

async function assumeConversation() {
  if (!state.currentConversationId) return;
  const res = await assumeConversationApi(state.currentConversationId);
  if (res.ok) {
    setQualifyingUI(false);
    showToast("Conversa assumida!", "success");
    loadConversations();
  }
}
window.assumeConversation = assumeConversation;

// --- Mobile context panel toggle ---
function toggleMobileContext() {
  const panel = document.getElementById('context-panel');
  if (!panel) return;
  if (panel.style.display === 'flex') {
    panel.style.display = 'none';
  } else {
    panel.style.display = 'flex';
    panel.style.position = 'fixed';
    panel.style.top = '0';
    panel.style.right = '0';
    panel.style.bottom = '0';
    panel.style.width = '85vw';
    panel.style.zIndex = '200';
    panel.style.boxShadow = '-2px 0 12px rgba(0,0,0,0.2)';
  }
}
window.toggleMobileContext = toggleMobileContext;

// --- Mobile bottom nav tab switching ---
window.switchBottomTab = function(tab) {
  document.querySelectorAll('.bottom-nav-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tab);
    // Set filled icon for active chat tab
    const icon = t.querySelector('.material-symbols-outlined');
    if (icon && t.dataset.tab === 'chat') {
      icon.style.fontVariationSettings = tab === 'chat' ? "'FILL' 1" : "'FILL' 0";
    }
  });

  const chatArea = document.getElementById('chat-area');
  const contextPanel = document.getElementById('context-panel');
  const placeholder = document.getElementById('bottom-nav-placeholder');

  if (tab === 'chat') {
    if (chatArea) chatArea.style.display = 'flex';
    if (contextPanel) contextPanel.style.display = '';
    if (placeholder) placeholder.style.display = 'none';
  } else {
    if (chatArea) chatArea.style.display = 'none';
    if (contextPanel) contextPanel.style.display = 'none';
    if (placeholder) placeholder.style.display = 'flex';
  }
};
