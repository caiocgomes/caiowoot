import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import *  # noqa: F401, F403

from app.services.rewarm_engine import REWARM_TOOL_NAME, run_rewarm_auto


def _rewarm_resp(action="send", message="oi", reason="parou"):
    mock = MagicMock()
    block = MagicMock()
    block.type = "tool_use"
    block.name = REWARM_TOOL_NAME
    block.input = {"action": action, "message": message, "reason": reason}
    mock.content = [block]
    return mock


async def _seed(db, phone, name, stage="handbook_sent"):
    cursor = await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, funnel_product, funnel_stage) VALUES (?, ?, 'CDO', ?)",
        (phone, name, stage),
    )
    conv_id = cursor.lastrowid
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, created_at) "
        "VALUES (?, 'inbound', 'oi', datetime('now','-1 day'))",
        (conv_id,),
    )
    await db.commit()
    return conv_id


@pytest.mark.asyncio
async def test_auto_send_delivers_all_send_items(db, mock_evolution_api):
    c1 = await _seed(db, "5511", "A")
    c2 = await _seed(db, "5522", "B")

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=[
        _rewarm_resp(action="send", message="mensagem 1"),
        _rewarm_resp(action="send", message="mensagem 2"),
    ])

    with patch("app.services.rewarm_engine.get_anthropic_client", return_value=mock_client), \
         patch("app.services.rewarm_engine.asyncio.sleep", new=AsyncMock()), \
         patch("app.services.rewarm_engine.settings") as s:
        s.rewarm_auto_send = True
        await run_rewarm_auto()

    for cid in (c1, c2):
        cur = await db.execute(
            "SELECT sent_by FROM messages WHERE conversation_id=? AND direction='outbound'",
            (cid,),
        )
        row = await cur.fetchone()
        assert row is not None
        assert row["sent_by"] == "rewarm_agent"


@pytest.mark.asyncio
async def test_auto_send_skips_when_agent_returns_skip(db, mock_evolution_api):
    c_send = await _seed(db, "5511", "A")
    c_skip = await _seed(db, "5522", "B")

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=[
        _rewarm_resp(action="send", message="vai"),
        _rewarm_resp(action="skip", message="", reason="cliente pediu parar"),
    ])

    with patch("app.services.rewarm_engine.get_anthropic_client", return_value=mock_client), \
         patch("app.services.rewarm_engine.asyncio.sleep", new=AsyncMock()), \
         patch("app.services.rewarm_engine.settings") as s:
        s.rewarm_auto_send = True
        await run_rewarm_auto()

    cur_send = await db.execute(
        "SELECT COUNT(*) AS n FROM messages WHERE conversation_id=? AND direction='outbound'",
        (c_send,),
    )
    assert (await cur_send.fetchone())["n"] == 1

    cur_skip = await db.execute(
        "SELECT COUNT(*) AS n FROM messages WHERE conversation_id=? AND direction='outbound'",
        (c_skip,),
    )
    assert (await cur_skip.fetchone())["n"] == 0


@pytest.mark.asyncio
async def test_run_rewarm_auto_noop_when_flag_false(db, mock_evolution_api):
    await _seed(db, "5511", "A")
    mock_client = AsyncMock()

    with patch("app.services.rewarm_engine.get_anthropic_client", return_value=mock_client), \
         patch("app.services.rewarm_engine.settings") as s:
        s.rewarm_auto_send = False
        await run_rewarm_auto()

    mock_client.messages.create.assert_not_called()


@pytest.mark.asyncio
async def test_preview_endpoint_ignores_auto_send_flag(client, db, mock_evolution_api):
    """Preview nunca envia, mesmo com flag automática ligada."""
    conv_id = await _seed(db, "5511", "A")

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=_rewarm_resp(action="send", message="auto"))

    with patch("app.services.rewarm_engine.get_anthropic_client", return_value=mock_client), \
         patch("app.services.rewarm_engine.settings") as s:
        s.rewarm_auto_send = True
        resp = await client.post("/rewarm/preview")

    assert resp.status_code == 200
    # Nenhuma mensagem outbound deve ter sido criada só pelo preview
    cur = await db.execute(
        "SELECT COUNT(*) AS n FROM messages WHERE conversation_id=? AND direction='outbound'",
        (conv_id,),
    )
    assert (await cur.fetchone())["n"] == 0
