import asyncio
import json
import logging

from fastapi import APIRouter, Request

from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# Evolution API webhook sends event as "messages.upsert" (lowercase, dot-separated)
MESSAGE_EVENTS = {"messages.upsert", "MESSAGES_UPSERT"}


@router.post("/webhook")
async def receive_webhook(request: Request):
    payload = await request.json()

    event = payload.get("event", "")
    if event not in MESSAGE_EVENTS:
        return {"status": "ignored", "event": event}

    data = payload.get("data", {})
    key = data.get("key", {})

    # Ignore messages sent by us
    if key.get("fromMe", False):
        return {"status": "ignored", "reason": "fromMe"}

    remote_jid = key.get("remoteJid", "")
    message_id = key.get("id", "")

    # Extract phone number from remoteJid (format: 5511999999999@s.whatsapp.net)
    phone_number = remote_jid.split("@")[0] if "@" in remote_jid else remote_jid
    if not phone_number:
        return {"status": "ignored", "reason": "no_phone"}

    # Extract message text
    message = data.get("message", {})
    text = (
        message.get("conversation")
        or message.get("extendedTextMessage", {}).get("text")
        or ""
    )
    if not text:
        return {"status": "ignored", "reason": "no_text"}

    contact_name = data.get("pushName", "")
    instance = payload.get("instance", {})
    instance_name = instance.get("instanceName", "") if isinstance(instance, dict) else str(instance)

    db = await get_db()
    try:
        # Dedup by evolution_message_id
        existing = await db.execute(
            "SELECT id FROM messages WHERE evolution_message_id = ?",
            (message_id,),
        )
        if await existing.fetchone():
            return {"status": "ignored", "reason": "duplicate"}

        # Get or create conversation
        row = await db.execute(
            "SELECT id FROM conversations WHERE phone_number = ?",
            (phone_number,),
        )
        conv = await row.fetchone()

        if conv:
            conversation_id = conv["id"]
            await db.execute(
                "UPDATE conversations SET contact_name = COALESCE(?, contact_name), updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (contact_name or None, conversation_id),
            )
        else:
            cursor = await db.execute(
                "INSERT INTO conversations (phone_number, contact_name) VALUES (?, ?)",
                (phone_number, contact_name or None),
            )
            conversation_id = cursor.lastrowid

        # Insert message
        cursor = await db.execute(
            "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (?, ?, 'inbound', ?)",
            (conversation_id, message_id, text),
        )
        msg_id = cursor.lastrowid

        await db.commit()

        # Trigger draft generation asynchronously
        from app.services.draft_engine import generate_drafts

        asyncio.create_task(generate_drafts(conversation_id, msg_id))

        # Notify connected WebSocket clients
        from app.websocket_manager import manager

        await manager.broadcast(
            conversation_id,
            {
                "type": "new_message",
                "conversation_id": conversation_id,
                "message": {
                    "id": msg_id,
                    "conversation_id": conversation_id,
                    "evolution_message_id": message_id,
                    "direction": "inbound",
                    "content": text,
                },
            },
        )

        return {"status": "ok", "conversation_id": conversation_id, "message_id": msg_id}
    finally:
        await db.close()
