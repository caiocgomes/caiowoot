"""Tests for auto-qualifying feature."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from tests.conftest import make_webhook_payload


def make_qualify_response(message, ready_for_handoff=False, summary=""):
    """Create a mock Claude response with proper tool_use block."""
    block = SimpleNamespace(
        type="tool_use",
        name="qualify_response",
        input={"message": message, "ready_for_handoff": ready_for_handoff, "qualification_summary": summary},
    )
    resp = MagicMock()
    resp.content = [block]
    return resp


@pytest.mark.asyncio
async def test_new_conversation_is_not_qualified(client, db):
    """New conversations should have is_qualified = False."""
    with patch("app.routes.webhook.auto_qualify_respond", new_callable=AsyncMock):
        res = await client.post("/webhook", json=make_webhook_payload())
        assert res.status_code == 200

    row = await db.execute("SELECT is_qualified FROM conversations WHERE phone_number = '5511999999999'")
    conv = await row.fetchone()
    assert conv["is_qualified"] == 0


@pytest.mark.asyncio
async def test_webhook_routes_to_auto_qualifier(client, db):
    """Unqualified conversations should trigger auto_qualify_respond, not generate_drafts."""
    with patch("app.routes.webhook.auto_qualify_respond", new_callable=AsyncMock) as mock_qualify:
        res = await client.post("/webhook", json=make_webhook_payload(phone="5511999990002"))
        assert res.status_code == 200
        mock_qualify.assert_called_once()


@pytest.mark.asyncio
async def test_webhook_routes_to_drafts_when_qualified(client, db):
    """Qualified conversations should trigger generate_drafts, not auto_qualify_respond."""
    await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, is_qualified) VALUES (?, ?, 1)",
        ("5511888880001", "Maria"),
    )
    await db.commit()

    payload = make_webhook_payload(phone="5511888880001", text="Oi")

    with patch("app.routes.webhook.auto_qualify_respond", new_callable=AsyncMock) as mock_qualify:
        res = await client.post("/webhook", json=payload)
        assert res.status_code == 200
        mock_qualify.assert_not_called()


@pytest.mark.asyncio
async def test_auto_qualify_sends_bot_message(client, db):
    """auto_qualify_respond should send a message with sent_by='bot'."""
    # Create unqualified conversation with a message
    await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, is_qualified) VALUES (?, ?, 0)",
        ("5511777770001", "Pedro"),
    )
    await db.commit()
    row = await db.execute("SELECT id FROM conversations WHERE phone_number = '5511777770001'")
    conv = await row.fetchone()
    conv_id = conv["id"]

    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content) VALUES (?, 'inbound', ?)",
        (conv_id, "Oi, quero saber sobre o curso"),
    )
    await db.commit()

    mock_response = make_qualify_response(
        "Oi Pedro! Sou o assistente virtual. Qual curso te interessa?",
        ready_for_handoff=False,
        summary="Lead perguntou sobre curso",
    )

    with patch("app.services.auto_qualifier.get_anthropic_client") as mock_client_fn, \
         patch("app.services.auto_qualifier.send_text_message", new_callable=AsyncMock) as mock_send, \
         patch("app.services.auto_qualifier.manager") as mock_ws:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_client_fn.return_value = mock_client
        mock_ws.broadcast = AsyncMock()

        from app.services.auto_qualifier import auto_qualify_respond
        await auto_qualify_respond(conv_id)

        mock_send.assert_called_once_with("5511777770001", "Oi Pedro! Sou o assistente virtual. Qual curso te interessa?")

    # Check message saved with sent_by = "bot"
    msgs = await db.execute(
        "SELECT direction, content, sent_by FROM messages WHERE conversation_id = ? AND direction = 'outbound'",
        (conv_id,),
    )
    bot_msg = await msgs.fetchone()
    assert bot_msg is not None
    assert bot_msg["sent_by"] == "bot"
    assert "assistente virtual" in bot_msg["content"]


@pytest.mark.asyncio
async def test_auto_qualify_handoff_sets_qualified(client, db):
    """When ready_for_handoff is True, is_qualified should be set to 1."""
    await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, is_qualified) VALUES (?, ?, 0)",
        ("5511666660001", "Ana"),
    )
    await db.commit()
    row = await db.execute("SELECT id FROM conversations WHERE phone_number = '5511666660001'")
    conv = await row.fetchone()
    conv_id = conv["id"]

    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content) VALUES (?, 'inbound', ?)",
        (conv_id, "Quero o curso de LLMs, trabalho com dados há 3 anos"),
    )
    await db.commit()

    mock_response = make_qualify_response(
        "Beleza! Já passei tudo pro atendente. Ele já tem todo o contexto!",
        ready_for_handoff=True,
        summary="Lead quer curso de LLMs, trabalha com dados há 3 anos",
    )

    with patch("app.services.auto_qualifier.get_anthropic_client") as mock_client_fn, \
         patch("app.services.auto_qualifier.send_text_message", new_callable=AsyncMock), \
         patch("app.services.auto_qualifier.manager") as mock_ws, \
         patch("app.services.auto_qualifier.generate_situation_summary", new_callable=AsyncMock):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_client_fn.return_value = mock_client
        mock_ws.broadcast = AsyncMock()

        from app.services.auto_qualifier import auto_qualify_respond
        await auto_qualify_respond(conv_id)

    # Check is_qualified is now True
    check = await db.execute("SELECT is_qualified FROM conversations WHERE id = ?", (conv_id,))
    result = await check.fetchone()
    assert result["is_qualified"] == 1


@pytest.mark.asyncio
async def test_assume_conversation(client, db):
    """POST /conversations/{id}/assume should set is_qualified to 1."""
    await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, is_qualified) VALUES (?, ?, 0)",
        ("5511555550001", "Carlos"),
    )
    await db.commit()
    row = await db.execute("SELECT id FROM conversations WHERE phone_number = '5511555550001'")
    conv = await row.fetchone()
    conv_id = conv["id"]

    res = await client.post(f"/conversations/{conv_id}/assume")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    check = await db.execute("SELECT is_qualified FROM conversations WHERE id = ?", (conv_id,))
    result = await check.fetchone()
    assert result["is_qualified"] == 1


@pytest.mark.asyncio
async def test_conversations_list_includes_is_qualified(client, db):
    """GET /conversations should include is_qualified field."""
    await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, is_qualified) VALUES (?, ?, 0)",
        ("5511444440001", "Diana"),
    )
    await db.commit()

    res = await client.get("/conversations")
    assert res.status_code == 200
    conversations = res.json()
    assert len(conversations) >= 1
    diana = [c for c in conversations if c.get("contact_name") == "Diana"]
    assert len(diana) == 1
    assert diana[0]["is_qualified"] == 0
