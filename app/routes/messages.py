import asyncio
import logging

import aiosqlite
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from starlette.requests import Request

from app.auth import get_operator_from_request
from app.database import get_db_connection
from app.models import RegenerateRequest, RewriteRequest
from app.services.draft_engine import regenerate_draft
from app.services.message_sender import send_and_record
from app.services.send_executor import check_duplicate_send, DuplicateSendError
from app.services.text_rewrite import rewrite_text

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/conversations/{conversation_id}/send")
async def send_message(
    conversation_id: int,
    request: Request,
    db: aiosqlite.Connection = Depends(get_db_connection),
    text: str = Form(...),
    draft_id: int | None = Form(None),
    draft_group_id: str | None = Form(None),
    selected_draft_index: int | None = Form(None),
    operator_instruction: str | None = Form(None),
    regeneration_count: int = Form(0),
    file: UploadFile | None = File(None),
):
    operator = get_operator_from_request(request)

    # Dedup guard
    if await check_duplicate_send(db, conversation_id, text):
        raise HTTPException(status_code=409, detail="Mensagem idêntica enviada há menos de 5 segundos")

    # Read file bytes if present (file processing stays in route handler)
    file_bytes = None
    file_name = None
    file_content_type = None
    if file and file.filename:
        file_bytes = await file.read()
        file_name = file.filename
        file_content_type = file.content_type or "application/octet-stream"

    try:
        result = await send_and_record(
            db=db,
            conv_id=conversation_id,
            text=text,
            operator=operator,
            draft_id=draft_id,
            draft_group_id=draft_group_id,
            selected_draft_index=selected_draft_index,
            operator_instruction=operator_instruction,
            regeneration_count=regeneration_count,
            file_bytes=file_bytes,
            filename=file_name,
            content_type=file_content_type,
        )
        return {"status": "ok", "message_id": result["message_id"]}
    except DuplicateSendError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Failed to send message via Evolution API")
        raise HTTPException(status_code=502, detail=f"Evolution API error: {e}")


@router.post("/conversations/{conversation_id}/regenerate")
async def regenerate(conversation_id: int, req: RegenerateRequest, request: Request, db: aiosqlite.Connection = Depends(get_db_connection)):
    operator = get_operator_from_request(request)
    row = await db.execute(
        "SELECT id FROM conversations WHERE id = ?",
        (conversation_id,),
    )
    if not await row.fetchone():
        raise HTTPException(status_code=404, detail="Conversation not found")

    asyncio.create_task(
        regenerate_draft(
            conversation_id,
            req.trigger_message_id,
            draft_index=req.draft_index,
            operator_instruction=req.operator_instruction,
            operator_name=operator,
        )
    )

    return {"status": "ok", "message": "Regeneration started"}


@router.post("/conversations/{conversation_id}/suggest")
async def suggest_followup(conversation_id: int, request: Request, db: aiosqlite.Connection = Depends(get_db_connection)):
    operator = get_operator_from_request(request)
    row = await db.execute(
        "SELECT id FROM conversations WHERE id = ?",
        (conversation_id,),
    )
    if not await row.fetchone():
        raise HTTPException(status_code=404, detail="Conversation not found")

    row = await db.execute(
        "SELECT id, direction FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT 1",
        (conversation_id,),
    )
    last_msg = await row.fetchone()
    if not last_msg:
        raise HTTPException(status_code=409, detail="No messages in conversation")
    if last_msg["direction"] != "outbound":
        raise HTTPException(status_code=409, detail="Last message is not outbound")

    last_msg_id = last_msg["id"]

    from app.services.draft_engine import generate_drafts

    asyncio.create_task(
        generate_drafts(conversation_id, last_msg_id, proactive=True, operator_name=operator)
    )

    return {"status": "ok"}


@router.post("/conversations/{conversation_id}/rewrite")
async def rewrite_message(conversation_id: int, req: RewriteRequest, db: aiosqlite.Connection = Depends(get_db_connection)):
    row = await db.execute(
        "SELECT id FROM conversations WHERE id = ?",
        (conversation_id,),
    )
    if not await row.fetchone():
        raise HTTPException(status_code=404, detail="Conversation not found")

    rewritten = await rewrite_text(req.text)
    return {"text": rewritten}
