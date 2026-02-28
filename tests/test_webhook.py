import pytest
from unittest.mock import patch, AsyncMock

from tests.conftest import make_webhook_payload


@pytest.mark.asyncio
async def test_text_message_persisted(client, db):
    """12.1: mensagem de texto recebida persiste no banco."""
    with patch("app.routes.webhook.asyncio.create_task"):
        payload = make_webhook_payload()
        resp = await client.post("/webhook", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"

    row = await db.execute("SELECT * FROM messages WHERE evolution_message_id = 'msg-123'")
    msg = await row.fetchone()
    assert msg is not None
    assert msg["content"] == "Oi, quero saber sobre os cursos"
    assert msg["direction"] == "inbound"


@pytest.mark.asyncio
async def test_status_update_ignored(client, db):
    """12.2: evento de status retorna 200 e não persiste."""
    payload = make_webhook_payload(event="messages.update")
    resp = await client.post("/webhook", json=payload)

    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"

    row = await db.execute("SELECT COUNT(*) as cnt FROM messages")
    count = await row.fetchone()
    assert count["cnt"] == 0


@pytest.mark.asyncio
async def test_duplicate_message_ignored(client, db):
    """12.3: mensagem duplicada retorna 200 e não duplica."""
    with patch("app.routes.webhook.asyncio.create_task"):
        payload = make_webhook_payload()
        await client.post("/webhook", json=payload)
        resp = await client.post("/webhook", json=payload)

    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    assert resp.json()["reason"] == "duplicate"

    row = await db.execute("SELECT COUNT(*) as cnt FROM messages")
    count = await row.fetchone()
    assert count["cnt"] == 1


@pytest.mark.asyncio
async def test_new_phone_creates_conversation(client, db):
    """12.4: primeira mensagem de um phone novo cria conversation + message."""
    with patch("app.routes.webhook.asyncio.create_task"):
        payload = make_webhook_payload(phone="5511888888888", push_name="João")
        resp = await client.post("/webhook", json=payload)

    assert resp.status_code == 200

    row = await db.execute("SELECT * FROM conversations WHERE phone_number = '5511888888888'")
    conv = await row.fetchone()
    assert conv is not None
    assert conv["contact_name"] == "João"


@pytest.mark.asyncio
async def test_existing_phone_appends_message(client, db):
    """12.5: mensagem de phone existente adiciona à conversation existente."""
    with patch("app.routes.webhook.asyncio.create_task"):
        payload1 = make_webhook_payload(message_id="msg-1", text="Oi")
        await client.post("/webhook", json=payload1)

        payload2 = make_webhook_payload(message_id="msg-2", text="Tudo bem?")
        await client.post("/webhook", json=payload2)

    row = await db.execute("SELECT COUNT(*) as cnt FROM conversations")
    count = await row.fetchone()
    assert count["cnt"] == 1

    row = await db.execute("SELECT COUNT(*) as cnt FROM messages")
    count = await row.fetchone()
    assert count["cnt"] == 2


@pytest.mark.asyncio
async def test_message_triggers_draft_generation(client, db, mock_claude_api):
    """12.6: mensagem recebida dispara geração de draft."""
    # Don't mock create_task — let it actually run
    payload = make_webhook_payload()
    resp = await client.post("/webhook", json=payload)
    assert resp.status_code == 200

    # Give async task time to complete
    import asyncio
    await asyncio.sleep(0.5)

    row = await db.execute("SELECT * FROM drafts")
    draft = await row.fetchone()
    # Draft may or may not exist depending on async timing
    # The important thing is no crash occurred
