import pytest
from unittest.mock import patch, AsyncMock

from tests.conftest import make_webhook_payload


async def _create_conversation_with_inbound(client, db):
    """Helper: create a conversation via webhook and return conversation_id."""
    with patch("app.routes.webhook.asyncio.create_task"):
        payload = make_webhook_payload()
        await client.post("/webhook", json=payload)

    row = await db.execute("SELECT id FROM conversations LIMIT 1")
    conv = await row.fetchone()
    return conv["id"]


@pytest.mark.asyncio
async def test_opening_conversation_updates_last_read_at(client, db):
    """4.1: opening conversation updates last_read_at."""
    conv_id = await _create_conversation_with_inbound(client, db)

    # Verify last_read_at is NULL before opening
    row = await db.execute("SELECT last_read_at FROM conversations WHERE id = ?", (conv_id,))
    conv = await row.fetchone()
    assert conv["last_read_at"] is None

    # Open conversation
    resp = await client.get(f"/conversations/{conv_id}")
    assert resp.status_code == 200

    # Verify last_read_at is now set
    row = await db.execute("SELECT last_read_at FROM conversations WHERE id = ?", (conv_id,))
    conv = await row.fetchone()
    assert conv["last_read_at"] is not None


@pytest.mark.asyncio
async def test_is_new_true_when_inbound_after_null_last_read_at(client, db):
    """4.2: is_new true when inbound message exists and last_read_at is NULL."""
    await _create_conversation_with_inbound(client, db)

    resp = await client.get("/conversations")
    assert resp.status_code == 200
    conversations = resp.json()

    assert len(conversations) == 1
    assert conversations[0]["is_new"] == 1
    assert conversations[0]["needs_reply"] == 1


@pytest.mark.asyncio
async def test_is_new_false_after_opening_conversation(client, db):
    """4.3: is_new false after opening conversation (last_read_at updated)."""
    conv_id = await _create_conversation_with_inbound(client, db)

    # Open the conversation to set last_read_at
    await client.get(f"/conversations/{conv_id}")

    # Now check list
    resp = await client.get("/conversations")
    conversations = resp.json()

    assert len(conversations) == 1
    assert conversations[0]["is_new"] == 0
    # Still needs reply since last message is inbound
    assert conversations[0]["needs_reply"] == 1


@pytest.mark.asyncio
async def test_needs_reply_true_when_last_message_inbound(client, db):
    """4.4: needs_reply true when last message is inbound."""
    await _create_conversation_with_inbound(client, db)

    resp = await client.get("/conversations")
    conversations = resp.json()

    assert len(conversations) == 1
    assert conversations[0]["needs_reply"] == 1


@pytest.mark.asyncio
async def test_needs_reply_false_when_last_message_outbound(client, db):
    """4.5: needs_reply false when last message is outbound."""
    conv_id = await _create_conversation_with_inbound(client, db)

    # Open conversation to set last_read_at
    await client.get(f"/conversations/{conv_id}")

    # Insert an outbound message
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content) VALUES (?, 'outbound', 'Resposta enviada')",
        (conv_id,),
    )
    await db.commit()

    resp = await client.get("/conversations")
    conversations = resp.json()

    assert len(conversations) == 1
    assert conversations[0]["needs_reply"] == 0
    assert conversations[0]["is_new"] == 0
