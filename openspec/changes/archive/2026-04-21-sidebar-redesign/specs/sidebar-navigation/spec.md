## ADDED Requirements

### Requirement: Conversas como estado default
A sidebar mostra a lista de conversas por padrão, sem necessidade de tab selection.

#### Scenario: App carrega pela primeira vez
- **WHEN** o app carrega
- **THEN** a sidebar mostra a busca de conversas e a lista de conversas, sem barra de tabs

#### Scenario: Operador volta de uma ferramenta
- **WHEN** o operador clica "← Conversas" dentro de uma ferramenta
- **THEN** a sidebar volta a mostrar a lista de conversas e o header mostra "CaioWoot"

### Requirement: Menu dropdown de ferramentas
Um botão ☰ no header abre um dropdown com as 3 ferramentas disponíveis.

#### Scenario: Abrir menu de ferramentas
- **WHEN** o operador clica no botão ☰ no header
- **THEN** um dropdown aparece com 3 opções: Conhecimento, Aprendizado, Campanhas, cada uma com ícone e descrição curta

#### Scenario: Selecionar ferramenta do menu
- **WHEN** o operador clica em uma opção do menu (ex: "Conhecimento")
- **THEN** o dropdown fecha, a sidebar mostra o conteúdo de Conhecimento, e o header muda para "← 📚 Conhecimento"

#### Scenario: Fechar menu sem selecionar
- **WHEN** o operador clica fora do dropdown ou pressiona Escape
- **THEN** o dropdown fecha e a sidebar permanece no estado anterior

### Requirement: Navegação de volta
Quando uma ferramenta está ativa, o header mostra um botão de voltar.

#### Scenario: Voltar para conversas
- **WHEN** o operador está em uma ferramenta e clica no botão "←" no header
- **THEN** a sidebar volta para o estado default (lista de conversas) e o header restaura "CaioWoot"

### Requirement: Compatibilidade mobile
O novo layout funciona em telas mobile (< 768px).

#### Scenario: Menu dropdown no mobile
- **WHEN** o operador abre o menu ☰ no mobile
- **THEN** os items do dropdown têm min-height de 44px para toque confortável

#### Scenario: Voltar de ferramenta no mobile
- **WHEN** o operador está em uma ferramenta no mobile
- **THEN** o botão "← Conversas" funciona da mesma forma que no desktop
