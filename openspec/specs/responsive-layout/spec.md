## ADDED Requirements

### Requirement: Navegação lista-detalhe no mobile
Abaixo de 768px, o app SHALL seguir padrão mobile de navegação lista-detalhe: a sidebar (lista de conversas) é a tela inicial. Ao selecionar uma conversa, a sidebar é substituída pela tela de chat. Um botão de voltar no header permite retornar à lista.

#### Scenario: Estado inicial no mobile (nenhuma conversa selecionada)
- **WHEN** o viewport é menor que 768px e nenhuma conversa está selecionada
- **THEN** a sidebar SHALL estar visível em tela cheia (width 100%) e o main area SHALL estar oculto

#### Scenario: Conversa selecionada no mobile
- **WHEN** o usuário toca em uma conversa na sidebar no mobile
- **THEN** a sidebar SHALL ser ocultada e o main area SHALL aparecer em tela cheia com a conversa selecionada

#### Scenario: Voltar para lista de conversas
- **WHEN** o usuário toca no botão de voltar (hamburger) no header do chat no mobile
- **THEN** o main area SHALL ser ocultado e a sidebar SHALL reaparecer em tela cheia

#### Scenario: Sidebar como overlay quando conversa está aberta
- **WHEN** o usuário toca no botão hamburger enquanto uma conversa está aberta no mobile
- **THEN** a sidebar SHALL aparecer como overlay (position fixed, z-index alto, largura 85vw) sobre o chat

#### Scenario: Fechar overlay ao tocar fora
- **WHEN** a sidebar está aberta como overlay no mobile e o usuário toca fora dela
- **THEN** a sidebar SHALL fechar e retornar ao chat

### Requirement: Draft cards como pills compactos no mobile
Abaixo de 768px, os draft cards SHALL ser exibidos como pills compactos em uma linha horizontal, mostrando apenas o label da abordagem (sem o texto do draft). O texto do draft selecionado SHALL ir direto para o textarea. O primeiro draft SHALL ser auto-selecionado quando os drafts aparecem.

#### Scenario: Pills em linha horizontal
- **WHEN** o viewport é menor que 768px e existem draft cards visíveis
- **THEN** os cards SHALL ser exibidos como pills compactos em flex-direction row, sem o texto do draft visível

#### Scenario: Auto-seleção do primeiro draft
- **WHEN** os drafts são carregados no mobile
- **THEN** o primeiro draft SHALL ser automaticamente selecionado e seu texto SHALL popular o textarea

### Requirement: Mensagens expandidas no mobile
Abaixo de 768px, as mensagens SHALL ter `max-width: 90%` em vez de 70%.

#### Scenario: Largura de mensagem no mobile
- **WHEN** o viewport é menor que 768px
- **THEN** cada mensagem (.msg) SHALL ter max-width de 90%

### Requirement: Textarea adaptado ao mobile
Abaixo de 768px, o textarea SHALL ter `min-height: 100px` e o auto-resize SHALL usar limite proporcional ao viewport (40vh) em vez de valor fixo.

#### Scenario: Textarea menor no mobile
- **WHEN** o viewport é menor que 768px
- **THEN** o textarea SHALL ter min-height de 100px

#### Scenario: Auto-resize proporcional
- **WHEN** o usuário digita texto no mobile e o conteúdo excede a altura visível
- **THEN** o textarea SHALL expandir até no máximo 40vh

### Requirement: Touch targets mínimos de 44px
Abaixo de 768px, todos os botões interativos SHALL ter altura mínima de 44px para conformidade com guidelines de acessibilidade iOS.

#### Scenario: Botões com área de toque adequada
- **WHEN** o viewport é menor que 768px
- **THEN** `#send-btn`, `#attach-btn`, `#regen-all-btn`, `#regen-instruction-btn` e botões de draft cards SHALL ter min-height de 44px

### Requirement: Compose area empilha no mobile
Abaixo de 768px, o `#draft-area` SHALL empilhar textarea e botões verticalmente, com botões abaixo do textarea em linha horizontal.

#### Scenario: Layout do compose no mobile
- **WHEN** o viewport é menor que 768px
- **THEN** o textarea SHALL ocupar largura total e o btn-group SHALL ficar abaixo, em `flex-direction: row` com `justify-content: flex-end`

### Requirement: Viewport height correto no iOS
O body SHALL usar `100dvh` como altura para lidar corretamente com a barra de endereço do Safari iOS.

#### Scenario: Altura do viewport no iOS standalone
- **WHEN** o app é aberto em modo standalone no iOS
- **THEN** o layout SHALL ocupar a altura completa da tela sem overflow causado por `100vh`

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
