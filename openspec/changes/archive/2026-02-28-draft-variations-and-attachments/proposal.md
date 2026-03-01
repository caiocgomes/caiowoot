## Why

O CaioWoot hoje gera um único draft de resposta por mensagem recebida. Isso força o operador a aceitar a abordagem que a IA escolheu ou reescrever do zero. Falta controle sobre o tom e a direção da resposta, falta capacidade de enviar anexos (PDFs de curso, imagens), e o sistema não armazena dados suficientes para tuning futuro do modelo.

## What Changes

- O draft engine passa a gerar 3 variações de resposta em paralelo usando Haiku (mais rápido e barato que Sonnet para variações)
- O operador visualiza as 3 opções, escolhe uma, edita se quiser e envia
- Cada opção individual pode ser regenerada, ou todas de uma vez
- Uma barra de instrução permite ao operador dar contexto/direção para a IA antes de regenerar ("foca no preço", "ela é técnica, pode aprofundar")
- O operador pode anexar arquivos (imagem, PDF, documento) ao enviar a mensagem
- O sistema salva o prompt completo usado em arquivo no disco (nomeado pelo hash) e registra no banco: todas as opções geradas, qual foi escolhida, instrução do operador, mensagem final enviada, contagem de regenerações
- O textarea de composição da resposta passa a ser maior (mais linhas visíveis), facilitando leitura e edição de respostas longas

## Capabilities

### New Capabilities
- `draft-variations`: Geração de 3 variações de draft em paralelo via Haiku, com seleção, regeneração individual/total e barra de instrução do operador
- `attachments`: Upload e envio de anexos (imagem, PDF, documento) via Evolution API
- `prompt-logging`: Persistência do prompt completo em arquivo (hash.txt) e registro expandido de edit_pairs para tuning futuro

### Modified Capabilities
- `draft-engine`: Muda de 1 draft Sonnet para 3 variações Haiku em paralelo, incorpora instrução do operador no prompt
- `inbox-ui`: Nova área de variações com botões de seleção/regeneração, barra de instrução, botão de anexo
- `message-sender`: Suporte a envio de mídia via Evolution API (sendMedia/sendDocument)

## Impact

- **app/services/draft_engine.py**: Refatorar para gerar 3 variações em paralelo, aceitar instrução do operador, salvar prompt em disco
- **app/static/index.html + app.js**: Nova UI com área de variações, barra de instrução, upload de anexo
- **app/routes/messages.py**: Aceitar multipart/form-data com arquivo, rotear para endpoint correto da Evolution API
- **app/database.py**: Schema de drafts e edit_pairs expandido (operator_instruction, selected_draft_index, all_drafts, prompt_hash, regeneration_count, media_url, media_type)
- **app/services/evolution.py**: Novos métodos para sendMedia/sendDocument
- **app/models.py**: Modelos atualizados
- **Diretório data/prompts/**: Novo diretório para arquivos de prompt
- **Dependência**: Modelo Haiku (claude-haiku-4-5-20251001) adicionado ao .env/config
