"""Rotas do cold rewarm: preview (modal) e execute (dispara batch)."""

import asyncio
import logging

import aiosqlite
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from app.database import get_db_connection
from app.services.cold_triage import execute_batch, run_preview

logger = logging.getLogger(__name__)
router = APIRouter()

_background_tasks: set[asyncio.Task] = set()


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

    task = asyncio.create_task(execute_batch(items))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return Response(status_code=202)
