## Context

O draft engine gera respostas sugeridas chamando `build_prompt_parts` em `app/services/prompt_builder.py`. Essa função monta o `user_content` passado ao Haiku com histórico completo da conversa mais uma instrução final fixa:

```python
# prompt_builder.py:334
final_instruction = "Gere o draft de resposta para a última mensagem do cliente."
```

O ponto âncora (a "última mensagem do cliente") é resolvido implicitamente pelo modelo olhando o histórico. No fluxo inicial (cliente escreve, sistema gera 3 variações) isso funciona: o modelo responde ao que veio. No fluxo de regenerate, quando o operador já selecionou e enviou uma das variações anteriores, essa outbound entra no histórico mas a instrução continua mandando "responder à última mensagem do cliente". O modelo vê o histórico e infere que deve responder à última inbound, desconsiderando que parte já foi respondida, gerando drafts que repetem o que o operador já falou.

`proactive=True` já muda a instrução para "última foi do operador, gere continuação", mas esse flag não é ativado em regenerate por default. Além disso, a semântica de "proactive" é "lead silenciou, reengaje", diferente de "turno ainda aberto, complete a resposta".

## Goals / Non-Goals

**Goals:**
- Regenerar drafts considera o que o operador já enviou em resposta ao mesmo turn do cliente.
- Quando há outbound parcial, o modelo é instruído explicitamente a complementar, não a refazer.
- Fluxo inicial de `generate_drafts` (antes de qualquer outbound) permanece idêntico.
- Zero mudança de dependências, schema de banco ou interface.

**Non-Goals:**
- Detecção global de "turn do cliente" (sessões conversacionais com múltiplas inbounds). O escopo é dentro de um único `trigger_message_id`.
- Resumo automático do que foi respondido vs. que ficou em aberto. O modelo recebe as mensagens brutas e decide o que falta; não montamos análise estrutural.
- Mudar comportamento do `proactive=True`, que tem semântica diferente (reengajamento após silêncio).

## Decisions

### D1. Detecção por `trigger_message_id` em vez de heurística temporal

O ponto lógico do "turn" é o `message_id` da inbound que disparou o draft. `generate_drafts` e `regenerate_draft` já recebem esse id. Vamos propagá-lo até `build_prompt_parts`, que executa um `SELECT id, direction, content, created_at FROM messages WHERE conversation_id = ? AND id > ? AND direction = 'outbound' ORDER BY created_at`. Simples e preciso.

**Alternativa rejeitada:** inferir outbounds por janela temporal (últimos N minutos). Sensível a pausas longas, induz falsos positivos quando o operador trabalha devagar.

### D2. Seção dedicada no user_content, não inline com histórico

O histórico cronológico já contém as outbounds. Isso não basta: o modelo precisa de sinalização explícita de que essas outbounds foram em resposta a essa inbound específica. Adicionar seção tipo "## Respostas já enviadas neste turno" logo antes da instrução final dá sinal inequívoco.

**Alternativa rejeitada:** enriquecer o histórico com marcadores inline (`[resposta parcial]`). Bagunça o histórico limpo e não destaca o sinal. Seção separada isola o contrato.

### D3. Instrução final condicional

Quando há outbound intermediária, `final_instruction` vira:

> "O cliente mandou a mensagem acima e você já começou a responder. Suas mensagens já enviadas nesse turno estão listadas acima. O cliente ainda não respondeu. Gere um draft que complete o que ainda não foi endereçado na mensagem do cliente, sem repetir o que você já disse."

Quando não há outbound intermediária, mantém a instrução atual. Isso preserva o fluxo inicial.

**Alternativa rejeitada:** sempre usar a nova instrução. Desnecessariamente reescreve a semântica do fluxo inicial, risco de regressão em testes.

### D4. Passar `trigger_message_id` como parâmetro, não inferir

`build_prompt_parts` recebe `conversation_id` hoje. Adicionar `trigger_message_id` explícito evita a tentação de usar "última inbound do histórico" como proxy, que falharia se o cliente tivesse enviado novas mensagens enquanto o operador digitava (edge case raro mas possível).

**Alternativa rejeitada:** inferir `trigger_message_id = last_inbound_id`. Simples mas frágil; o caller já tem a info, então passamos.

### D5. Compatibilidade com calls externas

Outros calls para `build_prompt_parts` podem existir (rotas de attachment suggestion, proactive). Vamos fazer o parâmetro **opcional** (`trigger_message_id: int | None = None`). Se `None`, comportamento atual. Só `generate_drafts` e `regenerate_draft` vão passar o id.

## Risks / Trade-offs

- **[Modelo ignora a seção nova]** → mitigado pela instrução final explícita que refere a seção, e pela posição dela (próxima à instrução final, fresca na atenção do modelo).
- **[Operador editou e enviou mensagem não relacionada ao turn]** → a query pega TODA outbound depois do trigger. Se o operador mandou algo não relacionado (ex: um áudio, uma piada), vai aparecer na seção. Aceitável: melhor risco que a alternativa de ignorar. Se virar problema na prática, filtrar depois.
- **[Regenerate antes de enviar qualquer draft]** → nenhum outbound posterior ao trigger, seção fica vazia, comportamento idêntico ao atual. Por construção.
- **[Múltiplas outbounds acumuladas]** → seção pode ficar longa. Aceitável; é literal contexto necessário. Limite prático: se o operador mandou 10 mensagens sem resposta do cliente, o problema é outro.

## Migration Plan

Sem migration. Deploy direto; primeira regeneração após o deploy já reflete o novo comportamento.

**Rollback**: reverter o commit. Sem estado persistente afetado.

## Open Questions

Nenhuma. Implementação direta.
