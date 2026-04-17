"""Testes da proteção contra disparo para leads que já compraram."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import *  # noqa: F401, F403

from app.services.cold_triage import (
    COLD_CLASSIFY_TOOL_NAME,
    COLD_COMPOSE_TOOL_NAME,
    run_preview,
)


def _classify_resp(classification, confidence="high", stage_reached="link_sent", quote="paguei aqui", reasoning="x"):
    mock = MagicMock()
    block = MagicMock()
    block.type = "tool_use"
    block.name = COLD_CLASSIFY_TOOL_NAME
    block.input = {
        "classification": classification,
        "confidence": confidence,
        "stage_reached": stage_reached,
        "quote_from_lead": quote,
        "reasoning": reasoning,
    }
    mock.content = [block]
    return mock


def _compose_resp(message):
    mock = MagicMock()
    block = MagicMock()
    block.type = "tool_use"
    block.name = COLD_COMPOSE_TOOL_NAME
    block.input = {"message": message}
    mock.content = [block]
    return mock


async def _seed_cold_conv(db, phone):
    cursor = await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, funnel_product, funnel_stage) "
        "VALUES (?, 'Ana', 'curso-cdo', 'qualifying')",
        (phone,),
    )
    conv_id = cursor.lastrowid
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, created_at) "
        "VALUES (?, 'inbound', 'paguei aqui e ja acessei a plataforma', datetime('now','-40 days'))",
        (conv_id,),
    )
    await db.commit()
    return conv_id


@pytest.mark.asyncio
async def test_ja_comprou_lead_marked_do_not_contact(db):
    """Lead classificado como ja_comprou: skip + cold_do_not_contact=1 na conversa."""
    conv_id = await _seed_cold_conv(db, "5511")

    mock_client = AsyncMock()

    def dispatcher(*args, **kwargs):
        tools = kwargs.get("tools") or []
        tool_name = tools[0]["name"] if tools else ""
        if tool_name == COLD_CLASSIFY_TOOL_NAME:
            return _classify_resp("ja_comprou", "high", "link_sent", "paguei aqui")
        return _compose_resp("nao usado")

    mock_client.messages.create = AsyncMock(side_effect=dispatcher)

    with patch("app.services.cold_triage.get_anthropic_client", return_value=mock_client):
        items = await run_preview(db=db)

    # Aparece no preview com action=skip
    assert len(items) == 1
    assert items[0]["action"] == "skip"
    assert items[0]["classification"] == "ja_comprou"

    # cold_do_not_contact foi marcado na conversa
    cur = await db.execute(
        "SELECT cold_do_not_contact FROM conversations WHERE id = ?",
        (conv_id,),
    )
    row = await cur.fetchone()
    assert row["cold_do_not_contact"] == 1


@pytest.mark.asyncio
async def test_ja_comprou_lead_never_returns_to_pool_after_marked(db):
    """Depois de marcado do-not-contact, o lead sai do pool de candidatos."""
    conv_id = await _seed_cold_conv(db, "5522")

    mock_client = AsyncMock()

    def dispatcher(*args, **kwargs):
        tools = kwargs.get("tools") or []
        tool_name = tools[0]["name"] if tools else ""
        if tool_name == COLD_CLASSIFY_TOOL_NAME:
            return _classify_resp("ja_comprou", "high", "link_sent", "paguei")
        return _compose_resp("nao usado")

    mock_client.messages.create = AsyncMock(side_effect=dispatcher)

    with patch("app.services.cold_triage.get_anthropic_client", return_value=mock_client):
        await run_preview(db=db)

    # Segundo preview: não inclui o lead
    from app.services.cold_triage import select_cold_candidates
    candidates = await select_cold_candidates(db)
    assert not any(c["id"] == conv_id for c in candidates)


@pytest.mark.asyncio
async def test_non_purchase_leads_not_marked_do_not_contact(db):
    """Lead classificado como objecao_preco não dispara cold_do_not_contact."""
    conv_id = await _seed_cold_conv(db, "5533")

    mock_client = AsyncMock()

    def dispatcher(*args, **kwargs):
        tools = kwargs.get("tools") or []
        tool_name = tools[0]["name"] if tools else ""
        if tool_name == COLD_CLASSIFY_TOOL_NAME:
            return _classify_resp("objecao_preco", "high", "link_sent", "ta salgado")
        return _compose_resp("oi")

    mock_client.messages.create = AsyncMock(side_effect=dispatcher)

    with patch("app.services.cold_triage.get_anthropic_client", return_value=mock_client):
        await run_preview(db=db)

    cur = await db.execute(
        "SELECT cold_do_not_contact FROM conversations WHERE id = ?",
        (conv_id,),
    )
    row = await cur.fetchone()
    assert row["cold_do_not_contact"] == 0
