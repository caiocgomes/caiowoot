import logging
from datetime import datetime

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from starlette.requests import Request

from app.auth import get_operator_from_request
from app.database import get_db_connection
from app.websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter()


class ScheduleRequest(BaseModel):
    content: str
    send_at: str  # ISO 8601 timestamp
    draft_id: int | None = None
    draft_group_id: str | None = None
    selected_draft_index: int | None = None


@router.post("/conversations/{conversation_id}/schedule")
async def schedule_send(conversation_id: int, req: ScheduleRequest, request: Request, db: aiosqlite.Connection = Depends(get_db_connection)):
    operator = get_operator_from_request(request)
    row = await db.execute(
        "SELECT id FROM conversations WHERE id = ?",
        (conversation_id,),
    )
    if not await row.fetchone():
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Validate send_at is in the future
    try:
        send_at = datetime.fromisoformat(req.send_at)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid send_at format")

    cursor = await db.execute(
        """INSERT INTO scheduled_sends
           (conversation_id, content, send_at, draft_id, draft_group_id, selected_draft_index, created_by)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (conversation_id, req.content, req.send_at, req.draft_id,
         req.draft_group_id, req.selected_draft_index, operator),
    )
    scheduled_id = cursor.lastrowid
    await db.commit()

    scheduled_send = {
        "id": scheduled_id,
        "conversation_id": conversation_id,
        "content": req.content,
        "send_at": req.send_at,
        "status": "pending",
        "draft_id": req.draft_id,
        "draft_group_id": req.draft_group_id,
        "selected_draft_index": req.selected_draft_index,
        "created_by": operator,
    }

    await manager.broadcast(
        conversation_id,
        {
            "type": "scheduled_send_created",
            "conversation_id": conversation_id,
            "scheduled_send": scheduled_send,
        },
    )

    return {"status": "ok", "scheduled_send": scheduled_send}


@router.get("/conversations/{conversation_id}/scheduled")
async def list_scheduled(conversation_id: int, db: aiosqlite.Connection = Depends(get_db_connection)):
    row = await db.execute(
        "SELECT id FROM conversations WHERE id = ?",
        (conversation_id,),
    )
    if not await row.fetchone():
        raise HTTPException(status_code=404, detail="Conversation not found")

    rows = await db.execute(
        """SELECT id, conversation_id, content, send_at, status, draft_id,
                  draft_group_id, selected_draft_index, created_by, created_at
           FROM scheduled_sends
           WHERE conversation_id = ? AND status = 'pending'
           ORDER BY send_at""",
        (conversation_id,),
    )
    sends = await rows.fetchall()
    return [dict(s) for s in sends]


@router.delete("/scheduled-sends/{scheduled_id}")
async def cancel_scheduled(scheduled_id: int, db: aiosqlite.Connection = Depends(get_db_connection)):
    # Atomically cancel only if still pending
    await db.execute(
        """UPDATE scheduled_sends
           SET status = 'cancelled', cancelled_reason = 'operator_cancelled'
           WHERE id = ? AND status = 'pending'""",
        (scheduled_id,),
    )
    changes = db.total_changes  # Check if row was actually updated

    # Fetch the record to get conversation_id for broadcast
    row = await db.execute(
        "SELECT id, conversation_id, content, send_at, status FROM scheduled_sends WHERE id = ?",
        (scheduled_id,),
    )
    record = await row.fetchone()
    if not record:
        raise HTTPException(status_code=404, detail="Scheduled send not found")

    if record["status"] != "cancelled":
        raise HTTPException(status_code=409, detail="Scheduled send already sent or already cancelled")

    await db.commit()

    await manager.broadcast(
        record["conversation_id"],
        {
            "type": "scheduled_send_cancelled",
            "conversation_id": record["conversation_id"],
            "scheduled_send_id": scheduled_id,
            "reason": "operator_cancelled",
        },
    )

    return {"status": "ok"}
