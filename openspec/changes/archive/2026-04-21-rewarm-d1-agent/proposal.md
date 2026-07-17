## Why

Leads do curso CDO que recebem handbook ou link de pagamento, mas não fecham no mesmo dia, tendem a esfriar rapidamente. Hoje o operador precisaria revisar conversa por conversa para escrever uma mensagem de reesquentamento personalizada — inviável em escala. Precisamos de um agente que, em D+1, identifique essas conversas, leia o histórico de cada uma, decida se vale reesquentar e o que dizer, e dispare as mensagens — com revisão humana opcional nos primeiros dias até ganharmos confiança para rodar totalmente automatizado.

## What Changes

- Novo botão "Reesquentar D-1" na UI que dispara o agente para todas as conversas elegíveis no momento do clique.
- Agente por conversa decide entre `send` (com mensagem personalizada no tom da própria conversa) e `skip` (com razão logada) após ler o histórico completo.
- Tela de revisão transiente após o clique: lista as sugestões, permite editar/remover itens individuais, e envia em batch.
- Rate limit no envio em massa: intervalo base de 60s com jitter aleatório `uniform(-20, +40)` por envio (janela real 40s–100s).
- Flag de configuração `REWARM_AUTO_SEND` (default false). Quando ligada, o pipeline pula a tela de revisão e envia direto — preparando o caminho para automação via cron sem mudança de código.
- Telemetria de qualidade das mensagens de reesquentamento sai no fluxo de análise geral existente (`operator_coaching`/`conversation_analysis`), sem dashboard separado.

## Capabilities

### New Capabilities
- `rewarm-agent`: Agente autônomo que, disparado manualmente (ou via cron no futuro), identifica conversas CDO elegíveis a reesquentamento D-1, decide conteúdo por conversa lendo o histórico, apresenta para revisão (ou envia direto se flag automática estiver ligada) e dispara envios com rate limit anti-spam.

### Modified Capabilities
<!-- Nenhuma. `message-sender`, `conversation-funnel` e `operator-coaching` são reutilizados como estão. -->

## Impact

- **Novo service** `app/services/rewarm_engine.py` com prompt dedicado de agente de reesquentamento (Haiku).
- **Novo módulo de rotas** `app/routes/rewarm.py` com `POST /rewarm/preview` e `POST /rewarm/execute`.
- **Nova configuração** `REWARM_AUTO_SEND` em `app/config.py` (booleano, default false).
- **Frontend**: botão novo + modal de revisão em `app/static/` (HTML/JS/CSS). Reusa padrões de UI existentes.
- **Reuso** de `app/services/message_sender.py` para envio efetivo e de `app/services/claude_client.py` para chamadas Haiku.
- **Sem migrações de banco.** A query filtra só pelo estado atual de `conversations.funnel_product`, `funnel_stage` e pela presença de mensagens em D-1 na tabela `messages`.
- **Interação com fluxo normal**: o endpoint pula conversas que tenham draft pendente (não enviado) para não encavalar com respostas em aberto.
