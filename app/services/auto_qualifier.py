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
                "description": "True se todas as perguntas foram bem respondidas e pode passar pro atendente"
            },
            "answers": {
                "type": "object",
                "description": "Mapa de cada pergunta configurada para a resposta extraída da conversa. Use o texto da pergunta como chave. Valor null se ainda não respondida, string com a resposta resumida se respondida.",
                "additionalProperties": {"type": ["string", "null"]}
            }
        },
        "required": ["message", "ready_for_handoff", "answers"]
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

    prompt = f"""Você é um entrevistador de pré-atendimento do {attendant_name}. Você é um assistente virtual e deve ser transparente sobre isso.

SEU ÚNICO TRABALHO é obter boas respostas para estas perguntas:
{questions}

COMO ENTREVISTAR:
- Você pode mandar várias perguntas de uma vez na primeira mensagem
- Se a pessoa responder de forma rasa ("sim", "trabalho com dados"), aprofunde com subperguntas: "onde? há quanto tempo? que tipo de trabalho?"
- Se a pessoa pular uma pergunta, volte nela depois
- Seja breve, informal, amigável. É WhatsApp, não email.
- Máximo de 4 trocas antes do handoff obrigatório

REGRA MAIS IMPORTANTE - NUNCA RESPONDA PERGUNTAS:
- Se a pessoa perguntar QUALQUER COISA (preço, conteúdo, certificado, duração, desconto, qualquer coisa), diga algo como "boa pergunta! o {attendant_name} vai te responder sobre isso" e volte para as perguntas de qualificação pendentes
- Você NÃO sabe nada sobre os cursos. Não tente ajudar, explicar, ou dar contexto
- Seu papel é APENAS fazer perguntas, NUNCA responder

CASO ESPECIAL - PRESENTE / COMPRANDO PARA OUTRA PESSOA:
- Se a pessoa indicar que está comprando para outra pessoa (presente, indicação, etc.), NÃO faça as perguntas de qualificação normais
- Colete apenas: qual curso e para quem é o presente
- Faça handoff imediato com essa informação

HANDOFF:
- Faça handoff quando todas as perguntas tiverem boas respostas
- No campo "answers" da tool, mapeie cada pergunta para a resposta extraída (ou null se não respondida)"""

    if greeting_example:
        prompt += f"\n\nPRIMEIRA MENSAGEM: use algo como \"{greeting_example}\" e já inclua as perguntas"

    if handoff_example:
        prompt += f"\nMENSAGEM DE HANDOFF: use algo como \"{handoff_example}\""

    if force_handoff:
        prompt += "\n\nIMPORTANTE: Você já trocou 4 mensagens. Faça o handoff AGORA, independente de ter todas as respostas. Inclua no answers o que conseguiu e null no que faltou."

    return prompt


async def auto_qualify_respond(conversation_id: int, trigger_message_id: int | None = None):
    """Handle auto-qualifying response for a conversation."""
    db = await get_db()
    try:
        # Load conversation
        row = await db.execute(
            "SELECT id, phone_number, contact_name, is_qualified FROM conversations WHERE id = ?",
            (conversation_id,),
        )
        conv = await row.fetchone()
        if not conv:
            return
        if conv["is_qualified"]:
            # Conversation was qualified between webhook read and now.
            # Generate drafts for the message that triggered this call.
            logger.info("Conv %d already qualified, falling back to generate_drafts (msg_id=%s)", conversation_id, trigger_message_id)
            if trigger_message_id:
                from app.services.draft_engine import generate_drafts
                await generate_drafts(conversation_id, trigger_message_id)
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
        answers = tool_result.get("answers", {})
        # Handoff if bot says ready, or all answers are non-null, or forced by exchange limit
        all_answered = answers and all(v is not None for v in answers.values())
        ready_for_handoff = tool_result.get("ready_for_handoff", False) or all_answered or force_handoff

        # Build structured qualification summary from answers
        summary_lines = []
        for question, answer in answers.items():
            if answer:
                summary_lines.append(f"- {question}: {answer}")
            else:
                summary_lines.append(f"- {question}: Não respondida")
        qualification_summary = "\n".join(summary_lines) if summary_lines else ""

        # Send message via Evolution API
        try:
            await send_text_message(conv["phone_number"], message_text)
        except Exception:
            logger.exception("Failed to send qualifying message for conv %d", conversation_id)
            return

        # Save message to DB
        cursor = await db.execute(
            """INSERT INTO messages (conversation_id, direction, content, sent_by)
               VALUES (?, 'outbound', ?, 'bot')""",
            (conversation_id, message_text),
        )
        msg_id = cursor.lastrowid

        # If ready for handoff
        if ready_for_handoff:
            await db.execute(
                "UPDATE conversations SET is_qualified = 1 WHERE id = ?",
                (conversation_id,),
            )

        await db.commit()

        # Broadcast the message (use known data instead of re-querying)
        await manager.broadcast(conversation_id, {
            "type": "new_message",
            "conversation_id": conversation_id,
            "message": {
                "id": msg_id,
                "conversation_id": conversation_id,
                "direction": "outbound",
                "content": message_text,
                "sent_by": "bot",
            },
        })

        if ready_for_handoff:
            # Generate situation summary from conversation history
            summary_result = None
            try:
                history = "\n".join(
                    f"{'Cliente' if m['direction'] == 'inbound' else 'Bot'}: {m['content']}"
                    for m in messages
                )
                # Include the bot's handoff message
                history += f"\nBot: {message_text}"
                summary_result = await generate_situation_summary(history, conv["contact_name"] or "")

                # Persist summary in drafts table so GET /conversations/{id} can find it
                await db.execute(
                    """INSERT INTO drafts (conversation_id, trigger_message_id, draft_text, situation_summary, variation_index, approach)
                       VALUES (?, ?, '', ?, 0, 'qualifying')""",
                    (conversation_id, msg_id, summary_result.get("summary", "")),
                )

                # Update funnel data if the summary provided product/stage
                if summary_result.get("product") or summary_result.get("stage"):
                    await db.execute(
                        "UPDATE conversations SET funnel_product = COALESCE(?, funnel_product), funnel_stage = COALESCE(?, funnel_stage) WHERE id = ?",
                        (summary_result.get("product"), summary_result.get("stage"), conversation_id),
                    )

                await db.commit()
            except Exception:
                logger.exception("Failed to generate summary after qualifying conv %d", conversation_id)

            # Broadcast qualification complete
            situation_summary_text = summary_result.get("summary", "") if summary_result else qualification_summary
            await manager.broadcast(conversation_id, {
                "type": "conversation_qualified",
                "conversation_id": conversation_id,
                "summary": situation_summary_text,
                "funnel_product": summary_result.get("product") if summary_result else None,
                "funnel_stage": summary_result.get("stage") if summary_result else None,
            })

    except Exception:
        logger.exception("Error in auto_qualify_respond for conv %d", conversation_id)
    finally:
        await db.close()
