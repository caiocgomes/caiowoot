## Context

O draft engine monta o histórico de conversa como uma sequência plana de `Cliente: texto` / `Caio: texto` sem nenhuma informação de quando cada mensagem aconteceu. A tabela `messages` já tem `created_at` para cada mensagem. O campo é preenchido no INSERT tanto pelo webhook (inbound) quanto pelo send (outbound).

O operador frequentemente responde horas depois da última mensagem do cliente. A LLM não tem como saber disso e gera drafts que ignoram o gap temporal, o que resulta em respostas que parecem fora de contexto.

## Goals / Non-Goals

**Goals:**
- Incluir timestamps nas últimas mensagens do histórico para dar noção de ritmo da conversa
- Informar explicitamente o horário atual e o tempo de espera do cliente
- Permitir que a LLM adapte o tom quando há atraso significativo

**Non-Goals:**
- Mudar o formato de armazenamento das mensagens
- Adicionar timezone configurável (usar horário do servidor, que é o do operador)
- Mudar o comportamento do situation summary (ele já captura contexto suficiente)
- Timestamps nos few-shot examples (complicaria sem benefício claro)

## Decisions

**Timestamps apenas nas últimas 10 mensagens, mensagens anteriores sem timestamp.**
As primeiras mensagens da conversa estabelecem contexto geral (quem é o cliente, o que quer). Timestamp nelas é ruído. As últimas 10 são onde o ritmo da conversa importa. Alternativa considerada: timestamps em todas (gasta tokens sem ganho), apenas na última (perde o ritmo entre mensagens recentes).

**Formato de timestamp: `[HH:MM]` para mensagens de hoje, `[DD/MM HH:MM]` para dias anteriores.**
Otimiza legibilidade. A LLM não precisa do ano. Horário no formato 24h porque é o padrão brasileiro e evita ambiguidade AM/PM.

**Seção explícita de contexto temporal no final do prompt, antes do pedido de geração.**
Uma linha com horário atual e tempo de espera calculado. Fica próximo da instrução de geração para ter mais peso no output. Formato: `## Contexto temporal\nAgora são HH:MM (DD/MM). Última mensagem do cliente foi há Xh Ymin.`

**Instrução no system prompt para a LLM considerar o contexto temporal.**
Adicionar orientação leve no system prompt: reconhecer atrasos quando relevante (sem ser servil), ajustar cumprimento ao horário. Sem forçar fórmulas fixas.

## Risks / Trade-offs

Aumento de tokens no prompt (marginal: ~50-100 tokens extras para timestamps + contexto) → Custo negligível dado o volume atual.

LLM pode ficar excessivamente apologética em atrasos pequenos (30min) → Mitigação via instrução no system prompt orientando a só mencionar atraso quando for significativo (> 1-2 horas).
