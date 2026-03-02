## Why

O operador frequentemente rascunha respostas rápidas no textarea com erros de digitação, frases truncadas e explicações incompletas. Hoje ele precisa reescrever manualmente ou selecionar um draft gerado pela IA (que pode não refletir exatamente o que ele queria dizer). Falta um caminho intermediário: "eu sei o que quero dizer, só preciso que fique bonito".

## What Changes

- Novo botão "Reescrever" no grupo de botões do compose area (junto com Enviar e 📎)
- Novo endpoint `POST /conversations/{id}/rewrite` que recebe o texto do textarea e retorna uma versão polida via Claude Haiku
- O texto reescrito substitui o conteúdo do textarea diretamente (replace in-place)
- Prompt fixo focado em: português correto, tom de WhatsApp, sem adicionar informações novas, seguir de perto o conteúdo original

## Capabilities

### New Capabilities
- `text-rewrite`: Polish de texto livre do operador via LLM. Recebe texto rascunhado, retorna versão com português correto e tom adequado para WhatsApp, sem alterar o conteúdo semântico.

### Modified Capabilities
- `inbox-ui`: Novo botão "Reescrever" no btn-group do compose area, com feedback visual durante o processamento.

## Impact

- **Backend**: Novo endpoint em `app/routes/conversations.py`, nova função de serviço para chamada Haiku
- **Frontend**: Novo botão em `app/static/index.html`, novo handler JS em `app/static/app.js`
- **Testes**: Novos testes para o endpoint e para a lógica de rewrite
- **Dependências**: Nenhuma nova (usa Claude Haiku que já está integrado)
