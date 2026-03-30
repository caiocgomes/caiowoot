"""Playwright e2e test fixtures.

Spins up the real FastAPI app on a random port with a temporary SQLite DB
seeded with sample conversations, messages, and drafts.
"""

import os
import sqlite3
import tempfile
import threading
import time
import uuid

import pytest
import requests
import uvicorn

# Set env vars BEFORE importing app
os.environ["EVOLUTION_API_URL"] = "http://localhost:8080"
os.environ["EVOLUTION_API_KEY"] = "test-key"
os.environ["EVOLUTION_INSTANCE"] = "test-instance"
os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
os.environ["APP_PASSWORD"] = ""  # no auth required


def _seed_db(db_path: str) -> None:
    """Seed the database with sample data for e2e tests."""
    from app.database import SCHEMA

    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)

    # Conversation
    conn.execute(
        "INSERT INTO conversations (id, phone_number, contact_name, status, is_qualified, funnel_product, funnel_stage) "
        "VALUES (1, '5511999999999', 'Mabel Coelho', 'active', 1, 'curso-cdo', 'decided')"
    )

    # Inbound message
    conn.execute(
        "INSERT INTO messages (id, conversation_id, evolution_message_id, direction, content, created_at) "
        "VALUES (1, 1, 'evo-in-1', 'inbound', 'Oi, quero saber sobre o curso de CDO', '2026-03-29 10:40:00')"
    )

    # Outbound human message
    conn.execute(
        "INSERT INTO messages (id, conversation_id, evolution_message_id, direction, content, sent_by, created_at) "
        "VALUES (2, 1, 'evo-out-1', 'outbound', 'Claro! O curso De Analista a CDO é focado em liderança de dados.', 'Caio', '2026-03-29 10:41:00')"
    )

    # Inbound reply
    conn.execute(
        "INSERT INTO messages (id, conversation_id, evolution_message_id, direction, content, created_at) "
        "VALUES (3, 1, 'evo-in-2', 'inbound', 'Qual o investimento?', '2026-03-29 10:42:00')"
    )

    # Outbound bot message
    conn.execute(
        "INSERT INTO messages (id, conversation_id, evolution_message_id, direction, content, sent_by, created_at) "
        "VALUES (4, 1, 'evo-out-2', 'outbound', 'O investimento é de R$4.997 à vista ou 12x de R$497.', 'bot', '2026-03-29 10:43:00')"
    )

    # Pending drafts (3 variations)
    group_id = str(uuid.uuid4())
    for i, (approach, text, justification) in enumerate([
        ("direct", "O investimento é R$4.997 à vista com desconto de 15%.", "Abordagem direta focando no preço."),
        ("consultive", "Antes de falar do investimento, me conta: qual sua experiência atual com dados?", "Abordagem consultiva para qualificar."),
        ("casual", "Opa! O valor é bem acessível, R$4.997 à vista. Quer que eu mande o handbook?", "Abordagem casual e amigável."),
    ]):
        conn.execute(
            "INSERT INTO drafts (conversation_id, trigger_message_id, draft_text, justification, status, "
            "draft_group_id, variation_index, approach, situation_summary) "
            "VALUES (1, 3, ?, ?, 'pending', ?, ?, ?, 'Lead interessado no curso CDO, perguntou sobre investimento.')",
            (text, justification, group_id, i, approach),
        )

    conn.commit()
    conn.close()


@pytest.fixture(scope="session")
def live_server():
    """Start the FastAPI app on a random port and yield the base URL."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp.name
    tmp.close()

    _seed_db(db_path)

    os.environ["DATABASE_PATH"] = db_path

    # Re-import app to pick up new DATABASE_PATH
    import importlib
    import app.config
    importlib.reload(app.config)
    import app.database
    importlib.reload(app.database)
    import app.main
    importlib.reload(app.main)

    the_app = app.main.app

    config = uvicorn.Config(
        the_app,
        host="127.0.0.1",
        port=0,  # random port
        log_level="warning",
    )
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server to be ready
    for _ in range(50):
        try:
            # Server exposes its port after startup
            if server.started:
                break
        except Exception:
            pass
        time.sleep(0.1)

    # Get the actual port
    sockets = server.servers[0].sockets if server.servers else []
    port = sockets[0].getsockname()[1] if sockets else 8002

    base_url = f"http://127.0.0.1:{port}"

    # Verify it's up
    for _ in range(20):
        try:
            r = requests.get(f"{base_url}/health", timeout=2)
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(0.2)

    yield base_url

    server.should_exit = True
    thread.join(timeout=5)

    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture(scope="session")
def browser_context_args():
    """Default browser context args for all tests."""
    return {"ignore_https_errors": True}


@pytest.fixture
def desktop_page(page):
    """Page with desktop viewport (1280x800)."""
    page.set_viewport_size({"width": 1280, "height": 800})
    return page


@pytest.fixture
def mobile_page(page):
    """Page with mobile viewport (390x844, iPhone 14 equivalent)."""
    page.set_viewport_size({"width": 390, "height": 844})
    return page
