## 1. Testes do classify_conversation (tests/test_classify_conversation.py)

- [x] 1.1 Criar test_classify_conversation.py com teste de classificação com sucesso (mock retorna product+stage, verifica response e banco)
- [x] 1.2 Teste: classificar conversa sem mensagens retorna nulls
- [x] 1.3 Teste: classificar conversa inexistente retorna 404

## 2. Testes dos endpoints admin (tests/test_admin_routes.py)

- [x] 2.1 Teste: GET analysis_status com run existente retorna dados completos
- [x] 2.2 Teste: GET analysis_status com run inexistente retorna 404
- [x] 2.3 Teste: GET analysis_results com run completa (inserir assessments + digests no banco, verificar formatação)
- [x] 2.4 Teste: GET analysis_results sem runs retorna run null
- [x] 2.5 Teste: endpoints admin rejeitam request sem sessão admin (403)

## 3. Testes de JSON parse fallback (tests/test_operator_coaching.py)

- [x] 3.1 Teste: _generate_operator_digest com JSON válido da LLM
- [x] 3.2 Teste: _generate_operator_digest com JSON embutido em texto markdown
- [x] 3.3 Teste: _generate_operator_digest com resposta sem JSON retorna fallback
