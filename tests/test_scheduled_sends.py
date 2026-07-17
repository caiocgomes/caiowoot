"""Tests for scheduled sends: CRUD routes and background worker."""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from tests.conftest import make_webhook_payload


# ── Helpers ──────────────────────────────────────────────────────────


async def insert_conversation(db, phone="5511999999999", name="Maria"):
    cursor = await db.execute(
        "INSERT INTO conversations (phone_number, contact_name) VALUES (?, ?)",
        (phone, name),
    )
    await db.commit()
    return cursor.lastrowid


async def insert_scheduled_send(
    db,
    conversation_id,
    content="Oi, tudo bem?",
    send_at="2099-12-31T23:59:00",
    status="pending",
    created_by="caio",
    draft_id=None,
    draft_group_id=None,
    selected_draft_index=None,
):
    cursor = await db.execute(
        """INSERT INTO scheduled_sends
           (conversation_id, content, send_at, status, created_by, draft_id, draft_group_id, selected_draft_index)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (conversation_id, content, send_at, status, created_by, draft_id, draft_group_id, selected_draft_index),
    )
    await db.commit()
    return cursor.lastrowid


# ── 1. CRUD Route Tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_schedule_send_success(client, db):
    conv_id = await insert_conversation(db)
    resp = await client.post(
        f"/conversations/{conv_id}/schedule",
        json={"content": "Te retorno amanhã!", "send_at": "2099-12-31T10:00:00"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    ss = data["scheduled_send"]
    assert ss["conversation_id"] == conv_id
    assert ss["content"] == "Te retorno amanhã!"
    assert ss["send_at"] == "2099-12-31T10:00:00"
    assert ss["status"] == "pending"

    # Verify persisted in DB
    row = await db.execute("SELECT * FROM scheduled_sends WHERE id = ?", (ss["id"],))
    record = await row.fetchone()
    assert record is not None
    assert record["content"] == "Te retorno amanhã!"


@pytest.mark.asyncio
async def test_schedule_send_conversation_not_found(client, db):
    resp = await client.post(
        "/conversations/99999/schedule",
        json={"content": "Oi", "send_at": "2099-12-31T10:00:00"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_schedule_send_invalid_send_at(client, db):
    conv_id = await insert_conversation(db)
    resp = await client.post(
        f"/conversations/{conv_id}/schedule",
        json={"content": "Oi", "send_at": "not-a-date"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_scheduled_sends(client, db):
    conv_id = await insert_conversation(db)
    # Insert two scheduled sends with different times (later first to verify ordering)
    await insert_scheduled_send(db, conv_id, content="Segundo", send_at="2099-12-31T14:00:00")
    await insert_scheduled_send(db, conv_id, content="Primeiro", send_at="2099-12-31T09:00:00")

    resp = await client.get(f"/conversations/{conv_id}/scheduled")
    assert resp.status_code == 200
    sends = resp.json()
    assert len(sends) == 2
    # Should be ordered by send_at ascending
    assert sends[0]["content"] == "Primeiro"
    assert sends[1]["content"] == "Segundo"


@pytest.mark.asyncio
async def test_list_scheduled_conversation_not_found(client, db):
    resp = await client.get("/conversations/99999/scheduled")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cancel_scheduled_send_success(client, db):
    conv_id = await insert_conversation(db)
    send_id = await insert_scheduled_send(db, conv_id)

    resp = await client.delete(f"/scheduled-sends/{send_id}")
    assert resp.status_code == 200

    # Verify status changed in DB
    row = await db.execute("SELECT status, cancelled_reason FROM scheduled_sends WHERE id = ?", (send_id,))
    record = await row.fetchone()
    assert record["status"] == "cancelled"
    assert record["cancelled_reason"] == "operator_cancelled"


@pytest.mark.asyncio
async def test_cancel_scheduled_send_not_found(client, db):
    resp = await client.delete("/scheduled-sends/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cancel_scheduled_send_already_sent(client, db):
    conv_id = await insert_conversation(db)
    send_id = await insert_scheduled_send(db, conv_id, status="sent")

    resp = await client.delete(f"/scheduled-sends/{send_id}")
    assert resp.status_code == 409


# ── 2. Background Worker Tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_process_due_sends_success(db):
    conv_id = await insert_conversation(db)
    send_id = await insert_scheduled_send(
        db, conv_id, content="Follow-up automático", send_at="2000-01-01T00:00:00", created_by="caio"
    )

    mock_execute = AsyncMock(return_value={"message_id": 1, "edit_pair_id": None})

    with patch("app.services.scheduler.execute_send", mock_execute):
        from app.services.scheduler import _process_due_sends
        await _process_due_sends()

    # Verify execute_send was called with correct args
    mock_execute.assert_called_once_with(
        conversation_id=conv_id,
        text="Follow-up automático",
        operator="caio",
        draft_id=None,
        draft_group_id=None,
        selected_draft_index=None,
    )

    # Verify status changed to sent
    row = await db.execute("SELECT status, sent_at FROM scheduled_sends WHERE id = ?", (send_id,))
    record = await row.fetchone()
    assert record["status"] == "sent"
    assert record["sent_at"] is not None


@pytest.mark.asyncio
async def test_process_due_sends_ignores_future(db):
    conv_id = await insert_conversation(db)
    send_id = await insert_scheduled_send(
        db, conv_id, content="Ainda não é hora", send_at="2099-12-31T23:59:00"
    )

    mock_execute = AsyncMock()

    with patch("app.services.scheduler.execute_send", mock_execute):
        from app.services.scheduler import _process_due_sends
        await _process_due_sends()

    mock_execute.assert_not_called()

    # Status should remain pending
    row = await db.execute("SELECT status FROM scheduled_sends WHERE id = ?", (send_id,))
    record = await row.fetchone()
    assert record["status"] == "pending"


@pytest.mark.asyncio
async def test_process_due_sends_reverts_on_failure(db):
    conv_id = await insert_conversation(db)
    send_id = await insert_scheduled_send(
        db, conv_id, content="Vai falhar", send_at="2000-01-01T00:00:00"
    )

    mock_execute = AsyncMock(side_effect=Exception("Evolution API down"))

    with patch("app.services.scheduler.execute_send", mock_execute):
        from app.services.scheduler import _process_due_sends
        await _process_due_sends()

    # Status should revert to pending for retry
    row = await db.execute("SELECT status FROM scheduled_sends WHERE id = ?", (send_id,))
    record = await row.fetchone()
    assert record["status"] == "pending"


# ── 3. Tick sem sends devidos não escreve no banco ──────────────────


class _SpyConn:
    """Espião de conexão: registra statements e commits; close vira no-op."""

    def __init__(self, conn):
        self._conn = conn
        self.statements = []
        self.commit_count = 0

    async def execute(self, sql, *args, **kwargs):
        self.statements.append(" ".join(sql.split()).lower())
        return await self._conn.execute(sql, *args, **kwargs)

    async def commit(self):
        self.commit_count += 1
        await self._conn.commit()

    async def close(self):
        pass  # conexão compartilhada do teste, não fechar

    def __getattr__(self, name):
        return getattr(self._conn, name)


@pytest.mark.asyncio
async def test_tick_sem_sends_devidos_nao_emite_update_nem_commit(db):
    """Tick do scheduler sem sends devidos não pode emitir UPDATE nem commit.

    Hoje: red — _process_due_sends faz UPDATE em scheduled_sends + commit
    incondicionalmente a cada tick, mesmo sem nada devido. O contrato novo
    exige checar antes de escrever (tick barato quando não há nada devido).
    """
    conv_id = await insert_conversation(db)
    # Send pendente mas no futuro: existe linha na tabela, nada está devido
    await insert_scheduled_send(db, conv_id, content="Só no futuro", send_at="2099-12-31T23:59:00")

    spy = _SpyConn(db)

    async def spy_get_db():
        return spy

    mock_execute = AsyncMock()

    with patch("app.services.scheduler.get_db", spy_get_db), \
         patch("app.services.scheduler.execute_send", mock_execute):
        from app.services.scheduler import _process_due_sends
        await _process_due_sends()

    mock_execute.assert_not_called()

    updates_scheduled = [
        s for s in spy.statements if s.startswith("update") and "scheduled_sends" in s
    ]
    assert updates_scheduled == [], (
        f"tick sem sends devidos emitiu UPDATE em scheduled_sends: {updates_scheduled}"
    )
    assert spy.commit_count == 0, (
        f"tick sem sends devidos chamou commit {spy.commit_count}x; não deveria escrever nada"
    )
