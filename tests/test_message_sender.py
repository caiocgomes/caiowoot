import json
import pytest
from unittest.mock import patch, AsyncMock

import httpx


@pytest.mark.asyncio
async def test_send_text_no_file(client, db, mock_evolution_api):
    """15.8: POST /send sem arquivo usa sendText (regressão)."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.commit()

    resp = await client.post(
        "/conversations/1/send",
        data={"text": "Oi Maria!"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    row = await db.execute(
        "SELECT * FROM messages WHERE conversation_id = 1 AND direction = 'outbound'"
    )
    msg = await row.fetchone()
    assert msg is not None
    assert msg["content"] == "Oi Maria!"
    assert msg["media_type"] is None


@pytest.mark.asyncio
async def test_send_image_calls_send_media(client, db, mock_evolution_api):
    """15.6: POST /send com arquivo imagem chama sendMedia."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.commit()

    resp = await client.post(
        "/conversations/1/send",
        data={"text": "Olha essa foto"},
        files={"file": ("photo.jpg", b"fake-image-bytes", "image/jpeg")},
    )

    assert resp.status_code == 200

    row = await db.execute(
        "SELECT * FROM messages WHERE conversation_id = 1 AND direction = 'outbound'"
    )
    msg = await row.fetchone()
    assert msg["media_type"] == "image"

    # Verify Evolution API was called with sendMedia endpoint
    call_args = mock_evolution_api.post.call_args
    url = call_args.kwargs.get("url") or call_args.args[0]
    assert "sendMedia" in url


@pytest.mark.asyncio
async def test_send_pdf_calls_send_document(client, db, mock_evolution_api):
    """15.7: POST /send com arquivo PDF chama sendDocument."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.commit()

    resp = await client.post(
        "/conversations/1/send",
        data={"text": "Segue o material"},
        files={"file": ("handbook.pdf", b"fake-pdf-bytes", "application/pdf")},
    )

    assert resp.status_code == 200

    row = await db.execute(
        "SELECT * FROM messages WHERE conversation_id = 1 AND direction = 'outbound'"
    )
    msg = await row.fetchone()
    assert msg["media_type"] == "document"

    # Verify Evolution API was called with sendMedia/document endpoint
    call_args = mock_evolution_api.post.call_args
    url = call_args.kwargs.get("url") or call_args.args[0]
    assert "sendMedia" in url


@pytest.mark.asyncio
async def test_edit_pair_with_all_metadata(client, db, mock_evolution_api):
    """15.9: edit_pair criado com all_drafts_json, selected_draft_index, prompt_hash."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (id, conversation_id, evolution_message_id, direction, content) "
        "VALUES (1, 1, 'msg-1', 'inbound', 'Quanto custa?')"
    )
    # Insert a draft group with 3 variations
    group_id = "test-group-uuid"
    for i, (approach, text) in enumerate([
        ("direta", "O CDO custa R$4000/ano"),
        ("consultiva", "Qual seu interesse em IA?"),
        ("casual", "Opa! Bora conversar sobre os cursos?"),
    ]):
        await db.execute(
            """INSERT INTO drafts
               (id, conversation_id, trigger_message_id, draft_text, justification,
                draft_group_id, variation_index, approach, prompt_hash, operator_instruction)
               VALUES (?, 1, 1, ?, ?, ?, ?, ?, 'testhash123', 'foca no preço')""",
            (i + 1, text, f"Justificativa {approach}", group_id, i, approach),
        )
    await db.commit()

    resp = await client.post(
        "/conversations/1/send",
        data={
            "text": "O CDO custa R$4000/ano, que dá R$11/dia",
            "draft_id": "1",
            "draft_group_id": group_id,
            "selected_draft_index": "0",
            "operator_instruction": "foca no preço",
            "regeneration_count": "1",
        },
    )

    assert resp.status_code == 200

    row = await db.execute("SELECT * FROM edit_pairs WHERE conversation_id = 1")
    pair = await row.fetchone()
    assert pair is not None
    assert pair["was_edited"] == 1
    assert pair["prompt_hash"] == "testhash123"
    assert pair["selected_draft_index"] == 0
    assert pair["operator_instruction"] == "foca no preço"
    assert pair["regeneration_count"] == 1

    # Verify all_drafts_json contains the 3 variations
    all_drafts = json.loads(pair["all_drafts_json"])
    assert len(all_drafts) == 3
    assert all_drafts[0]["approach"] == "direta"
    assert all_drafts[1]["approach"] == "consultiva"
    assert all_drafts[2]["approach"] == "casual"


@pytest.mark.asyncio
async def test_send_evolution_failure(client, db):
    """Falha no Evolution API retorna erro e não persiste."""
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
            data={"text": "Oi Maria!"},
        )

    assert resp.status_code == 502

    row = await db.execute("SELECT COUNT(*) as cnt FROM messages")
    count = await row.fetchone()
    assert count["cnt"] == 0


@pytest.mark.asyncio
async def test_edit_pair_unedited(client, db, mock_evolution_api):
    """Envio sem edição cria edit_pair com was_edited=false."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (id, conversation_id, evolution_message_id, direction, content) "
        "VALUES (1, 1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.execute(
        "INSERT INTO drafts (conversation_id, trigger_message_id, draft_text, justification) "
        "VALUES (1, 1, 'Oi! Tudo bem?', 'Saudação')"
    )
    await db.commit()

    resp = await client.post(
        "/conversations/1/send",
        data={"text": "Oi! Tudo bem?", "draft_id": "1"},
    )

    assert resp.status_code == 200

    row = await db.execute("SELECT * FROM edit_pairs WHERE conversation_id = 1")
    pair = await row.fetchone()
    assert pair["was_edited"] == 0


@pytest.mark.asyncio
async def test_no_edit_pair_without_draft(client, db, mock_evolution_api):
    """Envio manual sem draft não cria edit_pair."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.commit()

    resp = await client.post(
        "/conversations/1/send",
        data={"text": "Oi, tudo bem?"},
    )

    assert resp.status_code == 200

    row = await db.execute("SELECT COUNT(*) as cnt FROM edit_pairs")
    count = await row.fetchone()
    assert count["cnt"] == 0
