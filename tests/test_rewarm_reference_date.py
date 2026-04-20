"""Testes da parametrização de reference_date em select_rewarm_candidates e no endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import *  # noqa: F401, F403

from app.services.rewarm_engine import REWARM_TOOL_NAME, select_rewarm_candidates


def _rewarm_resp(action="send", message="oi", reason="x"):
    mock = MagicMock()
    block = MagicMock()
    block.type = "tool_use"
    block.name = REWARM_TOOL_NAME
    block.input = {"action": action, "message": message, "reason": reason}
    mock.content = [block]
    return mock


async def _seed(db, phone, last_inbound_offset_days):
    cursor = await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, funnel_product, funnel_stage) "
        "VALUES (?, 'X', 'curso-cdo', 'handbook_sent')",
        (phone,),
    )
    conv_id = cursor.lastrowid
    await db.execute(
        f"INSERT INTO messages (conversation_id, direction, content, created_at) "
        f"VALUES (?, 'inbound', 'oi', datetime('now','-{last_inbound_offset_days} days'))",
        (conv_id,),
    )
    await db.commit()
    return conv_id


@pytest.mark.asyncio
async def test_select_without_reference_date_uses_yesterday(db):
    """Sem parâmetro: filtra por ontem (comportamento original)."""
    await _seed(db, "5511", last_inbound_offset_days=1)
    await _seed(db, "5522", last_inbound_offset_days=3)

    rows = await select_rewarm_candidates(db)
    phones = [r["phone_number"] for r in rows]
    assert "5511" in phones
    assert "5522" not in phones


@pytest.mark.asyncio
async def test_select_with_reference_date_three_days_ago(db):
    """Com reference_date=(3 dias atrás): só o lead que falou há 3 dias aparece."""
    from datetime import date, timedelta
    await _seed(db, "5511", last_inbound_offset_days=1)
    await _seed(db, "5522", last_inbound_offset_days=3)

    three_days_ago = (date.today() - timedelta(days=3)).isoformat()
    rows = await select_rewarm_candidates(db, reference_date=three_days_ago)
    phones = [r["phone_number"] for r in rows]
    assert "5522" in phones
    assert "5511" not in phones


@pytest.mark.asyncio
async def test_select_with_reference_date_no_match(db):
    """Reference_date com nenhum candidato: lista vazia."""
    await _seed(db, "5511", last_inbound_offset_days=1)
    rows = await select_rewarm_candidates(db, reference_date="2020-01-01")
    assert rows == []


# ---- endpoint ----

@pytest.mark.asyncio
async def test_preview_endpoint_uses_reference_date_from_body(client, db):
    from datetime import date, timedelta
    await _seed(db, "5533", last_inbound_offset_days=5)

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=_rewarm_resp(action="send", message="oi"))

    five_days_ago = (date.today() - timedelta(days=5)).isoformat()

    with patch("app.services.rewarm_engine.get_anthropic_client", return_value=mock_client):
        resp = await client.post("/rewarm/preview", json={"reference_date": five_days_ago})

    assert resp.status_code == 200
    body = resp.json()
    assert body["reference_date"] == five_days_ago
    assert len(body["items"]) == 1
    assert body["items"][0]["phone_number"] == "5533"


@pytest.mark.asyncio
async def test_preview_endpoint_rejects_malformed_date(client, db):
    resp = await client.post("/rewarm/preview", json={"reference_date": "nope"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_preview_endpoint_without_body_uses_default(client, db):
    """Body vazio ou body {} continua funcionando com default=ontem."""
    await _seed(db, "5544", last_inbound_offset_days=1)

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=_rewarm_resp(action="send", message="oi"))

    with patch("app.services.rewarm_engine.get_anthropic_client", return_value=mock_client):
        resp = await client.post("/rewarm/preview")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
