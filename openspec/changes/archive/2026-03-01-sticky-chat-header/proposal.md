## Why

No mobile, ao rolar as mensagens de uma conversa, o header (botão voltar + nome do contato) desaparece. O operador perde a navegação e precisa rolar até o topo para voltar à lista de conversas. Isso quebra a usabilidade em sessões longas com muitas mensagens.

## What Changes

- O `#chat-header` passa a ficar fixo no topo da tela durante scroll no mobile
- Correção do layout flexbox para garantir que apenas `#messages` faz scroll, não o container inteiro

## Capabilities

### New Capabilities

(nenhuma)

### Modified Capabilities

- `responsive-layout`: Adicionar requirement de header fixo no mobile durante scroll de mensagens

## Impact

- `app/static/index.html`: CSS do `#chat-header` e `#main`
- Nenhuma mudança de backend ou lógica JS
