## Why

Três módulos com lógica de negócio real estão abaixo de 80% de cobertura: conversations.py (65%), admin.py (65%) e operator_coaching.py (77%). São endpoints que formatam dados, fazem queries compostas e parsam respostas de LLM. Regressões nesses caminhos afetam diretamente o operador e o gestor.

## What Changes

- Testes para o endpoint `POST /conversations/{id}/classify` (conversations.py linhas 166-224)
- Testes para os endpoints admin `GET /admin/analysis/status/{id}` e `GET /admin/analysis/results` (admin.py linhas 82-194)
- Testes para o fallback de JSON parsing em `_generate_operator_digest` (operator_coaching.py linhas 317-331)
- Nenhuma mudança em código de produção

## Capabilities

### New Capabilities

- `test-coverage-block-a`: Testes para endpoints de classificação, admin analysis e parsing de digest

### Modified Capabilities

## Impact

- `tests/test_classify_conversation.py` (novo)
- `tests/test_admin_routes.py` (modificado - adicionar testes de status e results)
- `tests/test_operator_coaching.py` (modificado - adicionar testes de JSON fallback)
- Sem mudanças em código de produção
