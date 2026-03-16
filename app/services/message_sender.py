import asyncio
import json
import logging

from app.services.evolution import send_text_message, send_media_message, send_document_message
from app.services.strategic_annotation import generate_annotation
from app.websocket_manager import manager

logger = logging.getLogger(__name__)


async def send_and_record(
    db,
    conv_id: int,
    text: str,
    operator: str | None = None,
    draft_id: int | None = None,
    draft_group_id: str | None = None,
    selected_draft_index: int | None = None,
    operator_instruction: str | None = None,
    regeneration_count: int = 0,
    file_bytes: bytes | None = None,
    filename: str | None = None,
    content_type: str | None = None,
) -> dict:
    """Unified message send: handles text-only and file sends, edit_pair recording, annotation triggering.

    Returns dict with message_id and edit_pair_id (if applicable).
    """
    row = await db.execute(
        "SELECT phone_number FROM conversations WHERE id = ?",
        (conv_id,),
    )
    conv = await row.fetchone()
    if not conv:
        raise ValueError(f"Conversation {conv_id} not found")

    # Send via Evolution API
    media_url = None
    media_type = None
    attachment_filename = None

    if file_bytes and filename:
        import base64
        b64_data = base64.b64encode(file_bytes).decode()
        ct = content_type or "application/octet-stream"

        if ct.startswith("image/"):
            await send_media_message(conv["phone_number"], b64_data, ct, text)
            media_type = "image"
        else:
            await send_document_message(conv["phone_number"], b64_data, filename, text)
            media_type = "document"
        attachment_filename = filename
    else:
        await send_text_message(conv["phone_number"], text)

    # Insert message
    cursor = await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, media_url, media_type, sent_by) VALUES (?, 'outbound', ?, ?, ?, ?)",
        (conv_id, text, media_url, media_type, operator),
    )
    msg_id = cursor.lastrowid

    # Save attachment file to disk if present
    if file_bytes and filename:
        import os
        from pathlib import Path
        from app.config import settings
        attachments_dir = Path(settings.database_path).parent / "attachments"
        os.makedirs(attachments_dir, exist_ok=True)
        file_path = attachments_dir / f"{msg_id}_{filename}"
        file_path.write_bytes(file_bytes)
        media_url = str(file_path)
        await db.execute(
            "UPDATE messages SET media_url = ? WHERE id = ?",
            (media_url, msg_id),
        )

    await db.execute(
        "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (conv_id,),
    )

    # Record edit pair if draft was used
    edit_pair_id = None
    draft = None
    customer_message = ""
    was_edited = False

    if draft_id:
        draft_row = await db.execute(
            "SELECT draft_text, trigger_message_id, draft_group_id, prompt_hash, operator_instruction, situation_summary FROM drafts WHERE id = ? AND conversation_id = ?",
            (draft_id, conv_id),
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
                (conv_id, customer_message, draft["draft_text"], text, was_edited,
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

    # Broadcast via WebSocket
    broadcast_msg = {
        "type": "message_sent",
        "conversation_id": conv_id,
        "message": {
            "id": msg_id,
            "conversation_id": conv_id,
            "direction": "outbound",
            "content": text,
        },
    }
    if media_type:
        broadcast_msg["message"]["media_type"] = media_type

    await manager.broadcast(conv_id, broadcast_msg)

    return {"message_id": msg_id, "edit_pair_id": edit_pair_id}
