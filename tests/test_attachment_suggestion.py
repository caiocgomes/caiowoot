import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import make_draft_tool_response

os.environ.setdefault("EVOLUTION_API_URL", "http://localhost:8080")
os.environ.setdefault("EVOLUTION_API_KEY", "test-key")
os.environ.setdefault("EVOLUTION_INSTANCE", "test-instance")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("DATABASE_PATH", ":memory:")


# --- 8.1 Endpoint tests ---


@pytest.mark.asyncio
async def test_list_attachments_returns_filenames(client):
    """GET /api/attachments lists files from knowledge/attachments/."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        Path(tmpdir, "handbook-cdo.pdf").write_text("fake pdf")
        Path(tmpdir, "handbook-zero.pdf").write_text("fake pdf")

        with patch("app.routes.attachments.ATTACHMENTS_DIR", Path(tmpdir)):
            res = await client.get("/api/attachments")
            assert res.status_code == 200
            data = res.json()
            assert data == ["handbook-cdo.pdf", "handbook-zero.pdf"]


@pytest.mark.asyncio
async def test_serve_attachment_file(client):
    """GET /api/attachments/<filename> serves the file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, "handbook-cdo.pdf").write_bytes(b"fake pdf content")

        with patch("app.routes.attachments.ATTACHMENTS_DIR", Path(tmpdir)):
            res = await client.get("/api/attachments/handbook-cdo.pdf")
            assert res.status_code == 200
            assert b"fake pdf content" in res.content


@pytest.mark.asyncio
async def test_path_traversal_blocked(client):
    """GET /api/attachments/<filename> blocks path traversal."""
    res = await client.get("/api/attachments/..%2F..%2Fetc%2Fpasswd")
    assert res.status_code in (400, 404, 422)


@pytest.mark.asyncio
async def test_attachment_not_found(client):
    """GET /api/attachments/<filename> returns 404 for missing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.routes.attachments.ATTACHMENTS_DIR", Path(tmpdir)):
            res = await client.get("/api/attachments/nonexistent.pdf")
            assert res.status_code == 404


@pytest.mark.asyncio
async def test_list_attachments_requires_auth():
    """GET /api/attachments returns 401 without auth when password is set."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.config import settings

    original = settings.app_password
    settings.app_password = "test-pass"
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            res = await c.get("/api/attachments")
            assert res.status_code == 401
    finally:
        settings.app_password = original


# --- 8.2 Edit pair attachment_filename tests ---


@pytest.mark.asyncio
async def test_edit_pair_records_attachment_filename(db, client, mock_evolution_api):
    """attachment_filename gravado quando operador envia com anexo."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    # Create a draft so we can reference it
    await db.execute(
        """INSERT INTO drafts (conversation_id, trigger_message_id, draft_text, justification, draft_group_id, variation_index, approach, status)
           VALUES (1, 1, 'Draft text', 'justification', 'group-1', 0, 'direta', 'pending')"""
    )
    await db.commit()

    import io
    from httpx import AsyncClient

    files = {"file": ("handbook-cdo.pdf", io.BytesIO(b"fake pdf"), "application/pdf")}
    data = {
        "text": "Draft text",
        "draft_id": "1",
        "draft_group_id": "group-1",
        "selected_draft_index": "0",
        "regeneration_count": "0",
    }

    with patch("app.routes.messages.generate_annotation", new_callable=AsyncMock):
        res = await client.post("/conversations/1/send", data=data, files=files)

    assert res.status_code == 200

    row = await db.execute("SELECT attachment_filename FROM edit_pairs WHERE conversation_id = 1")
    ep = await row.fetchone()
    assert ep is not None
    assert ep["attachment_filename"] == "handbook-cdo.pdf"


@pytest.mark.asyncio
async def test_edit_pair_null_attachment_when_no_file(db, client, mock_evolution_api):
    """attachment_filename NULL quando sem anexo."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.execute(
        """INSERT INTO drafts (conversation_id, trigger_message_id, draft_text, justification, draft_group_id, variation_index, approach, status)
           VALUES (1, 1, 'Draft text', 'justification', 'group-1', 0, 'direta', 'pending')"""
    )
    await db.commit()

    data = {
        "text": "My custom message",
        "draft_id": "1",
        "draft_group_id": "group-1",
        "selected_draft_index": "0",
        "regeneration_count": "0",
    }

    with patch("app.routes.messages.generate_annotation", new_callable=AsyncMock):
        res = await client.post("/conversations/1/send", data=data)

    assert res.status_code == 200

    row = await db.execute("SELECT attachment_filename FROM edit_pairs WHERE conversation_id = 1")
    ep = await row.fetchone()
    assert ep is not None
    assert ep["attachment_filename"] is None


# --- 8.3 Draft engine tests ---


@pytest.mark.asyncio
async def test_extract_tool_response_with_attachment():
    """_extract_tool_response extrai suggested_attachment do tool_use."""
    from app.services.draft_engine import _extract_tool_response

    mock_response = make_draft_tool_response("Segue o handbook!", "Cliente pediu detalhes.", "handbook-cdo.pdf")

    draft, justification, suggested = _extract_tool_response(mock_response)
    assert draft == "Segue o handbook!"
    assert justification == "Cliente pediu detalhes."
    assert suggested == "handbook-cdo.pdf"


@pytest.mark.asyncio
async def test_extract_tool_response_null_attachment_when_absent():
    """_extract_tool_response retorna None quando suggested_attachment ausente."""
    from app.services.draft_engine import _extract_tool_response

    mock_response = make_draft_tool_response("Oi!", "Greeting.")

    draft, justification, suggested = _extract_tool_response(mock_response)
    assert suggested is None


@pytest.mark.asyncio
async def test_validate_suggested_attachment_existing_file():
    """Validação aceita arquivo existente."""
    from app.services.draft_engine import _validate_suggested_attachment

    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, "handbook-cdo.pdf").write_text("fake")
        with patch("app.services.draft_engine.ATTACHMENTS_DIR", Path(tmpdir)):
            assert _validate_suggested_attachment("handbook-cdo.pdf") == "handbook-cdo.pdf"


@pytest.mark.asyncio
async def test_validate_suggested_attachment_nonexistent_file():
    """Validação descarta arquivo inexistente."""
    from app.services.draft_engine import _validate_suggested_attachment

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.draft_engine.ATTACHMENTS_DIR", Path(tmpdir)):
            assert _validate_suggested_attachment("hallucinated.pdf") is None


@pytest.mark.asyncio
async def test_validate_suggested_attachment_none():
    """Validação retorna None para None."""
    from app.services.draft_engine import _validate_suggested_attachment
    assert _validate_suggested_attachment(None) is None


@pytest.mark.asyncio
async def test_attachments_section_in_prompt(db):
    """Seção 'Anexos disponíveis' aparece no prompt quando há arquivos."""
    from app.services.draft_engine import _build_prompt_parts

    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.commit()

    with patch("app.services.draft_engine.list_known_attachments", return_value=["handbook-cdo.pdf", "handbook-zero.pdf"]):
        user_content, _, _, _ = await _build_prompt_parts(db, 1)

    assert "## Anexos disponíveis" in user_content
    assert "handbook-cdo.pdf" in user_content
    assert "handbook-zero.pdf" in user_content


@pytest.mark.asyncio
async def test_no_attachments_section_when_empty(db):
    """Sem seção 'Anexos disponíveis' quando diretório vazio."""
    from app.services.draft_engine import _build_prompt_parts

    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.commit()

    with patch("app.services.draft_engine.list_known_attachments", return_value=[]):
        user_content, _, _, _ = await _build_prompt_parts(db, 1)

    assert "## Anexos disponíveis" not in user_content


# --- 8.4 Few-shot attachment tests ---


@pytest.mark.asyncio
async def test_fewshot_retrieval_includes_attachment(db):
    """Few-shot from retrieval inclui 'Anexo enviado:' quando presente."""
    from app.services.draft_engine import _build_fewshot_from_retrieval

    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        """INSERT INTO edit_pairs (conversation_id, customer_message, original_draft, final_message, was_edited, situation_summary, attachment_filename)
           VALUES (1, 'Me fala do CDO', 'O CDO é...', 'Segue o handbook', 1, 'Cliente pediu detalhes', 'handbook-cdo.pdf')"""
    )
    await db.commit()

    result = await _build_fewshot_from_retrieval(db, [1])
    assert "Anexo enviado: handbook-cdo.pdf" in result


@pytest.mark.asyncio
async def test_fewshot_retrieval_no_attachment_line_when_null(db):
    """Few-shot from retrieval sem 'Anexo enviado:' quando NULL."""
    from app.services.draft_engine import _build_fewshot_from_retrieval

    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        """INSERT INTO edit_pairs (conversation_id, customer_message, original_draft, final_message, was_edited, situation_summary)
           VALUES (1, 'Oi', 'Oi!', 'Fala!', 1, 'Primeiro contato')"""
    )
    await db.commit()

    result = await _build_fewshot_from_retrieval(db, [1])
    assert "Anexo enviado:" not in result


@pytest.mark.asyncio
async def test_fewshot_fallback_includes_attachment(db):
    """Few-shot fallback inclui 'Anexo enviado:' quando presente."""
    from app.services.draft_engine import _build_fewshot_fallback

    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        """INSERT INTO edit_pairs (conversation_id, customer_message, original_draft, final_message, was_edited, attachment_filename)
           VALUES (1, 'Quero o handbook', 'Claro!', 'Segue!', 1, 'handbook-zero-a-analista.pdf')"""
    )
    await db.commit()

    result = await _build_fewshot_fallback(db)
    assert "Anexo enviado: handbook-zero-a-analista.pdf" in result


@pytest.mark.asyncio
async def test_fewshot_fallback_no_attachment_line_when_null(db):
    """Few-shot fallback sem 'Anexo enviado:' quando NULL."""
    from app.services.draft_engine import _build_fewshot_fallback

    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        """INSERT INTO edit_pairs (conversation_id, customer_message, original_draft, final_message, was_edited)
           VALUES (1, 'Oi', 'Oi!', 'Fala!', 1)"""
    )
    await db.commit()

    result = await _build_fewshot_fallback(db)
    assert "Anexo enviado:" not in result


# --- 8.5 Strategic annotation tests ---


@pytest.mark.asyncio
async def test_annotation_includes_attachment_filename():
    """generate_annotation inclui attachment_filename no user content."""
    from app.services.strategic_annotation import generate_annotation

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.close = AsyncMock()

    with patch("app.services.strategic_annotation.anthropic.AsyncAnthropic") as mock_anthropic, \
         patch("app.services.strategic_annotation.get_db", return_value=mock_db), \
         patch("app.services.strategic_annotation.index_edit_pair"):

        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = [AsyncMock(text="Operador enviou handbook do CDO.")]
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        await generate_annotation(
            edit_pair_id=1,
            customer_message="Me conta do CDO",
            original_draft="O CDO é...",
            final_message="Segue o handbook!",
            was_edited=True,
            situation_summary="Cliente pediu detalhes do CDO",
            attachment_filename="handbook-cdo.pdf",
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        user_content = call_kwargs["messages"][0]["content"]
        assert "Operador anexou: handbook-cdo.pdf" in user_content


@pytest.mark.asyncio
async def test_annotation_no_attachment_when_none():
    """generate_annotation não inclui attachment quando None."""
    from app.services.strategic_annotation import generate_annotation

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.close = AsyncMock()

    with patch("app.services.strategic_annotation.anthropic.AsyncAnthropic") as mock_anthropic, \
         patch("app.services.strategic_annotation.get_db", return_value=mock_db), \
         patch("app.services.strategic_annotation.index_edit_pair"):

        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = [AsyncMock(text="Anotação normal.")]
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        await generate_annotation(
            edit_pair_id=2,
            customer_message="Oi",
            original_draft="Oi!",
            final_message="Fala!",
            was_edited=True,
            situation_summary="Primeiro contato",
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        user_content = call_kwargs["messages"][0]["content"]
        assert "Operador anexou:" not in user_content


# --- 8.6 suggested_attachment persistence tests ---


@pytest.mark.asyncio
async def test_suggested_attachment_persisted_in_drafts(db):
    """generate_drafts persists suggested_attachment to the drafts table."""
    from app.services.draft_engine import generate_drafts

    await db.execute(
        "INSERT INTO conversations (phone_number, contact_name) VALUES ('5511999999999', 'Maria')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Me manda o handbook')"
    )
    await db.commit()

    with patch("app.services.draft_engine.anthropic.AsyncAnthropic") as mock_api:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=[
            make_draft_tool_response("Segue o handbook!", "Cliente pediu.", "handbook-cdo.pdf"),
            make_draft_tool_response("Claro, vou enviar!", "Pedido direto.", None),
            make_draft_tool_response("Opa, mando já!", "Casual.", "handbook-cdo.pdf"),
        ])
        mock_api.return_value = mock_client

        with patch("app.services.draft_engine._validate_suggested_attachment", side_effect=lambda x: x):
            await generate_drafts(1, 1)

    rows = await db.execute(
        "SELECT variation_index, suggested_attachment FROM drafts WHERE conversation_id = 1 ORDER BY variation_index"
    )
    drafts = await rows.fetchall()
    assert len(drafts) == 3
    assert drafts[0]["suggested_attachment"] == "handbook-cdo.pdf"
    assert drafts[1]["suggested_attachment"] is None
    assert drafts[2]["suggested_attachment"] == "handbook-cdo.pdf"


@pytest.mark.asyncio
async def test_suggested_attachment_returned_in_pending_drafts(db, client):
    """GET /conversations/:id returns suggested_attachment in pending_drafts."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.execute(
        """INSERT INTO drafts (conversation_id, trigger_message_id, draft_text, justification,
           draft_group_id, variation_index, approach, status, suggested_attachment)
           VALUES (1, 1, 'Segue!', 'Pediu handbook', 'group-1', 0, 'direta', 'pending', 'handbook-cdo.pdf')"""
    )
    await db.execute(
        """INSERT INTO drafts (conversation_id, trigger_message_id, draft_text, justification,
           draft_group_id, variation_index, approach, status, suggested_attachment)
           VALUES (1, 1, 'Claro!', 'Consultiva', 'group-1', 1, 'consultiva', 'pending', NULL)"""
    )
    await db.commit()

    res = await client.get("/conversations/1")
    assert res.status_code == 200
    data = res.json()
    pending = data["pending_drafts"]
    assert len(pending) == 2
    assert pending[0]["suggested_attachment"] == "handbook-cdo.pdf"
    assert pending[1]["suggested_attachment"] is None


@pytest.mark.asyncio
async def test_regenerate_draft_persists_suggested_attachment(db):
    """regenerate_draft persists suggested_attachment when regenerating all drafts."""
    from app.services.draft_engine import regenerate_draft

    await db.execute(
        "INSERT INTO conversations (phone_number, contact_name) VALUES ('5511999999999', 'Maria')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) VALUES (1, 'msg-1', 'inbound', 'Me manda o handbook')"
    )
    # Create initial drafts so regenerate has a group to replace
    for i, approach in enumerate(["direta", "consultiva", "casual"]):
        await db.execute(
            """INSERT INTO drafts (conversation_id, trigger_message_id, draft_text, justification,
               draft_group_id, variation_index, approach, status)
               VALUES (1, 1, 'old draft', 'old', 'group-1', ?, ?, 'pending')""",
            (i, approach),
        )
    await db.commit()

    with patch("app.services.draft_engine.anthropic.AsyncAnthropic") as mock_api:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=[
            make_draft_tool_response("Novo draft 1", "Razão 1", "handbook-cdo.pdf"),
            make_draft_tool_response("Novo draft 2", "Razão 2", None),
            make_draft_tool_response("Novo draft 3", "Razão 3", "handbook-zero.pdf"),
        ])
        mock_api.return_value = mock_client

        with patch("app.services.draft_engine._validate_suggested_attachment", side_effect=lambda x: x):
            await regenerate_draft(1, 1)

    rows = await db.execute(
        "SELECT variation_index, suggested_attachment FROM drafts WHERE conversation_id = 1 ORDER BY variation_index"
    )
    drafts = await rows.fetchall()
    assert len(drafts) == 3
    assert drafts[0]["suggested_attachment"] == "handbook-cdo.pdf"
    assert drafts[1]["suggested_attachment"] is None
    assert drafts[2]["suggested_attachment"] == "handbook-zero.pdf"
