import logging

from fastapi import APIRouter, HTTPException

from app.database import get_db
from app.models import SendRequest
from app.services.evolution import send_text_message
from app.websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/conversations/{conversation_id}/send")
async def send_message(conversation_id: int, req: SendRequest):
    db = await get_db()
    try:
        # Get conversation
        row = await db.execute(
            "SELECT phone_number FROM conversations WHERE id = ?",
            (conversation_id,),
        )
        conv = await row.fetchone()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Send via Evolution API
        try:
            await send_text_message(conv["phone_number"], req.text)
        except Exception as e:
            logger.exception("Failed to send message via Evolution API")
            raise HTTPException(status_code=502, detail=f"Evolution API error: {e}")

        # Persist outbound message
        cursor = await db.execute(
            "INSERT INTO messages (conversation_id, direction, content) VALUES (?, 'outbound', ?)",
            (conversation_id, req.text),
        )
        msg_id = cursor.lastrowid

        # Update conversation timestamp
        await db.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )

        # Record edit pair if draft was used
        if req.draft_id:
            draft_row = await db.execute(
                "SELECT draft_text, trigger_message_id FROM drafts WHERE id = ? AND conversation_id = ?",
                (req.draft_id, conversation_id),
            )
            draft = await draft_row.fetchone()
            if draft:
                # Get the customer message that triggered the draft
                trigger_row = await db.execute(
                    "SELECT content FROM messages WHERE id = ?",
                    (draft["trigger_message_id"],),
                )
                trigger_msg = await trigger_row.fetchone()
                customer_message = trigger_msg["content"] if trigger_msg else ""

                was_edited = draft["draft_text"] != req.text

                await db.execute(
                    "INSERT INTO edit_pairs (conversation_id, customer_message, original_draft, final_message, was_edited) VALUES (?, ?, ?, ?, ?)",
                    (conversation_id, customer_message, draft["draft_text"], req.text, was_edited),
                )

                # Mark draft as sent
                await db.execute(
                    "UPDATE drafts SET status = 'sent' WHERE id = ?",
                    (req.draft_id,),
                )

        await db.commit()

        # Notify WebSocket
        await manager.broadcast(
            conversation_id,
            {
                "type": "message_sent",
                "conversation_id": conversation_id,
                "message": {
                    "id": msg_id,
                    "conversation_id": conversation_id,
                    "direction": "outbound",
                    "content": req.text,
                },
            },
        )

        return {"status": "ok", "message_id": msg_id}
    finally:
        await db.close()
