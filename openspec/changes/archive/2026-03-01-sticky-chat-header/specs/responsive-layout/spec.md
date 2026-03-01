## ADDED Requirements

### Requirement: Chat header fixo durante scroll no mobile
Abaixo de 768px, o `#chat-header` (botão voltar + nome do contato) SHALL permanecer visível e fixo no topo da área de chat enquanto o operador rola as mensagens. Apenas o container de mensagens (`#messages`) SHALL fazer scroll.

#### Scenario: Header visível após scroll longo
- **WHEN** o viewport é menor que 768px e o operador rola para baixo em uma conversa com muitas mensagens
- **THEN** o `#chat-header` SHALL permanecer visível no topo da tela, com o botão de voltar e nome do contato acessíveis

#### Scenario: Scroll não afeta header
- **WHEN** o operador rola as mensagens até o final da conversa no mobile
- **THEN** o header SHALL manter sua posição fixa e apenas o conteúdo de `#messages` SHALL se mover

#### Scenario: Sem regressão no desktop
- **WHEN** o viewport é maior que 768px
- **THEN** o layout do chat SHALL funcionar como antes, com o header no topo e mensagens scrolláveis abaixo
