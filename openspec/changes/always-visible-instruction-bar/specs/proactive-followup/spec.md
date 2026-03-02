## REMOVED Requirements

### Requirement: Operador pode solicitar drafts de continuação via botão
**Reason**: O botão "Sugerir resposta" é substituído pela barra de instrução + botão regenerar que agora está sempre visível. O operador pode usar o regenerar pra gerar drafts em qualquer contexto (inbound sem drafts ou outbound querendo follow-up).
**Migration**: O operador usa o botão regenerar na barra de instrução. O endpoint `POST /conversations/{id}/suggest` permanece no backend mas não é mais chamado pelo frontend.
