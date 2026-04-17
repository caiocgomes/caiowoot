import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import *  # noqa: F401, F403

from app.services import rewarm_bandit
from app.services.rewarm_bandit import FEATURE_NAMES, PRODUCTIVE_TOOL_NAME, handle_reward_inbound


def _productive_resp(productive: bool):
    mock = MagicMock()
    block = MagicMock()
    block.type = "tool_use"
    block.name = PRODUCTIVE_TOOL_NAME
    block.input = {"productive": productive, "reason": "x"}
    mock.content = [block]
    return mock


async def _seed_conv_with_sent_dispatch(db, phone, sent_offset="-2 hours"):
    cursor = await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, funnel_product, funnel_stage) "
        "VALUES (?, 'X', 'curso-cdo', 'handbook_sent')",
        (phone,),
    )
    conv_id = cursor.lastrowid
    features_json = json.dumps({name: 0.0 for name in FEATURE_NAMES})
    send_cursor = await db.execute(
        "INSERT INTO scheduled_sends (conversation_id, content, send_at, status, created_by) "
        "VALUES (?, 'toque', datetime('now'), 'sent', 'rewarm_agent')",
        (conv_id,),
    )
    scheduled_send_id = send_cursor.lastrowid
    await db.execute(
        f"""INSERT INTO rewarm_dispatches
           (conversation_id, features_json, arm, scheduled_send_id, scheduled_for, sent_at, status)
           VALUES (?, ?, 'noon', ?, datetime('now', '{sent_offset}'), datetime('now', '{sent_offset}'), 'sent')""",
        (conv_id, features_json, scheduled_send_id),
    )
    # mensagem do operador (rewarm) antes do inbound
    await db.execute(
        f"INSERT INTO messages (conversation_id, direction, content, created_at) "
        f"VALUES (?, 'outbound', 'toque rewarm', datetime('now', '{sent_offset}'))",
        (conv_id,),
    )
    # inbound novo
    cursor = await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, created_at) "
        "VALUES (?, 'inbound', 'qual o valor do curso?', datetime('now'))",
        (conv_id,),
    )
    inbound_msg_id = cursor.lastrowid
    await db.commit()
    return conv_id, inbound_msg_id


@pytest.mark.asyncio
async def test_handle_reward_inbound_productive(db):
    conv_id, msg_id = await _seed_conv_with_sent_dispatch(db, "5511")

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=_productive_resp(True))

    with patch("app.services.rewarm_bandit.get_anthropic_client", return_value=mock_client):
        await handle_reward_inbound(conv_id, msg_id)

    cur = await db.execute(
        "SELECT responded_at, productive, reward, closed_at, status FROM rewarm_dispatches WHERE conversation_id = ?",
        (conv_id,),
    )
    row = await cur.fetchone()
    assert row["productive"] == 1
    assert row["reward"] == 1
    assert row["responded_at"] is not None
    assert row["closed_at"] is not None
    assert row["status"] == "closed"


@pytest.mark.asyncio
async def test_handle_reward_inbound_non_productive(db):
    conv_id, msg_id = await _seed_conv_with_sent_dispatch(db, "5522")

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=_productive_resp(False))

    with patch("app.services.rewarm_bandit.get_anthropic_client", return_value=mock_client):
        await handle_reward_inbound(conv_id, msg_id)

    cur = await db.execute(
        "SELECT productive, reward FROM rewarm_dispatches WHERE conversation_id = ?",
        (conv_id,),
    )
    row = await cur.fetchone()
    assert row["productive"] == 0
    assert row["reward"] == 0


@pytest.mark.asyncio
async def test_handle_reward_inbound_ignores_stale_dispatch(db):
    conv_id, msg_id = await _seed_conv_with_sent_dispatch(db, "5533", sent_offset="-50 hours")
    mock_client = AsyncMock()
    with patch("app.services.rewarm_bandit.get_anthropic_client", return_value=mock_client):
        await handle_reward_inbound(conv_id, msg_id)

    mock_client.messages.create.assert_not_called()
    cur = await db.execute(
        "SELECT productive FROM rewarm_dispatches WHERE conversation_id = ?",
        (conv_id,),
    )
    row = await cur.fetchone()
    assert row["productive"] is None


@pytest.mark.asyncio
async def test_handle_reward_inbound_no_dispatch_is_noop(db):
    cursor = await db.execute(
        "INSERT INTO conversations (phone_number, contact_name) VALUES ('5544', 'X')",
    )
    conv_id = cursor.lastrowid
    cursor = await db.execute(
        "INSERT INTO messages (conversation_id, direction, content) VALUES (?, 'inbound', 'oi')",
        (conv_id,),
    )
    inbound_id = cursor.lastrowid
    await db.commit()

    mock_client = AsyncMock()
    with patch("app.services.rewarm_bandit.get_anthropic_client", return_value=mock_client):
        await handle_reward_inbound(conv_id, inbound_id)
    mock_client.messages.create.assert_not_called()


@pytest.mark.asyncio
async def test_mark_dispatch_skipped_on_client_reply(db):
    # Seed: dispatch pending (sem sent_at) vinculado a scheduled_send pending
    cur = await db.execute(
        "INSERT INTO conversations (phone_number, contact_name) VALUES ('5599', 'X')"
    )
    conv_id = cur.lastrowid
    cur = await db.execute(
        "INSERT INTO scheduled_sends (conversation_id, content, send_at, status, created_by) "
        "VALUES (?, 'toque', datetime('now','+4 hours'), 'pending', 'rewarm_agent')",
        (conv_id,),
    )
    send_id = cur.lastrowid
    features_json = json.dumps({name: 0.0 for name in FEATURE_NAMES})
    await db.execute(
        """INSERT INTO rewarm_dispatches
           (conversation_id, features_json, arm, scheduled_send_id, scheduled_for, status)
           VALUES (?, ?, 'noon', ?, datetime('now','+4 hours'), 'pending')""",
        (conv_id, features_json, send_id),
    )
    await db.commit()

    await rewarm_bandit.mark_dispatch_skipped_client_replied(db, send_id)
    await db.commit()

    cur = await db.execute(
        "SELECT status, closed_at FROM rewarm_dispatches WHERE scheduled_send_id = ?",
        (send_id,),
    )
    row = await cur.fetchone()
    assert row["status"] == "skipped_client_replied"
    assert row["closed_at"] is not None
