import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from tests.conftest import *  # noqa: F401, F403


def _make_analysis_response(
    engagement_level="medium",
    sale_status="active",
    factual_issues=None,
    overall_assessment="Avaliação teste",
):
    return MagicMock(
        content=[
            MagicMock(
                text=json.dumps(
                    {
                        "factual_issues": factual_issues or [],
                        "engagement_level": engagement_level,
                        "engagement_notes": "Notas teste",
                        "sale_status": sale_status,
                        "recovery_potential": "none",
                        "recovery_suggestion": None,
                        "overall_assessment": overall_assessment,
                    },
                    ensure_ascii=False,
                )
            )
        ]
    )


@pytest.mark.asyncio
async def test_analyze_conversation_basic(db):
    """analyze_conversation collects messages, edit_pairs, and returns structured assessment."""
    # Setup: create conversation with messages and edit_pairs
    await db.execute("INSERT INTO conversations (phone_number, contact_name) VALUES ('5511999', 'Joao')")
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, sent_by) VALUES (1, 'inbound', 'Oi, quero saber do curso', NULL)"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, sent_by) VALUES (1, 'outbound', 'Ola Joao!', 'Miguel')"
    )
    await db.execute(
        """INSERT INTO edit_pairs (conversation_id, customer_message, original_draft, final_message, was_edited, selected_draft_index, regeneration_count)
           VALUES (1, 'Oi, quero saber do curso', 'Ola Joao!', 'Ola Joao!', 0, 0, 0)"""
    )
    await db.commit()

    mock_response = _make_analysis_response(
        engagement_level="low",
        overall_assessment="Miguel aceitou draft sem editar. Piloto automatico.",
    )

    with patch("app.services.conversation_analysis.get_anthropic_client") as mock_anthropic, \
         patch("app.services.conversation_analysis.load_knowledge_base", return_value="Curso X custa R$1000"):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        from app.services.conversation_analysis import analyze_conversation

        result = await analyze_conversation(db, 1, "Miguel", "2026-01-01", "2026-12-31")

    assert result["engagement_level"] == "low"
    assert result["operator_name"] == "Miguel"
    assert result["contact_name"] == "Joao"
    assert result["conversation_id"] == 1
    assert "draft_acceptance_rate" in result["metrics"]

    # Verify prompt includes knowledge base
    call_args = mock_client.messages.create.call_args
    system_blocks = call_args.kwargs["system"]
    assert any("Curso X custa R$1000" in block["text"] for block in system_blocks)

    # Verify prompt includes edit_pair data
    user_msg = call_args.kwargs["messages"][0]["content"]
    assert "Editou: não" in user_msg or "was_edited" in user_msg.lower() or "nao" in user_msg.lower()


@pytest.mark.asyncio
async def test_analyze_conversation_pilot_mode(db):
    """When all edit_pairs have was_edited=false, prompt includes pilot mode context."""
    await db.execute("INSERT INTO conversations (phone_number, contact_name) VALUES ('5511999', 'Maria')")
    for i in range(3):
        await db.execute(
            "INSERT INTO messages (conversation_id, direction, content, sent_by) VALUES (1, 'inbound', ?, NULL)",
            (f"Msg cliente {i}",),
        )
        await db.execute(
            "INSERT INTO messages (conversation_id, direction, content, sent_by) VALUES (1, 'outbound', ?, 'Miguel')",
            (f"Resposta {i}",),
        )
        await db.execute(
            """INSERT INTO edit_pairs (conversation_id, customer_message, original_draft, final_message, was_edited, selected_draft_index, regeneration_count)
               VALUES (1, ?, ?, ?, 0, 0, 0)""",
            (f"Msg cliente {i}", f"Resposta {i}", f"Resposta {i}"),
        )
    await db.commit()

    mock_response = _make_analysis_response(engagement_level="low")

    with patch("app.services.conversation_analysis.get_anthropic_client") as mock_anthropic, \
         patch("app.services.conversation_analysis.load_knowledge_base", return_value=""):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        from app.services.conversation_analysis import analyze_conversation

        result = await analyze_conversation(db, 1, "Miguel", "2026-01-01", "2026-12-31")

    assert result["metrics"]["draft_acceptance_rate"] == 100.0


@pytest.mark.asyncio
async def test_analyze_conversation_factual_error(db):
    """Assessment includes factual issues when LLM detects them."""
    await db.execute("INSERT INTO conversations (phone_number, contact_name) VALUES ('5511999', 'Pedro')")
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, sent_by) VALUES (1, 'inbound', 'Quanto custa?', NULL)"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, sent_by) VALUES (1, 'outbound', 'Custa R$500', 'Miguel')"
    )
    await db.commit()

    mock_response = _make_analysis_response(
        factual_issues=[
            {
                "message_excerpt": "Custa R$500",
                "claim": "Curso custa R$500",
                "knowledge_says": "Curso custa R$1000",
                "severity": "high",
            }
        ]
    )

    with patch("app.services.conversation_analysis.get_anthropic_client") as mock_anthropic, \
         patch("app.services.conversation_analysis.load_knowledge_base", return_value="Curso custa R$1000"):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        from app.services.conversation_analysis import analyze_conversation

        result = await analyze_conversation(db, 1, "Miguel", "2026-01-01", "2026-12-31")

    assert len(result["factual_issues"]) == 1
    assert result["factual_issues"][0]["severity"] == "high"


@pytest.mark.asyncio
async def test_analyze_conversation_no_edit_pairs(db):
    """Conversations without edit_pairs are still analyzed."""
    await db.execute("INSERT INTO conversations (phone_number, contact_name) VALUES ('5511999', 'Ana')")
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, sent_by) VALUES (1, 'inbound', 'Oi', NULL)"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, sent_by) VALUES (1, 'outbound', 'Ola!', 'Caio')"
    )
    await db.commit()

    mock_response = _make_analysis_response()

    with patch("app.services.conversation_analysis.get_anthropic_client") as mock_anthropic, \
         patch("app.services.conversation_analysis.load_knowledge_base", return_value=""):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        from app.services.conversation_analysis import analyze_conversation

        result = await analyze_conversation(db, 1, "Caio", "2026-01-01", "2026-12-31")

    assert result["metrics"]["draft_acceptance_rate"] is None

    # Verify prompt mentions lack of draft data
    user_msg = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "sem dados" in user_msg.lower() or "diretamente" in user_msg.lower()
