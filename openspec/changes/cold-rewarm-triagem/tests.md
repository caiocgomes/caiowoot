## Cenários de teste

### Classificação (`tests/test_cold_triage_classify.py`)

- **[given] conversa com "mês que vem volto" [when] classify [then]** retorna `classification='objecao_timing'`, `quote_from_lead` contém a frase do lead, `confidence='high'`.
- **[given] conversa onde lead viu preço e não respondeu [when] classify [then]** `classification='objecao_preco'`, quote cita a reação ao preço.
- **[given] conversa com "não quero mais" [when] classify [then]** `classification='negativo_explicito'`, confidence='high'.
- **[given] conversa genérica sem sinal claro [when] classify [then]** `classification='perdido_no_ruido'` ou `'nao_classificavel'`, confidence≤med.
- **[given] Haiku retorna confidence='low' [when] apply_matrix depois [then]** ação = 'skip' independente da classification.
- **[given] Haiku falha (timeout/exception) [when] classify [then]** retorna dict com classification='nao_classificavel' e confidence='low' (não levanta).

### Matriz (`tests/test_cold_triage_matrix.py`)

Tabela esperada com cap não atingido:

| classification      | link_sent | handbook_sent |
|---------------------|-----------|---------------|
| objecao_preco       | mentoria  | skip          |
| objecao_timing      | mentoria  | mentoria      |
| objecao_conteudo    | mentoria  | conteudo      |
| tire_kicker         | skip      | skip          |
| negativo_explicito  | skip      | skip          |
| perdido_no_ruido    | conteudo  | skip          |
| nao_classificavel   | skip      | skip          |

Com cap atingido (`mentoria_used >= cap`):

| classification      | link_sent | handbook_sent |
|---------------------|-----------|---------------|
| objecao_preco       | conteudo  | skip          |
| objecao_timing      | conteudo  | skip          |
| objecao_conteudo    | conteudo  | skip          |

- Um teste por linha de cada tabela (parametrizado).
- Confidence low sempre força skip.

### Seleção (`tests/test_cold_triage_candidates.py`)

- **[given] conversas variadas [when] select_cold_candidates [then]** retorna apenas curso-cdo + handbook/link + última inbound >30d + não no cooldown.
- **[given] conversa com cold_do_not_contact=1 [when] select [then]** não aparece.
- **[given] conversa com cold_dispatch criado há 60 dias [when] select [then]** não aparece (cooldown 90d).
- **[given] conversa com cold_dispatch há 100 dias [when] select [then]** aparece de novo.
- **[given] mix link/handbook [when] select [then]** link_sent vem antes na ordenação.
- **[given] mix de dias frios [when] select [then]** mais frescos vêm antes dentro do mesmo estágio.

### Compositor (`tests/test_cold_triage_compose.py`)

- **[given] action=mentoria + quote='mes que vem volto' [when] compose [then]** prompt Haiku recebe a quote no user content (verifica chamada).
- **[given] Haiku retorna message string [when] compose [then]** retorna a string exata.
- **[given] Haiku retorna vazio [when] compose [then]** retorna string vazia (fallback, apply_matrix já tratou).
- **[given] sistema roda compose [then]** messages.create é chamado com tool COLD_COMPOSE_TOOL.

### Routes (`tests/test_cold_rewarm_routes.py`)

- **[given] candidatos válidos + Haiku mocks [when] POST /cold-rewarm/preview [then]** 200, lista de items, grava status='previewed' em cold_dispatches.
- **[given] pool vazio [when] POST preview [then]** retorna [].
- **[given] items aprovados [when] POST execute [then]** 202, background task dispara, cold_dispatches atualizado para status='sent' com scheduled_send_id.
- **[given] item com mensagem editada no payload [when] execute [then]** `message_sent` = mensagem editada, `message_draft` permanece com o original.
- **[given] execute falha em 1 item [when] batch [then]** demais continuam, item falho fica status='failed'.

### Reward hook (`tests/test_cold_reward_hook.py`)

- **[given] conv com cold_dispatch sent <7d [when] webhook inbound [then]** responded_at é preenchido.
- **[given] conv sem cold_dispatch [when] webhook inbound [then]** nada acontece no cold (D-1 hook continua independente).
- **[given] cold_dispatch já com responded_at [when] inbound novo [then]** responded_at não é sobrescrito.
- **[given] cold_dispatch sent há 30 dias [when] inbound [then]** não conta (janela de reward expirou).

### Cap mensal (`tests/test_cold_mentoria_cap.py`)

- **[given] 15 dispatches com action=mentoria sent este mês [when] run_preview [then]** próximos candidatos com ação lógica mentoria viram conteudo (link) ou skip (handbook).
- **[given] dispatches do mês anterior [when] contagem [then]** não contam (zera no dia 1 do mês).
- **[given] dispatches status=previewed (não aprovados) [when] contagem [then]** não contam (só sent/approved).
