## Why

Quando o operador regenera um draft depois de já ter enviado uma ou mais mensagens em resposta ao mesmo turn do cliente, os drafts regenerados ignoram essas mensagens e voltam a sugerir o que já foi dito. Exemplo real: cliente pergunta "qual a ementa?" e "quanto é?" no mesmo turn; o operador envia resposta sobre ementa; ao regenerar, o sistema sugere de novo variações sobre a ementa ao invés de avançar para o preço que ainda não foi respondido. O prompt sempre instrui o modelo a "responder à última mensagem do cliente", sem sinalizar que parte da resposta já foi enviada, então o Haiku ancora no mesmo ponto e refaz trabalho.

## What Changes

- `build_prompt_parts` passa a receber `trigger_message_id` e detecta outbounds subsequentes do operador até o momento da chamada.
- Quando há outbounds após o trigger, o `user_content` ganha uma seção explícita destacando as respostas já enviadas (com timestamps e texto) separadas do histórico cronológico geral.
- A `final_instruction` é reescrita nesse caso para dizer ao modelo que o operador já iniciou a resposta e o próximo draft deve complementar o que ficou em aberto no turn do cliente, sem repetir o que já foi dito.
- `generate_drafts` e `regenerate_draft` em `draft_engine.py` passam o `trigger_message_id` adiante.
- Sem mudança de comportamento quando não há outbound intermediária (fluxo original preservado).

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability. A mudança é refinamento do draft-engine existente. -->

### Modified Capabilities
- `draft-engine`: o contrato de "responder à última mensagem do cliente" passa a reconhecer respostas parciais já enviadas pelo operador no mesmo turn, instruindo o modelo a complementar em vez de repetir.

## Impact

- **Modifica** `app/services/prompt_builder.py`: assinatura de `build_prompt_parts` ganha `trigger_message_id`; nova seção opcional no `user_content`; instrução final condicional.
- **Modifica** `app/services/draft_engine.py`: `generate_drafts` e `regenerate_draft` passam `trigger_message_id` para `build_prompt_parts`.
- **Sem migration**, sem mudança de schema de banco, sem dependência nova.
- **Testes**: novos cenários cobrindo regenerate com outbounds intermediárias, fluxo original preservado, múltiplas outbounds no mesmo turn.
