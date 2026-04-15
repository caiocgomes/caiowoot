"""Rotas do agente de reesquentamento D-1."""

import asyncio
import logging
import uuid

import aiosqlite
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from app.database import get_db_connection
from app.services.rewarm_engine import (
    decide_rewarm_action,
    run_batch,
    select_rewarm_candidates,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Track background tasks so tests can await them. In production this set grows and
# entries auto-remove when done; memory footprint is negligible.
_background_tasks: set[asyncio.Task] = set()


class ExecuteItem(BaseModel):
    conversation_id: int
    message: str


class ExecuteRequest(BaseModel):
    items: list[ExecuteItem]


@router.post("/rewarm/preview")
async def rewarm_preview(db: aiosqlite.Connection = Depends(get_db_connection)):
    """Roda query + agente para cada candidata. Nunca envia mensagem. Retorna lista de sugestões."""
    candidates = await select_rewarm_candidates(db)
    if not candidates:
        return []

    async def decide(cand):
        decision = await decide_rewarm_action(cand["id"], db=db)
        return {
            "item_id": uuid.uuid4().hex,
            "conversation_id": cand["id"],
            "phone_number": cand["phone_number"],
            "contact_name": cand["contact_name"],
            "funnel_stage": cand["funnel_stage"],
            "action": decision["action"],
            "message": decision["message"],
            "reason": decision["reason"],
        }

    results = await asyncio.gather(*(decide(c) for c in candidates))
    return list(results)


@router.post("/rewarm/execute", status_code=202)
async def rewarm_execute(req: ExecuteRequest):
    """Dispara envio em batch em background e retorna 202 imediatamente."""
    items = [{"conversation_id": it.conversation_id, "message": it.message} for it in req.items]
    task = asyncio.create_task(run_batch(items, sent_by="rewarm_reviewed"))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return Response(status_code=202)
