"""Prompt construction logic extracted from draft_engine.

Builds system prompts, conversation history, few-shot examples,
and approach modifiers for draft generation.
"""

import logging
from datetime import datetime
from pathlib import Path

from app.config import now_local
from app.services.knowledge import load_knowledge_base
from app.services.learned_rules import get_active_rules
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
Use a tool draft_response para retornar sua resposta."""


async def build_system_prompt(operator_name: str | None = None) -> str:
    from app.services.prompt_config import get_all_prompts
    from app.services.operator_profile import get_profile

    prompts = await get_all_prompts()

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


async def get_approach_modifiers() -> list[tuple[str, str]]:
    from app.services.prompt_config import get_all_prompts

    prompts = await get_all_prompts()
    return [
        ("direta", prompts["approach_direta"]),
        ("consultiva", prompts["approach_consultiva"]),
        ("casual", prompts["approach_casual"]),
    ]


def build_rules_section(rules: list[dict]) -> str:
    if not rules:
        return ""
    items = "\n".join(f"{i+1}. {r['rule_text']}" for i, r in enumerate(rules))
    return f"\n\n## Regras aprendidas\n{items}"


async def build_conversation_history(db, conversation_id: int, operator_name: str | None = None) -> tuple[str, str, str | None]:
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


async def build_fewshot_from_retrieval(db, edit_pair_ids: list[int]) -> str:
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


async def build_fewshot_fallback(db) -> str:
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


def build_temporal_context(last_inbound_iso: str | None) -> str:
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


async def build_prompt_parts(
    db,
    conversation_id: int,
    operator_instruction: str | None = None,
    situation_summary: str | None = None,
    proactive: bool = False,
    operator_name: str | None = None,
):
    conversation_history, first_name, last_inbound_iso = await build_conversation_history(db, conversation_id, operator_name)

    # Generate situation summary if not provided
    if situation_summary is None:
        try:
            summary_result = await generate_situation_summary(
                conversation_history, contact_name=first_name
            )
            situation_summary = summary_result["summary"]
            # Update conversation funnel if AI extracted product/stage
            funnel_product = summary_result.get("product")
            funnel_stage = summary_result.get("stage")
            if funnel_product or funnel_stage:
                updates = []
                params = []
                if funnel_product:
                    updates.append("funnel_product = ?")
                    params.append(funnel_product)
                if funnel_stage:
                    updates.append("funnel_stage = ?")
                    params.append(funnel_stage)
                params.append(conversation_id)
                await db.execute(
                    f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?",
                    params,
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
                few_shot_text = await build_fewshot_from_retrieval(db, similar_ids)
        except Exception:
            logger.exception("Smart retrieval failed, falling back to chronological")

    # Fallback to chronological if smart retrieval yielded nothing
    if not few_shot_text:
        few_shot_text = await build_fewshot_fallback(db)

    knowledge = load_knowledge_base()

    # Load learned rules
    rules = await get_active_rules()
    rules_section = build_rules_section(rules)

    # Build knowledge section for system prompt
    knowledge_section = f"\n\n## Base de conhecimento dos cursos\n\n{knowledge}"

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

    temporal_section = build_temporal_context(last_inbound_iso)

    display_name = operator_name or "Caio"
    if proactive:
        final_instruction = f"A última mensagem da conversa foi enviada pelo {display_name}. Gere uma mensagem de continuação natural, retomando o contexto da conversa."
    else:
        final_instruction = "Gere o draft de resposta para a última mensagem do cliente."

    user_content = f"""{few_shot_text}
{attachments_section}
{instruction_text}
{client_section}
{summary_section}
## Conversa atual

{conversation_history}
{temporal_section}

{final_instruction}"""

    return user_content, situation_summary, rules_section, knowledge_section
