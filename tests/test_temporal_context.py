import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest

from app.config import now_local
from app.services.draft_engine import (
    _build_conversation_history,
    _build_temporal_context,
    generate_drafts,
)

SP = ZoneInfo("America/Sao_Paulo")


def _utc_iso(dt: datetime) -> str:
    """Convert to UTC naive ISO (matches CURRENT_TIMESTAMP behavior)."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.isoformat()


@pytest.mark.asyncio
async def test_timestamps_on_last_10_messages_only(db):
    """Mensagens além das últimas 10 não têm timestamp."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    now = now_local()
    for i in range(15):
        ts = _utc_iso(now - timedelta(minutes=15 - i))
        await db.execute(
            "INSERT INTO messages (conversation_id, evolution_message_id, direction, content, created_at) VALUES (1, ?, 'inbound', ?, ?)",
            (f"msg-{i}", f"mensagem {i}", ts),
        )
    await db.commit()

    history, _, _ = await _build_conversation_history(db, 1)
    lines = history.strip().split("\n")

    # First 5 lines should have no timestamp
    for line in lines[:5]:
        assert not line.startswith("["), f"Expected no timestamp: {line}"

    # Last 10 lines should have timestamps
    for line in lines[5:]:
        assert line.startswith("["), f"Expected timestamp: {line}"


@pytest.mark.asyncio
async def test_today_messages_format_hhmm(db):
    """Mensagens de hoje formatadas como [HH:MM]."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    now = now_local()
    ts = _utc_iso(now - timedelta(minutes=5))
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content, created_at) VALUES (1, 'msg-1', 'inbound', 'Oi', ?)",
        (ts,),
    )
    await db.commit()

    history, _, _ = await _build_conversation_history(db, 1)
    # Should match [HH:MM] format (no date)
    assert history.startswith("[")
    assert "/" not in history.split("]")[0], "Today's message should not include date"


@pytest.mark.asyncio
async def test_previous_day_messages_format_ddmm_hhmm(db):
    """Mensagens de dias anteriores formatadas como [DD/MM HH:MM]."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    yesterday = now_local() - timedelta(days=1)
    ts = _utc_iso(yesterday)
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content, created_at) VALUES (1, 'msg-1', 'inbound', 'Oi', ?)",
        (ts,),
    )
    await db.commit()

    history, _, _ = await _build_conversation_history(db, 1)
    bracket_content = history.split("]")[0].lstrip("[")
    assert "/" in bracket_content, "Previous day message should include DD/MM"


@pytest.mark.asyncio
async def test_all_messages_get_timestamps_when_10_or_fewer(db):
    """Com 10 ou menos mensagens, todas têm timestamp."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    now = now_local()
    for i in range(5):
        ts = _utc_iso(now - timedelta(minutes=5 - i))
        await db.execute(
            "INSERT INTO messages (conversation_id, evolution_message_id, direction, content, created_at) VALUES (1, ?, 'inbound', ?, ?)",
            (f"msg-{i}", f"mensagem {i}", ts),
        )
    await db.commit()

    history, _, _ = await _build_conversation_history(db, 1)
    lines = history.strip().split("\n")
    assert len(lines) == 5
    for line in lines:
        assert line.startswith("["), f"Expected timestamp on all messages: {line}"


def test_temporal_context_delay_over_1h():
    """Atraso > 1h mostra horas e minutos."""
    three_hours_ago = (now_local() - timedelta(hours=3, minutes=15)).isoformat()
    result = _build_temporal_context(three_hours_ago)
    assert "3h 15min" in result
    assert "Agora são" in result


def test_temporal_context_delay_under_1h():
    """Atraso < 1h mostra apenas minutos, sem horas."""
    twelve_min_ago = (now_local() - timedelta(minutes=12)).isoformat()
    result = _build_temporal_context(twelve_min_ago)
    assert "12min" in result
    # Should not contain hour format like "Xh"
    import re
    after_foi = result.split("foi")[1]
    assert not re.search(r"\d+h", after_foi), f"Should not have hours: {after_foi}"


def test_temporal_context_no_inbound():
    """Sem mensagem inbound, mostra apenas horário atual."""
    result = _build_temporal_context(None)
    assert "Agora são" in result
    assert "cliente" not in result


def test_temporal_context_exact_hours():
    """Atraso de horas exatas sem minutos sobressalentes."""
    two_hours_ago = (now_local() - timedelta(hours=2)).isoformat()
    result = _build_temporal_context(two_hours_ago)
    assert "2h" in result
    # Should not show "0min"
    assert "0min" not in result


@pytest.mark.asyncio
async def test_prompt_contains_temporal_section(db, mock_claude_api):
    """Prompt gerado contém seção de contexto temporal."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    now = now_local()
    ts = _utc_iso(now - timedelta(hours=2))
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content, created_at) VALUES (1, 'msg-1', 'inbound', 'Oi', ?)",
        (ts,),
    )
    await db.commit()

    await generate_drafts(1, 1)

    call_kwargs = mock_claude_api.messages.create.call_args_list[0].kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "## Contexto temporal" in user_content
    assert "Agora são" in user_content
    assert "2h" in user_content


@pytest.mark.asyncio
async def test_prompt_contains_timestamps_in_history(db, mock_claude_api):
    """Prompt contém timestamps nas mensagens do histórico."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    now = now_local()
    ts = _utc_iso(now - timedelta(minutes=10))
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content, created_at) VALUES (1, 'msg-1', 'inbound', 'Oi', ?)",
        (ts,),
    )
    await db.commit()

    await generate_drafts(1, 1)

    call_kwargs = mock_claude_api.messages.create.call_args_list[0].kwargs
    user_content = call_kwargs["messages"][0]["content"]
    # History should contain timestamped message
    assert "[" in user_content.split("Conversa atual")[1].split("Contexto temporal")[0]


@pytest.mark.asyncio
async def test_last_inbound_iso_tracks_inbound_only(db):
    """last_inbound_iso reflete apenas mensagens inbound, não outbound."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    now = now_local()
    inbound_ts = _utc_iso(now - timedelta(hours=3))
    outbound_ts = _utc_iso(now - timedelta(hours=1))
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content, created_at) VALUES (1, 'msg-1', 'inbound', 'Oi', ?)",
        (inbound_ts,),
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, created_at) VALUES (1, 'outbound', 'Resposta', ?)",
        (outbound_ts,),
    )
    await db.commit()

    _, _, last_inbound_iso = await _build_conversation_history(db, 1)
    last_inbound = datetime.fromisoformat(last_inbound_iso)
    # Should be ~3 hours ago (the inbound), not 1 hour ago (the outbound)
    delta = now - last_inbound
    assert delta.total_seconds() > 10000  # > 2.7 hours
