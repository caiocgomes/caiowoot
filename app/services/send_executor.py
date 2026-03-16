import logging

from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.services.message_sender import send_and_record

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
    return datetime.now(timezone.utc) - created_at < timedelta(seconds=DEDUP_WINDOW_SECONDS)


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
    """Core send logic: delegates to send_and_record.

    Used by both the immediate send endpoint and the scheduled send background worker.
    Returns dict with message_id and edit_pair_id (if applicable).
    """
    db = await get_db()
    try:
        # Dedup guard: reject identical message to same conversation within 5s
        if await check_duplicate_send(db, conversation_id, text):
            raise DuplicateSendError("Mensagem idêntica enviada há menos de 5 segundos")

        return await send_and_record(
            db=db,
            conv_id=conversation_id,
            text=text,
            operator=operator,
            draft_id=draft_id,
            draft_group_id=draft_group_id,
            selected_draft_index=selected_draft_index,
            operator_instruction=operator_instruction,
            regeneration_count=regeneration_count,
        )
    finally:
        await db.close()
