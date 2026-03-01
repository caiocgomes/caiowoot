## Why

Hoje o `draft_engine` monta o prompt para o Claude sem nenhuma informação sobre quem é o cliente. O `contact_name` (vindo do `pushName` do WhatsApp) já existe no banco e já aparece na interface para o operador, mas a LLM gera respostas genéricas sem saber o nome da pessoa. Isso faz as mensagens soarem impessoais, especialmente em conversas mais longas onde seria natural o Caio usar o primeiro nome do cliente.

## What Changes

- Buscar o `contact_name` da conversa dentro de `_build_prompt_parts` e incluí-lo como contexto no prompt enviado ao Claude
- Extrair o primeiro nome do `contact_name` (para evitar usar nome completo, que soa artificial no WhatsApp)
- Adicionar orientação no system prompt sobre quando e como usar o nome (de forma natural, sem repetir a cada mensagem)
- Aumentar a altura do campo de escrita de mensagens na interface para exibir mais linhas de uma vez (está pequeno e difícil de ler)

## Capabilities

### New Capabilities

- `sender-context`: Inclusão do primeiro nome do cliente como contexto no prompt de geração de drafts, com orientação de uso natural no system prompt
- `bigger-edit-field`: Aumentar a área de edição de mensagens na interface para mostrar mais linhas visíveis

### Modified Capabilities

_(nenhuma capability existente tem spec formal afetada)_

## Impact

- **Código**: `app/services/draft_engine.py` (funções `_build_prompt_parts` e possivelmente `SYSTEM_PROMPT`), `app/static/app.js` e/ou CSS (campo de edição)
- **Banco**: Nenhuma alteração de schema; usa `conversations.contact_name` que já existe
- **Tokens**: Aumento negligível (uma linha a mais no prompt)
- **Comportamento**: Drafts passarão a usar o primeiro nome do cliente ocasionalmente. O operador mantém controle total (pode editar antes de enviar). Campo de edição fica maior e mais confortável para ler/editar
- **Testes**: Testes existentes de geração de draft precisam ser atualizados para incluir `contact_name` no fixture de conversa
