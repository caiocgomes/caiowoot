## MODIFIED Requirements

### Requirement: Webhook Origin Validation

Adicionar validação opcional de origem no endpoint `POST /webhook`, verificando header de autenticação da Evolution API quando configurado. Mantém compatibilidade com deployments existentes que não usam token.

#### Scenario: Validação de token configurada

- **WHEN** `POST /webhook` receives a request
- **THEN** it checks for Evolution API auth header/token if configured

#### Scenario: Falha na validação

- **WHEN** validation fails
- **THEN** returns 401

#### Scenario: Sem validação configurada

- **WHEN** no validation is configured
- **THEN** accepts all requests (backward compatible)
