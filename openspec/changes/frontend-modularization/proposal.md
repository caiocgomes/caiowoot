## Why

O frontend é um monolito de dois arquivos (app.js com 1900 linhas e 80 funções, index.html com 636 linhas incluindo 354 de CSS inline). Cada feature nova cresce linearmente os mesmos arquivos, a navegação entre views é O(n²) em show/hide manual, e o CSS já está inconsistente (features recentes usam inline styles). O ponto de inflexão chegou: a próxima rodada de melhorias de design/usabilidade precisa de uma base modular para não degradar mais.

## What Changes

- Dividir app.js em ES modules nativos (sem build step), um por domínio funcional
- Extrair CSS inline para arquivos separados por feature com design tokens compartilhados via CSS custom properties
- Introduzir um view manager leve que substitui o padrão atual de show/hide manual entre views
- Centralizar estado em um módulo dedicado (substituindo variáveis globais espalhadas)
- Centralizar chamadas fetch em um módulo api.js (substituindo fetch inline em cada função)
- Limpar inline styles do HTML de campaigns e mover para classes CSS
- **Nenhuma mudança visual ou de comportamento** — refactor puramente estrutural

## Capabilities

### New Capabilities
- `frontend-modules`: Estrutura de ES modules para o frontend (entry point, state, api, ws, router, ui modules)
- `frontend-design-tokens`: CSS custom properties como sistema de design tokens (cores, spacing, radius, tipografia)
- `frontend-view-router`: View manager leve que gerencia navegação entre views sem show/hide manual

### Modified Capabilities
_(nenhuma — este refactor não altera requisitos de capabilities existentes, apenas reorganiza implementação)_

## Impact

- `app/static/app.js` — será dividido em ~12 módulos em `app/static/js/`
- `app/static/index.html` — CSS inline removido, substituído por imports de arquivos CSS; script tag muda para `type="module"`
- Novo diretório `app/static/css/` com ~8 arquivos CSS
- Novo diretório `app/static/js/` com ~12 arquivos JS
- Cache busting: mudança de `app.js?v=16` para `js/main.js` (module imports gerenciam cache diferente)
- Nenhuma mudança no backend, APIs, WebSocket protocol ou banco de dados
