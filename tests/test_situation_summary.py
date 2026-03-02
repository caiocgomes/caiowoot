import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.situation_summary import generate_situation_summary, CLASSIFY_TOOL


def _make_tool_use_response(summary="Resumo.", product=None, stage=None):
    """Create a mock response with a tool_use content block."""
    mock_response = MagicMock()
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "classify_conversation"
    tool_block.input = {"summary": summary, "product": product, "stage": stage}
    mock_response.content = [tool_block]
    return mock_response


@pytest.mark.asyncio
async def test_generate_summary_calls_haiku():
    with patch("app.services.situation_summary.anthropic.AsyncAnthropic") as mock:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_tool_use_response(
                summary="Primeiro contato. Cliente viu vídeo e perguntou preço sem contexto.",
                product="curso-llm",
                stage="qualifying",
            )
        )
        mock.return_value = mock_client

        result = await generate_situation_summary(
            "Cliente: Quanto custa o curso?",
            contact_name="Maria",
        )

        assert result["summary"] == "Primeiro contato. Cliente viu vídeo e perguntou preço sem contexto."
        assert result["product"] == "curso-llm"
        assert result["stage"] == "qualifying"

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "Maria" in call_kwargs["messages"][0]["content"]
        assert "Quanto custa o curso?" in call_kwargs["messages"][0]["content"]
        assert call_kwargs["tool_choice"] == {"type": "tool", "name": "classify_conversation"}


@pytest.mark.asyncio
async def test_generate_summary_without_contact_name():
    with patch("app.services.situation_summary.anthropic.AsyncAnthropic") as mock:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_tool_use_response(summary="Primeiro contato genérico.")
        )
        mock.return_value = mock_client

        result = await generate_situation_summary("Cliente: Oi")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "Cliente:" not in call_kwargs["messages"][0]["content"].split("\n")[0]
        assert "Oi" in call_kwargs["messages"][0]["content"]


@pytest.mark.asyncio
async def test_generate_summary_null_product_stage():
    with patch("app.services.situation_summary.anthropic.AsyncAnthropic") as mock:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_tool_use_response(
                summary="Primeiro contato sem produto identificado.",
                product=None,
                stage=None,
            )
        )
        mock.return_value = mock_client

        result = await generate_situation_summary("Cliente: Oi")
        assert result["summary"] == "Primeiro contato sem produto identificado."
        assert result["product"] is None
        assert result["stage"] is None


@pytest.mark.asyncio
async def test_generate_summary_fallback_no_tool_block():
    """If response has no tool_use block, returns empty fallback."""
    with patch("app.services.situation_summary.anthropic.AsyncAnthropic") as mock:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Some plain text"
        mock_response.content = [text_block]
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock.return_value = mock_client

        result = await generate_situation_summary("Cliente: Oi")
        assert result["summary"] == ""
        assert result["product"] is None
        assert result["stage"] is None
