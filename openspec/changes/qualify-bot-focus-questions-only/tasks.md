## 1. Tool schema

- [x] 1.1 Atualizar `QUALIFY_TOOL` em `auto_qualifier.py`: substituir `qualification_summary` (string) por `answers` (object com additionalProperties string|null). Manter `message` e `ready_for_handoff`.

## 2. Prompt do bot

- [x] 2.1 Reescrever o prompt em `_build_qualifying_prompt()`: papel de entrevistador, lista de perguntas como tópicos a cobrir, liberdade para agrupar e aprofundar, proibição absoluta de responder dúvidas
- [x] 2.2 Adicionar instrução explícita para quando o lead faz uma pergunta: reconhecer, redirecionar para atendente, voltar às perguntas pendentes
- [x] 2.3 Adicionar instrução sobre subperguntas: quando resposta é rasa, aprofundar antes de passar para próxima

## 3. Lógica de handoff

- [x] 3.1 Atualizar critério de handoff em `auto_qualify_respond()`: checar se todas as chaves em `answers` têm valor não-null (além do limite de 4 trocas existente)
- [x] 3.2 Construir `qualification_summary` estruturado a partir de `answers`: listar cada pergunta com resposta ou "Não respondida"

## 4. Testes

- [x] 4.1 Atualizar `make_qualify_response()` em `test_auto_qualifying.py` para usar novo schema com `answers`
- [x] 4.2 Teste: bot retorna answers com perguntas mapeadas para respostas
- [x] 4.3 Teste: handoff quando todas as answers são não-null
- [x] 4.4 Teste: handoff por limite de trocas inclui answers parciais no resumo
