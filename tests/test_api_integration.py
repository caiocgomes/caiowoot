import pytest
from unittest.mock import patch, AsyncMock

from tests.conftest import make_webhook_payload


@pytest.mark.asyncio
async def test_conversations_ordered_by_last_message(client, db):
    """GET /conversations retorna lista ordenada por última mensagem."""
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
async def test_conversation_detail_returns_pending_drafts_array(client, db):
    """15.10: GET /conversations/{id} retorna array de pending drafts."""
    await db.execute(
        "INSERT INTO conversations (id, phone_number, contact_name) VALUES (1, '5511999999999', 'Maria')"
    )
    await db.execute(
        "INSERT INTO messages (id, conversation_id, evolution_message_id, direction, content) VALUES (1, 1, 'msg-1', 'inbound', 'Oi')"
    )
    # Insert 3 drafts in a group
    group_id = "test-group-uuid"
    for i, (approach, text) in enumerate([
        ("direta", "Oi! Qual seu interesse?"),
        ("consultiva", "E aí! Me conta mais?"),
        ("casual", "Opa! Tudo bem?"),
    ]):
        await db.execute(
            """INSERT INTO drafts
               (conversation_id, trigger_message_id, draft_text, justification,
                draft_group_id, variation_index, approach)
               VALUES (1, 1, ?, ?, ?, ?, ?)""",
            (text, f"Abordagem {approach}", group_id, i, approach),
        )
    await db.commit()

    resp = await client.get("/conversations/1")
    assert resp.status_code == 200
    data = resp.json()

    assert data["conversation"]["contact_name"] == "Maria"
    assert len(data["messages"]) == 1
    assert data["messages"][0]["content"] == "Oi"

    # Verify pending_drafts is an array of 3
    assert "pending_drafts" in data
    assert len(data["pending_drafts"]) == 3
    assert data["pending_drafts"][0]["draft_text"] == "Oi! Qual seu interesse?"
    assert data["pending_drafts"][0]["approach"] == "direta"
    assert data["pending_drafts"][1]["approach"] == "consultiva"
    assert data["pending_drafts"][2]["approach"] == "casual"
    # All share the same group
    assert all(d["draft_group_id"] == group_id for d in data["pending_drafts"])


@pytest.mark.asyncio
async def test_conversation_detail_no_drafts(client, db):
    """GET /conversations/{id} sem drafts retorna array vazio."""
    await db.execute(
        "INSERT INTO conversations (id, phone_number) VALUES (1, '5511999999999')"
    )
    await db.commit()

    resp = await client.get("/conversations/1")
    data = resp.json()
    assert data["pending_drafts"] == []


@pytest.mark.asyncio
async def test_full_flow(client, db, mock_evolution_api, mock_claude_api):
    """Fluxo completo: webhook → drafts → GET → send → edit_pair."""
    # 1. Receive webhook
    with patch("app.routes.webhook.asyncio.create_task"):
        payload = make_webhook_payload(text="Quanto custa o CDO?")
        resp = await client.post("/webhook", json=payload)
    assert resp.status_code == 200
    conv_id = resp.json()["conversation_id"]

    # 2. Generate drafts manually (since we mocked create_task)
    from app.services.draft_engine import generate_drafts
    msg_id = resp.json()["message_id"]
    await generate_drafts(conv_id, msg_id)

    # 3. GET conversation shows pending_drafts array
    resp = await client.get(f"/conversations/{conv_id}")
    data = resp.json()
    assert len(data["pending_drafts"]) == 3
    draft_id = data["pending_drafts"][0]["id"]

    # 4. Send edited message (using Form data)
    resp = await client.post(
        f"/conversations/{conv_id}/send",
        data={
            "text": "O CDO custa R$4000/ano, que dá R$11/dia!",
            "draft_id": str(draft_id),
        },
    )
    assert resp.status_code == 200

    # 5. Verify edit_pair
    row = await db.execute("SELECT * FROM edit_pairs")
    pair = await row.fetchone()
    assert pair is not None
    assert pair["customer_message"] == "Quanto custa o CDO?"
    assert pair["was_edited"] == 1
