import pytest
from unittest.mock import patch, AsyncMock

from tests.conftest import make_webhook_payload


@pytest.mark.asyncio
async def test_conversations_ordered_by_last_message(client, db):
    """16.1: GET /conversations retorna lista ordenada por última mensagem."""
    await db.execute(
        "INSERT INTO conversations (id, phone_number, contact_name) VALUES (1, '5511111111111', 'Alice')"
    )
    await db.execute(
        "INSERT INTO conversations (id, phone_number, contact_name) VALUES (2, '5511222222222', 'Bob')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content, created_at) VALUES (1, 'old-msg', 'inbound', 'Mensagem antiga', '2024-01-01 10:00:00')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content, created_at) VALUES (2, 'new-msg', 'inbound', 'Mensagem nova', '2024-01-02 10:00:00')"
    )
    await db.commit()

    resp = await client.get("/conversations")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data) == 2
    assert data[0]["contact_name"] == "Bob"  # Most recent first
    assert data[1]["contact_name"] == "Alice"


@pytest.mark.asyncio
async def test_conversation_detail_with_draft(client, db):
    """16.2: GET /conversations/{id} retorna mensagens e draft pendente."""
    await db.execute(
        "INSERT INTO conversations (id, phone_number, contact_name) VALUES (1, '5511999999999', 'Maria')"
    )
    await db.execute(
        "INSERT INTO messages (id, conversation_id, evolution_message_id, direction, content) VALUES (1, 1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.execute(
        "INSERT INTO drafts (conversation_id, trigger_message_id, draft_text, justification) VALUES (1, 1, 'Oi! Tudo bem?', 'Saudação inicial')"
    )
    await db.commit()

    resp = await client.get("/conversations/1")
    assert resp.status_code == 200
    data = resp.json()

    assert data["conversation"]["contact_name"] == "Maria"
    assert len(data["messages"]) == 1
    assert data["messages"][0]["content"] == "Oi"
    assert data["pending_draft"] is not None
    assert data["pending_draft"]["draft_text"] == "Oi! Tudo bem?"
    assert data["pending_draft"]["justification"] == "Saudação inicial"


@pytest.mark.asyncio
async def test_full_flow(client, db, mock_evolution_api, mock_claude_api):
    """16.3: fluxo completo: webhook → draft → GET → send → edit_pair."""
    # 1. Receive webhook
    with patch("app.routes.webhook.asyncio.create_task"):
        payload = make_webhook_payload(text="Quanto custa o CDO?")
        resp = await client.post("/webhook", json=payload)
    assert resp.status_code == 200
    conv_id = resp.json()["conversation_id"]

    # 2. Generate draft manually (since we mocked create_task)
    from app.services.draft_engine import generate_draft
    msg_id = resp.json()["message_id"]
    await generate_draft(conv_id, msg_id)

    # 3. GET conversation shows draft
    resp = await client.get(f"/conversations/{conv_id}")
    data = resp.json()
    assert data["pending_draft"] is not None
    draft_id = data["pending_draft"]["id"]

    # 4. Send edited message
    resp = await client.post(
        f"/conversations/{conv_id}/send",
        json={"text": "O CDO custa R$4000/ano, que dá R$11/dia!", "draft_id": draft_id},
    )
    assert resp.status_code == 200

    # 5. Verify edit_pair
    row = await db.execute("SELECT * FROM edit_pairs")
    pair = await row.fetchone()
    assert pair is not None
    assert pair["customer_message"] == "Quanto custa o CDO?"
    assert pair["was_edited"] == 1
