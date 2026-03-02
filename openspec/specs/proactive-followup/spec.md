## ADDED Requirements

### ~~Requirement: Operador pode solicitar drafts de continuação via botão~~ [REMOVED]
**Removed by change `always-visible-instruction-bar`**: O botão "Sugerir resposta" é substituído pela barra de instrução + botão regenerar que agora está sempre visível. O operador pode usar o regenerar pra gerar drafts em qualquer contexto (inbound sem drafts ou outbound querendo follow-up). O endpoint `POST /conversations/{id}/suggest` permanece no backend mas não é mais chamado pelo frontend.

### Requirement: Endpoint de geração proativa de drafts
O sistema SHALL expor um endpoint `POST /conversations/{id}/suggest` que valida que a última mensagem é outbound, identifica o ID dessa mensagem, e dispara geração de drafts com flag proativa.

#### Scenario: Requisição válida com última mensagem outbound
- **WHEN** o endpoint recebe uma requisição e a última mensagem da conversa é outbound
- **THEN** o sistema SHALL disparar `generate_drafts(conversation_id, last_message_id, proactive=True)` de forma assíncrona
- **THEN** SHALL retornar `{"status": "ok"}` imediatamente

#### Scenario: Requisição quando última mensagem é inbound
- **WHEN** o endpoint recebe uma requisição e a última mensagem da conversa é inbound
- **THEN** o sistema SHALL retornar HTTP 409 com mensagem explicativa

#### Scenario: Conversa não encontrada
- **WHEN** o endpoint recebe uma requisição com `conversation_id` inexistente
- **THEN** o sistema SHALL retornar HTTP 404

### Requirement: Fluxo de envio preservado para drafts proativos
Quando o operador envia uma mensagem baseada em draft proativo, o sistema SHALL seguir o mesmo fluxo de envio que drafts reativos: registrar edit_pair, gerar anotação estratégica, marcar drafts como sent/discarded.

#### Scenario: Edit pair registrado com contexto de followup
- **WHEN** o operador envia uma mensagem baseada em draft proativo
- **THEN** o `edit_pair.customer_message` SHALL conter o texto da última mensagem outbound (a que motivou o followup)
- **THEN** os demais campos do edit_pair SHALL ser preenchidos normalmente (original_draft, final_message, was_edited, etc.)
