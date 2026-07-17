## Why

A interface de conversa atual usa tokens visuais genéricos (cor WhatsApp `#25D366`, system fonts, bordas 1px, sombras brutas) que não diferenciam o produto e dificultam a distinção visual entre mensagens humanas e outputs de IA. O design system "Veridian Copilot" foi criado no Stitch com a tela de referência "Conversa Mobile com Comando de IA" para elevar a qualidade visual a nível editorial, tratar a IA como camada fundacional (glassmorphism, badge Copilot, refinamento inline) e melhorar a ergonomia do operador (carrossel de drafts, toolbar de compose rica, bottom nav).

## What Changes

- Substituir tokens de design (cores, tipografia, border-radius, sombras) pelos tokens do design system Veridian Copilot
- Trocar system fonts por Inter (Google Fonts) e ícones emoji/text por Material Symbols Outlined
- Redesenhar message bubbles: outbound brancas sem borda, IA com efeito glass-ai + badge "Veridian Copilot"
- Trocar draft cards de layout row side-by-side para carrossel horizontal scrollável com snap, card selecionado com fundo primary
- Adicionar input de refinamento inline para outputs de IA (refine prompt + botão regenerate)
- Redesenhar compose area com toolbar rica (Formalize, Translate, Attach) acima do textarea
- Aplicar regra "No-Line": eliminar bordas 1px de separação, usar tonal layering (background shifts entre surface tiers)
- Adicionar bottom navigation (Chat, Insights, History) no mobile
- Redesenhar header da conversa com avatar, badge de papel do contato e botões de ação

## Capabilities

### New Capabilities
- `design-tokens-veridian`: Design tokens CSS (cores, tipografia, espaçamento, border-radius, sombras) alinhados ao design system Veridian Copilot
- `glass-ai-messages`: Renderização diferenciada de mensagens de IA com efeito glassmorphism, badge Copilot e indicador de verificação
- `draft-carousel`: Carrossel horizontal de draft cards com snap scroll, seleção visual com fundo primary, e input de refinamento inline
- `compose-toolbar`: Toolbar rica no compose area com ações Formalize, Translate e Attach integradas ao fluxo existente
- `mobile-bottom-nav`: Bottom navigation bar com tabs Chat, Insights, History para navegação mobile
- `e2e-playwright-infra`: Setup de Playwright como framework de testes e2e para o frontend, com fixtures para subir o server e navegar

### Modified Capabilities
- `inbox-ui`: Layout de mensagens muda para tonal layering sem bordas, header redesenhado com avatar e badge
- `responsive-layout`: Mobile ganha bottom nav, compose area e draft cards adaptados ao novo design
- `draft-variations`: Apresentação visual dos drafts muda de row para carrossel, adição de refinamento inline (backend de regenerate já existe)
- `context-panel-ui`: Estilização do painel alinhada aos novos tokens (cores, tipografia, sem bordas)

## Impact

- **CSS**: Reescrita completa de `tokens.css`, modificações significativas em `base.css`, `compose.css`, `mobile.css`, `sidebar.css`, `context-panel.css`
- **HTML**: `index.html` precisa de reestruturação do compose area, draft cards container, header do chat, e adição de bottom nav
- **JS**: `drafts.js` (carrossel + refinamento), `messages.js` (glass-ai rendering), `compose.js` (toolbar actions), novo módulo ou extensão para bottom nav routing
- **Assets**: Adição de Google Fonts (Inter) e Material Symbols via CDN
- **Backend**: Nenhuma mudança. Endpoints existentes (`/regenerate`, `/rewrite`, `/send`) já suportam todas as interações propostas
- **Testes**: Adição de Playwright + pytest-playwright como dev dependencies para testes e2e do frontend
- **Risco**: Mudança visual grande, mitigada por testes e2e automatizados que validam computed styles, responsive viewports e interações
