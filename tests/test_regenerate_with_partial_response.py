"""Testes da detecção de outbounds entre trigger_message e o regenerate,
e da instrução complementar quando há resposta parcial em andamento."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import *  # noqa: F401, F403

from app.services.prompt_builder import (
    COMPLEMENTARY_FINAL_INSTRUCTION,
    _load_post_trigger_outbounds,
    build_prompt_parts,
)


async def _seed_conv(db, phone="5511"):
    cursor = await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, funnel_product, funnel_stage) "
        "VALUES (?, 'Ana', 'curso-cdo', 'qualifying')",
        (phone,),
    )
    return cursor.lastrowid


async def _seed_message(db, conv_id, direction, content, created_at=None, sent_by=None):
    if created_at is None:
        await db.execute(
            "INSERT INTO messages (conversation_id, direction, content, sent_by) VALUES (?, ?, ?, ?)",
            (conv_id, direction, content, sent_by),
        )
    else:
        await db.execute(
            "INSERT INTO messages (conversation_id, direction, content, created_at, sent_by) VALUES (?, ?, ?, ?, ?)",
            (conv_id, direction, content, created_at, sent_by),
        )
    cur = await db.execute("SELECT last_insert_rowid() AS id")
    row = await cur.fetchone()
    await db.commit()
    return row["id"]


# ───────────────────────── _load_post_trigger_outbounds ─────────────────────────


@pytest.mark.asyncio
async def test_load_post_trigger_outbounds_none_trigger_returns_empty(db):
    conv_id = await _seed_conv(db, "5501")
    await _seed_message(db, conv_id, "inbound", "oi")
    result = await _load_post_trigger_outbounds(db, conv_id, None)
    assert result == []


@pytest.mark.asyncio
async def test_load_post_trigger_outbounds_no_outbounds_returns_empty(db):
    conv_id = await _seed_conv(db, "5502")
    inbound_id = await _seed_message(db, conv_id, "inbound", "qual a ementa?")
    result = await _load_post_trigger_outbounds(db, conv_id, inbound_id)
    assert result == []


@pytest.mark.asyncio
async def test_load_post_trigger_outbounds_one_outbound_returned(db):
    conv_id = await _seed_conv(db, "5503")
    inbound_id = await _seed_message(db, conv_id, "inbound", "qual a ementa?")
    await _seed_message(db, conv_id, "outbound", "a ementa é X Y Z", sent_by="caio")
    result = await _load_post_trigger_outbounds(db, conv_id, inbound_id)
    assert len(result) == 1
    assert result[0]["content"] == "a ementa é X Y Z"
    assert result[0]["sent_by"] == "caio"


@pytest.mark.asyncio
async def test_load_post_trigger_outbounds_chronological_order(db):
    conv_id = await _seed_conv(db, "5504")
    inbound_id = await _seed_message(db, conv_id, "inbound", "oi")
    await _seed_message(db, conv_id, "outbound", "primeira", sent_by="caio")
    await _seed_message(db, conv_id, "outbound", "segunda", sent_by="caio")
    await _seed_message(db, conv_id, "outbound", "terceira", sent_by="caio")
    result = await _load_post_trigger_outbounds(db, conv_id, inbound_id)
    assert [m["content"] for m in result] == ["primeira", "segunda", "terceira"]


@pytest.mark.asyncio
async def test_load_post_trigger_outbounds_ignores_inbound_noise(db):
    conv_id = await _seed_conv(db, "5505")
    inbound_id = await _seed_message(db, conv_id, "inbound", "oi")
    await _seed_message(db, conv_id, "outbound", "resp 1", sent_by="caio")
    # inbound intermediária (cliente respondeu): não deve aparecer
    await _seed_message(db, conv_id, "inbound", "ok entendi")
    await _seed_message(db, conv_id, "outbound", "resp 2", sent_by="caio")
    result = await _load_post_trigger_outbounds(db, conv_id, inbound_id)
    assert [m["content"] for m in result] == ["resp 1", "resp 2"]


# ───────────────────────── build_prompt_parts ─────────────────────────


@pytest.mark.asyncio
async def test_build_prompt_parts_without_trigger_id_preserves_original_behavior(db):
    """Legacy: call sem trigger_message_id, user_content não muda."""
    conv_id = await _seed_conv(db, "5511")
    await _seed_message(db, conv_id, "inbound", "qual a ementa do curso?")
    await _seed_message(db, conv_id, "outbound", "a ementa é ...", sent_by="caio")

    user_content, _, _, _ = await build_prompt_parts(
        db, conv_id, trigger_message_id=None
    )
    assert "Respostas já enviadas neste turno" not in user_content
    assert "Gere o draft de resposta para a última mensagem do cliente." in user_content


@pytest.mark.asyncio
async def test_build_prompt_parts_with_trigger_but_no_outbound_preserves_original(db):
    """Trigger dado mas nenhuma outbound posterior: comportamento original."""
    conv_id = await _seed_conv(db, "5512")
    inbound_id = await _seed_message(db, conv_id, "inbound", "qual a ementa?")

    user_content, _, _, _ = await build_prompt_parts(
        db, conv_id, trigger_message_id=inbound_id
    )
    assert "Respostas já enviadas neste turno" not in user_content
    assert "Gere o draft de resposta para a última mensagem do cliente." in user_content


@pytest.mark.asyncio
async def test_build_prompt_parts_with_one_post_trigger_outbound_adds_section(db):
    """Com uma outbound depois do trigger: seção aparece e instrução é reescrita."""
    conv_id = await _seed_conv(db, "5513")
    inbound_id = await _seed_message(db, conv_id, "inbound", "qual a ementa? quanto custa?")
    await _seed_message(db, conv_id, "outbound", "a ementa cobre A, B e C", sent_by="caio")

    user_content, _, _, _ = await build_prompt_parts(
        db, conv_id, trigger_message_id=inbound_id
    )
    assert "Respostas já enviadas neste turno" in user_content
    assert "a ementa cobre A, B e C" in user_content
    assert COMPLEMENTARY_FINAL_INSTRUCTION in user_content
    assert "Gere o draft de resposta para a última mensagem do cliente." not in user_content


@pytest.mark.asyncio
async def test_build_prompt_parts_with_multiple_post_trigger_outbounds(db):
    """Múltiplas outbounds: todas listadas em ordem."""
    conv_id = await _seed_conv(db, "5514")
    inbound_id = await _seed_message(db, conv_id, "inbound", "me fala mais")
    await _seed_message(db, conv_id, "outbound", "primeira", sent_by="caio")
    await _seed_message(db, conv_id, "outbound", "segunda", sent_by="caio")
    await _seed_message(db, conv_id, "outbound", "terceira", sent_by="caio")

    user_content, _, _, _ = await build_prompt_parts(
        db, conv_id, trigger_message_id=inbound_id
    )

    # Seção presente
    assert "Respostas já enviadas neste turno" in user_content
    # Ordem cronológica preservada
    idx_first = user_content.index("primeira")
    idx_second = user_content.index("segunda")
    idx_third = user_content.index("terceira")
    assert idx_first < idx_second < idx_third
    assert COMPLEMENTARY_FINAL_INSTRUCTION in user_content


@pytest.mark.asyncio
async def test_build_prompt_parts_proactive_ignores_post_trigger_section(db):
    """proactive=True: instrução proactive continua, NUNCA adiciona seção nova."""
    conv_id = await _seed_conv(db, "5515")
    inbound_id = await _seed_message(db, conv_id, "inbound", "oi")
    await _seed_message(db, conv_id, "outbound", "tudo bem?", sent_by="caio")

    user_content, _, _, _ = await build_prompt_parts(
        db, conv_id, trigger_message_id=inbound_id, proactive=True, operator_name="Caio"
    )
    assert "Respostas já enviadas neste turno" not in user_content
    assert COMPLEMENTARY_FINAL_INSTRUCTION not in user_content
    assert "mensagem de continuação natural" in user_content
