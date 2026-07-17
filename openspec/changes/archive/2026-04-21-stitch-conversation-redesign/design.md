## Context

O frontend CaioWoot é uma PWA vanilla JS com arquitetura modular (ES6 imports). CSS organizado em 10 arquivos com tokens centralizados em `tokens.css`. A tela de conversa é o core do produto: header, mensagens, draft cards, compose area, context panel. O design system "Veridian Copilot" foi prototipado no Stitch com a tela "Conversa Mobile com Comando de IA" como referência canônica. O HTML dessa tela usa Tailwind via CDN, mas a implementação real deve manter a abordagem atual de CSS vanilla com custom properties.

Stack atual: HTML estático (`index.html`), CSS com design tokens (`tokens.css`), JS modular (`js/ui/*.js`), WebSocket para real-time. Backend não muda.

## Goals / Non-Goals

**Goals:**
- Aplicar o design system Veridian Copilot na tela de conversa (tokens, tipografia, ícones, layout)
- Diferenciar visualmente mensagens de IA (glass-ai) de mensagens humanas
- Melhorar UX de seleção de drafts com carrossel horizontal e refinamento inline
- Adicionar toolbar rica no compose e bottom nav no mobile
- Manter compatibilidade com todos os fluxos existentes (send, schedule, regenerate, classify, rewrite)

**Non-Goals:**
- Migrar para framework JS (React, Vue, etc.)
- Usar Tailwind no build real (o protótipo Stitch usa Tailwind; a implementação usa CSS vanilla com custom properties)
- Redesenhar sidebar de conversas ou outras telas (knowledge, campaigns, review, settings)
- Mudar backend, API ou WebSocket protocol
- Implementar funcionalidade real para os tabs Insights e History do bottom nav (apenas placeholder/routing)

## Decisions

### D1: CSS custom properties em vez de Tailwind

O protótipo Stitch usa Tailwind via CDN. A implementação vai traduzir os tokens para CSS custom properties em `tokens.css`, mantendo a abordagem existente.

**Alternativa considerada:** Adotar Tailwind no projeto. Descartada porque adicionaria build step, mudaria a abordagem de toda a codebase, e o escopo dessa change é visual, não arquitetural.

### D2: Material Symbols via CDN

Adicionar Material Symbols Outlined via Google Fonts CDN no `index.html`. Usar `<span class="material-symbols-outlined">icon_name</span>` em vez dos emojis e text atuais.

**Alternativa considerada:** Icon sprites ou SVG inline. CDN é mais simples, não requer build, e o protótipo já usa essa abordagem.

### D3: Inter via Google Fonts CDN

Carregar Inter (300,400,500,600,700,800) via Google Fonts. Definir como font principal no body.

### D4: Glass-ai como classe CSS, não componente JS

O efeito glassmorphism para mensagens de IA será uma classe CSS (`glass-ai`) aplicada condicionalmente em `messages.js` baseado no campo `msg.bot` ou novo marcador de origem IA. Não requer novo componente.

### D5: Draft carousel com CSS scroll-snap nativo

Usar `overflow-x: auto` + `scroll-snap-type: x mandatory` + `scroll-snap-align: start` nos draft cards. Cards com largura fixa (~240px). Sem biblioteca JS de carrossel.

**Alternativa considerada:** Swiper.js ou similar. CSS nativo é suficiente e evita dependência.

### D6: Refinamento inline reutiliza endpoint existente

O input "Refine last output" mapeia para o mesmo `POST /conversations/{id}/regenerate` com `operator_instruction`. Não requer novo endpoint. O input substitui visualmente o `#instruction-bar` atual mas mantém o mesmo comportamento.

### D7: Compose toolbar actions mapeiam para funcionalidade existente

- "Formalize" = chama `/rewrite` com prompt de formalização (já existe)
- "Translate" = chama `/rewrite` com prompt de tradução (extensão simples)
- "Attach" = abre file picker (já existe)

O endpoint `/rewrite` já aceita texto livre. A toolbar é reorganização visual, não funcionalidade nova.

### D8: Bottom nav como routing de tabs, não novas telas

Os tabs Insights e History no bottom nav serão placeholders que mostram estado vazio ("Em breve"). O tab Chat é o default e já funciona. Isso permite lançar o redesign visual sem bloquear em funcionalidade nova.

### D9: Playwright para testes e2e do frontend

Adicionar `playwright` e `pytest-playwright` como dev dependencies. Testes em `tests/e2e/`. Fixture `live_server` sobe o FastAPI com `uvicorn` em porta aleatória, fixture `page` navega com Chromium headless. Testes validam computed styles, viewport responsivo (390px mobile, 1280px desktop), e interações (click draft, refinement, toolbar).

**Alternativa considerada:** Vitest + jsdom para testar lógica JS isolada. Descartada porque 90% dos cenários dessa change são visuais (cores, backdrop-filter, scroll-snap, tonal layering) e jsdom não renderiza CSS. Playwright testa o que o usuário realmente vê.

**Alternativa considerada:** Cypress. Descartada porque Playwright tem melhor integração com pytest (stack existente) e suporte nativo a múltiplos viewports.

### D10: Tonal layering via surface tiers

Eliminar todas as `border: 1px solid` usadas para separação de seções. Substituir por mudanças de background entre os tiers do design system: `surface` $\rightarrow$ `surface-container-low` $\rightarrow$ `surface-container` $\rightarrow$ `surface-container-high` $\rightarrow$ `surface-container-highest`. Ghost borders (outline-variant a 20% opacity) onde acessibilidade exigir.

## Risks / Trade-offs

**Regressão visual em telas não-conversa** $\rightarrow$ Tokens globais (`tokens.css`) afetam sidebar, campaigns, settings. Mitigação: testar manualmente todas as telas após trocar tokens. Manter seletores específicos onde necessário.

**Performance de CDN fonts** $\rightarrow$ Inter + Material Symbols são ~200KB adicionais no primeiro load. Mitigação: `display=swap` no link, preconnect para fonts.googleapis.com. PWA cacheia após primeiro load.

**Carrossel horizontal sem affordance visual** $\rightarrow$ Usuário pode não perceber que há mais cards fora da viewport. Mitigação: mostrar borda parcial do próximo card (peek), padding assimétrico.

**Bottom nav conflita com safe area do iOS** $\rightarrow$ Mitigação: usar `env(safe-area-inset-bottom)` no padding inferior do bottom nav.

**Translate no compose toolbar é funcionalidade nova** $\rightarrow$ O endpoint `/rewrite` existe mas não tem modo "translate" explícito. Mitigação: enviar instruction "traduza para inglês" como texto livre no rewrite, ou implementar como TODO com botão desabilitado inicialmente.
