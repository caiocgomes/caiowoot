## Context

O frontend do CaioWoot é um monolito vanilla JS/HTML/CSS: app.js (1877 linhas, ~80 funções), index.html (636 linhas com 354 de CSS inline). Sem framework, sem build step, sem bundler. O app funciona como PWA mobile e desktop.

Estado atual de navegação: 4 tabs no sidebar (Conversas, Conhecimento, Aprendizado, Campanhas) controlam ~8 views no main area via show/hide manual. Cada nova view precisa saber sobre todas as outras para escondê-las.

Estado da aplicação: 10 variáveis globais no topo do app.js (currentConversationId, currentCampaignId, ws, attachedFile, etc.). Chamadas fetch espalhadas em ~30 funções diferentes.

## Goals / Non-Goals

**Goals:**
- Dividir app.js em módulos ES nativos sem introduzir build step
- Extrair CSS para arquivos separados com design tokens via custom properties
- Criar view manager que elimine o padrão O(n²) de show/hide
- Centralizar estado e chamadas de API
- Manter 100% do comportamento e visual existente (refactor puro)

**Non-Goals:**
- Introduzir framework (React, Vue, Svelte, etc.)
- Introduzir bundler (Vite, webpack, esbuild)
- Redesenhar UI ou UX
- Adicionar testes de frontend
- Mudar algo no backend

## Decisions

### ES Modules nativos via `<script type="module">`

Todos os browsers modernos suportam ES modules. Cada módulo exporta funções específicas, o entry point (main.js) importa e inicializa. Sem bundler, sem transpile.

Estrutura de diretórios:

```
app/static/
  js/
    main.js              ← entry point, importa módulos, chama init()
    state.js             ← estado centralizado com getters/setters
    api.js               ← todas as chamadas fetch centralizadas
    ws.js                ← WebSocket connection + event dispatch
    router.js            ← view manager
    utils.js             ← escapeHtml, formatTime, etc.
    notifications.js     ← browser notifications, sound, title badge
    ui/
      conversations.js   ← lista de conversas, render, open
      messages.js        ← render de mensagens no chat
      drafts.js          ← draft cards, seleção, regeneração
      compose.js         ← área de composição, send, rewrite, attach
      schedule.js        ← agendamento de envios
      knowledge.js       ← CRUD de documentos de conhecimento
      review.js          ← review de anotações + regras
      campaigns.js       ← lista, form, detail, variações
      settings.js        ← modal de configurações
      context-panel.js   ← painel de contexto (funnel, summary)
  css/
    tokens.css           ← custom properties (cores, spacing, radius)
    base.css             ← reset, layout, tipografia, msg bubbles
    sidebar.css          ← sidebar, tabs, conversation list
    compose.css          ← draft cards, compose area, buttons
    context-panel.css    ← painel de contexto
    knowledge.css        ← editor de knowledge
    review.css           ← review detail, rules
    campaigns.css        ← campaigns form, detail, progress
    settings.css         ← modal de settings, promote modal
    mobile.css           ← media queries mobile
  index.html             ← estrutura HTML limpa, imports CSS/JS
```

### State centralizado

```javascript
// state.js
const state = {
  currentConversationId: null,
  currentCampaignId: null,
  currentDrafts: [],
  selectedDraftIndex: null,
  // ...
};
export default state;
```

Módulos importam `state` e leem/escrevem nele diretamente. Não precisa de observable/reactive pattern para a escala atual.

### View Router leve

```javascript
// router.js
const views = {
  'chat':       { sidebar: 'conversation-list', main: 'chat-wrapper' },
  'knowledge':  { sidebar: 'knowledge-list',    main: null },
  'kb-editor':  { sidebar: 'knowledge-list',    main: 'kb-editor' },
  'kb-new':     { sidebar: 'knowledge-list',    main: 'kb-new-form' },
  'review':     { sidebar: 'review-list',       main: null },
  'review-detail': { sidebar: 'review-list',    main: 'review-detail' },
  'rule-detail':   { sidebar: 'review-list',    main: 'rule-detail' },
  'campaigns':  { sidebar: 'campaign-list',     main: null },
  'campaign-form':   { sidebar: 'campaign-list', main: 'campaign-form' },
  'campaign-detail': { sidebar: 'campaign-list', main: 'campaign-detail' },
};

export function navigate(viewName) {
  // 1. Esconde TODOS os elementos de sidebar e main
  // 2. Mostra os dois elementos do view selecionado
  // 3. Atualiza tab ativa no sidebar
}
```

Uma função `navigate()` substitui toda a lógica espalhada de show/hide. Adicionar uma view nova = adicionar uma entrada no objeto.

### API centralizada

```javascript
// api.js
async function request(path, options = {}) {
  const res = await fetch(path, options);
  if (res.status === 401) { window.location.href = '/login.html'; return; }
  return res;
}

export async function getConversations() { ... }
export async function sendMessage(convId, text, attachment) { ... }
export async function getCampaigns() { ... }
// etc.
```

O interceptor de 401 sai do monkey-patch global de fetch para dentro do wrapper.

### CSS Design Tokens

```css
/* tokens.css */
:root {
  --color-primary: #25D366;
  --color-primary-hover: #1da851;
  --color-danger: #c62828;
  --color-border: #ddd;
  --color-border-light: #eee;
  --color-text: #333;
  --color-text-secondary: #666;
  --color-text-muted: #888;
  --color-bg: #f5f5f5;
  --color-bg-card: #fff;
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-pill: 20px;
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 12px;
  --space-lg: 16px;
  --space-xl: 24px;
  --font-mono: 'SF Mono', 'Fira Code', 'Consolas', monospace;
}
```

### Ordem de migração

A migração é feita de forma incremental. Em cada passo, o app continua funcionando:

1. Criar `css/tokens.css` com custom properties; referenciá-las no CSS existente
2. Extrair CSS do index.html para arquivos separados por feature
3. Criar `js/state.js`, `js/api.js`, `js/utils.js` com o código extraído
4. Criar `js/router.js` e substituir show/hide nas funções existentes
5. Extrair cada domínio de UI para seu módulo (conversations, drafts, etc.)
6. Converter `index.html` para `<script type="module" src="js/main.js">`
7. Limpar inline styles do HTML de campaigns
8. Remover app.js antigo

## Risks / Trade-offs

**ES modules e cache**: Modules usam cache do browser normalmente. Em produção, se precisar bust cache, a opção é query string nos imports ou versionamento de path. Para uso atual (interno, poucos usuários) não é problema.

**Ordem de carregamento**: `<script type="module">` é deferred por padrão, o que é o comportamento desejado. Mas se algum inline script no HTML depender de funções globais do app.js, vai quebrar. Precisa auditar e eliminar essas dependências (o onclick handlers no HTML referem funções que precisam estar no scope global ou serem registradas via addEventListener).

**onclick handlers no HTML**: O index.html atual usa `onclick="openConversation(id)"` em vários elementos. Em ES modules, funções não ficam no escopo global automaticamente. Opções: (a) exportar para window explicitamente as funções usadas em onclick, (b) migrar para addEventListener nos módulos. A opção (a) é mais pragmática para a migração incremental; (b) é o target final mas pode ser feito depois.

**Service Worker**: O sw.js atual é mínimo (só registro). Não deve ser afetado pela mudança de estrutura de arquivos.
