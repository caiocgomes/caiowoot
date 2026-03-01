## Context

O app é um FastAPI que serve arquivos estáticos de `app/static/` montados na raiz com `StaticFiles(directory="app/static", html=True)`. A UI inteira está em um `index.html` com CSS inline (tag `<style>`) e um `app.js`. Não existe nenhuma media query, nenhum ícone, nenhum manifest. O layout é flexbox desktop-only: sidebar fixa 320px + main area.

O objetivo é tornar o app instalável como PWA no iPhone e usável em tela de celular.

## Goals / Non-Goals

**Goals:**
- App instalável via "Add to Home Screen" no iOS Safari
- Layout funcional em telas de 375px+ (iPhone SE em diante)
- Sidebar com mecanismo de show/hide no mobile
- Draft cards legíveis no mobile (stacking vertical)
- Touch targets adequados (44px mínimo)

**Non-Goals:**
- Suporte offline (app de comunicação, sem conexão não tem utilidade)
- Push notifications (complexidade alta, pode ser change futuro)
- Redesign visual (manter a identidade atual, só adaptar layout)
- CSS framework externo (manter CSS inline, só adicionar media queries)
- Testes automatizados de responsividade (validação visual manual)

## Decisions

### 1. Service worker mínimo (fetch passthrough)

O SW só precisa existir para que o browser aceite o install prompt. Não cacheia nada. Intercepta fetch e repassa direto para a rede.

```js
self.addEventListener('fetch', (e) => e.respondWith(fetch(e.request)));
```

**Alternativa descartada**: Workbox com cache strategies. Overhead desnecessário para um app que não precisa de offline.

### 2. Sidebar como drawer overlay no mobile

Abaixo de 768px, a sidebar fica `display: none` por padrão. Um botão hamburger no header do chat a mostra como overlay (`position: fixed`, `z-index: 100`, largura 85vw). Clicar em uma conversa fecha o drawer automaticamente.

**Alternativa descartada**: Bottom tab navigation. Mais complexo e não combina com o padrão atual de sidebar. O drawer é mais natural para quem já usa o layout desktop.

**Alternativa descartada**: Sidebar sempre visível mas estreita (ícones). A lista de conversas precisa mostrar nome + preview, não funciona com ícones.

### 3. Breakpoint único em 768px

Um breakpoint só. Abaixo de 768px = mobile. Acima = desktop (comportamento atual preservado). Não vale a complexidade de breakpoints intermediários para um app utilitário.

### 4. Draft cards: stack vertical no mobile

As 3 cards empilham verticalmente com `flex-direction: column`. Cada card ocupa largura total. O `max-height: 120px` se mantém para não dominar a tela.

### 5. Inline style do draft-cards-container: mover para classe

A div `<div style="display:flex; gap:8px; align-items:stretch;">` precisa virar classe CSS para a media query funcionar. Inline styles têm prioridade sobre media queries.

### 6. Ícone: SVG simples gerado como data URI convertido para PNG

Criar um ícone minimalista com as iniciais "CW" (CaioWoot) em verde (#25D366, a cor do botão de enviar). Gerar como SVG inline e converter para PNG 192x192 e 512x512. Sem dependência externa.

### 7. Meta tags iOS específicas

```html
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="theme-color" content="#ffffff">
<link rel="apple-touch-icon" href="icon-192.png">
```

`status-bar-style: default` mantém a barra de status com fundo claro, consistente com o app. Sem complicar com `black-translucent`.

### 8. Textarea max-height dinâmico no mobile

No JS, ao detectar viewport < 768px, o `autoResize` usa `40vh` como limite em vez de 500px fixo. Isso evita que o textarea empurre o teclado virtual para fora da tela.

## Risks / Trade-offs

- **iOS Safari quirks com standalone mode**: O `100vh` no iOS não desconta a barra de endereço. Mitigação: usar `100dvh` (dynamic viewport height) no body.
- **Inline style com prioridade alta**: A div de draft-cards tem inline style que bloqueia media query. Mitigação: converter para classe CSS (task explícita).
- **Teclado virtual reduz viewport**: Quando o teclado abre no mobile, o viewport encolhe. Mitigação: textarea com max-height em vh, não px.
- **Cache do service worker**: Browsers podem cachear o SW agressivamente. Mitigação: incluir `Cache-Control: no-cache` no header ou versionar o SW.
