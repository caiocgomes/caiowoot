## Context

CaioWoot envia mensagens de forma síncrona: operador clica "Enviar", sistema chama Evolution API imediatamente. Não existe mecanismo de envio diferido. Toda a lógica de envio (Evolution API + persistência + edit_pair + WebSocket broadcast) está inline no endpoint `POST /conversations/{id}/send`.

O sistema usa SQLite com WAL mode, asyncio sem workers externos, e frontend vanilla JS com WebSocket para real-time.

## Goals / Non-Goals

**Goals:**
- Permitir que o operador agende envio de mensagem de texto para um horário futuro
- Cancelar automaticamente envios agendados quando o cliente responde (contexto invalidado)
- Permitir cancelamento manual pelo operador
- Integrar com o learning loop (edit_pairs) quando o envio efetivamente acontece
- Sobreviver a restarts do servidor (envios pendentes não se perdem)

**Non-Goals:**
- Envio agendado de arquivos/imagens (apenas texto no v1)
- Agendamento recorrente ("toda segunda manda X")
- Agendamento baseado em eventos ("quando o boleto vencer")
- Interface de gestão global de todos os agendamentos

## Decisions

### 1. SQLite como fila de agendamentos (sem Redis/Celery/APScheduler)

Nova tabela `scheduled_sends` funciona como fila persistente. Um loop asyncio faz polling a cada 30 segundos buscando envios pendentes com `send_at <= now()`.

**Alternativas consideradas:**
- APScheduler com SQLite jobstore: adiciona dependência externa, API mais complexa do que o necessário
- Celery/Redis: infraestrutura desproporcional para o volume esperado (dezenas de agendamentos simultâneos, não milhares)

**Rationale:** O sistema já usa SQLite para tudo. O polling de 30s é aceitável para o caso de uso (follow-ups de vendas, não mensagens time-critical). Na reinicialização do servidor, o loop retoma e envia qualquer mensagem que ficou pendente durante downtime.

### 2. Atomicidade via UPDATE ... WHERE status = 'pending'

Tanto o loop de envio quanto o webhook de cancelamento fazem `UPDATE scheduled_sends SET status = X WHERE status = 'pending'`. SQLite serializa writes, então apenas um dos dois consegue transicionar o status. O que perder a corrida vê `changes() == 0` e segue sem ação.

### 3. Cancelamento por conversa inteira

Quando o cliente manda mensagem, TODOS os envios agendados pendentes daquela conversa são cancelados. Não faz sentido enviar mensagem pré-composta quando o contexto mudou.

### 4. Extração de lógica de envio para função compartilhada

A lógica de "enviar via Evolution API + inserir em messages + criar edit_pair + broadcast WebSocket" será extraída do endpoint `/send` para uma função `execute_send()` em um service. Tanto o endpoint quanto o background worker usam essa função.

### 5. Edit pair criado apenas no envio efetivo

Se o agendamento for cancelado, nenhum edit_pair é criado. Se for enviado pelo worker, o edit_pair é criado nesse momento com as informações do draft original (armazenadas na tabela `scheduled_sends`).

## Data Model

```sql
CREATE TABLE scheduled_sends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    content TEXT NOT NULL,
    send_at TIMESTAMP NOT NULL,
    status TEXT DEFAULT 'pending',
    cancelled_reason TEXT,
    cancelled_by_message_id INTEGER,
    draft_id INTEGER,
    draft_group_id TEXT,
    selected_draft_index INTEGER,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP
);
```

Status transitions: `pending` → `sending` → `sent` | `cancelled`

## Risks / Trade-offs

- **[Mensagem fora de contexto se cancelamento falhar]** → O cancelamento é atômico no SQLite; se o webhook processar a mensagem inbound, o UPDATE cancela antes do próximo polling. Janela de risco é de no máximo 30s se o polling já estiver executando no momento exato.
- **[Envios atrasados após downtime]** → Mensagens pendentes durante downtime são enviadas no restart. Para follow-ups de vendas isso é aceitável (melhor tarde do que nunca). O operador verá no UI que a mensagem foi enviada.
- **[Polling consome queries desnecessárias]** → Um SELECT a cada 30s em uma tabela pequena é negligível para SQLite. Indexar `(status, send_at)` garante performance.
