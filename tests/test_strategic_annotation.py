import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

os.environ.setdefault("EVOLUTION_API_URL", "http://localhost:8080")
os.environ.setdefault("EVOLUTION_API_KEY", "test-key")
os.environ.setdefault("EVOLUTION_INSTANCE", "test-instance")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("DATABASE_PATH", ":memory:")

from app.services.strategic_annotation import generate_annotation, ANNOTATION_PROMPT


@pytest.mark.asyncio
async def test_annotation_for_edited_message():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.close = AsyncMock()

    with patch("app.services.strategic_annotation.anthropic.AsyncAnthropic") as mock_anthropic, \
         patch("app.services.strategic_annotation.get_db", return_value=mock_db), \
         patch("app.services.strategic_annotation.index_edit_pair") as mock_index:

        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = [AsyncMock(text="IA recomendou curso direto. Operador voltou para qualificação.")]
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        await generate_annotation(
            edit_pair_id=1,
            customer_message="Quanto custa o curso?",
            original_draft="O CDO é R$2997",
            final_message="Me conta o que vc faz primeiro",
            was_edited=True,
            situation_summary="Primeiro contato, preço direto",
        )

        # Verify Haiku was called with correct prompt
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == ANNOTATION_PROMPT
        assert "editado" in call_kwargs["messages"][0]["content"]
        assert "Quanto custa o curso?" in call_kwargs["messages"][0]["content"]

        # Verify annotation was saved to DB
        mock_db.execute.assert_called()
        update_call = [c for c in mock_db.execute.call_args_list if "UPDATE edit_pairs" in str(c)]
        assert len(update_call) == 1

        # Verify indexed in ChromaDB
        mock_index.assert_called_once_with(
            edit_pair_id=1,
            situation_summary="Primeiro contato, preço direto",
            was_edited=True,
        )


@pytest.mark.asyncio
async def test_annotation_for_accepted_message():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.close = AsyncMock()

    with patch("app.services.strategic_annotation.anthropic.AsyncAnthropic") as mock_anthropic, \
         patch("app.services.strategic_annotation.get_db", return_value=mock_db), \
         patch("app.services.strategic_annotation.index_edit_pair"):

        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = [AsyncMock(text="Abordagem de ancoragem em ROI validada por aceitação.")]
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        await generate_annotation(
            edit_pair_id=2,
            customer_message="É caro",
            original_draft="Pensa assim: são R$10 por dia...",
            final_message="Pensa assim: são R$10 por dia...",
            was_edited=False,
            situation_summary="Objeção de preço após qualificação",
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "sem edição" in call_kwargs["messages"][0]["content"]


@pytest.mark.asyncio
async def test_annotation_failure_is_non_blocking():
    with patch("app.services.strategic_annotation.anthropic.AsyncAnthropic") as mock_anthropic, \
         patch("app.services.strategic_annotation.get_db") as mock_get_db:

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("API Error"))
        mock_anthropic.return_value = mock_client

        # Should not raise
        await generate_annotation(
            edit_pair_id=3,
            customer_message="Oi",
            original_draft="Oi!",
            final_message="Oi!",
            was_edited=False,
        )

        # DB should not have been called since annotation failed before
        mock_get_db.assert_not_called()


@pytest.mark.asyncio
async def test_annotation_without_situation_summary():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.close = AsyncMock()

    with patch("app.services.strategic_annotation.anthropic.AsyncAnthropic") as mock_anthropic, \
         patch("app.services.strategic_annotation.get_db", return_value=mock_db), \
         patch("app.services.strategic_annotation.index_edit_pair") as mock_index:

        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = [AsyncMock(text="Anotação sem summary.")]
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        await generate_annotation(
            edit_pair_id=4,
            customer_message="Oi",
            original_draft="Oi!",
            final_message="Fala!",
            was_edited=True,
            situation_summary=None,
        )

        # Should NOT index in ChromaDB without summary
        mock_index.assert_not_called()

        # But should still save annotation to DB
        mock_db.execute.assert_called()
