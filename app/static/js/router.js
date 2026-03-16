import state from './state.js';

const views = {
  'conversations': { sidebar: 'conversation-list', main: null, tab: 'conversations', emptyText: 'Selecione uma conversa' },
  'chat': { sidebar: 'conversation-list', main: 'chat-wrapper', tab: 'conversations' },
  'knowledge': { sidebar: 'knowledge-list', main: null, tab: 'knowledge' },
  'kb-editor': { sidebar: 'knowledge-list', main: 'kb-editor', tab: 'knowledge' },
  'kb-new': { sidebar: 'knowledge-list', main: 'kb-new-form', tab: 'knowledge' },
  'review': { sidebar: 'review-list', main: null, tab: 'review', emptyText: 'Selecione uma anotação ou regra' },
  'review-detail': { sidebar: 'review-list', main: 'review-detail', tab: 'review' },
  'rule-detail': { sidebar: 'review-list', main: 'rule-detail', tab: 'review' },
  'campaigns': { sidebar: 'campaign-list', main: null, tab: 'campaigns', emptyText: 'Selecione ou crie uma campanha' },
  'campaign-form': { sidebar: 'campaign-list', main: 'campaign-form', tab: 'campaigns' },
  'campaign-detail': { sidebar: 'campaign-list', main: 'campaign-detail', tab: 'campaigns' },
};

const sidebarPanels = ['conversation-list', 'knowledge-list', 'review-list', 'campaign-list'];
const mainPanels = ['chat-wrapper', 'kb-editor', 'kb-new-form', 'review-detail', 'rule-detail', 'campaign-form', 'campaign-detail'];

export function navigate(viewName) {
  const view = views[viewName];
  if (!view) return;

  // Hide all sidebar panels
  for (const id of sidebarPanels) {
    document.getElementById(id).style.display = 'none';
  }
  // Hide all main panels
  for (const id of mainPanels) {
    document.getElementById(id).style.display = 'none';
  }

  // Show sidebar
  if (view.sidebar) {
    document.getElementById(view.sidebar).style.display = 'block';
  }

  // Show main or empty
  const mainEmpty = document.getElementById('main-empty');
  if (view.main) {
    document.getElementById(view.main).style.display = 'flex';
    mainEmpty.style.display = 'none';
  } else {
    mainEmpty.style.display = 'flex';
    mainEmpty.textContent = view.emptyText || '';
  }

  // Update tabs
  if (view.tab) {
    state.currentTab = view.tab;
    document.querySelectorAll('.sidebar-tab').forEach(t => {
      t.classList.toggle('active', t.dataset.tab === view.tab);
    });
  }

  // Context panel: only show in chat view
  const ctxPanel = document.getElementById('context-panel');
  if (ctxPanel) {
    ctxPanel.style.display = viewName === 'chat' ? '' : 'none';
  }
}
