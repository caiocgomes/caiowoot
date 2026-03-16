import logging
from datetime import datetime

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_db_connection
from app.services.situation_summary import generate_situation_summary
from app.websocket_manager import manager

logger = logging.getLogger(__name__)

VALID_FUNNEL_STAGES = {"qualifying", "decided", "handbook_sent", "link_sent", "purchased"}


class FunnelUpdate(BaseModel):
    funnel_product: str | None = None
    funnel_stage: str | None = None

router = APIRouter()


@router.get("/conversations")
async def list_conversations(db: aiosqlite.Connection = Depends(get_db_connection)):
    rows = await db.execute("""
        SELECT
            c.id, c.phone_number, c.contact_name, c.status,
            c.is_qualified, c.funnel_product, c.funnel_stage,
            c.created_at, c.updated_at,
            m.content as last_message,
            m.created_at as last_message_at,
            CASE WHEN EXISTS (
                SELECT 1 FROM messages m2
                WHERE m2.conversation_id = c.id AND m2.direction = 'inbound'
                AND m2.created_at > COALESCE(c.last_read_at, '1970-01-01')
            ) THEN 1 ELSE 0 END as is_new,
            CASE WHEN (
                SELECT m6.direction FROM messages m6
                WHERE m6.conversation_id = c.id
                ORDER BY m6.created_at DESC, m6.id DESC LIMIT 1
            ) = 'inbound' THEN 1 ELSE 0 END as needs_reply,
            (SELECT m5.sent_by FROM messages m5
             WHERE m5.conversation_id = c.id AND m5.direction = 'outbound' AND m5.sent_by IS NOT NULL
             ORDER BY m5.created_at DESC LIMIT 1
            ) as last_responder,
            CASE WHEN EXISTS (
                SELECT 1 FROM scheduled_sends ss
                WHERE ss.conversation_id = c.id AND ss.status = 'pending'
            ) THEN 1 ELSE 0 END as has_scheduled
        FROM conversations c
        LEFT JOIN messages m ON m.id = (
            SELECT m4.id FROM messages m4
            WHERE m4.conversation_id = c.id
            ORDER BY m4.created_at DESC LIMIT 1
        )
        WHERE c.status = 'active'
        ORDER BY COALESCE(m.created_at, c.created_at) DESC
    """)
    conversations = await rows.fetchall()
    return [dict(row) for row in conversations]


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: int, db: aiosqlite.Connection = Depends(get_db_connection)):
    # Mark as read
    await db.execute(
        "UPDATE conversations SET last_read_at = CURRENT_TIMESTAMP WHERE id = ?",
        (conversation_id,),
    )
    await db.commit()

    # Get conversation
    row = await db.execute(
        "SELECT * FROM conversations WHERE id = ?",
        (conversation_id,),
    )
    conv = await row.fetchone()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get messages
    rows = await db.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conversation_id,),
    )
    messages = [dict(m) for m in await rows.fetchall()]

    # Get pending drafts (full group)
    draft_row = await db.execute(
        "SELECT draft_group_id FROM drafts WHERE conversation_id = ? AND status = 'pending' ORDER BY created_at DESC LIMIT 1",
        (conversation_id,),
    )
    draft = await draft_row.fetchone()
    pending_drafts = []
    if draft and draft["draft_group_id"]:
        group_rows = await db.execute(
            "SELECT * FROM drafts WHERE draft_group_id = ? ORDER BY variation_index",
            (draft["draft_group_id"],),
        )
        pending_drafts = [dict(d) for d in await group_rows.fetchall()]
    elif draft:
        pending_drafts = [dict(draft)]

    # Get latest situation summary from drafts
    summary_row = await db.execute(
        "SELECT situation_summary FROM drafts WHERE conversation_id = ? AND situation_summary IS NOT NULL ORDER BY created_at DESC LIMIT 1",
        (conversation_id,),
    )
    summary = await summary_row.fetchone()
    latest_summary = summary["situation_summary"] if summary else None

    return {
        "conversation": dict(conv),
        "messages": messages,
        "pending_drafts": pending_drafts,
        "situation_summary": latest_summary,
    }


@router.patch("/conversations/{conversation_id}/funnel")
async def update_funnel(conversation_id: int, body: FunnelUpdate, db: aiosqlite.Connection = Depends(get_db_connection)):
    if body.funnel_stage and body.funnel_stage not in VALID_FUNNEL_STAGES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid funnel_stage. Valid values: {', '.join(sorted(VALID_FUNNEL_STAGES))}",
        )

    row = await db.execute("SELECT id FROM conversations WHERE id = ?", (conversation_id,))
    if not await row.fetchone():
        raise HTTPException(status_code=404, detail="Conversation not found")

    updates = []
    params = []
    if body.funnel_product is not None:
        updates.append("funnel_product = ?")
        params.append(body.funnel_product)
    if body.funnel_stage is not None:
        updates.append("funnel_stage = ?")
        params.append(body.funnel_stage)

    if updates:
        params.append(conversation_id)
        await db.execute(
            f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        await db.commit()

    return {"status": "ok"}


@router.post("/conversations/{conversation_id}/classify")
async def classify_conversation(conversation_id: int, db: aiosqlite.Connection = Depends(get_db_connection)):
    """Run AI classification on an existing conversation to populate funnel data."""
    try:
        row = await db.execute(
            "SELECT id, contact_name FROM conversations WHERE id = ?",
            (conversation_id,),
        )
        conv = await row.fetchone()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Build conversation history
        rows = await db.execute(
            "SELECT direction, content, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
        )
        messages = await rows.fetchall()
        if not messages:
            return {"summary": None, "product": None, "stage": None}

        contact_name = conv["contact_name"] or ""
        first_name = contact_name.split()[0] if contact_name.strip() else ""

        history_lines = []
        for msg in messages:
            prefix = "Cliente" if msg["direction"] == "inbound" else "Operador"
            history_lines.append(f"{prefix}: {msg['content']}")
        conversation_history = "\n".join(history_lines)

        result = await generate_situation_summary(
            conversation_history, contact_name=first_name
        )

        # Update funnel fields
        updates = []
        params = []
        if result.get("product"):
            updates.append("funnel_product = ?")
            params.append(result["product"])
        if result.get("stage"):
            updates.append("funnel_stage = ?")
            params.append(result["stage"])
        if updates:
            params.append(conversation_id)
            await db.execute(
                f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?",
                params,
            )

        # Persist summary so GET /conversations/{id} can find it
        if result.get("summary"):
            last_msg = await db.execute(
                "SELECT id FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT 1",
                (conversation_id,),
            )
            last = await last_msg.fetchone()
            if last:
                await db.execute(
                    """INSERT INTO drafts (conversation_id, trigger_message_id, draft_text, situation_summary, variation_index, approach)
                       VALUES (?, ?, '', ?, 0, 'classify')""",
                    (conversation_id, last["id"], result["summary"]),
                )

        await db.commit()

        return {
            "summary": result["summary"],
            "product": result.get("product"),
            "stage": result.get("stage"),
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to classify conversation %d", conversation_id)
        raise HTTPException(status_code=500, detail="Classification failed")


@router.post("/conversations/{conversation_id}/assume")
async def assume_conversation(conversation_id: int, db: aiosqlite.Connection = Depends(get_db_connection)):
    """Operator assumes control of a conversation, ending auto-qualification."""
    row = await db.execute("SELECT id, is_qualified FROM conversations WHERE id = ?", (conversation_id,))
    conv = await row.fetchone()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv["is_qualified"]:
        return {"status": "ok", "already_qualified": True}

    await db.execute("UPDATE conversations SET is_qualified = 1 WHERE id = ?", (conversation_id,))
    await db.commit()

    await manager.broadcast(conversation_id, {
        "type": "conversation_assumed",
        "conversation_id": conversation_id,
    })

    return {"status": "ok"}
