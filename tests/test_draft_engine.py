import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

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
async def test_first_name_included_in_prompt(db, mock_claude_api):
    """Primeiro nome do cliente aparece no prompt quando contact_name existe."""
    await db.execute(
        "INSERT INTO conversations (phone_number, contact_name) VALUES ('5511999999999', 'Maria Silva')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.commit()

    await generate_drafts(1, 1)

    call_kwargs = mock_claude_api.messages.create.call_args_list[0].kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "## Cliente" in user_content
    assert "Nome: Maria" in user_content
    # Não deve incluir sobrenome
    assert "Maria Silva" not in user_content


@pytest.mark.asyncio
async def test_no_name_section_when_contact_name_empty(db, mock_claude_api):
    """Sem contact_name, prompt não contém seção de nome."""
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
    assert "## Cliente" not in user_content


@pytest.mark.asyncio
async def test_generate_drafts_handles_claude_error(db):
    """When Claude API fails, fallback text should be saved as draft."""
    await db.execute(
        "INSERT INTO conversations (phone_number, contact_name) VALUES ('5511999999999', 'Maria')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Quero saber sobre os cursos')"
    )
    await db.commit()

    # Mock Claude to raise an exception on every call
    with patch("app.services.claude_client.get_anthropic_client") as mock_anthropic:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=Exception("API rate limit exceeded")
        )
        mock_anthropic.return_value = mock_client

        await generate_drafts(1, 1)

    # Verify 3 drafts were saved with fallback error text
    row = await db.execute("SELECT COUNT(*) as cnt FROM drafts WHERE conversation_id = 1")
    result = await row.fetchone()
    assert result["cnt"] == 3

    row = await db.execute("SELECT draft_text, justification FROM drafts WHERE conversation_id = 1 ORDER BY variation_index")
    drafts = await row.fetchall()
    for draft in drafts:
        assert draft["draft_text"] == "(Erro ao gerar esta variação)"
        assert "API rate limit exceeded" in draft["justification"]


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


# ───────────────────────── Contratos novos (refactor-velocidade): eventos WS ─────────────────────────
# generate_drafts deve emitir 'drafts_generating' antes de qualquer chamada LLM
# e 'drafts_error' quando a geração levanta exceção.

import app.websocket_manager as ws_module  # noqa: E402  (atributo manager é patchado pelo conftest)


def _broadcast_payloads(broadcast_mock, event_type):
    """Extrai das chamadas ao mock de broadcast os payloads (dicts) do tipo pedido."""
    payloads = []
    for call in broadcast_mock.call_args_list:
        for arg in list(call.args) + list(call.kwargs.values()):
            if isinstance(arg, dict) and arg.get("type") == event_type:
                payloads.append(arg)
    return payloads


@pytest.mark.asyncio
async def test_generate_drafts_emits_drafts_generating_before_llm(db):
    """generate_drafts emite 'drafts_generating' (draft_index=None) ANTES da primeira
    chamada LLM de geração."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) "
        "VALUES (1, 'msg-1', 'inbound', 'Quero saber sobre os cursos')"
    )
    await db.commit()

    ordem = []
    broadcast_mock = ws_module.manager.broadcast
    broadcast_mock.reset_mock()

    async def registra_broadcast(*args, **kwargs):
        for arg in list(args) + list(kwargs.values()):
            if isinstance(arg, dict) and arg.get("type") == "drafts_generating":
                ordem.append(("drafts_generating", arg))

    broadcast_mock.side_effect = registra_broadcast

    async def registra_llm(*args, **kwargs):
        ordem.append(("llm_call", None))
        return ("Rascunho gerado", "Justificativa", None)

    with patch(
        "app.services.draft_engine._call_haiku",
        new_callable=AsyncMock,
        side_effect=registra_llm,
    ):
        await generate_drafts(1, 1)

    generating = [i for i, (tipo, _) in enumerate(ordem) if tipo == "drafts_generating"]
    llm_calls = [i for i, (tipo, _) in enumerate(ordem) if tipo == "llm_call"]

    assert generating, "evento 'drafts_generating' não foi emitido pelo generate_drafts"
    assert llm_calls, "mock de _call_haiku não foi chamado"
    assert generating[0] < llm_calls[0], (
        "'drafts_generating' deve ser emitido antes da primeira chamada LLM"
    )

    payload = ordem[generating[0]][1]
    assert payload["conversation_id"] == 1
    assert payload["trigger_message_id"] == 1
    assert "draft_index" in payload and payload["draft_index"] is None


@pytest.mark.asyncio
async def test_generate_drafts_emits_drafts_error_on_exception(db):
    """Quando a geração levanta exceção, generate_drafts emite 'drafts_error'
    com conversation_id, trigger_message_id e error (string)."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) "
        "VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.commit()

    broadcast_mock = ws_module.manager.broadcast
    broadcast_mock.reset_mock()

    with patch(
        "app.services.draft_engine._build_prompt_parts",
        new_callable=AsyncMock,
        side_effect=RuntimeError("falha simulada na geração"),
    ):
        await generate_drafts(1, 1)

    erros = _broadcast_payloads(broadcast_mock, "drafts_error")
    assert erros, "evento 'drafts_error' não foi emitido após exceção na geração"
    payload = erros[-1]
    assert payload["conversation_id"] == 1
    assert payload["trigger_message_id"] == 1
    assert isinstance(payload.get("error"), str) and payload["error"], (
        "o campo 'error' deve ser uma string não-vazia"
    )
