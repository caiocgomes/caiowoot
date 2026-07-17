## ADDED Requirements

### Requirement: Health Check Endpoint

Endpoint `GET /health` que verifica o estado do banco de dados e das tasks em background, retornando status estruturado para monitoramento e orquestração de containers.

#### Scenario: Health check bem-sucedido

- **WHEN** `GET /health` is called
- **THEN** it returns 200 with `db_ok` and `background_tasks` status

#### Scenario: Banco inacessível

- **WHEN** DB is unreachable
- **THEN** health check returns 503

#### Scenario: Background tasks inativas

- **WHEN** background tasks (scheduler, campaign_executor) are dead
- **THEN** health check reports them as inactive
