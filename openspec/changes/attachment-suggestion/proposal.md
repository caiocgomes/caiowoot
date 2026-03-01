## Why

Quando o operador envia uma mensagem com anexo (ex: handbook de um curso), essa informação não entra no loop de aprendizado. O edit_pair grava apenas o texto, e o fato de ter ido um PDF junto desaparece. A LLM nunca vê exemplos como "nessa situação, o operador mandou o handbook do CDO", então não tem como aprender o padrão e sugerir anexos proativamente.

## What Changes

- Handbooks e outros anexos recorrentes ficam em um diretório conhecido (`knowledge/attachments/`) com nomes estáveis
- O edit_pair passa a registrar se o operador enviou um anexo e qual arquivo foi
- Os few-shot examples passam a incluir a informação de anexo ("Caio enviou [texto] + anexo: handbook CEO.pdf")
- A strategic annotation passa a considerar o envio de anexo na análise
- O formato JSON de saída do draft ganha campo opcional `suggested_attachment` com o nome do arquivo
- O frontend exibe a sugestão de anexo junto do draft, permitindo aceitar (pré-carrega o arquivo) ou ignorar

## Capabilities

### New Capabilities
- `attachment-suggestion`: Sugestão de anexo pelo draft engine. Cobre o catálogo implícito de arquivos em diretório conhecido, a inclusão de anexos disponíveis no prompt, o campo `suggested_attachment` no output JSON do draft, e a exibição/interação da sugestão no frontend.

### Modified Capabilities
- `message-sender`: Edit pair passa a capturar `attachment_filename` quando o operador envia mensagem com anexo.
- `draft-engine`: Prompt inclui lista de anexos disponíveis e few-shot examples passam a mostrar informação de anexo. Output JSON aceita campo `suggested_attachment`.
- `strategic-annotation`: Análise passa a considerar se o operador anexou um arquivo e qual, gerando annotations que capturam esse comportamento.
- `smart-retrieval`: Few-shot examples construídos a partir de edit_pairs passam a incluir informação de anexo quando presente.

## Impact

- **Backend**: `database.py` (migration para `attachment_filename` em `edit_pairs`), `routes/messages.py` (gravar attachment_filename no edit_pair), `services/draft_engine.py` (listar anexos no prompt, parsear `suggested_attachment`, incluir anexo nos few-shots), `services/strategic_annotation.py` (incluir anexo na análise)
- **Frontend**: `app.js` (exibir sugestão de anexo no draft, pré-carregar arquivo ao aceitar)
- **Storage**: Diretório `knowledge/attachments/` com os handbooks como arquivos de referência
- **Banco**: Migration adicionando coluna `attachment_filename TEXT` na tabela `edit_pairs`
