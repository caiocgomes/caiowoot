## 1. Database Schema Migration

- [x] 1.1 Adicionar campos à tabela drafts: draft_group_id, variation_index, approach, prompt_hash, operator_instruction
- [x] 1.2 Adicionar campos à tabela edit_pairs: operator_instruction, all_drafts_json, selected_draft_index, prompt_hash, regeneration_count
- [x] 1.3 Adicionar campos à tabela messages: media_url, media_type
- [x] 1.4 Criar diretório data/prompts/ no init_db

## 2. Config e Models

- [x] 2.1 Adicionar CLAUDE_HAIKU_MODEL ao config.py (default: claude-haiku-4-5-20251001)
- [x] 2.2 Atualizar Pydantic models: Draft (com variation_index, approach, draft_group_id), SendRequest (com draft_group_id, selected_draft_index, operator_instruction, regeneration_count), RegenerateRequest (draft_index, operator_instruction, trigger_message_id)

## 3. Prompt Logging

- [x] 3.1 Criar app/services/prompt_logger.py com função save_prompt(prompt_text) -> hash que salva em data/prompts/{hash}.txt e retorna o hash

## 4. Draft Engine (variações)

- [x] 4.1 Refatorar generate_draft para generate_drafts (plural): aceitar operator_instruction opcional, gerar 3 chamadas Haiku em paralelo com asyncio.gather, cada uma com approach modifier diferente
- [x] 4.2 Montar draft_group_id (uuid4) para agrupar as 3 variações
- [x] 4.3 Salvar prompt via prompt_logger e armazenar hash em cada draft
- [x] 4.4 Salvar 3 drafts no banco com variation_index (0,1,2) e approach
- [x] 4.5 Broadcast via WebSocket com tipo "drafts_ready" contendo array de 3 drafts (em vez de "draft_ready" com 1)

## 5. Regenerate Endpoint

- [x] 5.1 Criar POST /conversations/{id}/regenerate em app/routes/messages.py
- [x] 5.2 Implementar regeneração individual (draft_index específico): gerar 1 novo draft Haiku, substituir no banco, broadcast via WebSocket
- [x] 5.3 Implementar regeneração total (draft_index=null): gerar 3 novos drafts, substituir grupo inteiro

## 6. Evolution API: Media

- [x] 6.1 Adicionar send_media_message(phone, base64_data, mime_type, caption) em evolution.py
- [x] 6.2 Adicionar send_document_message(phone, base64_data, filename, caption) em evolution.py

## 7. Message Sender (attachments + metadata)

- [x] 7.1 Modificar POST /conversations/{id}/send para aceitar multipart/form-data com campo file opcional
- [x] 7.2 Implementar lógica de roteamento: sem arquivo → sendText, imagem → sendMedia, outro → sendDocument
- [x] 7.3 Salvar arquivo em data/attachments/{message_id}_{filename}
- [x] 7.4 Persistir media_url e media_type na mensagem outbound
- [x] 7.5 Expandir criação de edit_pair com all_drafts_json, selected_draft_index, operator_instruction, prompt_hash, regeneration_count

## 8. Webhook (atualizar trigger)

- [x] 8.1 Atualizar webhook.py para chamar generate_drafts (plural) em vez de generate_draft

## 9. Frontend: Draft Variations UI

- [x] 9.1 Criar área de 3 draft cards acima do textarea com preview truncado do texto de cada variação
- [x] 9.2 Adicionar botão de seleção (checkmark) em cada card que popula o textarea
- [x] 9.3 Adicionar botão de regeneração individual (refresh icon) em cada card
- [x] 9.4 Adicionar botão "regenerar todas" ao lado dos cards
- [x] 9.5 Highlight visual no card selecionado

## 10. Frontend: Instruction Bar

- [x] 10.1 Criar input de instrução entre os draft cards e o textarea com placeholder "Instrução para a IA (ex: foca no preço, ela é técnica...)"
- [x] 10.2 Conectar instrução ao endpoint de regeneração: enviar operator_instruction no POST /regenerate

## 11. Frontend: Attachments

- [x] 11.1 Adicionar botão de anexo (paperclip) ao lado do botão enviar
- [x] 11.2 Implementar file picker e preview/indicador do arquivo selecionado com botão de remover
- [x] 11.3 Modificar sendMessage() para enviar como FormData (multipart) quando há anexo

## 12. Frontend: Textarea Maior

- [x] 12.1 Aumentar min-height do textarea para ~120px (5 linhas) e implementar auto-resize

## 13. Frontend: WebSocket Updates

- [x] 13.1 Atualizar handleWSEvent para tratar "drafts_ready" (array de 3) em vez de "draft_ready" (1)
- [x] 13.2 Implementar atualização parcial de cards ao receber regeneração individual

## 14. Conversation Detail Endpoint

- [x] 14.1 Atualizar GET /conversations/{id} para retornar array de pending drafts (grupo completo) em vez de single pending_draft

## 15. Tests

- [x] 15.1 Test: generate_drafts gera 3 variações em paralelo com approaches diferentes
- [x] 15.2 Test: operator_instruction é incluída no prompt quando fornecida
- [x] 15.3 Test: prompt_hash é salvo em disco e referenciado no draft
- [x] 15.4 Test: POST /regenerate com draft_index=1 regenera apenas a variação 1
- [x] 15.5 Test: POST /regenerate com draft_index=null regenera todas as 3
- [x] 15.6 Test: POST /send com arquivo image chama sendMedia
- [x] 15.7 Test: POST /send com arquivo PDF chama sendDocument
- [x] 15.8 Test: POST /send sem arquivo usa sendText (regressão)
- [x] 15.9 Test: edit_pair criado com all_drafts_json, selected_draft_index, prompt_hash
- [x] 15.10 Test: GET /conversations/{id} retorna array de pending drafts
