from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import *  # noqa: F401, F403

from app.services import rewarm_cron
from app.services.rewarm_engine import REWARM_TOOL_NAME


def _rewarm_decision(action="send", message="oi", reason="x"):
    mock = MagicMock()
    block = MagicMock()
    block.type = "tool_use"
    block.name = REWARM_TOOL_NAME
    block.input = {"action": action, "message": message, "reason": reason}
    mock.content = [block]
    return mock


async def _seed_candidate(db, phone, stage="handbook_sent"):
    cursor = await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, funnel_product, funnel_stage) "
        "VALUES (?, 'X', 'curso-cdo', ?)",
        (phone, stage),
    )
    conv_id = cursor.lastrowid
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, created_at) "
        "VALUES (?, 'outbound', 'mensagem', datetime('now','-1 day'))",
        (conv_id,),
    )
    await db.commit()
    return conv_id


@pytest.mark.asyncio
async def test_daily_dispatch_noop_when_flag_off(db):
    await _seed_candidate(db, "5511")
    with patch("app.services.rewarm_cron.settings") as s:
        s.rewarm_auto_send = False
        result = await rewarm_cron.daily_dispatch()
    assert result["skipped"] == "flag_off"

    cursor = await db.execute("SELECT COUNT(*) AS n FROM rewarm_dispatches")
    assert (await cursor.fetchone())["n"] == 0


@pytest.mark.asyncio
async def test_daily_dispatch_creates_scheduled_send_and_dispatch(db):
    conv_id = await _seed_candidate(db, "5522")
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=_rewarm_decision(action="send", message="oi de novo"))

    with patch("app.services.rewarm_cron.settings") as s, \
         patch("app.services.rewarm_engine.get_anthropic_client", return_value=mock_client):
        s.rewarm_auto_send = True
        result = await rewarm_cron.daily_dispatch()

    assert result["dispatched"] == 1

    cur = await db.execute(
        "SELECT id, arm, scheduled_send_id, status FROM rewarm_dispatches WHERE conversation_id = ?",
        (conv_id,),
    )
    dispatch = await cur.fetchone()
    assert dispatch is not None
    assert dispatch["arm"] in ("noon", "evening")
    assert dispatch["scheduled_send_id"] is not None
    assert dispatch["status"] == "pending"

    cur = await db.execute(
        "SELECT content, status, created_by, send_at FROM scheduled_sends WHERE id = ?",
        (dispatch["scheduled_send_id"],),
    )
    send = await cur.fetchone()
    assert send["content"] == "oi de novo"
    assert send["status"] == "pending"
    assert send["created_by"] == "rewarm_agent"

    # send_at deve estar em UTC (não em horário local). Scheduler compara com datetime('now') do SQLite (UTC).
    # Slot noon (12:30 BRT) = 15:30 UTC ± jitter; slot evening (18:30 BRT) = 21:30 UTC ± jitter.
    from datetime import datetime as _dt
    send_at = _dt.strptime(send["send_at"], "%Y-%m-%d %H:%M:%S")
    if dispatch["arm"] == "noon":
        # 15:30 UTC ± 15 min → hora entre 15:15 e 15:45
        assert send_at.hour in (15,)
    else:
        # 21:30 UTC ± 15 min → hora entre 21:15 e 21:45
        assert send_at.hour in (21,)


@pytest.mark.asyncio
async def test_daily_dispatch_respects_agent_skip(db):
    conv_id = await _seed_candidate(db, "5533")
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=_rewarm_decision(action="skip", message="", reason="hostil"))

    with patch("app.services.rewarm_cron.settings") as s, \
         patch("app.services.rewarm_engine.get_anthropic_client", return_value=mock_client):
        s.rewarm_auto_send = True
        result = await rewarm_cron.daily_dispatch()

    assert result["dispatched"] == 0
    assert result["agent_skipped"] == 1

    cur = await db.execute("SELECT COUNT(*) AS n FROM rewarm_dispatches WHERE conversation_id = ?", (conv_id,))
    assert (await cur.fetchone())["n"] == 0


@pytest.mark.asyncio
async def test_slot_idempotency(db):
    # Marca morning como já rodado hoje
    await db.execute("INSERT INTO cron_runs (slot_key) VALUES ('morning')")
    await db.commit()

    today_iso = (await (await db.execute("SELECT strftime('%Y-%m-%d','now') AS d")).fetchone())["d"]
    assert await rewarm_cron._slot_already_ran(db, "morning", today_iso) is True
    assert await rewarm_cron._slot_already_ran(db, "nightly", today_iso) is False


@pytest.mark.asyncio
async def test_nightly_closeout_closes_stale_and_runs_refit(db):
    conv_id = await _seed_candidate(db, "5544")
    import json as _json
    from app.services.rewarm_bandit import FEATURE_NAMES
    features_json = _json.dumps({name: 0.0 for name in FEATURE_NAMES})
    await db.execute(
        """INSERT INTO rewarm_dispatches
           (conversation_id, features_json, arm, scheduled_for, sent_at, status)
           VALUES (?, ?, 'noon', '2026-01-01 12:30:00', datetime('now','-50 hours'), 'sent')""",
        (conv_id, features_json),
    )
    await db.commit()

    result = await rewarm_cron.nightly_closeout()
    assert result["closed"] == 1
