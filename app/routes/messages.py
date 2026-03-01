import asyncio
import base64
import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from starlette.requests import Request

from app.auth import get_operator_from_request
from app.config import settings
from app.database import get_db
from app.models import RegenerateRequest
from app.services.evolution import send_document_message, send_media_message, send_text_message
from app.services.draft_engine import regenerate_draft
from app.services.strategic_annotation import generate_annotation
from app.websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/conversations/{conversation_id}/send")
async def send_message(
    conversation_id: int,
    request: Request,
    text: str = Form(...),
    draft_id: int | None = Form(None),
    draft_group_id: str | None = Form(None),
    selected_draft_index: int | None = Form(None),
    operator_instruction: str | None = Form(None),
    regeneration_count: int = Form(0),
    file: UploadFile | None = File(None),
):
    operator = get_operator_from_request(request)
    db = await get_db()
    try:
        row = await db.execute(
            "SELECT phone_number FROM conversations WHERE id = ?",
            (conversation_id,),
        )
        conv = await row.fetchone()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        media_url = None
        media_type = None

        try:
            if file and file.filename:
                file_content = await file.read()
                b64_data = base64.b64encode(file_content).decode()
                content_type = file.content_type or "application/octet-stream"

                if content_type.startswith("image/"):
                    await send_media_message(conv["phone_number"], b64_data, content_type, text)
                    media_type = "image"
                else:
                    await send_document_message(conv["phone_number"], b64_data, file.filename, text)
                    media_type = "document"
            else:
                await send_text_message(conv["phone_number"], text)
        except Exception as e:
            logger.exception("Failed to send message via Evolution API")
            raise HTTPException(status_code=502, detail=f"Evolution API error: {e}")

        cursor = await db.execute(
            "INSERT INTO messages (conversation_id, direction, content, media_url, media_type, sent_by) VALUES (?, 'outbound', ?, ?, ?, ?)",
            (conversation_id, text, media_url, media_type, operator),
        )
        msg_id = cursor.lastrowid

        # Save attachment file to disk
        if file and file.filename and media_type:
            attachments_dir = Path(settings.database_path).parent / "attachments"
            os.makedirs(attachments_dir, exist_ok=True)
            file_path = attachments_dir / f"{msg_id}_{file.filename}"
            await file.seek(0)
            content = await file.read()
            file_path.write_bytes(content)
            media_url = str(file_path)
            await db.execute(
                "UPDATE messages SET media_url = ? WHERE id = ?",
                (media_url, msg_id),
            )

        await db.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )

        # Record edit pair if draft was used
        edit_pair_id = None
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
                        regeneration_count, situation_summary)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (conversation_id, customer_message, draft["draft_text"], text, was_edited,
                     operator_instruction or draft["operator_instruction"],
                     all_drafts_json, selected_draft_index, draft["prompt_hash"], regeneration_count,
                     draft["situation_summary"]),
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
                    "media_type": media_type,
                },
            },
        )

        return {"status": "ok", "message_id": msg_id}
    finally:
        await db.close()


@router.post("/conversations/{conversation_id}/regenerate")
async def regenerate(conversation_id: int, req: RegenerateRequest):
    db = await get_db()
    try:
        row = await db.execute(
            "SELECT id FROM conversations WHERE id = ?",
            (conversation_id,),
        )
        if not await row.fetchone():
            raise HTTPException(status_code=404, detail="Conversation not found")
    finally:
        await db.close()

    asyncio.create_task(
        regenerate_draft(
            conversation_id,
            req.trigger_message_id,
            draft_index=req.draft_index,
            operator_instruction=req.operator_instruction,
        )
    )

    return {"status": "ok", "message": "Regeneration started"}
