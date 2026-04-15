from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import *  # noqa: F401, F403

from app.services.rewarm_engine import (
    REWARM_SYSTEM_PROMPT,
    REWARM_TOOL_NAME,
    decide_rewarm_action,
)


def _make_rewarm_response(action="send", message="oi, como foi com o handbook?", reason="parou após handbook"):
    mock = MagicMock()
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = REWARM_TOOL_NAME
    tool_block.input = {"action": action, "message": message, "reason": reason}
    mock.content = [tool_block]
    return mock


async def _seed_basic_conversation(db, history=None):
    cursor = await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, funnel_product, funnel_stage) "
        "VALUES ('5511999', 'Joao', 'curso-cdo', 'handbook_sent')"
    )
    conv_id = cursor.lastrowid
    history = history or [
        ("inbound", "oi, quero saber do curso"),
        ("outbound", "Oi Joao! Te mandei o handbook"),
    ]
    for direction, content in history:
        await db.execute(
            "INSERT INTO messages (conversation_id, direction, content) VALUES (?, ?, ?)",
            (conv_id, direction, content),
        )
    await db.commit()
    return conv_id


@pytest.mark.asyncio
async def test_decide_rewarm_action_returns_send(db):
    conv_id = await _seed_basic_conversation(db)
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        return_value=_make_rewarm_response(
            action="send",
            message="oi Joao, como foi com o handbook? alguma dúvida?",
            reason="cliente parou após o handbook",
        )
    )
    with patch("app.services.rewarm_engine.get_anthropic_client", return_value=mock_client):
        decision = await decide_rewarm_action(conv_id, db=db)
    assert decision["action"] == "send"
    assert decision["message"].strip() != ""
    assert decision["reason"].strip() != ""


@pytest.mark.asyncio
async def test_decide_rewarm_action_skips_when_customer_declined(db):
    conv_id = await _seed_basic_conversation(
        db,
        history=[
            ("inbound", "oi, quero saber do curso"),
            ("outbound", "te mando o handbook"),
            ("inbound", "não tenho interesse, pode parar"),
        ],
    )
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        return_value=_make_rewarm_response(
            action="skip", message="", reason="cliente pediu para parar explicitamente"
        )
    )
    with patch("app.services.rewarm_engine.get_anthropic_client", return_value=mock_client):
        decision = await decide_rewarm_action(conv_id, db=db)
    assert decision["action"] == "skip"
    assert "parar" in decision["reason"].lower()


@pytest.mark.asyncio
async def test_decide_rewarm_action_skips_when_customer_bought_elsewhere(db):
    conv_id = await _seed_basic_conversation(db)
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        return_value=_make_rewarm_response(
            action="skip", message="", reason="cliente disse que comprou em outro lugar"
        )
    )
    with patch("app.services.rewarm_engine.get_anthropic_client", return_value=mock_client):
        decision = await decide_rewarm_action(conv_id, db=db)
    assert decision["action"] == "skip"
    assert "outro lugar" in decision["reason"].lower()


@pytest.mark.asyncio
async def test_rewarm_prompt_includes_conversation_history_and_tone_instruction(db):
    conv_id = await _seed_basic_conversation(
        db,
        history=[
            ("inbound", "e aí tranquilo? curti o curso"),
            ("outbound", "opa! bora 🚀 te mando o handbook aí"),
        ],
    )
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=_make_rewarm_response())
    with patch("app.services.rewarm_engine.get_anthropic_client", return_value=mock_client):
        await decide_rewarm_action(conv_id, db=db)

    call_kwargs = mock_client.messages.create.await_args.kwargs
    system = call_kwargs["system"]
    user_content = call_kwargs["messages"][0]["content"]

    # System prompt deve estar lá
    assert "reesquentamento" in system.lower() or "reesquenta" in system.lower()
    assert "tom" in system.lower() or "espelh" in system.lower()
    assert "skip" in system.lower()

    # User content deve incluir histórico real
    assert "e aí tranquilo? curti o curso" in user_content
    assert "bora 🚀 te mando o handbook aí" in user_content

    # Tool correto
    tools = call_kwargs["tools"]
    assert tools[0]["name"] == REWARM_TOOL_NAME


@pytest.mark.asyncio
async def test_decide_rewarm_action_handles_missing_conversation(db):
    mock_client = AsyncMock()
    with patch("app.services.rewarm_engine.get_anthropic_client", return_value=mock_client):
        decision = await decide_rewarm_action(99999, db=db)
    assert decision["action"] == "skip"
    assert "não encontrada" in decision["reason"].lower()
    # Should not have called Claude
    mock_client.messages.create.assert_not_called()


@pytest.mark.asyncio
async def test_decide_rewarm_action_recovers_from_empty_send_message(db):
    """Se o agente retorna send com message vazia, degrada para skip (defensive)."""
    conv_id = await _seed_basic_conversation(db)
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        return_value=_make_rewarm_response(action="send", message="", reason="teste")
    )
    with patch("app.services.rewarm_engine.get_anthropic_client", return_value=mock_client):
        decision = await decide_rewarm_action(conv_id, db=db)
    assert decision["action"] == "skip"
