"""Off-loop: chamadas síncronas pesadas devem sair do thread do event loop.

Contrato (fase GREEN): retrieve_similar (ChromaDB), save_prompt (I/O de disco),
index_edit_pair (ChromaDB), update_metadata (ChromaDB) e a recompressão de
imagem de campanha (PIL, CPU-bound) rodam via asyncio.to_thread, nunca no
thread do event loop.

Padrão dos testes: o spy síncrono registra threading.get_ident() no momento da
chamada; o assert compara com o ident do thread do event loop (capturado no
corpo do teste async). Hoje tudo roda inline no loop, então todos ficam red.

Os spies são patchados NO MÓDULO CALL-SITE, por cima dos patches do conftest
quando existirem (o patch aplicado por último vence).
"""

import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_retrieve_similar_roda_fora_do_thread_do_loop(db):
    """build_prompt_parts deve executar retrieve_similar via asyncio.to_thread."""
    await db.execute(
        "INSERT INTO conversations (phone_number, contact_name) VALUES ('5511999999999', 'Maria')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) "
        "VALUES (1, 'msg-1', 'inbound', 'Oi, quero saber dos cursos')"
    )
    await db.commit()

    loop_ident = threading.get_ident()
    registrados = []

    def spy_retrieve(situation_summary, k=5):
        registrados.append(threading.get_ident())
        return []

    # Re-patch por cima do patch do conftest: o patch interno vence
    with patch("app.services.prompt_builder.retrieve_similar", new=spy_retrieve):
        from app.services.prompt_builder import build_prompt_parts

        await build_prompt_parts(db, 1)

    assert registrados, "retrieve_similar não foi chamado durante build_prompt_parts"
    assert registrados[0] != loop_ident, (
        "retrieve_similar rodou no thread do event loop; "
        "deveria rodar via asyncio.to_thread"
    )


@pytest.mark.asyncio
async def test_save_prompt_roda_fora_do_thread_do_loop(db, mock_claude_api):
    """generate_drafts deve executar save_prompt via asyncio.to_thread."""
    await db.execute(
        "INSERT INTO conversations (phone_number, contact_name) VALUES ('5511999999999', 'Maria')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) "
        "VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.commit()

    loop_ident = threading.get_ident()
    registrados = []

    def spy_save_prompt(prompt):
        registrados.append(threading.get_ident())
        return "testhash123"

    # Re-patch por cima do patch do conftest: o patch interno vence
    with patch("app.services.draft_engine.save_prompt", new=spy_save_prompt):
        from app.services.draft_engine import generate_drafts

        await generate_drafts(1, 1)

    assert registrados, "save_prompt não foi chamado durante generate_drafts"
    assert registrados[0] != loop_ident, (
        "save_prompt rodou no thread do event loop; deveria rodar via asyncio.to_thread"
    )


@pytest.mark.asyncio
async def test_index_edit_pair_roda_fora_do_thread_do_loop():
    """generate_annotation deve executar index_edit_pair via asyncio.to_thread."""
    loop_ident = threading.get_ident()
    registrados = []

    def spy_index(**kwargs):
        registrados.append(threading.get_ident())

    mock_db = AsyncMock()
    mock_resposta = MagicMock()
    mock_resposta.content = [MagicMock(text="IA precificou cedo; operador requalificou.")]
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_resposta)

    with patch("app.services.strategic_annotation.get_anthropic_client", return_value=mock_client), \
         patch("app.services.strategic_annotation.get_db", return_value=mock_db), \
         patch("app.services.strategic_annotation.index_edit_pair", new=spy_index):
        from app.services.strategic_annotation import generate_annotation

        await generate_annotation(
            edit_pair_id=1,
            customer_message="Quanto custa?",
            original_draft="O CDO é R$2997",
            final_message="Me conta o que você faz primeiro",
            was_edited=True,
            situation_summary="Primeiro contato, preço direto",
        )

    assert registrados, "index_edit_pair não foi chamado durante generate_annotation"
    assert registrados[0] != loop_ident, (
        "index_edit_pair rodou no thread do event loop; "
        "deveria rodar via asyncio.to_thread"
    )


@pytest.mark.asyncio
async def test_update_metadata_roda_fora_do_thread_do_loop(client, db):
    """POST /review/{id}/validate deve executar update_metadata via asyncio.to_thread."""
    await db.execute("INSERT INTO conversations (phone_number) VALUES ('5511999999999')")
    cursor = await db.execute(
        """INSERT INTO edit_pairs
           (conversation_id, customer_message, original_draft, final_message, was_edited,
            situation_summary, strategic_annotation)
           VALUES (1, 'Quanto custa?', 'O CDO é R$2997', 'Me conta primeiro', 1,
                   'Primeiro contato', 'Anotação de teste')"""
    )
    ep_id = cursor.lastrowid
    await db.commit()

    loop_ident = threading.get_ident()
    registrados = []

    def spy_update(edit_pair_id, **kwargs):
        registrados.append(threading.get_ident())

    with patch("app.routes.review.update_metadata", new=spy_update):
        resp = await client.post(f"/review/{ep_id}/validate")

    assert resp.status_code == 200
    assert registrados, "update_metadata não foi chamado no fluxo de validação"
    assert registrados[0] != loop_ident, (
        "update_metadata rodou no thread do event loop; "
        "deveria rodar via asyncio.to_thread"
    )


@pytest.mark.asyncio
async def test_recompressao_de_imagem_roda_fora_do_thread_do_loop(db, tmp_path):
    """_send_one com image_path deve recomprimir a imagem via asyncio.to_thread.

    Contrato GREEN: existirá _recompress_image_sync executado via to_thread.
    Como o símbolo novo ainda não existe, o teste observa o comportamento:
    em qual thread PIL.Image.open é chamado durante o envio.
    """
    import PIL.Image
    from PIL import Image

    caminho_img = tmp_path / "campanha.jpg"
    Image.new("RGB", (8, 8), (200, 30, 30)).save(caminho_img, "JPEG")

    cursor = await db.execute(
        "INSERT INTO campaigns (name, base_message, status, min_interval, max_interval) "
        "VALUES ('Img', 'Oi', 'running', 60, 120)"
    )
    camp_id = cursor.lastrowid
    await db.execute(
        "INSERT INTO campaign_variations (campaign_id, variation_index, variation_text) "
        "VALUES (?, 0, 'Oi {{nome}}')",
        (camp_id,),
    )
    cursor = await db.execute(
        "INSERT INTO campaign_contacts (campaign_id, phone_number, name) "
        "VALUES (?, '5511999990001', 'João')",
        (camp_id,),
    )
    contact_id = cursor.lastrowid
    await db.commit()

    loop_ident = threading.get_ident()
    registrados = []
    open_real = PIL.Image.open

    def spy_open(*args, **kwargs):
        registrados.append(threading.get_ident())
        return open_real(*args, **kwargs)

    campanha = {"id": camp_id, "image_path": str(caminho_img)}
    contato = {
        "id": contact_id,
        "phone_number": "5511999990001",
        "name": "João",
        "variation_id": None,
    }

    with patch("PIL.Image.open", new=spy_open), \
         patch("app.services.campaign_executor.send_media_message", new_callable=AsyncMock), \
         patch("app.services.campaign_executor.manager") as mock_ws:
        mock_ws.broadcast = AsyncMock()
        from app.services.campaign_executor import _send_one

        ok = await _send_one(campanha, contato, db)

    assert ok is True, "envio de campanha com imagem falhou no setup do teste"
    assert registrados, "PIL.Image.open não foi chamado na recompressão da imagem"
    assert registrados[0] != loop_ident, (
        "recompressão de imagem (PIL) rodou no thread do event loop; "
        "deveria rodar via asyncio.to_thread"
    )
