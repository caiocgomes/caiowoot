import pytest
from unittest.mock import AsyncMock, patch

from tests.conftest import make_draft_tool_response


@pytest.mark.asyncio
async def test_regenerate_single_draft(db, mock_claude_api):
    """15.4: POST /regenerate com draft_index=1 regenera apenas a variação 1."""
    from app.services.draft_engine import generate_drafts, regenerate_draft

    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) "
        "VALUES (1, 'msg-1', 'inbound', 'Quanto custa?')"
    )
    await db.commit()

    # Generate initial 3 drafts
    await generate_drafts(1, 1)

    # Verify 3 drafts exist
    row = await db.execute("SELECT * FROM drafts WHERE conversation_id = 1 ORDER BY variation_index")
    drafts = await row.fetchall()
    assert len(drafts) == 3
    original_texts = [d["draft_text"] for d in drafts]

    # Reset mock for regeneration call
    mock_claude_api.messages.create = AsyncMock(
        return_value=make_draft_tool_response("Nova resposta regenerada!", "Regenerada.")
    )

    # Regenerate only variation 1
    await regenerate_draft(1, 1, draft_index=1)

    # Verify variation 1 was updated, others unchanged
    row = await db.execute("SELECT * FROM drafts WHERE conversation_id = 1 AND status = 'pending' ORDER BY variation_index")
    updated_drafts = await row.fetchall()
    assert len(updated_drafts) == 3

    # Variation 0 unchanged
    assert updated_drafts[0]["draft_text"] == original_texts[0]
    # Variation 1 regenerated
    assert updated_drafts[1]["draft_text"] == "Nova resposta regenerada!"
    # Variation 2 unchanged
    assert updated_drafts[2]["draft_text"] == original_texts[2]

    # Only 1 Claude call for the regeneration
    assert mock_claude_api.messages.create.call_count == 1


@pytest.mark.asyncio
async def test_regenerate_all_drafts(db, mock_claude_api):
    """15.5: POST /regenerate com draft_index=null regenera todas as 3."""
    from app.services.draft_engine import generate_drafts, regenerate_draft

    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) "
        "VALUES (1, 'msg-1', 'inbound', 'Quanto custa?')"
    )
    await db.commit()

    # Generate initial 3 drafts
    await generate_drafts(1, 1)

    row = await db.execute("SELECT * FROM drafts WHERE conversation_id = 1 ORDER BY variation_index")
    original_drafts = await row.fetchall()
    assert len(original_drafts) == 3
    original_group_id = original_drafts[0]["draft_group_id"]

    # Reset mock for regeneration
    mock_claude_api.messages.create = AsyncMock(side_effect=[
        make_draft_tool_response("Regen direta", "R1"),
        make_draft_tool_response("Regen consultiva", "R2"),
        make_draft_tool_response("Regen casual", "R3"),
    ])

    # Regenerate all (draft_index=None)
    await regenerate_draft(1, 1, draft_index=None)

    # Verify 3 new drafts exist
    row = await db.execute("SELECT * FROM drafts WHERE conversation_id = 1 AND status = 'pending' ORDER BY variation_index")
    new_drafts = await row.fetchall()
    assert len(new_drafts) == 3

    # All texts are new
    assert new_drafts[0]["draft_text"] == "Regen direta"
    assert new_drafts[1]["draft_text"] == "Regen consultiva"
    assert new_drafts[2]["draft_text"] == "Regen casual"

    # Swap atômico: o grupo novo substitui o antigo, sem reusar o group_id
    assert new_drafts[0]["draft_group_id"] != original_group_id

    # 3 Claude calls for full regeneration
    assert mock_claude_api.messages.create.call_count == 3


# ───────────────────────── Contratos novos (refactor-velocidade) ─────────────────────────
# Regenerate-all com swap atômico de grupo, reuso de situation_summary armazenado
# e eventos WebSocket 'drafts_generating' / 'drafts_error'.

import asyncio  # noqa: E402

import app.websocket_manager as ws_module  # noqa: E402  (atributo manager é patchado pelo conftest)


async def _seed_conversation(db):
    """Cria a conversa 1 com uma mensagem inbound de id 1."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) "
        "VALUES (1, 'msg-1', 'inbound', 'Quanto custa?')"
    )
    await db.commit()


def _broadcast_payloads(broadcast_mock, event_type):
    """Extrai das chamadas ao mock de broadcast os payloads (dicts) do tipo pedido."""
    payloads = []
    for call in broadcast_mock.call_args_list:
        for arg in list(call.args) + list(call.kwargs.values()):
            if isinstance(arg, dict) and arg.get("type") == event_type:
                payloads.append(arg)
    return payloads


def _fresh_regen_responses():
    """Mock de messages.create com 3 respostas novas para um regenerate-all."""
    return AsyncMock(side_effect=[
        make_draft_tool_response("Regen direta", "R1"),
        make_draft_tool_response("Regen consultiva", "R2"),
        make_draft_tool_response("Regen casual", "R3"),
    ])


@pytest.mark.asyncio
async def test_regenerate_all_creates_new_group_id(db, mock_claude_api):
    """Swap atômico (a): regenerate-all gera os drafts novos com draft_group_id NOVO,
    diferente do grupo anterior — não reutiliza o group_id antigo."""
    from app.services.draft_engine import generate_drafts, regenerate_draft

    await _seed_conversation(db)
    await generate_drafts(1, 1)

    row = await db.execute(
        "SELECT DISTINCT draft_group_id FROM drafts WHERE conversation_id = 1 AND status = 'pending'"
    )
    old_groups = [r["draft_group_id"] for r in await row.fetchall()]
    assert len(old_groups) == 1
    old_group_id = old_groups[0]

    mock_claude_api.messages.create = _fresh_regen_responses()

    await regenerate_draft(1, 1, draft_index=None)

    row = await db.execute(
        "SELECT DISTINCT draft_group_id FROM drafts WHERE conversation_id = 1 AND status = 'pending'"
    )
    new_groups = [r["draft_group_id"] for r in await row.fetchall()]
    assert len(new_groups) == 1, "após regenerate-all deve haver exatamente 1 grupo pending"
    assert new_groups[0] != old_group_id, (
        "regenerate-all deve criar draft_group_id NOVO (swap atômico), não reutilizar o antigo"
    )

    row = await db.execute(
        "SELECT COUNT(*) AS cnt FROM drafts WHERE draft_group_id = ? AND status = 'pending'",
        (new_groups[0],),
    )
    assert (await row.fetchone())["cnt"] == 3


@pytest.mark.asyncio
async def test_regenerate_all_keeps_old_group_until_new_ready(db, mock_claude_api):
    """Swap atômico (b): enquanto a geração está em andamento, o grupo ANTIGO continua
    pending com 3 drafts (nada deletado); ao concluir, o antigo some e só o novo fica."""
    from app.services.draft_engine import generate_drafts, regenerate_draft

    await _seed_conversation(db)
    await generate_drafts(1, 1)

    row = await db.execute(
        "SELECT DISTINCT draft_group_id FROM drafts WHERE conversation_id = 1 AND status = 'pending'"
    )
    old_group_id = (await row.fetchone())["draft_group_id"]

    entrou_na_geracao = asyncio.Event()
    libera_geracao = asyncio.Event()

    async def haiku_bloqueado(*args, **kwargs):
        entrou_na_geracao.set()
        await asyncio.wait_for(libera_geracao.wait(), timeout=10)
        return ("Regen bloqueada", "R", None)

    with patch(
        "app.services.draft_engine._call_haiku",
        new_callable=AsyncMock,
        side_effect=haiku_bloqueado,
    ):
        task = asyncio.create_task(regenerate_draft(1, 1, draft_index=None))
        try:
            await asyncio.wait_for(entrou_na_geracao.wait(), timeout=5)
            # Durante a geração: SELECT na mesma conexão vê o estado intermediário.
            row = await db.execute(
                "SELECT COUNT(*) AS cnt FROM drafts WHERE draft_group_id = ? AND status = 'pending'",
                (old_group_id,),
            )
            pendentes_durante = (await row.fetchone())["cnt"]
        finally:
            # Libera sempre, para o task não ficar pendurado se um assert falhar.
            libera_geracao.set()
            await asyncio.wait_for(task, timeout=10)

    assert pendentes_durante == 3, (
        "o grupo antigo deve continuar pending com 3 drafts durante a geração "
        "(swap atômico) — foi deletado antes dos drafts novos ficarem prontos"
    )

    # Após concluir: grupo antigo sumiu, só o novo está pending com 3 drafts.
    row = await db.execute(
        "SELECT COUNT(*) AS cnt FROM drafts WHERE draft_group_id = ? AND status = 'pending'",
        (old_group_id,),
    )
    assert (await row.fetchone())["cnt"] == 0, "grupo antigo deveria ter sido removido após o swap"

    row = await db.execute(
        "SELECT DISTINCT draft_group_id FROM drafts WHERE conversation_id = 1 AND status = 'pending'"
    )
    grupos = [r["draft_group_id"] for r in await row.fetchall()]
    assert len(grupos) == 1 and grupos[0] != old_group_id

    row = await db.execute(
        "SELECT COUNT(*) AS cnt FROM drafts WHERE draft_group_id = ? AND status = 'pending'",
        (grupos[0],),
    )
    assert (await row.fetchone())["cnt"] == 3


@pytest.mark.asyncio
async def test_regenerate_all_concurrent_leaves_single_pending_group(db, mock_claude_api):
    """Swap atômico (c): dois regenerate-all concorrentes terminam com exatamente
    1 grupo pending contendo 3 drafts."""
    from app.services.draft_engine import generate_drafts, regenerate_draft

    await _seed_conversation(db)
    await generate_drafts(1, 1)

    chamadas = 0
    barreira = asyncio.Event()

    async def haiku_com_barreira(*args, **kwargs):
        nonlocal chamadas
        chamadas += 1
        if chamadas >= 6:
            barreira.set()
        try:
            # Segura cada chamada até as duas gerações estarem em voo ao mesmo tempo.
            # Timeout curto para não travar caso a implementação serialize os regenerates.
            await asyncio.wait_for(barreira.wait(), timeout=0.25)
        except asyncio.TimeoutError:
            pass
        return (f"Regen {chamadas}", "R", None)

    with patch(
        "app.services.draft_engine._call_haiku",
        new_callable=AsyncMock,
        side_effect=haiku_com_barreira,
    ):
        t1 = asyncio.create_task(regenerate_draft(1, 1, draft_index=None))
        t2 = asyncio.create_task(regenerate_draft(1, 1, draft_index=None))
        await asyncio.wait_for(asyncio.gather(t1, t2), timeout=15)

    row = await db.execute(
        "SELECT DISTINCT draft_group_id FROM drafts WHERE conversation_id = 1 AND status = 'pending'"
    )
    grupos = [r["draft_group_id"] for r in await row.fetchall()]
    assert len(grupos) == 1, (
        f"após dois regenerate-all concorrentes deve restar exatamente 1 grupo pending, "
        f"encontrados {len(grupos)}"
    )

    row = await db.execute(
        "SELECT COUNT(*) AS cnt FROM drafts WHERE draft_group_id = ? AND status = 'pending'",
        (grupos[0],),
    )
    assert (await row.fetchone())["cnt"] == 3, "o grupo pending final deve ter exatamente 3 drafts"


@pytest.mark.asyncio
async def test_regenerate_reuses_stored_summary(db, mock_claude_api):
    """Reuso de summary: com drafts.situation_summary armazenado, regenerate NÃO chama
    generate_situation_summary e propaga o summary armazenado; sem summary armazenado,
    gera normalmente (fallback)."""
    import app.services.draft_engine as draft_engine_module
    import app.services.prompt_builder as prompt_builder_module
    from app.services.draft_engine import regenerate_draft

    await _seed_conversation(db)

    pb_mock = prompt_builder_module.generate_situation_summary
    de_mock = draft_engine_module.generate_situation_summary

    # Fase 1 (fallback): sem nenhum draft/summary armazenado, o resumo deve ser gerado.
    await regenerate_draft(1, 1, draft_index=None)
    assert pb_mock.await_count + de_mock.await_count >= 1, (
        "sem summary armazenado, regenerate deve gerar o resumo (fallback)"
    )

    # Fase 2 (reuso): com summary armazenado, o resumo NÃO deve ser regenerado.
    await db.execute(
        "UPDATE drafts SET situation_summary = 'Resumo armazenado da conversa.' WHERE conversation_id = 1"
    )
    await db.commit()

    pb_mock.reset_mock()
    de_mock.reset_mock()
    ws_module.manager.broadcast.reset_mock()
    mock_claude_api.messages.create = _fresh_regen_responses()

    await regenerate_draft(1, 1, draft_index=None)

    pb_mock.assert_not_called()
    de_mock.assert_not_called()

    row = await db.execute(
        "SELECT DISTINCT situation_summary FROM drafts WHERE conversation_id = 1 AND status = 'pending'"
    )
    resumos = [r["situation_summary"] for r in await row.fetchall()]
    assert resumos == ["Resumo armazenado da conversa."], (
        "os drafts novos devem carregar o summary armazenado, não um recém-gerado"
    )

    prontos = _broadcast_payloads(ws_module.manager.broadcast, "drafts_ready")
    assert prontos, "broadcast drafts_ready esperado após o regenerate"
    assert prontos[-1]["situation_summary"] == "Resumo armazenado da conversa.", (
        "o broadcast deve usar o summary armazenado"
    )


@pytest.mark.asyncio
async def test_regenerate_single_reuses_stored_summary(db, mock_claude_api):
    """Reuso de summary também no regenerate de variação única (draft_index=1)."""
    import app.services.draft_engine as draft_engine_module
    import app.services.prompt_builder as prompt_builder_module
    from app.services.draft_engine import generate_drafts, regenerate_draft

    await _seed_conversation(db)
    await generate_drafts(1, 1)

    await db.execute(
        "UPDATE drafts SET situation_summary = 'Resumo armazenado da conversa.' WHERE conversation_id = 1"
    )
    await db.commit()

    pb_mock = prompt_builder_module.generate_situation_summary
    de_mock = draft_engine_module.generate_situation_summary
    pb_mock.reset_mock()
    de_mock.reset_mock()

    mock_claude_api.messages.create = AsyncMock(
        return_value=make_draft_tool_response("Nova variação 1", "Regenerada.")
    )

    await regenerate_draft(1, 1, draft_index=1)

    pb_mock.assert_not_called()
    de_mock.assert_not_called()

    row = await db.execute(
        "SELECT situation_summary FROM drafts "
        "WHERE conversation_id = 1 AND variation_index = 1 AND status = 'pending'"
    )
    draft = await row.fetchone()
    assert draft["situation_summary"] == "Resumo armazenado da conversa."


@pytest.mark.asyncio
async def test_regenerate_emits_drafts_generating_before_llm(db, mock_claude_api):
    """regenerate_draft emite 'drafts_generating' (com draft_index) ANTES da primeira
    chamada LLM de geração."""
    from app.services.draft_engine import generate_drafts, regenerate_draft

    await _seed_conversation(db)
    await generate_drafts(1, 1)

    ordem = []
    broadcast_mock = ws_module.manager.broadcast
    broadcast_mock.reset_mock()

    async def registra_broadcast(*args, **kwargs):
        for arg in list(args) + list(kwargs.values()):
            if isinstance(arg, dict) and arg.get("type") == "drafts_generating":
                ordem.append(("drafts_generating", arg))

    broadcast_mock.side_effect = registra_broadcast

    async def registra_llm(*args, **kwargs):
        ordem.append(("llm_call", None))
        return ("Variação regenerada", "R", None)

    with patch(
        "app.services.draft_engine._call_haiku",
        new_callable=AsyncMock,
        side_effect=registra_llm,
    ):
        await regenerate_draft(1, 1, draft_index=1)

    generating = [i for i, (tipo, _) in enumerate(ordem) if tipo == "drafts_generating"]
    llm_calls = [i for i, (tipo, _) in enumerate(ordem) if tipo == "llm_call"]

    assert generating, "evento 'drafts_generating' não foi emitido pelo regenerate_draft"
    assert llm_calls, "mock de _call_haiku não foi chamado"
    assert generating[0] < llm_calls[0], (
        "'drafts_generating' deve ser emitido antes da primeira chamada LLM"
    )

    payload = ordem[generating[0]][1]
    assert payload["conversation_id"] == 1
    assert payload["trigger_message_id"] == 1
    assert payload.get("draft_index") == 1


@pytest.mark.asyncio
async def test_regenerate_emits_drafts_error_on_exception(db, mock_claude_api):
    """Quando a geração levanta exceção, regenerate_draft emite 'drafts_error'
    com conversation_id, trigger_message_id e error (string)."""
    from app.services.draft_engine import generate_drafts, regenerate_draft

    await _seed_conversation(db)
    await generate_drafts(1, 1)

    broadcast_mock = ws_module.manager.broadcast
    broadcast_mock.reset_mock()

    with patch(
        "app.services.draft_engine._build_prompt_parts",
        new_callable=AsyncMock,
        side_effect=RuntimeError("falha simulada na geração"),
    ):
        await regenerate_draft(1, 1, draft_index=None)

    erros = _broadcast_payloads(broadcast_mock, "drafts_error")
    assert erros, "evento 'drafts_error' não foi emitido após exceção na geração"
    payload = erros[-1]
    assert payload["conversation_id"] == 1
    assert payload["trigger_message_id"] == 1
    assert isinstance(payload.get("error"), str) and payload["error"], (
        "o campo 'error' deve ser uma string não-vazia"
    )
