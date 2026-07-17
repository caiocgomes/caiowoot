## 1. CSS: Tokens e Extração

- [x] 1.1 Criar `css/tokens.css` com custom properties (cores, spacing, radius, fontes)
- [x] 1.2 Extrair CSS do index.html para `css/base.css` (reset, layout, tipografia, msg bubbles, date separator)
- [x] 1.3 Extrair CSS para `css/sidebar.css` (sidebar, tabs, conversation list items)
- [x] 1.4 Extrair CSS para `css/compose.css` (draft cards, compose area, buttons, instruction bar, attachment bar, quick-attach)
- [x] 1.5 Extrair CSS para `css/context-panel.css` (context panel, funnel stages, summary)
- [x] 1.6 Extrair CSS para `css/knowledge.css` (kb editor, kb new form)
- [x] 1.7 Extrair CSS para `css/review.css` (review list, review detail, rules, promote modal)
- [x] 1.8 Extrair CSS para `css/campaigns.css` (campaign form, detail, progress, variations, contacts)
- [x] 1.9 Extrair CSS para `css/settings.css` (settings modal, tabs, fields)
- [x] 1.10 Extrair CSS para `css/mobile.css` (media queries mobile)
- [x] 1.11 Substituir valores literais por tokens em todos os arquivos CSS
- [x] 1.12 Remover bloco `<style>` e inline styles do index.html, adicionar `<link>` para cada CSS
- [ ] 1.13 Verificar que visual está idêntico ao antes

## 2. JS: Módulos Fundacionais

- [x] 2.1 Criar `js/state.js` extraindo as 10 variáveis globais do topo de app.js
- [x] 2.2 Criar `js/utils.js` extraindo escapeHtml, formatTime, normalizeTimestamp, formatTimeShort, formatDateSeparator, isMobile, autoResize
- [x] 2.3 Criar `js/api.js` centralizando todas as chamadas fetch (incluindo 401 interceptor) — catalogar todas as chamadas no app.js atual
- [x] 2.4 Criar `js/ws.js` extraindo connectWS, handleWSEvent, com sistema de registro de handlers por event type
- [x] 2.5 Criar `js/notifications.js` extraindo playNotificationSound, updateTitleBadge, notifyInbound, initNotificationButton
- [x] 2.6 Criar `js/router.js` com registro de views e função navigate()

## 3. JS: Módulos de UI

- [x] 3.1 Criar `js/ui/conversations.js` extraindo loadConversations, renderConversationList, openConversation
- [x] 3.2 Criar `js/ui/messages.js` extraindo appendMessage e render de mensagens
- [x] 3.3 Criar `js/ui/drafts.js` extraindo showDrafts, selectDraft, pollForUpdatedDrafts, regenerateDraft, regenerateAll
- [x] 3.4 Criar `js/ui/compose.js` extraindo sendMessage, rewriteText, handleFileSelect, removeAttachment, loadSuggestedAttachment, loadQuickAttachButtons
- [x] 3.5 Criar `js/ui/schedule.js` extraindo loadScheduledSends, addScheduledPill, removeScheduledPill, cancelScheduledSend, computeSendAt, scheduleMessage, initScheduleUI, toggleScheduleDropdown
- [x] 3.6 Criar `js/ui/knowledge.js` extraindo loadKnowledgeDocs, openDoc, saveDoc, deleteDoc, showNewDocForm, cancelNewDoc, createDoc
- [x] 3.7 Criar `js/ui/review.js` extraindo loadReviewItems, renderReviewStats, renderReviewList, openReviewItem, hideReviewDetail, validateAnnotation, rejectAnnotation, showPromoteModal, confirmPromote, loadRules, renderRulesList, openRuleDetail, toggleRule, saveRule
- [x] 3.8 Criar `js/ui/campaigns.js` extraindo loadCampaigns, openCampaignDetail, showCampaignForm, cancelCampaignForm, createCampaign, generateVariations, editVariation, startCampaign, pauseCampaign, resumeCampaign, retryCampaign
- [x] 3.9 Criar `js/ui/settings.js` extraindo openSettings, closeSettings, switchSettingsTab, loadSettingsPrompts, loadSettingsProfile, renderSettingsTab, saveSettings, resetPrompt
- [x] 3.10 Criar `js/ui/context-panel.js` extraindo renderContextPanel, updateFunnelProduct, classifyConversation, updateFunnelStage

## 4. JS: Entry Point e Integração

- [x] 4.1 Criar `js/main.js` que importa todos os módulos, chama init(), registra WS handlers, e expõe funções no window para onclick handlers
- [x] 4.2 Substituir `switchTab()` por chamadas ao router.navigate()
- [x] 4.3 Atualizar index.html: trocar `<script src="app.js?v=16">` por `<script type="module" src="js/main.js">`
- [ ] 4.4 Remover app.js antigo

## 5. Validação

- [ ] 5.1 Testar fluxo completo de conversas: abrir, ver mensagens, selecionar draft, editar, enviar
- [ ] 5.2 Testar WebSocket: nova mensagem inbound aparece em real-time
- [ ] 5.3 Testar campanhas: criar, gerar variações, iniciar, ver progresso
- [ ] 5.4 Testar knowledge: listar, criar, editar, deletar documento
- [ ] 5.5 Testar review: ver anotações, validar, rejeitar, promover a regra
- [ ] 5.6 Testar mobile: sidebar toggle, chat view, draft pills
- [ ] 5.7 Testar scheduled sends: agendar, cancelar
- [ ] 5.8 Testar settings: abrir, editar prompts, salvar
