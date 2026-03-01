## Why

O app hoje só funciona bem em desktop. A interface assume tela larga (sidebar fixa de 320px, draft cards lado a lado, sem media queries). Para operar pelo iPhone, precisa virar PWA instalável com layout responsivo. Sem isso, o operador só consegue responder clientes sentado no computador.

## What Changes

- Adicionar `manifest.json` com ícones, nome, cores e configuração de standalone display
- Adicionar service worker mínimo (sem cache offline, só o necessário para o install prompt funcionar no iOS)
- Adicionar meta tags para iOS (apple-mobile-web-app-capable, status-bar-style, apple-touch-icon)
- Criar ícones do app em SVG/PNG para home screen (192px e 512px)
- Adicionar media queries para mobile (breakpoint principal em 768px):
  - Navegação lista-detalhe no mobile: sidebar (lista) é a tela inicial, ao selecionar conversa mostra o chat em tela cheia, botão voltar retorna à lista
  - Draft cards empilham verticalmente em vez de 3 colunas
  - Textarea reduz min-height para 100px no mobile
  - Mensagens expandem para max-width 90%
  - Botões ganham área de toque mínima de 44px
  - Compose area empilha verticalmente
- Converter o inline style do container de draft cards para classe CSS (necessário para media query funcionar)
- Adicionar handler de resize no JS para ajustar max-height do textarea proporcionalmente ao viewport

## Capabilities

### New Capabilities

- `pwa-manifest`: Manifest, service worker, meta tags iOS e ícones para instalação como PWA
- `responsive-layout`: Media queries e ajustes de JS para layout mobile (sidebar drawer, stacking, touch targets)

### Modified Capabilities

_(nenhuma capability existente tem spec formal afetada)_

## Impact

- **Código**: `app/static/index.html` (meta tags, CSS media queries, referência ao manifest), `app/static/app.js` (sidebar toggle, viewport resize handler), novos arquivos `app/static/manifest.json`, `app/static/sw.js`, `app/static/icon-192.png`, `app/static/icon-512.png`
- **Backend**: Rota para servir o service worker na raiz (`/sw.js`) ou configuração de static files
- **Banco**: Nenhuma alteração
- **Breaking changes**: Nenhum. Desktop continua funcionando igual, media queries só ativam abaixo de 768px
- **Testes**: Testes existentes não são afetados (são de backend). Validação visual manual no iPhone
