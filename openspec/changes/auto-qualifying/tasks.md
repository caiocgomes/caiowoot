## 1. Database

- [x] 1.1 Adicionar campo `is_qualified INTEGER DEFAULT 0` na tabela `conversations` (SCHEMA + migration)
- [x] 1.2 Migration para conversas existentes: setar `is_qualified = 1` em todas as conversas que já existem

## 2. Backend: Auto-qualifier service

- [x] 2.1 Criar `app/services/auto_qualifier.py` com prompt de qualifying (transparente, sem venda, máximo 4 trocas)
- [x] 2.2 Implementar `auto_qualify_respond(conversation_id)`: carrega histórico, chama Claude Haiku com tool_use, extrai message + ready_for_handoff + qualification_summary
- [x] 2.3 Quando `ready_for_handoff = True`: enviar mensagem de handoff, setar `is_qualified = 1`, gerar situation_summary, broadcast WS `conversation_qualified`
- [x] 2.4 Enviar mensagem do robô via Evolution API e salvar no DB com `sent_by = "bot"`

## 3. Backend: Webhook routing

- [x] 3.1 No webhook de mensagem inbound, após criar/buscar conversa: checar `is_qualified`
- [x] 3.2 Se `is_qualified = False`: disparar `auto_qualify_respond` em background, NÃO gerar drafts
- [x] 3.3 Se `is_qualified = True`: fluxo normal (gerar drafts)

## 4. Backend: Assumir conversa

- [x] 4.1 Criar endpoint `POST /conversations/{id}/assume` que seta `is_qualified = 1` e broadcast WS `conversation_assumed`
- [x] 4.2 Retornar `is_qualified` nos endpoints GET `/conversations` (list) e GET `/conversations/{id}` (detail)

## 5. Frontend: Estado visual

- [x] 5.1 Na sidebar, adicionar classe `qualifying` em conversas com `is_qualified = false` (borda amarela/laranja + ícone robô)
- [x] 5.2 Ao abrir conversa não qualificada: esconder #compose, mostrar banner "Robô qualificando" com botão "Assumir conversa"
- [x] 5.3 Implementar `assumeConversation()` que chama POST /assume e atualiza UI
- [x] 5.4 Tratar eventos WS `conversation_qualified` e `conversation_assumed`: remover classe qualifying, mostrar compose normal
- [x] 5.5 Mensagens com `sent_by = "bot"` aparecem com estilo diferente (fundo azul claro em vez de verde)

## 6. Frontend: CSS

- [x] 6.1 Adicionar estilos para `.conv-item.qualifying` (borda amarela, ícone robô)
- [x] 6.2 Adicionar estilos para `#qualifying-banner` (banner com botão)
- [x] 6.3 Adicionar estilos para `.msg.outbound.bot` (fundo azul claro)

## 7. Testes

- [x] 7.1 Teste: mensagem de número novo cria conversa com is_qualified = False
- [x] 7.2 Teste: auto_qualify_respond envia mensagem e salva com sent_by = "bot"
- [x] 7.3 Teste: quando ready_for_handoff = True, is_qualified vira True e gera summary
- [x] 7.4 Teste: POST /assume seta is_qualified = True
- [x] 7.5 Teste: mensagem inbound em conversa qualificada gera drafts normalmente
- [x] 7.6 Teste: mensagem inbound em conversa não qualificada NÃO gera drafts
