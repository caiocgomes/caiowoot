import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

import anthropic

from app.config import now_local, settings
from app.database import get_db
from app.services.knowledge import load_knowledge_base
from app.services.learned_rules import get_active_rules
from app.services.prompt_logger import save_prompt
from app.services.situation_summary import generate_situation_summary
from app.services.smart_retrieval import retrieve_similar

logger = logging.getLogger(__name__)

ATTACHMENTS_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge" / "attachments"


def list_known_attachments() -> list[str]:
    if not ATTACHMENTS_DIR.exists():
        return []
    return sorted(f.name for f in ATTACHMENTS_DIR.iterdir() if f.is_file())


# --- Fixed infrastructure sections (not editable via UI) ---

WHATSAPP_FORMAT_SECTION = """## Formatação WhatsApp
A mensagem será enviada via WhatsApp. Use apenas formatação compatível:
- *negrito* (asteriscos), _itálico_ (underscores), ~tachado~ (til)
- Não use markdown, HTML, links clicáveis formatados ou cabeçalhos
- Quebre linhas para facilitar leitura, mas sem parágrafos longos
- Listas simples com - ou • quando necessário, sem aninhamento"""

TEMPORAL_CONTEXT_SECTION = """## Contexto temporal
O prompt inclui timestamps nas mensagens recentes e o horário atual. Use isso para:
- Se a última mensagem do cliente foi há mais de 1-2 horas, reconheça o atraso de forma natural (sem ser servil). Exemplo: "Desculpa a demora" ou "Voltando aqui"
- Ajuste o cumprimento ao horário: "Bom dia" / "Boa tarde" / "Boa noite"
- Se houve um gap grande na conversa, retome o contexto brevemente antes de continuar
- Não mencione o atraso se foi menos de ~1 hora, isso é normal em WhatsApp"""

ATTACHMENT_SECTION = """## Anexos
Quando a seção "Anexos disponíveis" estiver presente no prompt, você pode sugerir o envio de um arquivo junto com a mensagem. Sugira anexo quando o contexto indicar que o cliente está avançando na decisão de compra, pediu detalhes do programa, ou quando os exemplos anteriores mostram que o operador costuma enviar o arquivo nessa situação. Não sugira anexo se a conversa ainda está na fase de qualificação inicial."""

RESPONSE_FORMAT_SECTION = """## Formato de resposta
Responda SEMPRE em JSON com exatamente estes campos:
{
  "draft": "texto da mensagem proposta para o cliente",
  "justification": "1-2 frases explicando por que você escolheu essa abordagem (isso NÃO vai pro cliente, é só pro operador)",
  "suggested_attachment": "nome-do-arquivo.pdf ou null se não houver sugestão"
}"""

# Keep legacy constant for backward compatibility with tests that reference it
SYSTEM_PROMPT = None  # Now built dynamically via _build_system_prompt()

APPROACH_MODIFIERS = None  # Now built dynamically via _get_approach_modifiers()


async def _build_system_prompt(operator_name: str | None = None) -> str:
    from app.services.prompt_config import get_all_prompts, PROMPT_DEFAULTS
    from app.services.operator_profile import get_profile

    prompts = await get_all_prompts()

    # Determine operator display name
    display_name = operator_name or "Caio"
    profile_section = ""

    if operator_name:
        profile = await get_profile(operator_name)
        if profile:
            if profile["display_name"]:
                display_name = profile["display_name"]
            if profile["context"]:
                profile_section = f"\n\n## Sobre quem está respondendo\n{profile['context']}"

    opening = f"Você é o {display_name} respondendo mensagens de clientes no WhatsApp sobre cursos de IA."

    system = f"""{opening}
{profile_section}

## Postura
{prompts['postura']}

## Tom
{prompts['tom']}

## Regras
{prompts['regras']}

{WHATSAPP_FORMAT_SECTION}

{TEMPORAL_CONTEXT_SECTION}

{ATTACHMENT_SECTION}

{RESPONSE_FORMAT_SECTION}"""

    return system


async def _get_approach_modifiers() -> list[tuple[str, str]]:
    from app.services.prompt_config import get_all_prompts

    prompts = await get_all_prompts()
    return [
        ("direta", prompts["approach_direta"]),
        ("consultiva", prompts["approach_consultiva"]),
        ("casual", prompts["approach_casual"]),
    ]


def _parse_response(response_text: str) -> tuple[str, str, str | None]:
    text = response_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(text)
        suggested = parsed.get("suggested_attachment") or None
        return parsed.get("draft", text), parsed.get("justification", ""), suggested
    except json.JSONDecodeError:
        return text, "Resposta não veio em JSON, usando texto direto", None


def _build_rules_section(rules: list[dict]) -> str:
    if not rules:
        return ""
    items = "\n".join(f"{i+1}. {r['rule_text']}" for i, r in enumerate(rules))
    return f"\n\n## Regras aprendidas\n{items}"


async def _build_conversation_history(db, conversation_id: int, operator_name: str | None = None) -> tuple[str, str, str | None]:
    row = await db.execute(
        "SELECT contact_name FROM conversations WHERE id = ?",
        (conversation_id,),
    )
    conv = await row.fetchone()
    contact_name = (conv["contact_name"] or "") if conv else ""
    first_name = contact_name.split()[0] if contact_name.strip() else ""

    display_name = operator_name or "Caio"

    rows = await db.execute(
        "SELECT direction, content, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conversation_id,),
    )
    messages = await rows.fetchall()

    now = now_local()
    tz = now.tzinfo
    today = now.date()
    total = len(messages)
    timestamp_start = max(0, total - 10)

    history_lines = []
    last_inbound_time = None
    for i, msg in enumerate(messages):
        prefix = "Cliente" if msg["direction"] == "inbound" else display_name
        msg_time = datetime.fromisoformat(msg["created_at"])
        if msg_time.tzinfo is None:
            from datetime import timezone as _tz
            msg_time = msg_time.replace(tzinfo=_tz.utc).astimezone(tz)
        else:
            msg_time = msg_time.astimezone(tz)

        if msg["direction"] == "inbound":
            last_inbound_time = msg_time

        if i >= timestamp_start:
            if msg_time.date() == today:
                ts = f"[{msg_time.strftime('%H:%M')}] "
            else:
                ts = f"[{msg_time.strftime('%d/%m %H:%M')}] "
        else:
            ts = ""

        history_lines.append(f"{ts}{prefix}: {msg['content']}")
    conversation_history = "\n".join(history_lines)

    last_inbound_iso = last_inbound_time.isoformat() if last_inbound_time else None

    return conversation_history, first_name, last_inbound_iso


async def _build_fewshot_from_retrieval(db, edit_pair_ids: list[int]) -> str:
    if not edit_pair_ids:
        return ""

    placeholders = ",".join("?" * len(edit_pair_ids))
    rows = await db.execute(
        f"SELECT situation_summary, customer_message, original_draft, final_message, strategic_annotation, attachment_filename FROM edit_pairs WHERE id IN ({placeholders})",
        edit_pair_ids,
    )
    pairs = await rows.fetchall()

    if not pairs:
        return ""

    examples = []
    for pair in pairs:
        example = f"Situação: \"{pair['situation_summary'] or 'N/A'}\"\n"
        example += f"Cliente disse: \"{pair['customer_message']}\"\n"
        example += f"IA propôs: \"{pair['original_draft']}\"\n"
        example += f"Caio enviou: \"{pair['final_message']}\""
        if pair["strategic_annotation"]:
            example += f"\nPor quê: {pair['strategic_annotation']}"
        if pair["attachment_filename"]:
            example += f"\nAnexo enviado: {pair['attachment_filename']}"
        examples.append(example)

    return (
        "\n\n## Exemplos de como o Caio responde (aprenda com o tom e as correções estratégicas)\n\n"
        + "\n\n---\n\n".join(examples)
    )


async def _build_fewshot_fallback(db) -> str:
    rows = await db.execute(
        "SELECT customer_message, original_draft, final_message, attachment_filename FROM edit_pairs ORDER BY created_at DESC LIMIT 10",
    )
    edit_pairs = await rows.fetchall()

    if not edit_pairs:
        return ""

    examples = []
    for pair in reversed(list(edit_pairs)):
        example = (
            f"Cliente disse: \"{pair['customer_message']}\"\n"
            f"IA propôs: \"{pair['original_draft']}\"\n"
            f"Caio enviou: \"{pair['final_message']}\""
        )
        if pair["attachment_filename"]:
            example += f"\nAnexo enviado: {pair['attachment_filename']}"
        examples.append(example)
    return (
        "\n\n## Exemplos de como o Caio responde (aprenda com o tom e as correções)\n\n"
        + "\n\n---\n\n".join(examples)
    )


async def _build_prompt_parts(
    db,
    conversation_id: int,
    operator_instruction: str | None = None,
    situation_summary: str | None = None,
    proactive: bool = False,
    operator_name: str | None = None,
):
    conversation_history, first_name, last_inbound_iso = await _build_conversation_history(db, conversation_id, operator_name)

    # Generate situation summary if not provided
    if situation_summary is None:
        try:
            situation_summary = await generate_situation_summary(
                conversation_history, contact_name=first_name
            )
        except Exception:
            logger.exception("Failed to generate situation summary")
            situation_summary = None

    # Smart retrieval based on situation summary
    few_shot_text = ""
    if situation_summary:
        try:
            similar_ids = retrieve_similar(situation_summary, k=5)
            if similar_ids:
                few_shot_text = await _build_fewshot_from_retrieval(db, similar_ids)
        except Exception:
            logger.exception("Smart retrieval failed, falling back to chronological")

    # Fallback to chronological if smart retrieval yielded nothing
    if not few_shot_text:
        few_shot_text = await _build_fewshot_fallback(db)

    knowledge = load_knowledge_base()

    # Load learned rules
    rules = await get_active_rules()
    rules_section = _build_rules_section(rules)

    # List known attachments
    attachments = list_known_attachments()
    attachments_section = ""
    if attachments:
        items = "\n".join(f"- {name}" for name in attachments)
        attachments_section = f"\n\n## Anexos disponíveis\n{items}"

    instruction_text = ""
    if operator_instruction:
        instruction_text = f"\n\n## Instrução do operador\n{operator_instruction}"

    summary_section = ""
    if situation_summary:
        summary_section = f"\n\n## Situação atual\n{situation_summary}"

    client_section = f"\n\n## Cliente\nNome: {first_name}\n" if first_name else ""

    temporal_section = _build_temporal_context(last_inbound_iso)

    display_name = operator_name or "Caio"
    if proactive:
        final_instruction = f"A última mensagem da conversa foi enviada pelo {display_name}. Gere uma mensagem de continuação natural, retomando o contexto da conversa."
    else:
        final_instruction = "Gere o draft de resposta para a última mensagem do cliente."

    user_content = f"""## Base de conhecimento dos cursos

{knowledge}

{few_shot_text}
{attachments_section}
{instruction_text}
{client_section}
{summary_section}
## Conversa atual

{conversation_history}
{temporal_section}

{final_instruction}"""

    return user_content, situation_summary, rules_section


def _build_temporal_context(last_inbound_iso: str | None) -> str:
    now = now_local()
    now_str = now.strftime("%H:%M (%d/%m)")

    if not last_inbound_iso:
        return f"\n\n## Contexto temporal\nAgora são {now_str}."

    last_inbound = datetime.fromisoformat(last_inbound_iso)
    if last_inbound.tzinfo is None:
        from datetime import timezone as _tz
        last_inbound = last_inbound.replace(tzinfo=_tz.utc).astimezone(now.tzinfo)
    delta = now - last_inbound
    total_minutes = int(delta.total_seconds() / 60)

    if total_minutes < 1:
        elapsed = "agora mesmo"
    elif total_minutes < 60:
        elapsed = f"há {total_minutes}min"
    else:
        hours = total_minutes // 60
        minutes = total_minutes % 60
        if minutes > 0:
            elapsed = f"há {hours}h {minutes}min"
        else:
            elapsed = f"há {hours}h"

    return f"\n\n## Contexto temporal\nAgora são {now_str}. Última mensagem do cliente foi {elapsed}."


def _validate_suggested_attachment(suggested: str | None) -> str | None:
    if not suggested:
        return None
    file_path = ATTACHMENTS_DIR / suggested
    if file_path.exists() and file_path.is_file():
        return suggested
    return None


async def _call_haiku(user_content: str, approach_modifier: str, system_prompt: str, rules_section: str = "") -> tuple[str, str, str | None]:
    system = system_prompt + rules_section + f"\n\n## Estilo desta variação\n{approach_modifier}"
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=settings.claude_haiku_model,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )
    draft_text, justification, suggested = _parse_response(response.content[0].text)
    suggested = _validate_suggested_attachment(suggested)
    return draft_text, justification, suggested


async def generate_drafts(
    conversation_id: int,
    trigger_message_id: int,
    operator_instruction: str | None = None,
    proactive: bool = False,
    operator_name: str | None = None,
):
    db = await get_db()
    try:
        system_prompt = await _build_system_prompt(operator_name)
        approach_modifiers = await _get_approach_modifiers()

        user_content, situation_summary, rules_section = await _build_prompt_parts(
            db, conversation_id, operator_instruction, proactive=proactive, operator_name=operator_name
        )

        full_prompt = system_prompt + rules_section + "\n\n" + user_content
        prompt_hash = save_prompt(full_prompt)

        draft_group_id = str(uuid.uuid4())

        tasks = [
            _call_haiku(user_content, modifier, system_prompt, rules_section)
            for _, modifier in approach_modifiers
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        drafts = []
        for i, (approach_name, _) in enumerate(approach_modifiers):
            if isinstance(results[i], Exception):
                logger.error("Draft variation %d failed: %s", i, results[i])
                draft_text = "(Erro ao gerar esta variação)"
                justification = str(results[i])
                suggested_attachment = None
            else:
                draft_text, justification, suggested_attachment = results[i]

            cursor = await db.execute(
                """INSERT INTO drafts
                   (conversation_id, trigger_message_id, draft_text, justification,
                    draft_group_id, variation_index, approach, prompt_hash, operator_instruction,
                    situation_summary)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (conversation_id, trigger_message_id, draft_text, justification,
                 draft_group_id, i, approach_name, prompt_hash, operator_instruction,
                 situation_summary),
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
                "suggested_attachment": suggested_attachment,
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
    proactive: bool = False,
    operator_name: str | None = None,
):
    db = await get_db()
    try:
        system_prompt = await _build_system_prompt(operator_name)
        approach_modifiers = await _get_approach_modifiers()

        user_content, situation_summary, rules_section = await _build_prompt_parts(
            db, conversation_id, operator_instruction, proactive=proactive, operator_name=operator_name
        )
        full_prompt = system_prompt + rules_section + "\n\n" + user_content
        prompt_hash = save_prompt(full_prompt)

        if draft_index is not None:
            approach_name, modifier = approach_modifiers[draft_index]
            draft_text, justification, suggested_attachment = await _call_haiku(user_content, modifier, system_prompt, rules_section)

            row = await db.execute(
                """SELECT id, draft_group_id FROM drafts
                   WHERE conversation_id = ? AND trigger_message_id = ? AND variation_index = ? AND status = 'pending'
                   ORDER BY created_at DESC LIMIT 1""",
                (conversation_id, trigger_message_id, draft_index),
            )
            existing = await row.fetchone()
            if existing:
                await db.execute(
                    """UPDATE drafts SET draft_text = ?, justification = ?, prompt_hash = ?, operator_instruction = ?, situation_summary = ?
                       WHERE id = ?""",
                    (draft_text, justification, prompt_hash, operator_instruction, situation_summary, existing["id"]),
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
                "suggested_attachment": suggested_attachment if d["variation_index"] == draft_index else None,
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

            tasks = [_call_haiku(user_content, mod, system_prompt, rules_section) for _, mod in approach_modifiers]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            drafts = []
            for i, (approach_name, _) in enumerate(approach_modifiers):
                if isinstance(results[i], Exception):
                    draft_text = "(Erro ao gerar esta variação)"
                    justification = str(results[i])
                    suggested_attachment = None
                else:
                    draft_text, justification, suggested_attachment = results[i]

                cursor = await db.execute(
                    """INSERT INTO drafts
                       (conversation_id, trigger_message_id, draft_text, justification,
                        draft_group_id, variation_index, approach, prompt_hash, operator_instruction,
                        situation_summary)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (conversation_id, trigger_message_id, draft_text, justification,
                     draft_group_id, i, approach_name, prompt_hash, operator_instruction,
                     situation_summary),
                )
                drafts.append({
                    "id": cursor.lastrowid, "conversation_id": conversation_id,
                    "trigger_message_id": trigger_message_id,
                    "draft_text": draft_text, "justification": justification,
                    "status": "pending", "draft_group_id": draft_group_id,
                    "variation_index": i, "approach": approach_name,
                    "suggested_attachment": suggested_attachment,
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
