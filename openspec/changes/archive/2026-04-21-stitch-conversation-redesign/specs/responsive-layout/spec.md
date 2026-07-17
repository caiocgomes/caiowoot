## MODIFIED Requirements

### Requirement: Draft cards como pills compactos no mobile
Abaixo de 768px, os draft cards SHALL ser exibidos como carrossel horizontal compacto com scroll-snap, mantendo a mesma estrutura de cards do desktop mas com largura reduzida. O primeiro draft SHALL ser auto-selecionado quando os drafts aparecem. **CHANGE:** Draft cards no mobile agora usam o mesmo carrossel horizontal do desktop (não mais pills sem texto). Cards são compactos mas mantêm label e preview de 2 linhas.

#### Scenario: Carrossel compacto no mobile
- **WHEN** o viewport é menor que 768px e existem draft cards visíveis
- **THEN** os cards SHALL ser exibidos em carrossel horizontal com scroll-snap, cada card com largura de ~200px

#### Scenario: Auto-seleção do primeiro draft
- **WHEN** os drafts são carregados no mobile
- **THEN** o primeiro draft SHALL ser automaticamente selecionado e seu texto SHALL popular o textarea

### Requirement: Compose area empilha no mobile
Abaixo de 768px, o compose area SHALL empilhar toolbar e textarea verticalmente. A toolbar SHALL ficar acima do textarea. O botão send SHALL ficar dentro do textarea container, alinhado à direita. **CHANGE:** Layout do compose muda para acomodar a nova toolbar rica (Formalize/Translate/Attach) acima do textarea.

#### Scenario: Layout do compose no mobile
- **WHEN** o viewport é menor que 768px
- **THEN** a toolbar SHALL estar acima do textarea em largura total
- **THEN** o textarea SHALL ocupar largura total com botão send inline à direita

## ADDED Requirements

### Requirement: Bottom nav integrado ao layout mobile
Abaixo de 768px, o layout mobile SHALL incluir o bottom navigation bar fixo na parte inferior da tela. O conteúdo principal (mensagens + compose) SHALL ter padding-bottom suficiente para não ser ocultado pelo bottom nav.

#### Scenario: Conteúdo não sobreposto pelo bottom nav
- **WHEN** o viewport é menor que 768px e o bottom nav está visível
- **THEN** o conteúdo de mensagens e compose SHALL ter margin-bottom ou padding-bottom suficiente para evitar sobreposição

#### Scenario: Bottom nav ocupa posição fixa
- **WHEN** o viewport é menor que 768px
- **THEN** o bottom nav SHALL ter position fixed, bottom 0, full width, z-index acima do conteúdo
