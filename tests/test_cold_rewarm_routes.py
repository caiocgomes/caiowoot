from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import *  # noqa: F401, F403

from app.services.cold_triage import (
    COLD_CLASSIFY_TOOL_NAME,
    COLD_COMPOSE_TOOL_NAME,
    mark_cold_response_received,
)


def _classify_resp(classification, confidence, stage_reached="link_sent", quote="mes que vem volto"):
    mock = MagicMock()
    block = MagicMock()
    block.type = "tool_use"
    block.name = COLD_CLASSIFY_TOOL_NAME
    block.input = {
        "classification": classification,
        "confidence": confidence,
        "stage_reached": stage_reached,
        "quote_from_lead": quote,
        "reasoning": "x",
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


async def _seed_candidate(db, phone="5511", stage="qualifying"):
    """Seed com stage genérico (não link/handbook). Opção B infere stage_reached no classifier,
    não no filtro do SELECT."""
    cursor = await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, funnel_product, funnel_stage) "
        "VALUES (?, 'Ana', 'curso-cdo', ?)",
        (phone, stage),
    )
    conv_id = cursor.lastrowid
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, created_at) "
        "VALUES (?, 'inbound', 'mes que vem volto', datetime('now','-40 days'))",
        (conv_id,),
    )
    await db.commit()
    return conv_id


@pytest.mark.asyncio
async def test_preview_returns_items_and_creates_previewed_dispatches(client, db):
    # stage=qualifying (não handbook/link): opção B infere stage_reached=link_sent via Haiku
    conv_id = await _seed_candidate(db, "5511", stage="qualifying")
    mock_client = AsyncMock()

    def dispatcher(*args, **kwargs):
        tools = kwargs.get("tools") or []
        tool_name = tools[0]["name"] if tools else ""
        if tool_name == COLD_CLASSIFY_TOOL_NAME:
            return _classify_resp("objecao_timing", "high", stage_reached="link_sent")
        return _compose_resp("oi ana, caio aqui")

    mock_client.messages.create = AsyncMock(side_effect=dispatcher)

    with patch("app.services.cold_triage.get_anthropic_client", return_value=mock_client):
        resp = await client.post("/cold-rewarm/preview")

    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    item = items[0]
    assert item["conversation_id"] == conv_id
    assert item["classification"] == "objecao_timing"
    assert item["stage_reached"] == "link_sent"
    assert item["action"] == "mentoria"
    assert item["message"] == "oi ana, caio aqui"
    assert "dispatch_id" in item

    cur = await db.execute(
        "SELECT status, action, stage_reached FROM cold_dispatches WHERE id = ?",
        (item["dispatch_id"],),
    )
    row = await cur.fetchone()
    assert row["status"] == "previewed"
    assert row["action"] == "mentoria"
    assert row["stage_reached"] == "link_sent"


@pytest.mark.asyncio
async def test_preview_routes_only_qualifying_to_conteudo_not_mentoria(client, db):
    """Lead que nunca recebeu handbook/link: Haiku infere only_qualifying, matriz vira conteudo."""
    conv_id = await _seed_candidate(db, "5599", stage=None)
    mock_client = AsyncMock()

    def dispatcher(*args, **kwargs):
        tools = kwargs.get("tools") or []
        tool_name = tools[0]["name"] if tools else ""
        if tool_name == COLD_CLASSIFY_TOOL_NAME:
            return _classify_resp("objecao_timing", "high", stage_reached="only_qualifying")
        return _compose_resp("oi, publiquei sobre atribuicao")

    mock_client.messages.create = AsyncMock(side_effect=dispatcher)

    with patch("app.services.cold_triage.get_anthropic_client", return_value=mock_client):
        resp = await client.post("/cold-rewarm/preview")

    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["stage_reached"] == "only_qualifying"
    assert items[0]["action"] == "conteudo"


@pytest.mark.asyncio
async def test_preview_routes_nunca_qualificou_to_skip(client, db):
    await _seed_candidate(db, "5500", stage=None)
    mock_client = AsyncMock()

    def dispatcher(*args, **kwargs):
        tools = kwargs.get("tools") or []
        tool_name = tools[0]["name"] if tools else ""
        if tool_name == COLD_CLASSIFY_TOOL_NAME:
            return _classify_resp("tire_kicker", "high", stage_reached="nunca_qualificou")
        return _compose_resp("nao usado")

    mock_client.messages.create = AsyncMock(side_effect=dispatcher)

    with patch("app.services.cold_triage.get_anthropic_client", return_value=mock_client):
        resp = await client.post("/cold-rewarm/preview")

    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["action"] == "skip"


@pytest.mark.asyncio
async def test_preview_returns_empty_list_when_no_candidates(client, db):
    resp = await client.post("/cold-rewarm/preview")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_execute_returns_202_and_updates_dispatch(client, db, mock_evolution_api):
    conv_id = await _seed_candidate(db, "5522")

    # Cria preview dispatch
    cursor = await db.execute(
        """INSERT INTO cold_dispatches
           (conversation_id, classification, confidence, action, message_draft, status)
           VALUES (?, 'objecao_timing', 'high', 'mentoria', 'rascunho original', 'previewed')""",
        (conv_id,),
    )
    dispatch_id = cursor.lastrowid
    await db.commit()

    # Mocka asyncio.sleep pra não bloquear no rate limit
    with patch("app.services.cold_triage.asyncio.sleep", new=AsyncMock()):
        resp = await client.post(
            "/cold-rewarm/execute",
            json={
                "items": [
                    {
                        "dispatch_id": dispatch_id,
                        "conversation_id": conv_id,
                        "message": "mensagem editada pelo operador",
                    }
                ]
            },
        )
    assert resp.status_code == 202

    # Aguarda background task completar
    import asyncio as _asyncio
    for _ in range(20):
        await _asyncio.sleep(0.05)
        cur = await db.execute("SELECT status, message_sent FROM cold_dispatches WHERE id = ?", (dispatch_id,))
        row = await cur.fetchone()
        if row and row["status"] in ("sent", "failed"):
            break

    assert row is not None
    assert row["status"] == "sent"
    assert row["message_sent"] == "mensagem editada pelo operador"


@pytest.mark.asyncio
async def test_cold_response_hook_marks_responded_at(db):
    conv_id = await _seed_candidate(db, "5533")
    # Cold dispatch sent recentemente
    cursor = await db.execute(
        """INSERT INTO cold_dispatches
           (conversation_id, classification, confidence, action, message_sent, status, updated_at)
           VALUES (?, 'objecao_timing', 'high', 'mentoria', 'toque cold', 'sent', datetime('now','-1 hours'))""",
        (conv_id,),
    )
    dispatch_id = cursor.lastrowid
    # Inbound do lead
    cursor = await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, created_at) "
        "VALUES (?, 'inbound', 'ai quero sim', datetime('now'))",
        (conv_id,),
    )
    msg_id = cursor.lastrowid
    await db.commit()

    await mark_cold_response_received(conv_id, msg_id)

    cur = await db.execute("SELECT responded_at FROM cold_dispatches WHERE id = ?", (dispatch_id,))
    row = await cur.fetchone()
    assert row["responded_at"] is not None


@pytest.mark.asyncio
async def test_cold_response_hook_ignores_stale_dispatch(db):
    conv_id = await _seed_candidate(db, "5544")
    cursor = await db.execute(
        """INSERT INTO cold_dispatches
           (conversation_id, classification, confidence, action, message_sent, status, updated_at)
           VALUES (?, 'objecao_timing', 'high', 'mentoria', 'toque', 'sent', datetime('now','-10 days'))""",
        (conv_id,),
    )
    dispatch_id = cursor.lastrowid
    cursor = await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, created_at) "
        "VALUES (?, 'inbound', 'respondendo tarde', datetime('now'))",
        (conv_id,),
    )
    msg_id = cursor.lastrowid
    await db.commit()

    await mark_cold_response_received(conv_id, msg_id)

    cur = await db.execute("SELECT responded_at FROM cold_dispatches WHERE id = ?", (dispatch_id,))
    row = await cur.fetchone()
    assert row["responded_at"] is None


@pytest.mark.asyncio
async def test_cold_response_hook_noop_without_dispatch(db):
    cursor = await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, funnel_product, funnel_stage) "
        "VALUES ('5555', 'X', 'curso-cdo', 'link_sent')"
    )
    conv_id = cursor.lastrowid
    cursor = await db.execute(
        "INSERT INTO messages (conversation_id, direction, content) VALUES (?, 'inbound', 'oi')",
        (conv_id,),
    )
    msg_id = cursor.lastrowid
    await db.commit()

    # Não deve levantar
    await mark_cold_response_received(conv_id, msg_id)
