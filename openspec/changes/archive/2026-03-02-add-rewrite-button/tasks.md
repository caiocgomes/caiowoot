## 1. Backend - Serviço de rewrite

- [x] 1.1 Criar `app/services/text_rewrite.py` com função `rewrite_text(text: str) -> str` que chama Haiku com prompt fixo via tool_use
- [x] 1.2 Definir system prompt: português correto, tom WhatsApp, preservar conteúdo semântico, não adicionar informações

## 2. Backend - Endpoint

- [x] 2.1 Adicionar `POST /conversations/{conversation_id}/rewrite` em `app/routes/messages.py` com body `{"text": str}`, validação de conversation exists, retorno `{"text": str}`

## 3. Frontend

- [x] 3.1 Adicionar botão "Reescrever" no `#btn-group` entre Enviar e 📎 em `index.html`
- [x] 3.2 Estilizar botão (distinto do verde do Enviar, consistente com 📎)
- [x] 3.3 Implementar handler JS: chamar endpoint, replace textarea, loading state ("Reescrevendo..."), disabled durante request, error handling
- [x] 3.4 Desabilitar botão quando textarea está vazio

## 4. Testes

- [x] 4.1 Teste do endpoint `/rewrite` com mock da chamada Haiku: sucesso, conversation not found, texto vazio
- [x] 4.2 Teste unitário da função `rewrite_text`: verifica chamada correta ao Anthropic client com prompt e tool_use esperados
