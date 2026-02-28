import pytest
from unittest.mock import patch, AsyncMock

import httpx


@pytest.mark.asyncio
async def test_send_message_success(client, db, mock_evolution_api):
    """14.1: POST send envia via Evolution API e persiste outbound."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.commit()

    resp = await client.post(
        "/conversations/1/send",
        json={"text": "Oi Maria!"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    row = await db.execute(
        "SELECT * FROM messages WHERE conversation_id = 1 AND direction = 'outbound'"
    )
    msg = await row.fetchone()
    assert msg is not None
    assert msg["content"] == "Oi Maria!"


@pytest.mark.asyncio
async def test_send_message_evolution_failure(client, db):
    """14.2: falha no Evolution API retorna erro e não persiste."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.commit()

    with patch("app.services.evolution.httpx.AsyncClient") as mock:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.HTTPStatusError(
            "500", request=AsyncMock(), response=AsyncMock(status_code=500)
        ))
        mock.return_value = mock_client

        resp = await client.post(
            "/conversations/1/send",
            json={"text": "Oi Maria!"},
        )

    assert resp.status_code == 502

    row = await db.execute("SELECT COUNT(*) as cnt FROM messages")
    count = await row.fetchone()
    assert count["cnt"] == 0


@pytest.mark.asyncio
async def test_edit_pair_created_when_draft_edited(client, db, mock_evolution_api):
    """14.3: envio com draft editado cria edit_pair com was_edited=true."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Quanto custa?')"
    )
    await db.execute(
        "INSERT INTO drafts (conversation_id, trigger_message_id, draft_text, justification) VALUES (1, 1, 'O CDO custa R$4000/ano', 'Objeção de preço, ancorei em ROI')"
    )
    await db.commit()

    resp = await client.post(
        "/conversations/1/send",
        json={"text": "O CDO custa R$4000/ano, que dá R$11/dia", "draft_id": 1},
    )

    assert resp.status_code == 200

    row = await db.execute("SELECT * FROM edit_pairs WHERE conversation_id = 1")
    pair = await row.fetchone()
    assert pair is not None
    assert pair["was_edited"] == 1
    assert pair["original_draft"] == "O CDO custa R$4000/ano"
    assert pair["final_message"] == "O CDO custa R$4000/ano, que dá R$11/dia"


@pytest.mark.asyncio
async def test_edit_pair_unedited_flagged(client, db, mock_evolution_api):
    """14.4: envio sem edição cria edit_pair com was_edited=false."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.execute(
        "INSERT INTO drafts (conversation_id, trigger_message_id, draft_text, justification) VALUES (1, 1, 'Oi! Tudo bem?', 'Saudação')"
    )
    await db.commit()

    resp = await client.post(
        "/conversations/1/send",
        json={"text": "Oi! Tudo bem?", "draft_id": 1},
    )

    assert resp.status_code == 200

    row = await db.execute("SELECT * FROM edit_pairs WHERE conversation_id = 1")
    pair = await row.fetchone()
    assert pair["was_edited"] == 0


@pytest.mark.asyncio
async def test_no_edit_pair_without_draft(client, db, mock_evolution_api):
    """14.5: envio manual sem draft não cria edit_pair."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.commit()

    resp = await client.post(
        "/conversations/1/send",
        json={"text": "Oi, tudo bem?"},
    )

    assert resp.status_code == 200

    row = await db.execute("SELECT COUNT(*) as cnt FROM edit_pairs")
    count = await row.fetchone()
    assert count["cnt"] == 0
