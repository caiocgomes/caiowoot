## ADDED Requirements

### Requirement: Operador pode solicitar drafts de continuação via botão
O sistema SHALL exibir um botão "Sugerir resposta" na área de compose quando não há drafts pendentes e a última mensagem da conversa é outbound. Ao clicar, o sistema SHALL gerar 3 variações de draft como continuação da conversa.

#### Scenario: Botão visível quando última mensagem é outbound
- **WHEN** o operador abre uma conversa onde a última mensagem é outbound e não há drafts pendentes
- **THEN** o sistema SHALL exibir um botão "Sugerir resposta" na área de compose, acima do textarea

#### Scenario: Botão oculto quando última mensagem é inbound
- **WHEN** o operador abre uma conversa onde a última mensagem é inbound
- **THEN** o botão "Sugerir resposta" SHALL NOT ser exibido (drafts reativos já estarão sendo gerados)

#### Scenario: Botão oculto quando há drafts pendentes
- **WHEN** o operador abre uma conversa que já tem drafts pendentes (reativos ou proativos)
- **THEN** o botão "Sugerir resposta" SHALL NOT ser exibido

#### Scenario: Geração de drafts ao clicar
- **WHEN** o operador clica no botão "Sugerir resposta"
- **THEN** o sistema SHALL chamar `POST /conversations/{id}/suggest`
- **THEN** o botão SHALL ser desabilitado e exibir estado de loading enquanto os drafts são gerados
- **THEN** quando os drafts chegarem via WebSocket (`drafts_ready`), SHALL exibi-los normalmente (3 cards de variação)

#### Scenario: Botão desaparece após drafts gerados
- **WHEN** os drafts proativos são recebidos via WebSocket
- **THEN** o botão "Sugerir resposta" SHALL desaparecer e os draft cards SHALL ser exibidos no lugar

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
