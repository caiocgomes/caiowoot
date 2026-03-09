import asyncio
import json
import logging

from datetime import datetime, timedelta

from app.database import get_db
from app.services.evolution import send_text_message
from app.services.strategic_annotation import generate_annotation
from app.websocket_manager import manager

logger = logging.getLogger(__name__)

DEDUP_WINDOW_SECONDS = 5


class DuplicateSendError(Exception):
    pass


async def check_duplicate_send(db, conversation_id: int, content: str) -> bool:
    """Check if an identical outbound message was sent to this conversation within the dedup window."""
    row = await db.execute(
        "SELECT content, created_at FROM messages WHERE conversation_id = ? AND direction = 'outbound' ORDER BY created_at DESC LIMIT 1",
        (conversation_id,),
    )
    last_msg = await row.fetchone()
    if not last_msg:
        return False
    if last_msg["content"] != content:
        return False
    created_at = datetime.fromisoformat(last_msg["created_at"])
    return datetime.utcnow() - created_at < timedelta(seconds=DEDUP_WINDOW_SECONDS)


async def execute_send(
    conversation_id: int,
    text: str,
    operator: str | None = None,
    draft_id: int | None = None,
    draft_group_id: str | None = None,
    selected_draft_index: int | None = None,
    operator_instruction: str | None = None,
    regeneration_count: int = 0,
    attachment_filename: str | None = None,
) -> dict:
    """Core send logic: Evolution API call + insert message + edit_pair + WebSocket broadcast.

    Used by both the immediate send endpoint and the scheduled send background worker.
    Returns dict with message_id and edit_pair_id (if applicable).
    """
    db = await get_db()
    try:
        row = await db.execute(
            "SELECT phone_number FROM conversations WHERE id = ?",
            (conversation_id,),
        )
        conv = await row.fetchone()
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Dedup guard: reject identical message to same conversation within 5s
        if await check_duplicate_send(db, conversation_id, text):
            raise DuplicateSendError("Mensagem idêntica enviada há menos de 5 segundos")

        # Send via Evolution API (text only for scheduled sends)
        await send_text_message(conv["phone_number"], text)

        cursor = await db.execute(
            "INSERT INTO messages (conversation_id, direction, content, sent_by) VALUES (?, 'outbound', ?, ?)",
            (conversation_id, text, operator),
        )
        msg_id = cursor.lastrowid

        await db.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )

        # Record edit pair if draft was used
        edit_pair_id = None
        draft = None
        customer_message = ""
        was_edited = False
        if draft_id:
            draft_row = await db.execute(
                "SELECT draft_text, trigger_message_id, draft_group_id, prompt_hash, operator_instruction, situation_summary FROM drafts WHERE id = ? AND conversation_id = ?",
                (draft_id, conversation_id),
            )
            draft = await draft_row.fetchone()
            if draft:
                trigger_row = await db.execute(
                    "SELECT content FROM messages WHERE id = ?",
                    (draft["trigger_message_id"],),
                )
                trigger_msg = await trigger_row.fetchone()
                customer_message = trigger_msg["content"] if trigger_msg else ""

                was_edited = draft["draft_text"] != text

                # Get all drafts in the group
                all_drafts_json = None
                group_id = draft_group_id or draft["draft_group_id"]
                if group_id:
                    group_row = await db.execute(
                        "SELECT draft_text, approach FROM drafts WHERE draft_group_id = ? ORDER BY variation_index",
                        (group_id,),
                    )
                    group_drafts = await group_row.fetchall()
                    all_drafts_json = json.dumps([
                        {"text": d["draft_text"], "approach": d["approach"]}
                        for d in group_drafts
                    ], ensure_ascii=False)

                cursor = await db.execute(
                    """INSERT INTO edit_pairs
                       (conversation_id, customer_message, original_draft, final_message, was_edited,
                        operator_instruction, all_drafts_json, selected_draft_index, prompt_hash,
                        regeneration_count, situation_summary, attachment_filename)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (conversation_id, customer_message, draft["draft_text"], text, was_edited,
                     operator_instruction or draft["operator_instruction"],
                     all_drafts_json, selected_draft_index, draft["prompt_hash"], regeneration_count,
                     draft["situation_summary"], attachment_filename),
                )
                edit_pair_id = cursor.lastrowid

                # Mark all drafts in group as sent/discarded
                if group_id:
                    await db.execute(
                        "UPDATE drafts SET status = 'discarded' WHERE draft_group_id = ?",
                        (group_id,),
                    )
                await db.execute(
                    "UPDATE drafts SET status = 'sent' WHERE id = ?",
                    (draft_id,),
                )

        await db.commit()

        # Fire-and-forget strategic annotation in background
        if edit_pair_id and draft:
            asyncio.create_task(
                generate_annotation(
                    edit_pair_id=edit_pair_id,
                    customer_message=customer_message,
                    original_draft=draft["draft_text"],
                    final_message=text,
                    was_edited=was_edited,
                    situation_summary=draft["situation_summary"],
                    attachment_filename=attachment_filename,
                )
            )

        await manager.broadcast(
            conversation_id,
            {
                "type": "message_sent",
                "conversation_id": conversation_id,
                "message": {
                    "id": msg_id,
                    "conversation_id": conversation_id,
                    "direction": "outbound",
                    "content": text,
                },
            },
        )

        return {"message_id": msg_id, "edit_pair_id": edit_pair_id}
    finally:
        await db.close()
