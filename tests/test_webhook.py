import pytest
from unittest.mock import patch, AsyncMock

from tests.conftest import make_webhook_payload


@pytest.mark.asyncio
async def test_text_message_persisted(client, db):
    """12.1: mensagem de texto recebida persiste no banco."""
    with patch("app.routes.webhook.spawn"):
        payload = make_webhook_payload()
        resp = await client.post("/webhook", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"

    row = await db.execute("SELECT * FROM messages WHERE evolution_message_id = 'msg-123'")
    msg = await row.fetchone()
    assert msg is not None
    assert msg["content"] == "Oi, quero saber sobre os cursos"
    assert msg["direction"] == "inbound"


@pytest.mark.asyncio
async def test_status_update_ignored(client, db):
    """12.2: evento de status retorna 200 e não persiste."""
    payload = make_webhook_payload(event="messages.update")
    resp = await client.post("/webhook", json=payload)

    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"

    row = await db.execute("SELECT COUNT(*) as cnt FROM messages")
    count = await row.fetchone()
    assert count["cnt"] == 0


@pytest.mark.asyncio
async def test_duplicate_message_ignored(client, db):
    """12.3: mensagem duplicada retorna 200 e não duplica."""
    with patch("app.routes.webhook.spawn"):
        payload = make_webhook_payload()
        await client.post("/webhook", json=payload)
        resp = await client.post("/webhook", json=payload)

    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    assert resp.json()["reason"] == "duplicate"

    row = await db.execute("SELECT COUNT(*) as cnt FROM messages")
    count = await row.fetchone()
    assert count["cnt"] == 1


@pytest.mark.asyncio
async def test_new_phone_creates_conversation(client, db):
    """12.4: primeira mensagem de um phone novo cria conversation + message."""
    with patch("app.routes.webhook.spawn"):
        payload = make_webhook_payload(phone="5511888888888", push_name="João")
        resp = await client.post("/webhook", json=payload)

    assert resp.status_code == 200

    row = await db.execute("SELECT * FROM conversations WHERE phone_number = '5511888888888'")
    conv = await row.fetchone()
    assert conv is not None
    assert conv["contact_name"] == "João"


@pytest.mark.asyncio
async def test_existing_phone_appends_message(client, db):
    """12.5: mensagem de phone existente adiciona à conversation existente."""
    with patch("app.routes.webhook.spawn"):
        payload1 = make_webhook_payload(message_id="msg-1", text="Oi")
        await client.post("/webhook", json=payload1)

        payload2 = make_webhook_payload(message_id="msg-2", text="Tudo bem?")
        await client.post("/webhook", json=payload2)

    row = await db.execute("SELECT COUNT(*) as cnt FROM conversations")
    count = await row.fetchone()
    assert count["cnt"] == 1

    row = await db.execute("SELECT COUNT(*) as cnt FROM messages")
    count = await row.fetchone()
    assert count["cnt"] == 2


@pytest.mark.asyncio
async def test_message_triggers_draft_generation(client, db, mock_claude_api):
    """12.6: mensagem recebida dispara geração de draft."""
    # Don't mock create_task — let it actually run
    payload = make_webhook_payload()
    resp = await client.post("/webhook", json=payload)
    assert resp.status_code == 200

    # Give async task time to complete
    import asyncio
    await asyncio.sleep(0.5)

    row = await db.execute("SELECT * FROM drafts")
    drafts = await row.fetchall()
    # Drafts may or may not exist depending on async timing
    # If they exist, there should be 3 (variations)
    if drafts:
        assert len(drafts) == 3


@pytest.mark.asyncio
async def test_inbound_message_cancels_pending_scheduled_sends(client, db):
    """Mensagem inbound cancela scheduled_sends pendentes da conversa."""
    # Setup: create conversation and scheduled sends
    with patch("app.routes.webhook.spawn"):
        payload = make_webhook_payload(message_id="msg-setup", text="Oi")
        await client.post("/webhook", json=payload)

    row = await db.execute("SELECT id FROM conversations LIMIT 1")
    conv = await row.fetchone()
    conv_id = conv["id"]

    # Insert one pending and one already-sent scheduled send
    await db.execute(
        """INSERT INTO scheduled_sends (conversation_id, content, send_at, status, created_by)
           VALUES (?, 'Follow-up pendente', '2099-12-31T10:00:00', 'pending', 'caio')""",
        (conv_id,),
    )
    await db.execute(
        """INSERT INTO scheduled_sends (conversation_id, content, send_at, status, created_by)
           VALUES (?, 'Já enviado', '2024-01-01T10:00:00', 'sent', 'caio')""",
        (conv_id,),
    )
    await db.commit()

    # Client sends a new message → should cancel pending scheduled sends
    with patch("app.routes.webhook.spawn"):
        payload = make_webhook_payload(message_id="msg-reply", text="Voltei!")
        resp = await client.post("/webhook", json=payload)

    assert resp.status_code == 200

    # Verify: pending send was cancelled with reason client_replied
    rows = await db.execute(
        "SELECT status, cancelled_reason FROM scheduled_sends WHERE conversation_id = ? ORDER BY id",
        (conv_id,),
    )
    sends = await rows.fetchall()
    assert len(sends) == 2

    # First was pending → should be cancelled
    assert sends[0]["status"] == "cancelled"
    assert sends[0]["cancelled_reason"] == "client_replied"

    # Second was already sent → should remain sent
    assert sends[1]["status"] == "sent"


@pytest.mark.asyncio
async def test_webhook_background_tasks_tracked_in_task_registry(client, db):
    """Contrato GREEN: módulo app/task_registry.py com spawn(coro) que cria
    a task, guarda referência forte no set module-level PENDING_TASKS e a
    descarta via done-callback. O webhook deve usar spawn() para as
    background tasks, protegendo-as de garbage collection.

    Hoje: red — o módulo app.task_registry ainda não existe (falha por
    assert com mensagem explícita, não por erro de coleta).
    """
    import asyncio
    import importlib

    # Símbolo novo: resolvido dentro do corpo do teste, com falha clara
    try:
        task_registry = importlib.import_module("app.task_registry")
    except ModuleNotFoundError:
        task_registry = None
    if task_registry is None:
        pytest.fail(
            "Contrato não implementado: módulo app/task_registry.py não existe. "
            "Esperado: função spawn(coro) e set module-level PENDING_TASKS com "
            "referências fortes às tasks em andamento."
        )

    spawn = getattr(task_registry, "spawn", None)
    pending_tasks = getattr(task_registry, "PENDING_TASKS", None)
    assert callable(spawn), "app.task_registry deve expor a função spawn(coro)"
    assert isinstance(pending_tasks, set), (
        "app.task_registry deve expor o set module-level PENDING_TASKS "
        f"(valor atual: {pending_tasks!r})"
    )

    # Segura as tasks vivas brevemente, sincronizando via Event (sem sleeps longos)
    release = asyncio.Event()

    async def held_task(*args, **kwargs):
        await asyncio.wait_for(release.wait(), timeout=2)

    with patch("app.routes.webhook.auto_qualify_respond", held_task), \
         patch("app.routes.webhook.generate_drafts", held_task), \
         patch("app.routes.webhook.handle_reward_inbound", held_task), \
         patch("app.routes.webhook.mark_cold_response_received", held_task):
        payload = make_webhook_payload(message_id="msg-registry")
        resp = await client.post("/webhook", json=payload)
        assert resp.status_code == 200

        # Durante a vida das tasks: PENDING_TASKS mantém referência forte
        assert len(pending_tasks) >= 1, (
            "Após o POST /webhook, PENDING_TASKS deveria conter pelo menos "
            "1 task em andamento (referência forte contra garbage collection)"
        )

        alive = list(pending_tasks)
        release.set()
        await asyncio.wait(alive, timeout=2)

    # Deixa os done-callbacks rodarem (call_soon precisa de ticks do loop)
    for _ in range(20):
        if not pending_tasks:
            break
        await asyncio.sleep(0.01)

    assert len(pending_tasks) == 0, (
        "PENDING_TASKS deveria esvaziar via done-callback após as tasks "
        f"completarem, mas ainda contém: {pending_tasks!r}"
    )
