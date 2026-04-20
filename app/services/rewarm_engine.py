"""Agente de reesquentamento D-1 para leads do curso CDO.

Identifica conversas em que o lead recebeu handbook ou link em D-1 mas ainda não comprou,
pede ao Haiku uma mensagem de reesquentamento personalizada (ou skip se fizer mais mal que bem),
e orquestra envio em batch com rate limit anti-spam.
"""

import asyncio
import json
import logging
import random
from datetime import timedelta
from typing import Any

from app.config import now_local, settings
from app.database import get_db
from app.services.claude_client import get_anthropic_client
from app.services.message_sender import send_and_record

logger = logging.getLogger(__name__)

REWARM_STAGES = ("handbook_sent", "link_sent")
REWARM_PRODUCT = "curso-cdo"  # valor canônico — veja situation_summary.py e UI (index.html)
REWARM_TOOL_NAME = "rewarm_decision"

REWARM_TOOL = {
    "name": REWARM_TOOL_NAME,
    "description": "Decide se deve reesquentar essa conversa e, se sim, qual mensagem enviar.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["send", "skip"],
                "description": "send = enviar mensagem de reesquentamento; skip = não enviar nada.",
            },
            "message": {
                "type": "string",
                "description": "Texto da mensagem de reesquentamento quando action='send'. String vazia quando action='skip'.",
            },
            "reason": {
                "type": "string",
                "description": "Justificativa em 1-2 frases (por que enviar ou por que pular).",
            },
        },
        "required": ["action", "message", "reason"],
    },
}


REWARM_SYSTEM_PROMPT = """Você é um agente de reesquentamento de leads do curso CDO (Chief Data Officer) do Caio Gomes.

Sua tarefa: ler uma conversa entre o operador e o lead que recebeu handbook ou link de pagamento em D-1 mas não fechou, e decidir entre:

- **send**: criar UMA mensagem curta e natural para reanimar a conversa. A mensagem deve:
  - Espelhar o tom natural da conversa (formal/informal, uso de emoji, extensão média das mensagens do operador). NÃO use tom genérico.
  - Ter uma entrada específica baseada no que você inferir do histórico (dúvida não respondida? objeção implícita? silêncio?).
  - Ser escrita em português brasileiro correto, com acentuação.
  - Não ser invasiva nem pressionar. Abrir espaço para a pessoa responder.

- **skip**: pular quando o histórico sugere que mandar vai fazer mais mal que bem:
  - Lead explicitamente disse que não quer mais (variações: "não tenho interesse", "pode parar", "me tira daí").
  - Lead indicou que comprou em outro lugar ou já resolveu.
  - Houve hostilidade real no atendimento.
  - Já teve reesquentamento recente na própria conversa sem resposta.
  - Conversa avançou hoje (há mensagens de hoje) — sinal de engajamento ativo em outro fluxo.

Retorne SEMPRE via a tool `rewarm_decision` com action, message e reason. Em skip, message pode ser string vazia."""


def default_reference_date() -> str:
    """Default simples: ontem local."""
    return (now_local().date() - timedelta(days=1)).isoformat()


async def select_rewarm_candidates(
    db,
    reference_date: str | None = None,
) -> list[dict[str, Any]]:
    """Seleciona conversas candidatas a reesquentamento para uma data de referência.

    Critério: funnel_product=CDO, funnel_stage em (handbook_sent, link_sent),
    última mensagem da conversa tem DATE() = reference_date. Se `reference_date`
    é None, usa ontem local como default (comportamento histórico do D-1).
    """
    ref = reference_date or default_reference_date()
    cursor = await db.execute(
        """
        SELECT c.id, c.phone_number, c.contact_name, c.funnel_product, c.funnel_stage
        FROM conversations c
        WHERE c.funnel_product = ?
          AND c.funnel_stage IN (?, ?)
          AND (
              SELECT DATE(MAX(created_at))
              FROM messages m
              WHERE m.conversation_id = c.id
          ) = ?
        ORDER BY c.id
        """,
        (REWARM_PRODUCT, *REWARM_STAGES, ref),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def _load_conversation_history(db, conversation_id: int) -> list[dict[str, str]]:
    cursor = await db.execute(
        """SELECT direction, content, sent_by, created_at
           FROM messages WHERE conversation_id = ? ORDER BY created_at ASC, id ASC""",
        (conversation_id,),
    )
    rows = await cursor.fetchall()
    return [
        {
            "direction": r["direction"],
            "content": r["content"],
            "sent_by": r["sent_by"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def _format_history_for_prompt(history: list[dict[str, str]]) -> str:
    lines = []
    for m in history:
        tag = "cliente" if m["direction"] == "inbound" else f"operador ({m['sent_by'] or 'equipe'})"
        lines.append(f"[{m['created_at']}] {tag}: {m['content']}")
    return "\n".join(lines) if lines else "(conversa vazia)"


def _extract_rewarm_decision(response) -> dict[str, Any]:
    """Lê o bloco tool_use do response e devolve dict normalizado."""
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == REWARM_TOOL_NAME:
            inp = block.input or {}
            action = inp.get("action", "skip")
            message = (inp.get("message") or "").strip()
            reason = (inp.get("reason") or "").strip()
            if action == "send" and not message:
                # Defensive: agent said send but gave empty message → treat as skip
                return {"action": "skip", "message": "", "reason": reason or "agente retornou send sem mensagem"}
            return {"action": action, "message": message if action == "send" else "", "reason": reason}
    return {"action": "skip", "message": "", "reason": "sem tool_use na resposta"}


async def decide_rewarm_action(conversation_id: int, db=None) -> dict[str, Any]:
    """Pede ao Haiku a decisão de reesquentamento para uma conversa específica.

    Retorna {action, message, reason}.
    """
    if db is None:
        db = await get_db()
        owns_db = True
    else:
        owns_db = False

    try:
        conv_cursor = await db.execute(
            "SELECT id, phone_number, contact_name, funnel_product, funnel_stage FROM conversations WHERE id = ?",
            (conversation_id,),
        )
        conv = await conv_cursor.fetchone()
        if not conv:
            return {"action": "skip", "message": "", "reason": "conversa não encontrada"}

        history = await _load_conversation_history(db, conversation_id)
        history_text = _format_history_for_prompt(history)

        contact_name = conv["contact_name"] or "(sem nome)"
        stage = conv["funnel_stage"]

        user_content = (
            f"Lead: {contact_name}\n"
            f"Estágio atual do funil: {stage}\n"
            f"Produto: {conv['funnel_product']}\n\n"
            f"## Histórico da conversa\n{history_text}\n\n"
            f"Decida: reesquentar esse lead agora? Se sim, qual mensagem exata enviar?"
        )

        client = get_anthropic_client()
        response = await client.messages.create(
            model=settings.claude_haiku_model,
            max_tokens=1024,
            system=REWARM_SYSTEM_PROMPT,
            tools=[REWARM_TOOL],
            tool_choice={"type": "tool", "name": REWARM_TOOL_NAME},
            messages=[{"role": "user", "content": user_content}],
        )
        decision = _extract_rewarm_decision(response)
        logger.info(
            "rewarm decision conv=%s action=%s reason=%s",
            conversation_id, decision["action"], decision["reason"][:80],
        )
        return decision
    finally:
        if owns_db:
            await db.close()


def next_delay() -> float:
    """Intervalo entre envios em massa: 60s + uniform(-20, +40) → janela 40–100s."""
    return 60.0 + random.uniform(-20.0, 40.0)


async def run_batch(items: list[dict[str, Any]], sent_by: str) -> None:
    """Envia uma lista de itens {conversation_id, message} em sequência com rate limit.

    Cada item falho é logado e ignorado — o batch continua.
    """
    for idx, item in enumerate(items):
        if idx > 0:
            await asyncio.sleep(next_delay())
        conv_id = item["conversation_id"]
        message = item["message"]
        try:
            db = await get_db()
            try:
                await send_and_record(db, conv_id, message, operator=sent_by)
            finally:
                await db.close()
        except Exception as exc:  # noqa: BLE001
            logger.error("rewarm batch send failed conv=%s: %s", conv_id, exc)


async def run_rewarm_auto() -> dict[str, Any]:
    """Pipeline completo automático: select + decide + envia tudo que for 'send'.

    Respeita a flag `settings.rewarm_auto_send`. Se desligada, no-op.
    Envios saem marcados com sent_by='rewarm_agent'.
    """
    if not settings.rewarm_auto_send:
        logger.info("rewarm auto-send desligado; no-op")
        return {"sent": 0, "skipped": 0, "reason": "flag off"}

    db = await get_db()
    try:
        candidates = await select_rewarm_candidates(db)
    finally:
        await db.close()

    items_to_send: list[dict[str, Any]] = []
    skipped = 0
    for cand in candidates:
        decision = await decide_rewarm_action(cand["id"])
        if decision["action"] == "send":
            items_to_send.append({"conversation_id": cand["id"], "message": decision["message"]})
        else:
            skipped += 1
            logger.info("rewarm auto skip conv=%s reason=%s", cand["id"], decision["reason"])

    await run_batch(items_to_send, sent_by="rewarm_agent")
    return {"sent": len(items_to_send), "skipped": skipped}
