## MODIFIED Requirements

### Requirement: Decomposed Draft Engine

Decompor o `draft_engine.py` atual em três módulos com responsabilidades claras: `prompt_builder.py` para construção do prompt, `claude_client.py` para o singleton do Anthropic client, e `draft_engine.py` como orquestrador. Unificar a lógica duplicada entre `generate_drafts` e `regenerate_draft` num método compartilhado.

#### Scenario: Construção do prompt

- **WHEN** prompt needs to be built
- **THEN** `prompt_builder.py` constructs it (system prompt, conversation history, few-shot, knowledge, rules)

#### Scenario: Chamada ao Claude

- **WHEN** Claude needs to be called
- **THEN** `claude_client.py` singleton handles it

#### Scenario: Persistência de drafts

- **WHEN** drafts need to be persisted
- **THEN** `draft_engine.py` orchestrates the full flow

#### Scenario: Lógica compartilhada de geração

- **WHEN** `generate_drafts` or `regenerate_draft` is called
- **THEN** shared logic is in `_generate_draft_group()`, differences only in wrappers

### Requirement: Singleton Anthropic Client

Instância única do `AsyncAnthropic` reutilizada por todos os serviços que precisam chamar o Claude, em vez de criar uma nova instância a cada chamada.

#### Scenario: Serviço precisa do Claude

- **WHEN** any service needs Claude
- **THEN** it uses the shared singleton from `claude_client.py`

#### Scenario: Inicialização da aplicação

- **WHEN** app starts
- **THEN** one `AsyncAnthropic` instance is created and reused
