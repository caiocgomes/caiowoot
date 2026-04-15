import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from tests.conftest import *  # noqa: F401, F403

from app.routes.rewarm import _background_tasks
from app.services.rewarm_engine import REWARM_TOOL_NAME


async def _drain_background():
    while _background_tasks:
        await asyncio.gather(*list(_background_tasks), return_exceptions=True)


def _make_rewarm_resp(action="send", message="oi, tudo bem?", reason="parou após handbook"):
    mock = MagicMock()
    block = MagicMock()
    block.type = "tool_use"
    block.name = REWARM_TOOL_NAME
    block.input = {"action": action, "message": message, "reason": reason}
    mock.content = [block]
    return mock


async def _seed_candidate(db, phone, name, stage="handbook_sent"):
    cursor = await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, funnel_product, funnel_stage) VALUES (?, ?, 'CDO', ?)",
        (phone, name, stage),
    )
    conv_id = cursor.lastrowid
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, created_at) "
        "VALUES (?, 'inbound', 'oi', datetime('now', '-1 day'))",
        (conv_id,),
    )
    await db.commit()
    return conv_id


# ======================= PREVIEW =======================

@pytest.mark.asyncio
async def test_preview_returns_all_decisions(client, db):
    c1 = await _seed_candidate(db, "5511111", "Ana")
    c2 = await _seed_candidate(db, "5522222", "Bia")
    c3 = await _seed_candidate(db, "5533333", "Caio", stage="link_sent")

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=[
        _make_rewarm_resp(action="send", message="oi Ana", reason="parou"),
        _make_rewarm_resp(action="send", message="oi Bia", reason="parou"),
        _make_rewarm_resp(action="skip", message="", reason="cliente pediu parar"),
    ])

    with patch("app.services.rewarm_engine.get_anthropic_client", return_value=mock_client):
        resp = await client.post("/rewarm/preview")

    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 3

    ids = {item["conversation_id"] for item in body}
    assert ids == {c1, c2, c3}

    for item in body:
        assert "item_id" in item
        assert "conversation_id" in item
        assert "action" in item
        assert "reason" in item
        assert "contact_name" in item
        assert "phone_number" in item
        if item["action"] == "send":
            assert item["message"]


@pytest.mark.asyncio
async def test_preview_returns_empty_when_no_candidates(client, db):
    resp = await client.post("/rewarm/preview")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_preview_requires_auth():
    """Em produção com APP_PASSWORD setado, preview deve bloquear acesso sem sessão."""
    with patch("app.auth.settings") as s:
        s.app_password = "secret123"
        s.session_max_age = 3600
        transport = ASGITransport(app=__import__("app.main", fromlist=["app"]).app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post("/rewarm/preview")
    assert resp.status_code == 401


# ======================= EXECUTE =======================

@pytest.mark.asyncio
async def test_execute_returns_202_and_schedules_background(client, db, mock_evolution_api):
    conv_id = await _seed_candidate(db, "5544444", "Dudu")
    payload = {"items": [{"conversation_id": conv_id, "message": "oi Dudu, como vai?"}]}

    with patch("app.services.rewarm_engine.asyncio.sleep", new=AsyncMock()):
        resp = await client.post("/rewarm/execute", json=payload)
        assert resp.status_code == 202
        await _drain_background()

    cursor = await db.execute(
        "SELECT content, direction, sent_by FROM messages WHERE conversation_id = ? AND direction = 'outbound'",
        (conv_id,),
    )
    rows = await cursor.fetchall()
    assert len(rows) == 1
    assert rows[0]["content"] == "oi Dudu, como vai?"


@pytest.mark.asyncio
async def test_execute_uses_edited_message_when_provided(client, db, mock_evolution_api):
    conv_id = await _seed_candidate(db, "5555555", "Edu")
    edited = "texto editado pelo operador"
    payload = {"items": [{"conversation_id": conv_id, "message": edited}]}

    with patch("app.services.rewarm_engine.asyncio.sleep", new=AsyncMock()):
        await client.post("/rewarm/execute", json=payload)
        await _drain_background()

    cursor = await db.execute(
        "SELECT content FROM messages WHERE conversation_id = ? AND direction='outbound'",
        (conv_id,),
    )
    row = await cursor.fetchone()
    assert row["content"] == edited


@pytest.mark.asyncio
async def test_execute_continues_after_send_failure(client, db, mock_evolution_api):
    c1 = await _seed_candidate(db, "5566666", "Fran")
    c2 = await _seed_candidate(db, "5577777", "Gui")
    c3 = await _seed_candidate(db, "5588888", "Hugo")

    call_count = {"n": 0}

    original_send = mock_evolution_api.post

    async def flaky_post(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise RuntimeError("evolution boom")
        return await original_send(*args, **kwargs)

    mock_evolution_api.post = AsyncMock(side_effect=flaky_post)

    payload = {"items": [
        {"conversation_id": c1, "message": "msg 1"},
        {"conversation_id": c2, "message": "msg 2"},
        {"conversation_id": c3, "message": "msg 3"},
    ]}

    with patch("app.services.rewarm_engine.asyncio.sleep", new=AsyncMock()):
        await client.post("/rewarm/execute", json=payload)
        await _drain_background()

    # c1 e c3 devem ter outbound message, c2 não
    async def count_outbound(cid):
        cur = await db.execute(
            "SELECT COUNT(*) AS n FROM messages WHERE conversation_id=? AND direction='outbound'",
            (cid,),
        )
        return (await cur.fetchone())["n"]

    assert await count_outbound(c1) == 1
    assert await count_outbound(c2) == 0
    assert await count_outbound(c3) == 1


@pytest.mark.asyncio
async def test_execute_marks_messages_as_rewarm_reviewed(client, db, mock_evolution_api):
    conv_id = await _seed_candidate(db, "5599999", "Ivo")
    payload = {"items": [{"conversation_id": conv_id, "message": "oi Ivo"}]}

    with patch("app.services.rewarm_engine.asyncio.sleep", new=AsyncMock()):
        await client.post("/rewarm/execute", json=payload)
        await _drain_background()

    cursor = await db.execute(
        "SELECT sent_by FROM messages WHERE conversation_id=? AND direction='outbound'",
        (conv_id,),
    )
    row = await cursor.fetchone()
    assert row["sent_by"] == "rewarm_reviewed"
