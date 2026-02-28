import json
import logging

import anthropic

from app.config import settings
from app.database import get_db
from app.services.knowledge import load_knowledge_base

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é o Caio respondendo mensagens de clientes no WhatsApp sobre seus cursos de IA.

## Postura
- Você é um vendedor consultivo: entende o problema da pessoa e direciona pro curso certo
- Se o curso não for pra ela, diga isso. Não force venda
- Seja direto, sem enrolação, mas humano e acessível
- Nunca minta sobre o que o curso oferece
- Não ofereça descontos. Quando a pessoa mostrar objeção de preço, mostre valor relativo (custo por dia, ROI, comparação com MBA/bootcamp)
- Quando a pessoa estiver vaga, qualifique antes de recomendar: pergunte o que ela faz, qual o objetivo, qual a experiência com dados/IA

## Tom
- Direto, informal brasileiro (sem ser coloquial demais)
- Primeira pessoa, como se fosse o Caio digitando
- Frases curtas, sem firulas
- Pode usar "vc", "pra", "tá" naturalmente
- Sem emojis excessivos (no máximo 1-2 por mensagem quando natural)

## Regras
- Sempre responda em português brasileiro
- Se o cliente perguntar algo que você não sabe, diga que vai verificar
- Nunca invente informações sobre os cursos que não estejam na base de conhecimento
- Se for a primeira mensagem, foque em entender o que a pessoa precisa antes de vender

## Formato de resposta
Responda SEMPRE em JSON com exatamente estes campos:
{
  "draft": "texto da mensagem proposta para o cliente",
  "justification": "1-2 frases explicando por que você escolheu essa abordagem (isso NÃO vai pro cliente, é só pro operador)"
}"""


async def generate_draft(conversation_id: int, trigger_message_id: int):
    db = await get_db()
    try:
        # Load conversation history
        rows = await db.execute(
            "SELECT direction, content FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
        )
        messages = await rows.fetchall()

        # Build conversation history for prompt
        history_lines = []
        for msg in messages:
            prefix = "Cliente" if msg["direction"] == "inbound" else "Caio"
            history_lines.append(f"{prefix}: {msg['content']}")

        conversation_history = "\n".join(history_lines)

        # Load knowledge base
        knowledge = load_knowledge_base()

        # Load few-shot examples (10 most recent edit pairs)
        rows = await db.execute(
            "SELECT customer_message, original_draft, final_message FROM edit_pairs ORDER BY created_at DESC LIMIT 10",
        )
        edit_pairs = await rows.fetchall()

        few_shot_text = ""
        if edit_pairs:
            examples = []
            for pair in reversed(list(edit_pairs)):
                examples.append(
                    f"Cliente disse: \"{pair['customer_message']}\"\n"
                    f"IA propôs: \"{pair['original_draft']}\"\n"
                    f"Caio enviou: \"{pair['final_message']}\""
                )
            few_shot_text = (
                "\n\n## Exemplos de como o Caio responde (aprenda com o tom e as correções)\n\n"
                + "\n\n---\n\n".join(examples)
            )

        # Assemble user prompt
        user_content = f"""## Base de conhecimento dos cursos

{knowledge}

{few_shot_text}

## Conversa atual

{conversation_history}

Gere o draft de resposta para a última mensagem do cliente."""

        # Call Claude API
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=settings.claude_model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )

        # Parse response (strip markdown code fences if present)
        response_text = response.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            response_text = response_text.rsplit("```", 1)[0].strip()
        try:
            parsed = json.loads(response_text)
            draft_text = parsed.get("draft", response_text)
            justification = parsed.get("justification", "")
        except json.JSONDecodeError:
            draft_text = response_text
            justification = "Resposta não veio em JSON, usando texto direto"

        # Save draft
        cursor = await db.execute(
            "INSERT INTO drafts (conversation_id, trigger_message_id, draft_text, justification) VALUES (?, ?, ?, ?)",
            (conversation_id, trigger_message_id, draft_text, justification),
        )
        draft_id = cursor.lastrowid
        await db.commit()

        # Notify frontend via WebSocket
        from app.websocket_manager import manager

        await manager.broadcast(
            conversation_id,
            {
                "type": "draft_ready",
                "conversation_id": conversation_id,
                "draft": {
                    "id": draft_id,
                    "conversation_id": conversation_id,
                    "trigger_message_id": trigger_message_id,
                    "draft_text": draft_text,
                    "justification": justification,
                    "status": "pending",
                },
            },
        )

    except Exception:
        logger.exception("Failed to generate draft for conversation %d", conversation_id)
    finally:
        await db.close()
