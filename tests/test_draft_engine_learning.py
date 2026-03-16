import pytest
from unittest.mock import AsyncMock, patch

from app.services.draft_engine import generate_drafts
from tests.conftest import make_draft_tool_response


@pytest.mark.asyncio
async def test_situation_summary_included_in_prompt(db, mock_claude_api):
    """Situation summary aparece no prompt dos drafts."""
    await db.execute(
        "INSERT INTO conversations (phone_number, contact_name) VALUES ('5511999999999', 'Maria')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Quanto custa o curso?')"
    )
    await db.commit()

    await generate_drafts(1, 1)

    call_kwargs = mock_claude_api.messages.create.call_args_list[0].kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "## Situação atual" in user_content
    assert "Primeiro contato genérico." in user_content


@pytest.mark.asyncio
async def test_situation_summary_saved_in_drafts(db, mock_claude_api):
    """Situation summary é salvo na tabela de drafts."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.commit()

    await generate_drafts(1, 1)

    row = await db.execute("SELECT situation_summary FROM drafts WHERE conversation_id = 1 LIMIT 1")
    draft = await row.fetchone()
    assert draft["situation_summary"] == "Primeiro contato genérico."


@pytest.mark.asyncio
async def test_learned_rules_in_system_prompt(db):
    """Regras aprendidas aparecem no system prompt quando existem."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Quanto custa?')"
    )
    await db.execute(
        "INSERT INTO learned_rules (rule_text) VALUES ('Sempre qualificar antes de precificar.')"
    )
    await db.execute(
        "INSERT INTO learned_rules (rule_text) VALUES ('Objeção de preço: ancorar em custo por dia.')"
    )
    await db.commit()

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=make_draft_tool_response())

    with patch("app.services.prompt_builder.get_active_rules", new_callable=AsyncMock) as mock_rules, \
         patch("app.services.draft_engine.get_active_rules", new_callable=AsyncMock), \
         patch("app.services.claude_client.get_anthropic_client", return_value=mock_client):
        mock_rules.return_value = [
            {"id": 1, "rule_text": "Sempre qualificar antes de precificar."},
            {"id": 2, "rule_text": "Objeção de preço: ancorar em custo por dia."},
        ]

        await generate_drafts(1, 1)

        call_kwargs = mock_client.messages.create.call_args_list[0].kwargs
        system_blocks = call_kwargs["system"]
        system_text = " ".join(block["text"] for block in system_blocks)
        assert "## Regras aprendidas" in system_text
        assert "Sempre qualificar antes de precificar." in system_text
        assert "Objeção de preço: ancorar em custo por dia." in system_text


@pytest.mark.asyncio
async def test_smart_retrieval_used_for_fewshot(db):
    """Smart retrieval é usado quando retorna IDs."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Quanto custa?')"
    )
    await db.execute(
        "INSERT INTO edit_pairs (conversation_id, customer_message, original_draft, final_message, was_edited, situation_summary, strategic_annotation) VALUES (1, 'Quanto custa?', 'O CDO é R$2997', 'Me conta o que vc faz', 1, 'Primeiro contato, preço direto', 'IA jogou preço sem qualificar.')"
    )
    await db.commit()

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=make_draft_tool_response())

    with patch("app.services.prompt_builder.retrieve_similar", return_value=[1]) as mock_ret, \
         patch("app.services.draft_engine.retrieve_similar", return_value=[1]), \
         patch("app.services.claude_client.get_anthropic_client", return_value=mock_client), \
         patch("app.services.prompt_builder.get_active_rules", new_callable=AsyncMock, return_value=[]), \
         patch("app.services.draft_engine.get_active_rules", new_callable=AsyncMock, return_value=[]):

        await generate_drafts(1, 1)

        call_kwargs = mock_client.messages.create.call_args_list[0].kwargs
        user_content = call_kwargs["messages"][0]["content"]
        assert "correções estratégicas" in user_content
        assert "IA jogou preço sem qualificar." in user_content
        assert "Primeiro contato, preço direto" in user_content


@pytest.mark.asyncio
async def test_fallback_to_chronological_when_retrieval_fails(db, mock_claude_api):
    """Fallback para cronológico quando smart retrieval falha."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    for i in range(5):
        await db.execute(
            "INSERT INTO edit_pairs (conversation_id, customer_message, original_draft, final_message, was_edited) VALUES (1, ?, ?, ?, 1)",
            (f"pergunta {i}", f"draft {i}", f"final {i}"),
        )
    await db.commit()

    # retrieve_similar is already mocked to return [] in conftest
    await generate_drafts(1, 1)

    call_kwargs = mock_claude_api.messages.create.call_args_list[0].kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "Exemplos de como o Caio responde" in user_content
    assert "pergunta 0" in user_content
