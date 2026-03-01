import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.auth import (
    create_session_cookie,
    validate_session_cookie,
    get_operator_from_request,
    COOKIE_NAME,
    reset_rate_limit,
)


# --- Auth tests (5.1) ---


class TestSessionCookieWithOperator:
    def test_cookie_with_operator(self):
        with patch("app.auth.settings") as s:
            s.app_password = "secret123"
            s.session_max_age = 3600
            s.operator_list = ["Caio", "João"]
            cookie = create_session_cookie(operator="Caio")
            assert validate_session_cookie(cookie) is True

    def test_cookie_without_operator_rejected_when_operators_configured(self):
        with patch("app.auth.settings") as s:
            s.app_password = "secret123"
            s.session_max_age = 3600
            s.operator_list = ["Caio", "João"]
            cookie = create_session_cookie()  # no operator
            assert validate_session_cookie(cookie) is False

    def test_cookie_without_operator_accepted_when_no_operators(self):
        with patch("app.auth.settings") as s:
            s.app_password = "secret123"
            s.session_max_age = 3600
            s.operator_list = []
            cookie = create_session_cookie()
            assert validate_session_cookie(cookie) is True


class TestGetOperatorFromRequest:
    def test_extracts_operator(self):
        with patch("app.auth.settings") as s:
            s.app_password = "secret123"
            s.session_max_age = 3600
            cookie = create_session_cookie(operator="João")
            request = MagicMock()
            request.cookies = {COOKIE_NAME: cookie}
            assert get_operator_from_request(request) == "João"

    def test_returns_none_without_operator(self):
        with patch("app.auth.settings") as s:
            s.app_password = "secret123"
            s.session_max_age = 3600
            cookie = create_session_cookie()
            request = MagicMock()
            request.cookies = {COOKIE_NAME: cookie}
            assert get_operator_from_request(request) is None

    def test_returns_none_without_cookie(self):
        with patch("app.auth.settings") as s:
            s.app_password = "secret123"
            s.session_max_age = 3600
            request = MagicMock()
            request.cookies = {}
            assert get_operator_from_request(request) is None


@pytest.fixture(autouse=True)
def _reset_rate():
    reset_rate_limit()
    yield
    reset_rate_limit()


@pytest.mark.asyncio
async def test_login_with_operator(client, db):
    with patch("app.routes.login.settings") as s, \
         patch("app.routes.login.check_password", return_value=True), \
         patch("app.routes.login.create_session_cookie", return_value="valid-cookie") as mock_create:
        s.session_max_age = 3600
        s.operator_list = ["Caio", "João"]
        resp = await client.post("/login", json={"password": "secret", "operator": "Caio"})
    assert resp.status_code == 200
    mock_create.assert_called_once_with(operator="Caio")


@pytest.mark.asyncio
async def test_login_without_operator_when_required(client, db):
    with patch("app.routes.login.settings") as s, \
         patch("app.routes.login.check_password", return_value=True):
        s.operator_list = ["Caio", "João"]
        resp = await client.post("/login", json={"password": "secret"})
    assert resp.status_code == 400
    assert "operador" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_with_invalid_operator(client, db):
    with patch("app.routes.login.settings") as s, \
         patch("app.routes.login.check_password", return_value=True):
        s.operator_list = ["Caio", "João"]
        resp = await client.post("/login", json={"password": "secret", "operator": "Inexistente"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login_without_operator_when_not_required(client, db):
    with patch("app.routes.login.settings") as s, \
         patch("app.routes.login.check_password", return_value=True), \
         patch("app.routes.login.create_session_cookie", return_value="valid-cookie") as mock_create:
        s.session_max_age = 3600
        s.operator_list = []
        resp = await client.post("/login", json={"password": "secret"})
    assert resp.status_code == 200
    mock_create.assert_called_once_with(operator=None)


# --- Message tests (5.2) ---


@pytest.mark.asyncio
async def test_sent_by_recorded_on_outbound(client, db, mock_evolution_api):
    await db.execute("INSERT INTO conversations (phone_number) VALUES ('5511999999999')")
    await db.commit()

    with patch("app.routes.messages.get_operator_from_request", return_value="Caio"):
        resp = await client.post("/conversations/1/send", data={"text": "Oi!"})

    assert resp.status_code == 200
    row = await db.execute("SELECT sent_by FROM messages WHERE conversation_id = 1 AND direction = 'outbound'")
    msg = await row.fetchone()
    assert msg["sent_by"] == "Caio"


@pytest.mark.asyncio
async def test_sent_by_null_without_operator(client, db, mock_evolution_api):
    await db.execute("INSERT INTO conversations (phone_number) VALUES ('5511999999999')")
    await db.commit()

    with patch("app.routes.messages.get_operator_from_request", return_value=None):
        resp = await client.post("/conversations/1/send", data={"text": "Oi!"})

    assert resp.status_code == 200
    row = await db.execute("SELECT sent_by FROM messages WHERE conversation_id = 1 AND direction = 'outbound'")
    msg = await row.fetchone()
    assert msg["sent_by"] is None


# --- Conversation list tests (5.3) ---


@pytest.mark.asyncio
async def test_last_responder_in_conversation_list(client, db):
    await db.execute("INSERT INTO conversations (phone_number) VALUES ('5511999999999')")
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, sent_by) VALUES (1, 'outbound', 'Oi!', 'João')"
    )
    await db.commit()

    resp = await client.get("/conversations")
    assert resp.status_code == 200
    convs = resp.json()
    assert len(convs) == 1
    assert convs[0]["last_responder"] == "João"


@pytest.mark.asyncio
async def test_last_responder_null_without_outbound(client, db):
    await db.execute("INSERT INTO conversations (phone_number) VALUES ('5511999999999')")
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content) VALUES (1, 'inbound', 'Oi')"
    )
    await db.commit()

    resp = await client.get("/conversations")
    assert resp.status_code == 200
    convs = resp.json()
    assert len(convs) == 1
    assert convs[0]["last_responder"] is None


@pytest.mark.asyncio
async def test_last_responder_picks_most_recent(client, db):
    await db.execute("INSERT INTO conversations (phone_number) VALUES ('5511999999999')")
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, sent_by, created_at) "
        "VALUES (1, 'outbound', 'Msg 1', 'Caio', '2024-01-01 10:00:00')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, sent_by, created_at) "
        "VALUES (1, 'outbound', 'Msg 2', 'João', '2024-01-01 11:00:00')"
    )
    await db.commit()

    resp = await client.get("/conversations")
    convs = resp.json()
    assert convs[0]["last_responder"] == "João"


# --- Operators endpoint ---


@pytest.mark.asyncio
async def test_get_operators(client, db):
    with patch("app.routes.login.settings") as s:
        s.operator_list = ["Caio", "João"]
        resp = await client.get("/api/operators")
    assert resp.status_code == 200
    assert resp.json()["operators"] == ["Caio", "João"]


@pytest.mark.asyncio
async def test_get_operators_empty(client, db):
    with patch("app.routes.login.settings") as s:
        s.operator_list = []
        resp = await client.get("/api/operators")
    assert resp.status_code == 200
    assert resp.json()["operators"] == []
