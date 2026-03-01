## Context

O Caiowoot é um assistente WhatsApp que gera drafts de resposta para operadores. O contexto temporal no prompt (saudação, elapsed time, timestamps no histórico) usa `datetime.now()` naive, que assume o fuso do processo. O banco SQLite grava via `CURRENT_TIMESTAMP` em UTC. O endpoint de knowledge usa UTC explícito. O resultado: horários inconsistentes e incorretos para operadores em São Paulo.

## Goals / Non-Goals

**Goals:**
- Todas as datas exibidas no prompt e na UI usam `America/Sao_Paulo`
- Configuração de timezone centralizada em `Settings`
- Testes timezone-aware que validam o comportamento correto

**Non-Goals:**
- Migrar timestamps existentes no banco (ficam em UTC, conversão na leitura)
- Suporte multi-timezone por operador
- Mudar o formato de armazenamento do SQLite

## Decisions

### 1. Usar `zoneinfo` da stdlib (Python 3.9+)

Alternativas: `pytz`, `dateutil`.

`zoneinfo` já está na stdlib desde Python 3.9, o projeto usa Python 3.12+. Zero dependências extras. `pytz` tem API confusa com `localize()` vs `replace()` e está em modo de manutenção. Decisão simples.

### 2. Configuração via `Settings.timezone` com default `America/Sao_Paulo`

O campo aceita qualquer IANA timezone string. Default hardcoded para o caso de uso atual. Caso futuramente precise de outro fuso, basta trocar no `.env`. Não há necessidade de timezone por operador no momento.

### 3. Helper `now_local()` centralizado

Em vez de espalhar `datetime.now(ZoneInfo(settings.timezone))` em cada arquivo, criar um helper simples em `app/config.py` (ou junto ao settings) que retorna o datetime no fuso configurado. Reduz repetição e garante consistência.

### 4. Timestamps do banco tratados como UTC na leitura

`CURRENT_TIMESTAMP` do SQLite gera UTC. Na leitura, os isoformat strings do banco são parseados e convertidos para o fuso local. Para mensagens inseridas com timestamps explícitos (via Python), os valores já são isoformat strings naive, que serão tratados como UTC para consistência.

## Risks / Trade-offs

[Timestamps históricos ambíguos] → Os timestamps já gravados no banco são naive (sem info de timezone). Assumimos UTC, que é o comportamento de `CURRENT_TIMESTAMP`. Se alguma mensagem foi gravada com hora local do servidor (que não era UTC), haverá discrepância. Risco baixo: o servidor roda em UTC.

[Testes dependentes de horário] → Testes que comparam formatação de hora podem falhar dependendo do fuso da máquina de CI. Mitigação: testes devem mockar ou usar timezone explícito.
