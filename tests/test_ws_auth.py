import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.auth import COOKIE_NAME, create_session_cookie


@pytest.mark.asyncio
async def test_ws_rejects_without_cookie():
    """WebSocket should be rejected when password is set and no cookie."""
    from app.main import websocket_endpoint

    ws = AsyncMock()
    ws.cookies = {}

    with patch("app.main.validate_session_cookie", return_value=False):
        await websocket_endpoint(ws)

    ws.close.assert_called_once_with(code=4401)


@pytest.mark.asyncio
async def test_ws_accepts_with_valid_cookie():
    """WebSocket should be accepted with valid session cookie."""
    from app.main import websocket_endpoint

    ws = AsyncMock()
    ws.cookies = {COOKIE_NAME: "valid-cookie"}
    ws.receive_text = AsyncMock(side_effect=Exception("disconnect"))

    mock_connect = AsyncMock()
    with patch("app.main.validate_session_cookie", return_value=True), \
         patch("app.main.manager") as mock_manager:
        mock_manager.connect = mock_connect
        mock_manager.disconnect = MagicMock()
        try:
            await websocket_endpoint(ws)
        except Exception:
            pass

    ws.close.assert_not_called()
    mock_connect.assert_called_once_with(ws)


@pytest.mark.asyncio
async def test_ws_allows_when_no_password():
    """WebSocket should be accessible when no password configured."""
    from app.main import websocket_endpoint

    ws = AsyncMock()
    ws.cookies = {}
    ws.receive_text = AsyncMock(side_effect=Exception("disconnect"))

    mock_connect = AsyncMock()
    with patch("app.main.validate_session_cookie", return_value=True), \
         patch("app.main.manager") as mock_manager:
        mock_manager.connect = mock_connect
        mock_manager.disconnect = MagicMock()
        try:
            await websocket_endpoint(ws)
        except Exception:
            pass

    ws.close.assert_not_called()
    mock_connect.assert_called_once_with(ws)
