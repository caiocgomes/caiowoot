import json
import pytest
from unittest.mock import AsyncMock, patch

from app.services.draft_engine import generate_drafts


@pytest.mark.asyncio
async def test_generate_drafts_calls_claude_3_times(db, mock_claude_api):
    """15.1: generate_drafts gera 3 variações em paralelo com approaches diferentes."""
    await db.execute(
        "INSERT INTO conversations (phone_number, contact_name) VALUES ('5511999999999', 'Maria')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Quero saber sobre os cursos')"
    )
    await db.commit()

    await generate_drafts(1, 1)

    # Verify Claude was called 3 times (one per variation)
    assert mock_claude_api.messages.create.call_count == 3

    # Verify 3 drafts were saved
    row = await db.execute("SELECT COUNT(*) as cnt FROM drafts WHERE conversation_id = 1")
    result = await row.fetchone()
    assert result["cnt"] == 3

    # Verify they share the same draft_group_id
    row = await db.execute("SELECT DISTINCT draft_group_id FROM drafts WHERE conversation_id = 1")
    groups = await row.fetchall()
    assert len(groups) == 1

    # Verify variation_index 0, 1, 2
    row = await db.execute("SELECT variation_index FROM drafts ORDER BY variation_index")
    indices = [r["variation_index"] for r in await row.fetchall()]
    assert indices == [0, 1, 2]


@pytest.mark.asyncio
async def test_operator_instruction_included_in_prompt(db, mock_claude_api):
    """15.2: operator_instruction é incluída no prompt quando fornecida."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.commit()

    await generate_drafts(1, 1, operator_instruction="foca no preço")

    call_kwargs = mock_claude_api.messages.create.call_args_list[0].kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "foca no preço" in user_content

    # Verify operator_instruction saved in drafts
    row = await db.execute("SELECT operator_instruction FROM drafts WHERE conversation_id = 1 LIMIT 1")
    draft = await row.fetchone()
    assert draft["operator_instruction"] == "foca no preço"


@pytest.mark.asyncio
async def test_prompt_hash_saved_in_draft(db, mock_claude_api):
    """15.3: prompt_hash é salvo e referenciado no draft."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.commit()

    await generate_drafts(1, 1)

    row = await db.execute("SELECT prompt_hash FROM drafts WHERE conversation_id = 1 LIMIT 1")
    draft = await row.fetchone()
    assert draft["prompt_hash"] == "testhash123"


@pytest.mark.asyncio
async def test_drafts_persisted_with_pending_status(db, mock_claude_api):
    """Drafts são persistidos com status 'pending'."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.commit()

    await generate_drafts(1, 1)

    row = await db.execute("SELECT status FROM drafts WHERE conversation_id = 1")
    drafts = await row.fetchall()
    assert all(d["status"] == "pending" for d in drafts)


@pytest.mark.asyncio
async def test_fewshot_included_when_edit_pairs_exist(db, mock_claude_api):
    """Few-shot examples incluídos quando existem edit_pairs."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Quanto custa?')"
    )
    for i in range(5):
        await db.execute(
            "INSERT INTO edit_pairs (conversation_id, customer_message, original_draft, final_message, was_edited) VALUES (1, ?, ?, ?, 1)",
            (f"pergunta {i}", f"draft {i}", f"final {i}"),
        )
    await db.commit()

    await generate_drafts(1, 1)

    call_kwargs = mock_claude_api.messages.create.call_args_list[0].kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "Exemplos de como o Caio responde" in user_content
    assert "pergunta 0" in user_content


@pytest.mark.asyncio
async def test_cold_start_no_fewshot(db, mock_claude_api):
    """Sem edit_pairs, prompt sem few-shot."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.commit()

    await generate_drafts(1, 1)

    call_kwargs = mock_claude_api.messages.create.call_args_list[0].kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "Exemplos de como o Caio responde" not in user_content


@pytest.mark.asyncio
async def test_max_10_fewshot_examples(db, mock_claude_api):
    """Máximo de 10 few-shot examples."""
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

    await generate_drafts(1, 1)

    call_kwargs = mock_claude_api.messages.create.call_args_list[0].kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "Exemplos de como o Caio responde" in user_content
    example_count = user_content.count('Cliente disse:')
    assert example_count == 10
