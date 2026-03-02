from fastapi import APIRouter, HTTPException

from app.database import get_db

router = APIRouter()


@router.get("/conversations")
async def list_conversations():
    db = await get_db()
    try:
        rows = await db.execute("""
            SELECT
                c.id, c.phone_number, c.contact_name, c.status, c.created_at, c.updated_at,
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
                ) as last_responder
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
    finally:
        await db.close()


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: int):
    db = await get_db()
    try:
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

        return {
            "conversation": dict(conv),
            "messages": messages,
            "pending_drafts": pending_drafts,
        }
    finally:
        await db.close()
