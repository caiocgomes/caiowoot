import asyncio
import json
import logging
import uuid

import anthropic

from app.config import settings
from app.database import get_db
from app.services.knowledge import load_knowledge_base
from app.services.prompt_logger import save_prompt

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

APPROACH_MODIFIERS = [
    ("direta", "Responda de forma direta e objetiva, indo direto ao ponto."),
    ("consultiva", "Responda de forma consultiva, fazendo perguntas de qualificação antes de recomendar."),
    ("casual", "Responda de forma mais casual e acolhedora, priorizando conexão humana."),
]


def _parse_response(response_text: str) -> tuple[str, str]:
    text = response_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(text)
        return parsed.get("draft", text), parsed.get("justification", "")
    except json.JSONDecodeError:
        return text, "Resposta não veio em JSON, usando texto direto"


async def _build_prompt_parts(db, conversation_id: int, operator_instruction: str | None = None):
    rows = await db.execute(
        "SELECT direction, content FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conversation_id,),
    )
    messages = await rows.fetchall()

    history_lines = []
    for msg in messages:
        prefix = "Cliente" if msg["direction"] == "inbound" else "Caio"
        history_lines.append(f"{prefix}: {msg['content']}")
    conversation_history = "\n".join(history_lines)

    knowledge = load_knowledge_base()

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

    instruction_text = ""
    if operator_instruction:
        instruction_text = f"\n\n## Instrução do operador\n{operator_instruction}"

    user_content = f"""## Base de conhecimento dos cursos

{knowledge}

{few_shot_text}
{instruction_text}

## Conversa atual

{conversation_history}

Gere o draft de resposta para a última mensagem do cliente."""

    return user_content


async def _call_haiku(user_content: str, approach_modifier: str) -> tuple[str, str]:
    system = SYSTEM_PROMPT + f"\n\n## Estilo desta variação\n{approach_modifier}"
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=settings.claude_haiku_model,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )
    return _parse_response(response.content[0].text)


async def generate_drafts(
    conversation_id: int,
    trigger_message_id: int,
    operator_instruction: str | None = None,
):
    db = await get_db()
    try:
        user_content = await _build_prompt_parts(db, conversation_id, operator_instruction)

        full_prompt = SYSTEM_PROMPT + "\n\n" + user_content
        prompt_hash = save_prompt(full_prompt)

        draft_group_id = str(uuid.uuid4())

        tasks = [
            _call_haiku(user_content, modifier)
            for _, modifier in APPROACH_MODIFIERS
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        drafts = []
        for i, (approach_name, _) in enumerate(APPROACH_MODIFIERS):
            if isinstance(results[i], Exception):
                logger.error("Draft variation %d failed: %s", i, results[i])
                draft_text = "(Erro ao gerar esta variação)"
                justification = str(results[i])
            else:
                draft_text, justification = results[i]

            cursor = await db.execute(
                """INSERT INTO drafts
                   (conversation_id, trigger_message_id, draft_text, justification,
                    draft_group_id, variation_index, approach, prompt_hash, operator_instruction)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (conversation_id, trigger_message_id, draft_text, justification,
                 draft_group_id, i, approach_name, prompt_hash, operator_instruction),
            )
            drafts.append({
                "id": cursor.lastrowid,
                "conversation_id": conversation_id,
                "trigger_message_id": trigger_message_id,
                "draft_text": draft_text,
                "justification": justification,
                "status": "pending",
                "draft_group_id": draft_group_id,
                "variation_index": i,
                "approach": approach_name,
            })

        await db.commit()

        from app.websocket_manager import manager
        await manager.broadcast(
            conversation_id,
            {
                "type": "drafts_ready",
                "conversation_id": conversation_id,
                "draft_group_id": draft_group_id,
                "drafts": drafts,
            },
        )

    except Exception:
        logger.exception("Failed to generate drafts for conversation %d", conversation_id)
    finally:
        await db.close()


async def regenerate_draft(
    conversation_id: int,
    trigger_message_id: int,
    draft_index: int | None = None,
    operator_instruction: str | None = None,
):
    db = await get_db()
    try:
        user_content = await _build_prompt_parts(db, conversation_id, operator_instruction)
        full_prompt = SYSTEM_PROMPT + "\n\n" + user_content
        prompt_hash = save_prompt(full_prompt)

        if draft_index is not None:
            approach_name, modifier = APPROACH_MODIFIERS[draft_index]
            draft_text, justification = await _call_haiku(user_content, modifier)

            row = await db.execute(
                """SELECT id, draft_group_id FROM drafts
                   WHERE conversation_id = ? AND trigger_message_id = ? AND variation_index = ? AND status = 'pending'
                   ORDER BY created_at DESC LIMIT 1""",
                (conversation_id, trigger_message_id, draft_index),
            )
            existing = await row.fetchone()
            if existing:
                await db.execute(
                    """UPDATE drafts SET draft_text = ?, justification = ?, prompt_hash = ?, operator_instruction = ?
                       WHERE id = ?""",
                    (draft_text, justification, prompt_hash, operator_instruction, existing["id"]),
                )
                draft_group_id = existing["draft_group_id"]
            await db.commit()

            row = await db.execute(
                "SELECT * FROM drafts WHERE draft_group_id = ? ORDER BY variation_index",
                (draft_group_id,),
            )
            all_drafts = await row.fetchall()
            drafts = [{
                "id": d["id"], "conversation_id": d["conversation_id"],
                "trigger_message_id": d["trigger_message_id"],
                "draft_text": d["draft_text"], "justification": d["justification"],
                "status": d["status"], "draft_group_id": d["draft_group_id"],
                "variation_index": d["variation_index"], "approach": d["approach"],
            } for d in all_drafts]

        else:
            row = await db.execute(
                """SELECT draft_group_id FROM drafts
                   WHERE conversation_id = ? AND trigger_message_id = ? AND status = 'pending'
                   ORDER BY created_at DESC LIMIT 1""",
                (conversation_id, trigger_message_id),
            )
            existing = await row.fetchone()
            draft_group_id = existing["draft_group_id"] if existing else str(uuid.uuid4())

            await db.execute(
                "DELETE FROM drafts WHERE draft_group_id = ?",
                (draft_group_id,),
            )

            tasks = [_call_haiku(user_content, mod) for _, mod in APPROACH_MODIFIERS]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            drafts = []
            for i, (approach_name, _) in enumerate(APPROACH_MODIFIERS):
                if isinstance(results[i], Exception):
                    draft_text = "(Erro ao gerar esta variação)"
                    justification = str(results[i])
                else:
                    draft_text, justification = results[i]

                cursor = await db.execute(
                    """INSERT INTO drafts
                       (conversation_id, trigger_message_id, draft_text, justification,
                        draft_group_id, variation_index, approach, prompt_hash, operator_instruction)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (conversation_id, trigger_message_id, draft_text, justification,
                     draft_group_id, i, approach_name, prompt_hash, operator_instruction),
                )
                drafts.append({
                    "id": cursor.lastrowid, "conversation_id": conversation_id,
                    "trigger_message_id": trigger_message_id,
                    "draft_text": draft_text, "justification": justification,
                    "status": "pending", "draft_group_id": draft_group_id,
                    "variation_index": i, "approach": approach_name,
                })

            await db.commit()

        from app.websocket_manager import manager
        await manager.broadcast(
            conversation_id,
            {
                "type": "drafts_ready",
                "conversation_id": conversation_id,
                "draft_group_id": draft_group_id,
                "drafts": drafts,
            },
        )

    except Exception:
        logger.exception("Failed to regenerate drafts for conversation %d", conversation_id)
    finally:
        await db.close()
