import asyncio
import json
import logging

from app.database import get_db
from app.services.claude_client import get_anthropic_client
from app.services.evolution import send_text_message
from app.services.prompt_config import get_all_prompts
from app.services.situation_summary import generate_situation_summary
from app.websocket_manager import manager

logger = logging.getLogger(__name__)

QUALIFY_TOOL = {
    "name": "qualify_response",
    "description": "Gera resposta de qualificação para o lead",
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Mensagem para enviar ao lead via WhatsApp"
            },
            "ready_for_handoff": {
                "type": "boolean",
                "description": "True se já tem informação suficiente para passar pro atendente humano"
            },
            "qualification_summary": {
                "type": "string",
                "description": "Resumo do que foi aprendido sobre o lead até agora"
            }
        },
        "required": ["message", "ready_for_handoff"]
    }
}


async def _build_qualifying_prompt(db, force_handoff=False) -> str:
    """Build the qualifying system prompt from configurable settings."""
    prompts = await get_all_prompts(db)

    attendant_name = prompts.get("qualifying_attendant_name", "o atendente")
    questions = prompts.get("qualifying_questions", "- Qual curso interessa\n- Experiência na área\n- Objetivo com o curso")
    greeting_template = prompts.get("qualifying_greeting", "")
    handoff_template = prompts.get("qualifying_handoff", "")

    # Build greeting and handoff examples with attendant name
    greeting_example = greeting_template.replace("{attendant_name}", attendant_name) if greeting_template else ""
    handoff_example = handoff_template.replace("{attendant_name}", attendant_name) if handoff_template else ""

    prompt = f"""Você é um assistente de pré-atendimento do {attendant_name}. Seu papel é:

1. Se apresentar de forma transparente: você é um assistente virtual, o {attendant_name} vai atender em seguida
2. Coletar informações básicas sobre a pessoa:
{questions}
3. Quando tiver informação suficiente (2-3 respostas úteis), fazer o handoff

REGRAS ABSOLUTAS:
- NUNCA finja ser humano. Você é um assistente virtual.
- NUNCA fale preço, desconto ou condições de pagamento
- NUNCA prometa nada sobre o curso
- NUNCA dê opinião sobre qual curso é melhor
- Se a pessoa perguntar sobre preço/pagamento, diga que o {attendant_name} vai explicar isso
- Seja breve, informal, amigável. É WhatsApp, não email.
- Máximo de 4 trocas antes do handoff obrigatório"""

    if greeting_example:
        prompt += f"\n- Na primeira mensagem, use algo como: \"{greeting_example}\""

    if handoff_example:
        prompt += f"\n- Quando fizer handoff, use algo como: \"{handoff_example}\""

    if force_handoff:
        prompt += "\n\nIMPORTANTE: Você já trocou 4 mensagens. Faça o handoff AGORA, independente de ter todas as informações."

    return prompt


async def auto_qualify_respond(conversation_id: int):
    """Handle auto-qualifying response for a conversation."""
    db = await get_db()
    try:
        # Load conversation
        row = await db.execute(
            "SELECT id, phone_number, contact_name, is_qualified FROM conversations WHERE id = ?",
            (conversation_id,),
        )
        conv = await row.fetchone()
        if not conv or conv["is_qualified"]:
            return

        # Load message history
        msgs_row = await db.execute(
            "SELECT direction, content, sent_by, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at",
            (conversation_id,),
        )
        messages = await msgs_row.fetchall()

        # Count bot messages to enforce max 4 exchanges
        bot_messages = sum(1 for m in messages if m["sent_by"] == "bot")

        # Build conversation history for Claude
        claude_messages = []
        for msg in messages:
            role = "user" if msg["direction"] == "inbound" else "assistant"
            claude_messages.append({"role": role, "content": msg["content"]})

        # If we've hit 4 bot messages already, force handoff
        force_handoff = bot_messages >= 4

        # Build prompt from configurable settings
        system_prompt = await _build_qualifying_prompt(db, force_handoff)

        # Call Claude
        client = get_anthropic_client()
        try:
            response = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                system=system_prompt,
                messages=claude_messages,
                tools=[QUALIFY_TOOL],
                tool_choice={"type": "tool", "name": "qualify_response"},
            )
        except Exception:
            logger.exception("Failed to call Claude for auto-qualifying conv %d", conversation_id)
            return

        # Extract tool response
        tool_result = None
        for block in response.content:
            if block.type == "tool_use" and block.name == "qualify_response":
                tool_result = block.input
                break

        if not tool_result:
            logger.error("No tool response from Claude for auto-qualifying conv %d", conversation_id)
            return

        message_text = tool_result["message"]
        ready_for_handoff = tool_result.get("ready_for_handoff", False) or force_handoff
        qualification_summary = tool_result.get("qualification_summary", "")

        # Send message via Evolution API
        try:
            await send_text_message(conv["phone_number"], message_text)
        except Exception:
            logger.exception("Failed to send qualifying message for conv %d", conversation_id)
            return

        # Save message to DB
        await db.execute(
            """INSERT INTO messages (conversation_id, direction, content, sent_by)
               VALUES (?, 'outbound', ?, 'bot')""",
            (conversation_id, message_text),
        )

        # If ready for handoff
        if ready_for_handoff:
            await db.execute(
                "UPDATE conversations SET is_qualified = 1 WHERE id = ?",
                (conversation_id,),
            )

        await db.commit()

        # Broadcast the message
        msg_row = await db.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT 1",
            (conversation_id,),
        )
        sent_msg = await msg_row.fetchone()

        await manager.broadcast(conversation_id, {
            "type": "new_message",
            "conversation_id": conversation_id,
            "message": dict(sent_msg),
        })

        if ready_for_handoff:
            # Generate situation summary
            try:
                await generate_situation_summary(conversation_id)
            except Exception:
                logger.exception("Failed to generate summary after qualifying conv %d", conversation_id)

            # Broadcast qualification complete
            await manager.broadcast(conversation_id, {
                "type": "conversation_qualified",
                "conversation_id": conversation_id,
                "summary": qualification_summary,
            })

    except Exception:
        logger.exception("Error in auto_qualify_respond for conv %d", conversation_id)
    finally:
        await db.close()
