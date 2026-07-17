## ADDED Requirements

### Requirement: Draft Generation Loading State

Feedback visual durante a geração de drafts, com skeleton/spinner enquanto o Claude processa, e comportamento de seleção explícita pelo operador (sem auto-seleção).

#### Scenario: Mensagem inbound chega

- **WHEN** inbound message arrives
- **THEN** skeleton/spinner appears in `draft-cards-container`

#### Scenario: Drafts prontos via WebSocket

- **WHEN** `drafts_ready` event arrives via WS
- **THEN** skeleton is replaced by actual draft cards

#### Scenario: Drafts exibidos sem pré-seleção

- **WHEN** drafts are shown
- **THEN** NO draft is auto-selected (all 3 shown without pre-selection)

#### Scenario: Operador seleciona draft

- **WHEN** operator clicks a draft card
- **THEN** textarea is populated with that draft's text

#### Scenario: Nenhum draft selecionado

- **WHEN** no draft is selected
- **THEN** textarea shows placeholder "Selecione um draft acima"
