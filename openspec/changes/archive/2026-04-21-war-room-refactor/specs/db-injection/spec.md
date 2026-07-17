## ADDED Requirements

### Requirement: FastAPI Dependency Injection for DB

Substituir o padrão atual de importação direta de `get_db` em cada módulo por injeção de dependência nativa do FastAPI via `Depends(get_db_connection)`. Serviços recebem a conexão como parâmetro em vez de importar e chamar `get_db` internamente.

#### Scenario: Route handler acessa o banco

- **WHEN** a route handler needs DB access
- **THEN** it receives connection via `Depends(get_db_connection)`

#### Scenario: Service function acessa o banco

- **WHEN** a service function needs DB access
- **THEN** it receives `db` as a parameter (not importing `get_db`)

#### Scenario: Conexão é fechada após request

- **WHEN** request completes
- **THEN** connection is automatically closed by the framework

#### Scenario: PRAGMAs executados uma vez

- **WHEN** PRAGMAs need to be set
- **THEN** they are executed once at startup in `init_db()`, not per connection

#### Scenario: Testes sobrescrevem DB

- **WHEN** tests override DB
- **THEN** they use `app.dependency_overrides` instead of 16 manual patches
