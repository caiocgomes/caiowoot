import json
import pytest
from unittest.mock import AsyncMock, patch

from app.services.draft_engine import generate_draft


@pytest.mark.asyncio
async def test_generate_draft_calls_claude(db, mock_claude_api):
    """13.1: generate_draft monta prompt e chama Claude API."""
    # Insert conversation and message
    await db.execute(
        "INSERT INTO conversations (phone_number, contact_name) VALUES ('5511999999999', 'Maria')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Quero saber sobre os cursos')"
    )
    await db.commit()

    await generate_draft(1, 1)

    # Verify Claude was called
    mock_claude_api.messages.create.assert_called_once()
    call_kwargs = mock_claude_api.messages.create.call_args.kwargs
    assert "system" in call_kwargs
    assert "messages" in call_kwargs


@pytest.mark.asyncio
async def test_draft_parsed_as_json(db, mock_claude_api):
    """13.2: resposta da Claude é parseada como JSON com draft e justification."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.commit()

    await generate_draft(1, 1)

    row = await db.execute("SELECT * FROM drafts WHERE conversation_id = 1")
    draft = await row.fetchone()
    assert draft is not None
    assert draft["draft_text"] == "Oi! Tudo bem? Qual seu interesse em IA?"
    assert draft["justification"] == "Primeira mensagem, qualificando o lead."


@pytest.mark.asyncio
async def test_draft_persisted_with_pending_status(db, mock_claude_api):
    """13.3: draft é persistido com status 'pending'."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.commit()

    await generate_draft(1, 1)

    row = await db.execute("SELECT * FROM drafts WHERE conversation_id = 1")
    draft = await row.fetchone()
    assert draft["status"] == "pending"
    assert draft["trigger_message_id"] == 1


@pytest.mark.asyncio
async def test_fewshot_included_when_edit_pairs_exist(db, mock_claude_api):
    """13.4: few-shot examples incluídos quando existem edit_pairs."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Quanto custa?')"
    )
    # Add edit pairs
    for i in range(5):
        await db.execute(
            "INSERT INTO edit_pairs (conversation_id, customer_message, original_draft, final_message, was_edited) VALUES (1, ?, ?, ?, 1)",
            (f"pergunta {i}", f"draft {i}", f"final {i}"),
        )
    await db.commit()

    await generate_draft(1, 1)

    call_kwargs = mock_claude_api.messages.create.call_args.kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "Exemplos de como o Caio responde" in user_content
    assert "pergunta 0" in user_content


@pytest.mark.asyncio
async def test_cold_start_no_fewshot(db, mock_claude_api):
    """13.5: sem edit_pairs, prompt sem few-shot."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.commit()

    await generate_draft(1, 1)

    call_kwargs = mock_claude_api.messages.create.call_args.kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "Exemplos de como o Caio responde" not in user_content


@pytest.mark.asyncio
async def test_max_10_fewshot_examples(db, mock_claude_api):
    """13.6: máximo de 10 few-shot examples."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    for i in range(20):
        await db.execute(
            "INSERT INTO edit_pairs (conversation_id, customer_message, original_draft, final_message, was_edited) VALUES (1, ?, ?, ?, 1)",
            (f"pergunta {i}", f"draft {i}", f"final {i}"),
        )
    await db.commit()

    await generate_draft(1, 1)

    call_kwargs = mock_claude_api.messages.create.call_args.kwargs
    user_content = call_kwargs["messages"][0]["content"]
    # Should have at most 10 examples in the prompt
    assert "Exemplos de como o Caio responde" in user_content
    # Count the number of "Cliente disse:" occurrences (one per example)
    example_count = user_content.count('Cliente disse:')
    assert example_count == 10
