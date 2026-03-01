import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_suggest_endpoint_with_outbound_last_message(client, db, mock_claude_api):
    """POST /suggest returns ok when last message is outbound."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) "
        "VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content) "
        "VALUES (1, 'outbound', 'Falo contigo depois!')"
    )
    await db.commit()

    res = await client.post("/conversations/1/suggest")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_suggest_endpoint_rejects_inbound_last_message(client, db):
    """POST /suggest returns 409 when last message is inbound."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) "
        "VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.commit()

    res = await client.post("/conversations/1/suggest")
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_suggest_endpoint_404_for_missing_conversation(client, db):
    """POST /suggest returns 404 for non-existent conversation."""
    res = await client.post("/conversations/999/suggest")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_proactive_draft_uses_continuation_instruction(db, mock_claude_api):
    """generate_drafts with proactive=True uses continuation instruction."""
    from app.services.draft_engine import generate_drafts

    await db.execute(
        "INSERT INTO conversations (phone_number, contact_name) VALUES ('5511999999999', 'Maria')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) "
        "VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content) "
        "VALUES (1, 'outbound', 'Vou te enviar o PDF depois.')"
    )
    await db.commit()

    await generate_drafts(1, 2, proactive=True)

    # Verify the prompt uses continuation instruction
    call_kwargs = mock_claude_api.messages.create.call_args_list[0].kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "última mensagem da conversa foi enviada pelo Caio" in user_content
    assert "continuação natural" in user_content
    assert "última mensagem do cliente" not in user_content


@pytest.mark.asyncio
async def test_reactive_draft_uses_standard_instruction(db, mock_claude_api):
    """generate_drafts with proactive=False (default) uses standard instruction."""
    from app.services.draft_engine import generate_drafts

    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) "
        "VALUES (1, 'msg-1', 'inbound', 'Quanto custa?')"
    )
    await db.commit()

    await generate_drafts(1, 1)

    call_kwargs = mock_claude_api.messages.create.call_args_list[0].kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "última mensagem do cliente" in user_content
    assert "continuação natural" not in user_content
