## ADDED Requirements

### Requirement: Prompt inclui primeiro nome do cliente
O sistema SHALL extrair o primeiro nome do `contact_name` da conversa e incluí-lo como contexto no prompt enviado ao Claude para geração de drafts. A extração SHALL usar split simples no primeiro espaço do `contact_name`.

#### Scenario: Cliente com nome completo
- **WHEN** a conversa tem `contact_name` = "Maria Silva"
- **THEN** o prompt enviado ao Claude SHALL conter uma seção indicando que o nome do cliente é "Maria"

#### Scenario: Cliente com nome único
- **WHEN** a conversa tem `contact_name` = "João"
- **THEN** o prompt enviado ao Claude SHALL conter uma seção indicando que o nome do cliente é "João"

#### Scenario: Cliente sem nome (pushName vazio)
- **WHEN** a conversa tem `contact_name` vazio ou nulo
- **THEN** o prompt SHALL ser montado sem a seção de nome do cliente (comportamento atual preservado)

### Requirement: System prompt orienta uso natural do nome
O `SYSTEM_PROMPT` SHALL conter orientação para usar o nome do cliente de forma natural e esporádica, sem repetir em toda mensagem.

#### Scenario: Orientação presente no system prompt
- **WHEN** o sistema gera drafts para qualquer conversa
- **THEN** o system prompt SHALL incluir regra sobre uso natural do nome do cliente

### Requirement: Regeneração de drafts inclui nome
A função `regenerate_draft` SHALL passar o nome do cliente no prompt da mesma forma que `generate_drafts`, garantindo consistência entre geração e regeneração.

#### Scenario: Regeneração mantém contexto de nome
- **WHEN** o operador solicita regeneração de um draft
- **THEN** o prompt de regeneração SHALL incluir o primeiro nome do cliente (se disponível), idêntico ao prompt de geração original
