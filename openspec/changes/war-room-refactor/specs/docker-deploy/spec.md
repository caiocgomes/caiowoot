## ADDED Requirements

### Requirement: Docker Deployment

Containerizar a aplicação com Docker e docker-compose para deploy reproduzível. A imagem usa python:3.12-slim com uv para gerenciamento de dependências. Volumes montam dados persistentes e base de conhecimento.

#### Scenario: Build da imagem

- **WHEN** building the image
- **THEN** Dockerfile uses `python:3.12-slim` + `uv`

#### Scenario: Execução com docker-compose

- **WHEN** running with docker-compose
- **THEN** `data/` and `knowledge/` are mounted as volumes

#### Scenario: Crash do container

- **WHEN** container crashes
- **THEN** `restart: unless-stopped` brings it back

#### Scenario: Variáveis de ambiente

- **WHEN** `.env` exists
- **THEN** docker-compose reads it for environment variables

### Requirement: SQLite Backup

Script de backup automatizado para o banco SQLite com rotação de arquivos antigos.

#### Scenario: Execução do backup

- **WHEN** backup script runs
- **THEN** creates timestamped copy via `sqlite3 .backup`

#### Scenario: Rotação de backups antigos

- **WHEN** backups are older than 7 days
- **THEN** they are automatically deleted
