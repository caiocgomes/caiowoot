## Context

Os testes existentes em test_admin_routes.py e test_operator_coaching.py já cobrem cenários parciais. O conftest.py já patcha `generate_situation_summary` e tem fixtures de mock para Claude API. O admin requer `is_admin()` que checa o operador da sessão.

## Goals / Non-Goals

**Goals:**
- Cobrir classify_conversation happy path + error branches
- Cobrir analysis_status e analysis_results com dados reais no banco
- Cobrir JSON parse fallback do operator digest (resposta LLM malformada)
- Usar fixtures existentes sem criar novas abstrações

**Non-Goals:**
- Testar infra (database.py, prompt_logger.py, websocket_manager.py)
- Testar ChromaDB queries (smart_retrieval.py)
- Mudar código de produção

## Decisions

**1. classify_conversation: mock de generate_situation_summary**
Já mockado no conftest com return `{"summary": "Primeiro contato genérico.", "product": None, "stage": None}`. Para testar o update de funnel, vou criar um mock que retorna product e stage específicos.

**2. admin endpoints: inserir dados diretamente no banco**
Em vez de rodar a análise real (que chama LLM), inserir analysis_runs, conversation_assessments e operator_digests diretamente no banco de teste. Isso testa a lógica de query e formatação sem depender de mocks complexos.

**3. admin auth: usar cookie de sessão**
Os endpoints admin checam `is_admin()`. O test_admin_routes.py existente já tem padrão para isso. Vou verificar como setam o operador admin.

**4. JSON parse fallback: testar _generate_operator_digest diretamente**
Mockar a resposta do Anthropic client para retornar JSON inválido e verificar que o fallback funciona.

## Risks / Trade-offs

- [Acoplamento ao schema de response] Os testes de analysis_results verificam a estrutura do JSON retornado. Se mudar o formato, os testes quebram. → Aceitável, é exatamente o que queremos detectar.
