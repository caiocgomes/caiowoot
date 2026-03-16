## Context

O CaioWoot é um copiloto de vendas para WhatsApp. Hoje, toda mensagem inbound gera 3 drafts para o operador humano escolher. O operador é o gargalo: se não está disponível, o lead espera. Este design adiciona um robô de qualificação que atende o lead automaticamente na primeira interação, coleta informações básicas, e entrega a conversa qualificada para o operador.

## Goals / Non-Goals

**Goals:**
- Resposta imediata ao lead na primeira interação (< 5 segundos)
- Coletar informações de qualificação: curso de interesse, experiência, objetivo, dúvida
- Handoff transparente para operador humano com resumo pronto
- Operador pode assumir a conversa a qualquer momento
- Estado visual claro: conversa em qualifying (amarela) vs qualificada (verde)

**Non-Goals:**
- O robô NÃO vende. Não fala preço, não dá desconto, não faz promessas
- O robô NÃO finge ser humano
- Não existe "modo robô" permanente. É one-shot: qualifica e sai
- Não há re-qualifying. Uma vez True, nunca volta a False

## Decisions

### Estado no banco

```sql
ALTER TABLE conversations ADD COLUMN is_qualified INTEGER DEFAULT 0;
```

Novas conversas criadas pelo webhook começam com `is_qualified = 0` (False). O campo é permanente: uma vez setado para 1, não volta.

Para conversas existentes: migration seta `is_qualified = 1` (já foram atendidas por humano, não faz sentido qualificar).

### Prompt do robô de qualifying

O prompt é separado dos prompts de draft. Fica em `app/services/auto_qualifier.py`:

```python
QUALIFYING_SYSTEM_PROMPT = """
Você é um assistente de pré-atendimento do {operator_name}. Seu papel é:

1. Se apresentar de forma transparente: você é um assistente virtual, o {operator_name} vai atender em seguida
2. Coletar informações básicas sobre o lead:
   - Qual curso interessa (se não ficou claro pela mensagem)
   - Se já trabalha na área / nível de experiência
   - Qual o objetivo com o curso
   - Se tem alguma dúvida específica
3. Quando tiver informação suficiente (2-3 respostas úteis), fazer o handoff

REGRAS ABSOLUTAS:
- NUNCA finja ser humano
- NUNCA fale preço, desconto ou condições de pagamento
- NUNCA prometa nada sobre o curso
- NUNCA dê opinião sobre qual curso é melhor
- Se o lead perguntar sobre preço/pagamento, diga que o {operator_name} vai explicar isso
- Seja breve, informal, amigável. WhatsApp, não email
- Máximo de 4 trocas de mensagem antes do handoff
- Quando fizer handoff, diga algo como "Beleza, já passei tudo pro {operator_name}! Ele já tem todo o contexto da nossa conversa."

Use a tool "qualify_response" para responder.
"""
```

O prompt usa tool_use para structured output:

```python
QUALIFY_TOOL = {
    "name": "qualify_response",
    "description": "Gera resposta de qualificação",
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Mensagem para enviar ao lead"},
            "ready_for_handoff": {"type": "boolean", "description": "True se já tem info suficiente para passar pro operador"},
            "qualification_summary": {"type": "string", "description": "Resumo do que foi aprendido sobre o lead até agora"}
        },
        "required": ["message", "ready_for_handoff"]
    }
}
```

### Fluxo no webhook

```python
# webhook.py (dentro do handler de mensagem inbound)

# Checar se conversa está em qualifying
if not conversation["is_qualified"]:
    # Disparar auto-qualifying em background
    asyncio.create_task(auto_qualify_respond(conversation_id))
    # NÃO gerar drafts
    return

# Fluxo normal: gerar drafts
asyncio.create_task(generate_drafts(...))
```

### Fluxo do auto_qualifier

```python
async def auto_qualify_respond(conversation_id):
    # 1. Carregar histórico da conversa
    # 2. Montar prompt com QUALIFYING_SYSTEM_PROMPT + histórico
    # 3. Chamar Claude Haiku com tool_use
    # 4. Extrair message e ready_for_handoff
    # 5. Enviar message via Evolution API
    # 6. Inserir message no DB (direction=outbound, sent_by="bot")
    # 7. Se ready_for_handoff:
    #    a. UPDATE conversations SET is_qualified = 1
    #    b. Gerar situation_summary
    #    c. Broadcast WS com type="conversation_qualified"
    # 8. Broadcast WS com a mensagem enviada
```

### Handoff manual (assumir conversa)

```python
@router.post("/conversations/{id}/assume")
async def assume_conversation(id: int, db = Depends(get_db_connection)):
    await db.execute("UPDATE conversations SET is_qualified = 1 WHERE id = ?", (id,))
    await db.commit()
    # Broadcast para UI atualizar
    await manager.broadcast(0, {"type": "conversation_assumed", "conversation_id": id})
    return {"status": "ok"}
```

### Frontend: estado visual

**Sidebar:**
```css
.conv-item.qualifying { border-left: 3px solid #f57f17; }
.conv-item.qualifying .conv-name::before { content: "🤖 "; }
```

**Chat view quando is_qualified = False:**
- Mensagens aparecem normalmente (operador vê o que o robô e o lead estão dizendo)
- A área de composição (#compose) é substituída por:
```html
<div id="qualifying-banner">
  <span>🤖 Robô qualificando esta conversa</span>
  <button onclick="assumeConversation()">Assumir conversa</button>
</div>
```

**Transição para qualificada:**
- Quando `conversation_qualified` ou `conversation_assumed` chega via WS:
  - Sidebar: remove classe `qualifying`, adiciona indicador verde
  - Chat: banner desaparece, compose normal aparece
  - Context panel: atualiza com o resumo de qualificação

### Mensagens do robô no histórico

As mensagens enviadas pelo robô são salvas com `sent_by = "bot"` (distinct de operador humano). No chat, podem ter um estilo levemente diferente (ícone de robô, cor mais suave) para o operador saber visualmente quais foram automáticas.

```css
.msg.outbound.bot { background: #e3f2fd; }  /* azul claro em vez de verde */
```

### Knowledge base no qualifying

O robô de qualifying NÃO usa a knowledge base completa. Ele sabe os NOMES dos cursos (para perguntar qual interessa) mas não tem detalhes de conteúdo/preço. Isso evita que ele dê informações que deveriam vir do operador.

Os nomes dos cursos vêm da lista de produtos no context panel (curso-llm, curso-zero-a-analista, curso-cdo, ai-para-influencers).

## Risks / Trade-offs

**O robô pode espantar leads sensíveis a automação.** Mitigação: a mensagem de abertura é transparente e acolhedora. Se o lead ignorar ou disser "quero falar com gente", o robô faz handoff imediato.

**Limite de 4 trocas pode ser insuficiente para leads que falam pouco.** Mitigação: o prompt instrui o robô a fazer handoff mesmo com informação parcial. Qualquer coisa é melhor que nada.

**A mensagem "outbound" do robô via Evolution API consome o mesmo rate do operador.** Para volume baixo de novos leads, isso não é problema.

**Conversas existentes vão ser marcadas como is_qualified = 1 pela migration.** Isso é o comportamento correto: não queremos o robô entrando em conversas que já estão em andamento.
