"""Tests for draft engine reading prompts from DB and injecting operator profiles."""
import os
import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio
import aiosqlite

import app.database as db_module


class NonClosingConnection:
    def __init__(self, conn):
        self._conn = conn
    async def close(self):
        pass
    def __getattr__(self, name):
        return getattr(self._conn, name)


@pytest_asyncio.fixture
async def db():
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    await conn.executescript(db_module.SCHEMA)
    await conn.commit()

    wrapper = NonClosingConnection(conn)

    async def mock_get_db():
        return wrapper

    with patch("app.services.draft_engine.get_db", mock_get_db), \
         patch("app.services.learned_rules.get_db", mock_get_db), \
         patch("app.services.prompt_config.get_db", mock_get_db), \
         patch("app.services.operator_profile.get_db", mock_get_db), \
         patch("app.services.prompt_builder.generate_situation_summary", new_callable=AsyncMock, return_value="Primeiro contato."), \
         patch("app.services.draft_engine.generate_situation_summary", new_callable=AsyncMock, return_value="Primeiro contato."), \
         patch("app.services.prompt_builder.retrieve_similar", return_value=[]), \
         patch("app.services.draft_engine.retrieve_similar", return_value=[]), \
         patch("app.services.prompt_builder.get_active_rules", new_callable=AsyncMock, return_value=[]), \
         patch("app.services.draft_engine.get_active_rules", new_callable=AsyncMock, return_value=[]), \
         patch("app.websocket_manager.manager") as mock_ws, \
         patch("app.services.draft_engine.save_prompt", return_value="hash123"):
        mock_ws.broadcast = AsyncMock()
        yield conn

    await conn.close()


async def _setup_conversation(db, phone="5511999999999", name="Maria", text="Oi, quero saber dos cursos"):
    cursor = await db.execute(
        "INSERT INTO conversations (phone_number, contact_name) VALUES (?, ?)",
        (phone, name),
    )
    conv_id = cursor.lastrowid
    cursor = await db.execute(
        "INSERT INTO messages (conversation_id, direction, content) VALUES (?, 'inbound', ?)",
        (conv_id, text),
    )
    msg_id = cursor.lastrowid
    await db.commit()
    return conv_id, msg_id


@pytest.mark.asyncio
async def test_draft_engine_reads_prompts_from_db(db):
    """When prompts are customized in DB, draft engine should use them instead of hardcoded defaults."""
    from app.services.prompt_config import update_prompts
    from app.services.draft_engine import _build_system_prompt

    await update_prompts({"postura": "Postura customizada pelo admin"})

    system_prompt = await _build_system_prompt()
    assert "Postura customizada pelo admin" in system_prompt
    assert "vendedor consultivo" not in system_prompt  # default postura replaced


@pytest.mark.asyncio
async def test_draft_engine_uses_defaults_when_no_db_config(db):
    """When no custom prompts in DB, draft engine should use hardcoded defaults."""
    from app.services.draft_engine import _build_system_prompt

    system_prompt = await _build_system_prompt()
    assert "vendedor consultivo" in system_prompt  # default postura


@pytest.mark.asyncio
async def test_draft_engine_reads_approach_modifiers_from_db(db):
    """When approach modifiers are customized in DB, draft engine should use them."""
    from app.services.prompt_config import update_prompts
    from app.services.draft_engine import _get_approach_modifiers

    await update_prompts({"approach_direta": "Seja extremamente direto, sem rodeios."})

    modifiers = await _get_approach_modifiers()
    assert modifiers[0][1] == "Seja extremamente direto, sem rodeios."
    # Other modifiers should be defaults
    assert "consultiva" in modifiers[1][1].lower() or "qualificação" in modifiers[1][1].lower()


@pytest.mark.asyncio
async def test_draft_engine_injects_operator_profile(db):
    """When operator has a profile, it should be injected into the system prompt."""
    from app.services.operator_profile import upsert_profile
    from app.services.draft_engine import _build_system_prompt

    await upsert_profile("João", "João Silva", "Trabalho na equipe do Caio. Não sou o dono dos cursos.")

    system_prompt = await _build_system_prompt(operator_name="João")
    assert "João" in system_prompt
    assert "Trabalho na equipe do Caio" in system_prompt
    assert "Sobre quem está respondendo" in system_prompt


@pytest.mark.asyncio
async def test_draft_engine_no_profile_section_when_empty(db):
    """When operator has no profile, the 'Sobre quem está respondendo' section should be absent."""
    from app.services.draft_engine import _build_system_prompt

    system_prompt = await _build_system_prompt(operator_name="João")
    assert "Sobre quem está respondendo" not in system_prompt


@pytest.mark.asyncio
async def test_draft_engine_uses_display_name_in_opening(db):
    """Opening paragraph should use operator's display_name."""
    from app.services.operator_profile import upsert_profile
    from app.services.draft_engine import _build_system_prompt

    await upsert_profile("João", "João Silva", "Da equipe do Caio")

    system_prompt = await _build_system_prompt(operator_name="João")
    assert "João Silva" in system_prompt


@pytest.mark.asyncio
async def test_draft_engine_uses_operator_name_when_no_display_name(db):
    """When display_name is empty, use operator_name."""
    from app.services.operator_profile import upsert_profile
    from app.services.draft_engine import _build_system_prompt

    await upsert_profile("João", "", "Da equipe do Caio")

    system_prompt = await _build_system_prompt(operator_name="João")
    assert "João" in system_prompt


@pytest.mark.asyncio
async def test_draft_engine_default_name_when_no_operator(db):
    """When no operator is provided, fall back to 'Caio'."""
    from app.services.draft_engine import _build_system_prompt

    system_prompt = await _build_system_prompt(operator_name=None)
    assert "Caio" in system_prompt


@pytest.mark.asyncio
async def test_generate_drafts_accepts_operator_name(db):
    """generate_drafts should accept operator_name parameter."""
    conv_id, msg_id = await _setup_conversation(db)

    mock_response = AsyncMock()
    mock_response.content = [AsyncMock(text=json.dumps({
        "draft": "Oi! Como posso ajudar?",
        "justification": "Qualificando o lead.",
        "suggested_attachment": None,
    }))]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("app.services.claude_client.get_anthropic_client", return_value=mock_client):
        from app.services.draft_engine import generate_drafts
        await generate_drafts(conv_id, msg_id, operator_name="João")

    # Verify it was called (no exception thrown)
    assert mock_client.messages.create.call_count == 3


@pytest.mark.asyncio
async def test_proactive_uses_operator_name_in_instruction(db):
    """Proactive draft should use operator name instead of hardcoded 'Caio'."""
    conv_id, msg_id = await _setup_conversation(db)

    # Add an outbound message so proactive makes sense
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content) VALUES (?, 'outbound', ?)",
        (conv_id, "Tudo bem! Me conta mais."),
    )
    await db.commit()

    from app.services.draft_engine import _build_prompt_parts

    user_content, _, _, _ = await _build_prompt_parts(
        db, conv_id, proactive=True, operator_name="João"
    )
    assert "João" in user_content
