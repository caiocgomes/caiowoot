import json
import pytest
from unittest.mock import AsyncMock, patch

from app.services.situation_summary import generate_situation_summary, SUMMARY_PROMPT


@pytest.mark.asyncio
async def test_generate_summary_calls_haiku():
    with patch("app.services.situation_summary.anthropic.AsyncAnthropic") as mock:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = [
            AsyncMock(text="Primeiro contato. Cliente viu vídeo e perguntou preço sem contexto.")
        ]
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock.return_value = mock_client

        result = await generate_situation_summary(
            "Cliente: Quanto custa o curso?",
            contact_name="Maria",
        )

        assert result["summary"] == "Primeiro contato. Cliente viu vídeo e perguntou preço sem contexto."
        assert result["product"] is None  # plain text fallback
        assert result["stage"] is None

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == SUMMARY_PROMPT
        assert "Maria" in call_kwargs["messages"][0]["content"]
        assert "Quanto custa o curso?" in call_kwargs["messages"][0]["content"]
        assert call_kwargs["max_tokens"] == 256


@pytest.mark.asyncio
async def test_generate_summary_without_contact_name():
    with patch("app.services.situation_summary.anthropic.AsyncAnthropic") as mock:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = [AsyncMock(text="Primeiro contato genérico.")]
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock.return_value = mock_client

        result = await generate_situation_summary("Cliente: Oi")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "Cliente:" not in call_kwargs["messages"][0]["content"].split("\n")[0]
        assert "Oi" in call_kwargs["messages"][0]["content"]


@pytest.mark.asyncio
async def test_generate_summary_strips_whitespace():
    with patch("app.services.situation_summary.anthropic.AsyncAnthropic") as mock:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = [AsyncMock(text="  Resumo com espaços.  \n")]
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock.return_value = mock_client

        result = await generate_situation_summary("Cliente: Oi")
        assert result["summary"] == "Resumo com espaços."
