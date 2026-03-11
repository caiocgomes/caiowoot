## Why

No celular, apagar todo o texto do textarea de composição é trabalhoso (selecionar tudo + deletar). Quando o operador quer descartar o draft e ir pra outra direção, precisa de um toque só.

## What Changes

- Botão "limpar" (X) no textarea de composição de mensagem, visível quando há texto no campo
- Ao clicar, limpa o texto e reseta o estado de draft selecionado

## Capabilities

### New Capabilities

### Modified Capabilities
- `inbox-ui`: Adicionar botão de limpar no textarea de composição

## Impact

- **Frontend**: `app/static/app.js` e possivelmente `app/static/index.html` (botão + handler)
- Sem mudanças no backend
