"""Rotas do cold rewarm: preview (modal) e execute (dispara batch)."""

import logging

import aiosqlite
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from app.database import get_db_connection
from app.services.cold_triage import execute_batch, run_preview
from app.task_registry import spawn

logger = logging.getLogger(__name__)
router = APIRouter()


class ExecuteItem(BaseModel):
    dispatch_id: int
    conversation_id: int
    message: str


class ExecuteRequest(BaseModel):
    items: list[ExecuteItem]


@router.post("/cold-rewarm/preview")
async def cold_rewarm_preview(db: aiosqlite.Connection = Depends(get_db_connection)):
    """Gera até 20 sugestões classificadas e compostas. Grava status='previewed'."""
    items = await run_preview(db=db)
    return items


@router.post("/cold-rewarm/execute", status_code=202)
async def cold_rewarm_execute(req: ExecuteRequest):
    """Agenda envio em batch com rate limit. Retorna 202 imediatamente."""
    items = [
        {
            "dispatch_id": it.dispatch_id,
            "conversation_id": it.conversation_id,
            "message": it.message,
        }
        for it in req.items
    ]
    if not items:
        return Response(status_code=202)

    spawn(execute_batch(items))
    return Response(status_code=202)
