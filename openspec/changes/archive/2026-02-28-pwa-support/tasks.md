## 1. PWA Manifest e Service Worker

- [x] 1.1 Criar `app/static/manifest.json` com name, short_name, start_url, display standalone, theme_color, background_color e ícones 192/512
- [x] 1.2 Criar `app/static/sw.js` com fetch passthrough (sem cache)
- [x] 1.3 Criar ícones PNG `app/static/icon-192.png` e `app/static/icon-512.png` (iniciais CW, verde #25D366, fundo branco)

## 2. Meta tags e registro do SW

- [x] 2.1 Adicionar no `<head>` do `index.html`: link para manifest, meta tags iOS (apple-mobile-web-app-capable, status-bar-style, theme-color, apple-touch-icon)
- [x] 2.2 Adicionar script de registro do service worker no final do `index.html` (antes do app.js ou inline)

## 3. Responsividade CSS

- [x] 3.1 Alterar `body` height de `100vh` para `100dvh`
- [x] 3.2 Converter inline style `style="display:flex; gap:8px; align-items:stretch;"` do draft-cards-container para classe CSS `.draft-cards-row`
- [x] 3.3 Adicionar botão hamburger no `#chat-header` (visível só no mobile)
- [x] 3.4 Adicionar media query `@media (max-width: 767px)` com:
  - Sidebar oculta por padrão, classe `.open` para mostrar como overlay (position fixed, z-index 100, width 85vw)
  - Backdrop overlay quando sidebar aberta
  - Draft cards `flex-direction: column`
  - `.draft-cards-row` em column no mobile
  - `.msg` max-width 90%
  - `#draft-input` min-height 100px
  - `#draft-area` flex-direction column, btn-group em row abaixo
  - Botões com min-height 44px
  - Compose padding reduzido

## 4. JavaScript mobile

- [x] 4.1 Adicionar função `toggleSidebar()` e bind no botão hamburger
- [x] 4.2 Fechar sidebar ao selecionar conversa no mobile (dentro do handler de click de conv-item)
- [x] 4.3 Fechar sidebar ao clicar no backdrop
- [x] 4.4 Ajustar `autoResize` para usar `40vh` como limite no mobile em vez de 500px fixo
