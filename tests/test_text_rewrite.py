from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def make_rewrite_tool_response(text="Texto reescrito"):
    mock_response = MagicMock()
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "rewritten_text"
    tool_block.input = {"text": text}
    mock_response.content = [tool_block]
    return mock_response


@pytest.fixture
def mock_rewrite_api():
    with patch("app.services.text_rewrite.anthropic.AsyncAnthropic") as mock:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=make_rewrite_tool_response(
                "Oi Maria, então o curso tem 12 módulos e você vai ter acesso por 1 ano. O preço está R$ 997, mas dá para parcelar em 12x."
            )
        )
        mock.return_value = mock_client
        yield mock_client


# --- Endpoint tests ---


@pytest.mark.asyncio
async def test_rewrite_success(client, db, mock_rewrite_api):
    # Create a conversation
    await db.execute(
        "INSERT INTO conversations (phone_number, contact_name) VALUES (?, ?)",
        ("5511999999999", "Maria"),
    )
    await db.commit()

    res = await client.post(
        "/conversations/1/rewrite",
        json={"text": "oi maria, entao o curso ele tem 12 modulos e vc vai ter acesso por 1 ano"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "text" in data
    assert "módulos" in data["text"]

    # Verify Haiku was called
    mock_rewrite_api.messages.create.assert_called_once()
    call_kwargs = mock_rewrite_api.messages.create.call_args.kwargs
    assert call_kwargs["tools"][0]["name"] == "rewritten_text"
    assert call_kwargs["tool_choice"]["name"] == "rewritten_text"


@pytest.mark.asyncio
async def test_rewrite_conversation_not_found(client, db, mock_rewrite_api):
    res = await client.post(
        "/conversations/99999/rewrite",
        json={"text": "qualquer coisa"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_rewrite_empty_text(client, db, mock_rewrite_api):
    # Create a conversation
    await db.execute(
        "INSERT INTO conversations (phone_number, contact_name) VALUES (?, ?)",
        ("5511999999999", "Maria"),
    )
    await db.commit()

    res = await client.post(
        "/conversations/1/rewrite",
        json={"text": ""},
    )
    # Pydantic validation: empty string is still a valid string,
    # but we can test that the API handles it
    # (RewriteRequest accepts any string, empty included)
    assert res.status_code == 200 or res.status_code == 422


# --- Unit test for rewrite_text function ---


@pytest.mark.asyncio
async def test_rewrite_text_function():
    with patch("app.services.text_rewrite.anthropic.AsyncAnthropic") as mock:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=make_rewrite_tool_response("Texto polido e correto.")
        )
        mock.return_value = mock_client

        from app.services.text_rewrite import rewrite_text

        result = await rewrite_text("texto rascunhado rapido com erros")

        assert result == "Texto polido e correto."
        mock_client.messages.create.assert_called_once()

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "rewritten_text" in call_kwargs["tools"][0]["name"]
        assert call_kwargs["tool_choice"] == {"type": "tool", "name": "rewritten_text"}
        assert call_kwargs["messages"][0]["content"] == "texto rascunhado rapido com erros"
        assert "WhatsApp" in call_kwargs["system"]


@pytest.mark.asyncio
async def test_rewrite_text_fallback_to_text_block():
    """If LLM doesn't use tool_use, fallback to text block."""
    mock_response = MagicMock()
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "  Texto via fallback  "
    mock_response.content = [text_block]

    with patch("app.services.text_rewrite.anthropic.AsyncAnthropic") as mock:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock.return_value = mock_client

        from app.services.text_rewrite import rewrite_text

        result = await rewrite_text("algo")
        assert result == "Texto via fallback"
