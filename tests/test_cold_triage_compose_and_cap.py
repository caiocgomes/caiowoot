from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import *  # noqa: F401, F403

from app.services.cold_triage import (
    COLD_COMPOSE_TOOL_NAME,
    compose_message,
    count_mentoria_offers_this_month,
)


def _compose_resp(message: str):
    mock = MagicMock()
    block = MagicMock()
    block.type = "tool_use"
    block.name = COLD_COMPOSE_TOOL_NAME
    block.input = {"message": message}
    mock.content = [block]
    return mock


async def _seed_conv(db, phone):
    cursor = await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, funnel_product, funnel_stage) "
        "VALUES (?, 'Ana', 'curso-cdo', 'link_sent')",
        (phone,),
    )
    conv_id = cursor.lastrowid
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, created_at) "
        "VALUES (?, 'inbound', 'mes que vem eu volto', '2026-02-15 10:00:00')",
        (conv_id,),
    )
    await db.commit()
    return conv_id


@pytest.mark.asyncio
async def test_compose_message_returns_haiku_text(db):
    conv_id = await _seed_conv(db, "5511")
    expected = "oi ana, caio aqui. lembrei que vc falou em fevereiro que voltaria esse mes."

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=_compose_resp(expected))

    with patch("app.services.cold_triage.get_anthropic_client", return_value=mock_client):
        result = await compose_message(
            conversation_id=conv_id,
            action="mentoria",
            classification="objecao_timing",
            quote_from_lead="mes que vem eu volto",
            contact_name="Ana",
            db=db,
        )
    assert result == expected


@pytest.mark.asyncio
async def test_compose_includes_quote_in_user_content(db):
    conv_id = await _seed_conv(db, "5522")
    captured_messages = {}

    async def fake_create(**kwargs):
        captured_messages["content"] = kwargs["messages"][0]["content"]
        return _compose_resp("msg")

    mock_client = AsyncMock()
    mock_client.messages.create = fake_create

    with patch("app.services.cold_triage.get_anthropic_client", return_value=mock_client):
        await compose_message(
            conversation_id=conv_id,
            action="mentoria",
            classification="objecao_timing",
            quote_from_lead="mes que vem eu volto",
            contact_name="Ana",
            db=db,
        )

    assert "mes que vem eu volto" in captured_messages["content"]


@pytest.mark.asyncio
async def test_compose_sanitizes_em_dash(db):
    conv_id = await _seed_conv(db, "5577")
    dirty = "oi ana — caio aqui. lembrei que vc falou — em fevereiro -- que voltava agora"
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=_compose_resp(dirty))
    with patch("app.services.cold_triage.get_anthropic_client", return_value=mock_client):
        result = await compose_message(
            conversation_id=conv_id,
            action="mentoria",
            classification="objecao_timing",
            quote_from_lead="vc falou em fevereiro",
            contact_name="Ana",
            db=db,
        )
    assert "—" not in result
    assert "–" not in result
    assert " -- " not in result


@pytest.mark.asyncio
async def test_compose_on_exception_returns_empty(db):
    conv_id = await _seed_conv(db, "5533")
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=RuntimeError("boom"))
    with patch("app.services.cold_triage.get_anthropic_client", return_value=mock_client):
        result = await compose_message(
            conversation_id=conv_id,
            action="mentoria",
            classification="objecao_timing",
            quote_from_lead="x",
            contact_name="Y",
            db=db,
        )
    assert result == ""


@pytest.mark.asyncio
async def test_mentoria_cap_counts_only_sent_and_approved_this_month(db):
    # seed conv
    cursor = await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, funnel_product, funnel_stage) "
        "VALUES ('9999', 'X', 'curso-cdo', 'link_sent')"
    )
    conv_id = cursor.lastrowid

    # dispatches sent esse mês → contam
    for _ in range(3):
        await db.execute(
            """INSERT INTO cold_dispatches
               (conversation_id, classification, confidence, action, status, created_at)
               VALUES (?, 'objecao_timing', 'high', 'mentoria', 'sent', datetime('now'))""",
            (conv_id,),
        )
    # approved → conta
    await db.execute(
        """INSERT INTO cold_dispatches
           (conversation_id, classification, confidence, action, status, created_at)
           VALUES (?, 'objecao_timing', 'high', 'mentoria', 'approved', datetime('now'))""",
        (conv_id,),
    )
    # previewed → não conta
    await db.execute(
        """INSERT INTO cold_dispatches
           (conversation_id, classification, confidence, action, status, created_at)
           VALUES (?, 'objecao_timing', 'high', 'mentoria', 'previewed', datetime('now'))""",
        (conv_id,),
    )
    # mês anterior → não conta (ajustando created_at)
    await db.execute(
        """INSERT INTO cold_dispatches
           (conversation_id, classification, confidence, action, status, created_at)
           VALUES (?, 'objecao_timing', 'high', 'mentoria', 'sent', datetime('now','-45 days'))""",
        (conv_id,),
    )
    # action=conteudo → não conta
    await db.execute(
        """INSERT INTO cold_dispatches
           (conversation_id, classification, confidence, action, status, created_at)
           VALUES (?, 'perdido_no_ruido', 'high', 'conteudo', 'sent', datetime('now'))""",
        (conv_id,),
    )
    await db.commit()

    count = await count_mentoria_offers_this_month(db)
    assert count == 4  # 3 sent + 1 approved, no mês corrente


@pytest.mark.asyncio
async def test_mentoria_cap_start_of_month_is_utc(db):
    """Proteção: dispatches gravados em UTC NÃO podem ser confundidos quando o mês local (BRT)
    vira antes do mês UTC. Injeta um dispatch com created_at explicitamente no final do mês
    anterior (UTC) e confere que não entra na contagem."""
    from datetime import datetime, timezone
    from app.config import now_local

    cursor = await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, funnel_product, funnel_stage) "
        "VALUES ('7777', 'X', 'curso-cdo', 'link_sent')"
    )
    conv_id = cursor.lastrowid

    # Início do mês local atual em UTC
    start_local = now_local().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_utc = start_local.astimezone(timezone.utc)

    # Dispatch gravado 1 segundo ANTES do início do mês em UTC: ainda é mês anterior
    from datetime import timedelta
    before_utc = (start_utc - timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
    await db.execute(
        """INSERT INTO cold_dispatches
           (conversation_id, classification, confidence, action, status, created_at)
           VALUES (?, 'objecao_timing', 'high', 'mentoria', 'sent', ?)""",
        (conv_id, before_utc),
    )
    # Dispatch exatamente no início do mês UTC: conta
    at_utc = start_utc.strftime("%Y-%m-%d %H:%M:%S")
    await db.execute(
        """INSERT INTO cold_dispatches
           (conversation_id, classification, confidence, action, status, created_at)
           VALUES (?, 'objecao_timing', 'high', 'mentoria', 'sent', ?)""",
        (conv_id, at_utc),
    )
    await db.commit()

    count = await count_mentoria_offers_this_month(db)
    assert count == 1
