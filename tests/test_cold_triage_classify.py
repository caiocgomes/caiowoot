from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import *  # noqa: F401, F403

from app.services.cold_triage import (
    COLD_CLASSIFY_TOOL_NAME,
    classify_conversation,
)


def _classify_resp(classification, confidence, stage_reached="link_sent", quote="", reasoning="x"):
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


async def _seed_conv(db, phone, messages):
    cursor = await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, funnel_product, funnel_stage) "
        "VALUES (?, 'X', 'curso-cdo', 'link_sent')",
        (phone,),
    )
    conv_id = cursor.lastrowid
    for direction, content, created_at in messages:
        await db.execute(
            "INSERT INTO messages (conversation_id, direction, content, created_at) VALUES (?, ?, ?, ?)",
            (conv_id, direction, content, created_at),
        )
    await db.commit()
    return conv_id


@pytest.mark.asyncio
async def test_classify_returns_timing_for_volta_mes_que_vem(db):
    conv_id = await _seed_conv(db, "5511", [
        ("outbound", "aqui está o link", "2026-02-15 10:00:00"),
        ("inbound", "valeu, mês que vem eu volto pra fechar", "2026-02-15 10:05:00"),
    ])

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=_classify_resp(
        "objecao_timing", "high", "link_sent", "mês que vem eu volto", "lead adiou"
    ))
    with patch("app.services.cold_triage.get_anthropic_client", return_value=mock_client):
        result = await classify_conversation(conv_id, db=db)

    assert result["classification"] == "objecao_timing"
    assert result["confidence"] == "high"
    assert result["stage_reached"] == "link_sent"
    assert "mês que vem" in result["quote_from_lead"]


@pytest.mark.asyncio
async def test_classify_on_haiku_exception_returns_unclassifiable(db):
    conv_id = await _seed_conv(db, "5522", [
        ("outbound", "oi", "2026-02-15 10:00:00"),
    ])
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=RuntimeError("timeout"))
    with patch("app.services.cold_triage.get_anthropic_client", return_value=mock_client):
        result = await classify_conversation(conv_id, db=db)

    assert result["classification"] == "nao_classificavel"
    assert result["confidence"] == "low"
    assert result["stage_reached"] == "nunca_qualificou"


@pytest.mark.asyncio
async def test_classify_invalid_fields_are_normalized(db):
    conv_id = await _seed_conv(db, "5533", [("outbound", "oi", "2026-02-15 10:00:00")])
    mock_client = AsyncMock()
    block = MagicMock()
    block.type = "tool_use"
    block.name = COLD_CLASSIFY_TOOL_NAME
    block.input = {
        "classification": "qualquercoisa",
        "confidence": "nao_sei",
        "stage_reached": "stage_inventado",
        "quote_from_lead": "",
        "reasoning": "",
    }
    resp = MagicMock()
    resp.content = [block]
    mock_client.messages.create = AsyncMock(return_value=resp)
    with patch("app.services.cold_triage.get_anthropic_client", return_value=mock_client):
        result = await classify_conversation(conv_id, db=db)

    assert result["classification"] == "nao_classificavel"
    assert result["confidence"] == "low"
    assert result["stage_reached"] == "nunca_qualificou"


@pytest.mark.asyncio
async def test_classify_no_tool_use_fallback(db):
    conv_id = await _seed_conv(db, "5544", [("outbound", "oi", "2026-02-15 10:00:00")])
    mock_client = AsyncMock()
    resp = MagicMock()
    resp.content = []  # nenhum tool_use
    mock_client.messages.create = AsyncMock(return_value=resp)
    with patch("app.services.cold_triage.get_anthropic_client", return_value=mock_client):
        result = await classify_conversation(conv_id, db=db)

    assert result["classification"] == "nao_classificavel"
    assert result["stage_reached"] == "nunca_qualificou"
