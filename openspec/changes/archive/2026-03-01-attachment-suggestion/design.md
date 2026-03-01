## Context

O CaioWoot tem um loop de aprendizado contínuo: a cada mensagem enviada, o sistema grava um edit_pair (draft da IA vs mensagem final do operador), gera uma strategic annotation explicando a decisão, e usa esses exemplos como few-shot para drafts futuros.

O operador já pode enviar anexos (imagens e documentos via Evolution API). O arquivo é salvo em `data/attachments/` e a mensagem fica com `media_type` preenchido na tabela `messages`. Porém o edit_pair ignora completamente se houve anexo, e o draft engine não tem como sugerir um.

Os anexos recorrentes são handbooks de cursos (3-5 PDFs estáveis). O padrão de uso é previsível: o operador manda o handbook quando o cliente avança na decisão de compra ou pede detalhes do programa.

## Goals / Non-Goals

**Goals:**
- Capturar no edit_pair se o operador enviou anexo e qual arquivo
- Incluir informação de anexo nos few-shot examples e na strategic annotation
- Permitir que a LLM sugira um anexo específico no draft
- Exibir a sugestão no frontend com pré-carregamento do arquivo
- Manter handbooks em diretório conhecido para servir como catálogo implícito

**Non-Goals:**
- Upload de novos handbooks pelo frontend (operador adiciona arquivos manualmente no servidor)
- Sugestão de múltiplos anexos por draft
- Auto-envio de anexo sem confirmação do operador
- Indexar conteúdo dos PDFs para uso no prompt (a LLM sabe o nome, não o conteúdo)

## Decisions

### Diretório de anexos conhecidos: `knowledge/attachments/`

Os handbooks ficam em `knowledge/attachments/` com nomes descritivos (ex: `handbook-cdo.pdf`, `handbook-zero-a-analista.pdf`). O draft engine lista os arquivos desse diretório no momento de montar o prompt.

**Alternativa considerada**: tabela no banco com metadata dos anexos (nome, descrição, curso associado). Rejeitada porque adiciona CRUD sem necessidade. O filesystem já é o catálogo: o nome do arquivo é a identidade, e a LLM aprende quando usar cada um pelos exemplos.

### Coluna `attachment_filename` na tabela `edit_pairs`

Nova coluna `attachment_filename TEXT` em `edit_pairs`. Preenchida com o nome do arquivo quando o operador envia mensagem com anexo. NULL quando sem anexo. Grava apenas o filename (ex: `handbook-cdo.pdf`), não o path completo.

**Alternativa considerada**: gravar `media_type` no edit_pair em vez do filename. Rejeitada porque `media_type` é genérico ("document", "image") e não carrega informação suficiente para a LLM aprender qual arquivo específico enviar.

### Few-shot enriquecido com informação de anexo

O `_build_fewshot_from_retrieval` e `_build_fewshot_fallback` passam a incluir uma linha `Anexo enviado: <filename>` nos exemplos onde `attachment_filename` não é NULL. A LLM vê o padrão e aprende a associar situações com anexos.

**Alternativa considerada**: seção separada no prompt com estatísticas de uso de anexos. Rejeitada porque o few-shot já é o mecanismo natural de aprendizado do sistema. Adicionar mais uma seção fragmenta a informação.

### Lista de anexos disponíveis no prompt

Uma seção `## Anexos disponíveis` é adicionada ao user prompt com os nomes dos arquivos em `knowledge/attachments/`. Isso permite que a LLM saiba quais arquivos existem, mesmo antes de ter exemplos de uso.

O listing é dinâmico: lê o diretório a cada chamada. Sem cache, porque são poucos arquivos e o custo é negligível.

### Output JSON com campo `suggested_attachment`

O formato de resposta do draft muda de:
```json
{"draft": "...", "justification": "..."}
```
Para:
```json
{"draft": "...", "justification": "...", "suggested_attachment": "handbook-cdo.pdf"}
```

O campo `suggested_attachment` é opcional (pode ser `null` ou ausente). O `_parse_response` extrai o campo e o repassa junto com o draft.

**Alternativa considerada**: campo booleano `should_attach` sem especificar qual arquivo. Rejeitada porque o valor está em saber qual arquivo anexar, não apenas que algo deve ser anexado.

### Validação do arquivo sugerido

Quando a LLM sugere um `suggested_attachment`, o backend valida se o arquivo existe em `knowledge/attachments/`. Se não existir, o campo é descartado silenciosamente. Isso protege contra alucinações de filename.

### Strategic annotation enriquecida

O `generate_annotation` recebe o `attachment_filename` como parâmetro opcional. Quando presente, adiciona ao user content: `Operador anexou: <filename>`. A LLM de annotation passa a gerar anotações como "operador enviou handbook do CDO quando cliente pediu detalhes do programa".

### Frontend: sugestão de anexo no draft card

Quando o draft vem com `suggested_attachment`, o frontend exibe um indicador junto ao texto do draft (ex: "Sugestão: anexar handbook-cdo.pdf" com botão para aceitar). Ao aceitar, o sistema carrega o arquivo de `knowledge/attachments/` via um novo endpoint (`GET /api/attachments/<filename>`) e pré-popula o campo de attachment, como se o operador tivesse selecionado o arquivo manualmente.

O operador pode ignorar a sugestão e enviar só texto, ou trocar por outro anexo.

### Endpoint para servir anexos conhecidos

Novo endpoint `GET /api/attachments/<filename>` que serve arquivos de `knowledge/attachments/`. Usado pelo frontend para pré-carregar o anexo sugerido. Requer autenticação (cookie válido).

Novo endpoint `GET /api/attachments` que lista os arquivos disponíveis. Usado pelo draft engine para montar o prompt e pelo frontend se necessário.

## Risks / Trade-offs

- **LLM sugere anexo errado**: a validação de existência do arquivo mitiga alucinações de filename, mas a LLM pode sugerir handbook-cdo quando deveria ser handbook-zero-a-analista. Mitigação: conforme exemplos acumulam, a precisão melhora naturalmente. O operador sempre confirma antes de enviar.
- **Handbooks mudam de nome**: se o operador renomeia um arquivo, os edit_pairs antigos referenciam o nome velho, e a LLM pode sugerir um filename que não existe mais. Mitigação: a validação descarta sugestões de arquivos inexistentes. Os poucos exemplos com nome antigo saem do few-shot com o tempo.
- **Cold start**: antes de acumular edit_pairs com anexo, a LLM não tem exemplos para aprender. Mitigação: a seção "Anexos disponíveis" no prompt dá à LLM conhecimento dos arquivos desde o primeiro draft. A qualidade da sugestão melhora com uso.
- **Tamanho dos arquivos no endpoint**: servir PDFs grandes via o app pode ser lento. Mitigação: handbooks são tipicamente < 5MB, e o endpoint serve um arquivo por vez sob demanda.
